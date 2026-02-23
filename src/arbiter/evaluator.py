"""Conflict evaluator — the engine of the three-tier Arbiter framework.

Architecture
------------
EvaluatorProtocol defines the interface. Callers depend only on this.

Single-model evaluators:
  AnthropicEvaluator — Anthropic's Claude models (direct SDK)
  OpenAICompatibleEvaluator — any OpenAI-compatible endpoint

Multi-model evaluator:
  EnsembleEvaluator — runs multiple evaluators, merges results.
  OR-gate for detection (any evaluator flags → flagged),
  AND-gate for clean (all must agree → clean).

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

from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _parse_evaluation_response(raw: str) -> EvaluationResult:
    """Parse a JSON evaluation response into an EvaluationResult.

    Shared by all evaluator implementations. Fail-stop on unparseable
    responses — no silent fallbacks.
    """
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


def _build_prompt(system: SystemLayer, domain: DomainLayer, query: str) -> str:
    """Build the judge prompt from system/domain/query layers."""
    system_rules = "\n".join(f"- {r}" for r in system.rules) or "(none)"
    domain_entries = "\n".join(f"- {e}" for e in domain.entries) or "(none)"
    return _JUDGE_PROMPT.format(
        system_rules=system_rules,
        domain_entries=domain_entries,
        query=query,
    )


class OpenAICompatibleEvaluator:
    """Evaluator for any provider speaking the OpenAI chat completions API.

    Works with OpenRouter, OpenAI, Gemini, Qwen, xAI/Grok, Together,
    or any other OpenAI-compatible endpoint. Pass the model identifier
    and base URL for your provider.

    Examples:
        # OpenRouter (routes to any provider)
        OpenAICompatibleEvaluator(
            model="google/gemini-2.5-flash-preview",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )

        # OpenAI direct
        OpenAICompatibleEvaluator(
            model="gpt-4o-mini",
            api_key=os.environ["OPENAI_API_KEY"],
        )
    """

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "OpenAI SDK required. Install with: uv sync --extra openai-compat"
            ) from e
        kwargs: dict = {}
        if base_url is not None:
            kwargs["base_url"] = base_url
        if api_key is not None:
            kwargs["api_key"] = api_key
        if extra_headers is not None:
            kwargs["default_headers"] = extra_headers
        self._client = openai.OpenAI(**kwargs)
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
        prompt = _build_prompt(system, domain, query)

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content
        return _parse_evaluation_response(raw)


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
        prompt = _build_prompt(system, domain, query)

        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text
        return _parse_evaluation_response(raw)


class EnsembleEvaluator:
    """Multi-model evaluator that merges results from multiple backends.

    OR-gate for conflict detection: if any evaluator flags a conflict,
    the ensemble flags it. AND-gate for clean: all evaluators must agree
    the input is clean for the ensemble to resolve.

    This addresses the domain-dependent ranking problem: no single model
    is best across all domains. An ensemble of models with complementary
    domain strengths (e.g., Haiku for instruction compliance + Gemini for
    database schemas) catches conflicts that any single model misses.

    Evaluators run concurrently via ThreadPoolExecutor.
    """

    def __init__(self, evaluators: list[EvaluatorProtocol]) -> None:
        if not evaluators:
            raise ValueError("EnsembleEvaluator requires at least one evaluator")
        self._evaluators = evaluators

    def evaluate(
        self,
        system: SystemLayer,
        domain: DomainLayer,
        query: str,
        *,
        budget_usd: float | None = None,
    ) -> EvaluationResult:
        """Run all evaluators concurrently and merge results.

        Merge strategy:
        - If any evaluator detects conflicts, return unresolved with
          all unique conflicts collected from all evaluators.
        - If all evaluators agree clean, return the first evaluator's
          resolved output (arbitrary choice — all agreed it's clean).
        - If any evaluator raises, propagate the first exception.
        """
        results: list[EvaluationResult] = []

        with ThreadPoolExecutor(max_workers=len(self._evaluators)) as pool:
            futures = {
                pool.submit(ev.evaluate, system, domain, query, budget_usd=budget_usd): i
                for i, ev in enumerate(self._evaluators)
            }
            for future in as_completed(futures):
                results.append(future.result())

        all_conflicts: list[ConflictReport] = []
        any_unresolved = False
        first_output = None

        for result in results:
            if not result.resolved:
                any_unresolved = True
                all_conflicts.extend(result.conflicts)
            elif first_output is None:
                first_output = result.output

        if any_unresolved:
            # Deduplicate conflicts by (source, target) pair
            seen = set()
            unique = []
            for c in all_conflicts:
                key = (c.source, c.target)
                if key not in seen:
                    seen.add(key)
                    unique.append(c)
            return EvaluationResult(
                resolved=False,
                output=None,
                conflicts=unique,
            )

        return EvaluationResult(
            resolved=True,
            output=first_output,
            conflicts=[],
        )
