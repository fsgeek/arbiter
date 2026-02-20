"""Conflict evaluator — the engine of the three-tier Arbiter framework.

Architecture
------------
EvaluatorProtocol defines the interface. Callers depend only on this.
AnthropicEvaluator is the default implementation.

The evaluation prompt uses observer framing: the LLM acts as a neutral judge
examining instructions for internal consistency, not as the executor of those
instructions. This framing bypasses the executor/observer paradox where models
comply with violations when in executor role but detect them in observer role.

Conflict detection precedes resolution. If conflicts exist, the evaluator
surfaces them and does not attempt to resolve the query. This is the
core Arbiter guarantee: fail loudly rather than confabulate silently.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from .models import ConflictReport, DomainLayer, EvaluationResult, SystemLayer


class EvaluatorProtocol(Protocol):
    """Abstract interface for conflict evaluators.

    Implementations may differ in provider, model, evaluation strategy,
    or cost. Callers interact only with this interface.
    """

    def evaluate(
        self,
        system: SystemLayer,
        domain: DomainLayer,
        query: str,
        *,
        budget_usd: float | None = None,
    ) -> EvaluationResult: ...


_JUDGE_PROMPT = """\
You are a neutral evaluation judge for a query resolution system.

Your task: examine whether the domain knowledge contains conflicts that \
would prevent cleanly resolving the user query. Either surface the conflicts \
or resolve the query — never do both, never do neither.

## System Rules (invariant — the authority for this evaluation)

{system_rules}

## Domain Knowledge (contextual — may contain internal conflicts)

{domain_entries}

## User Query

{query}

## Instructions

1. Read all domain entries carefully.

2. Identify any entries that, together, create an unsatisfiable constraint \
for this specific query. A conflict exists when one entry recommends or \
requires something that another entry prohibits or contradicts, and both \
constraints apply to resolving this query.

3. If conflicts exist:
   - Set has_conflict to true
   - Describe each conflict: which entries conflict, what the contradiction is,
     and what information or change would resolve it
   - Leave output null — do not attempt to resolve the query

4. If no conflicts exist:
   - Set has_conflict to false
   - Resolve the query according to the system rules and domain knowledge
   - Provide the resolved output

Respond with valid JSON only. No explanation outside the JSON.

{{
  "has_conflict": <bool>,
  "conflicts": [
    {{
      "source": "<the domain entry that creates the conflict>",
      "target": "<the domain entry it conflicts with>",
      "description": "<what the contradiction is and why it affects this query>",
      "resolution_hint": "<what information or change would resolve this, or null>"
    }}
  ],
  "output": <string or null>
}}"""


def _extract_json(text: str) -> str:
    """Extract JSON from a response that may be wrapped in markdown code fences."""
    text = text.strip()
    # Handle ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class AnthropicEvaluator:
    """Evaluator backed by Anthropic's Claude models.

    Uses the cheapest capable model by default (Haiku). Pass a different
    model or use budget_usd to influence selection in future implementations.
    """

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
    ) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "Anthropic SDK required. Install with: uv sync --extra spike"
            ) from e
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def evaluate(
        self,
        system: SystemLayer,
        domain: DomainLayer,
        query: str,
        *,
        budget_usd: float | None = None,
    ) -> EvaluationResult:
        """Evaluate a query against system and domain layers.

        Returns an EvaluationResult with either resolved output or a list
        of conflicts. Never both. Raises ValueError if the LLM response
        cannot be parsed — fail-stop, no silent fallbacks.
        """
        system_rules = "\n".join(f"- {r}" for r in system.rules) or "(none)"
        domain_entries = (
            "\n".join(f"- {e}" for e in domain.entries) or "(none)"
        )

        prompt = _JUDGE_PROMPT.format(
            system_rules=system_rules,
            domain_entries=domain_entries,
            query=query,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text
        extracted = _extract_json(raw)

        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Evaluator returned unparseable response.\n"
                f"Raw response: {raw!r}\n"
                f"Parse error: {e}"
            ) from e

        conflicts = [
            ConflictReport(
                source=c["source"],
                target=c["target"],
                description=c["description"],
                resolution_hint=c.get("resolution_hint"),
            )
            for c in data.get("conflicts", [])
        ]

        return EvaluationResult(
            resolved=not data["has_conflict"],
            output=data.get("output"),
            conflicts=conflicts,
        )
