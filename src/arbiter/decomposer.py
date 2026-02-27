"""LLM-based prompt decomposer — breaks prompt blobs into classified blocks.

The decomposer is scope-guided: it uses the rule set's interests to
focus the LLM on dimensions that matter for evaluation. If the rules
only care about tool-usage and task-management, the decomposer focuses
on those dimensions.

Uses the existing evaluator backends (Anthropic, OpenAI-compatible) for
the LLM call. The model selection happens upstream via the registry.
"""

from __future__ import annotations

import json
import re

from .prompt_blocks import (
    BlockCategory,
    Modality,
    PromptBlock,
    Tier,
)
from .rules import CompiledRuleSet


class DecompositionError(Exception):
    """Raised when the LLM returns unparseable decomposition output."""


# The decomposition prompt. The LLM produces a JSON array of blocks.
_DECOMPOSE_PROMPT = """\
You are a system prompt analyst. Your task is to decompose a system prompt \
into contiguous blocks and classify each one.

## Classification Schema

### Tier (which layer of the system this block belongs to)
- system: Core identity and invariant rules. The constitution.
- domain: Contextual knowledge, domain-specific guidance. May conflict.
- application: Per-query or per-session context. Untrusted input.

### Category (what kind of block this is)
- identity: Who/what the agent is
- behavioral-constraint: Rules governing behavior
- tool-definition: Tool descriptions and usage instructions
- workflow: Multi-step processes and procedures
- policy: Security, safety, content policies
- context: Environmental info, user preferences, session state
- meta: Instructions about instructions (formatting, framing)

### Modality (deontic modality of directives)
- prohibition: "never", "do not", "must not"
- mandate: "always", "must", "required"
- permission: "may", "can", "allowed"
- definition: Declarative, no directive force
- mixed: Block contains multiple modalities

## Scope Dimensions of Interest

{scope_guidance}

## Task

Break the following system prompt into contiguous, non-overlapping blocks. \
Each block should be a coherent unit that establishes one or more behavioral \
contracts. Classify each block using the schema above.

For each block, identify:
- scope: What aspects of behavior this block constrains (list of strings)
- exports: Behavioral contracts this block establishes (list of strings)
- imports: Contracts this block depends on from other blocks (list of strings)

## System Prompt to Decompose

{prompt_text}

## Output Format

Respond with a JSON array only. No explanation outside the JSON.

[
  {{
    "id": "<source>/<short-descriptive-name>",
    "tier": "<system|domain|application>",
    "category": "<category>",
    "text": "<the exact text of this block>",
    "modality": "<modality>",
    "scope": ["<scope1>", "<scope2>"],
    "exports": ["<export1>"],
    "imports": ["<import1>"],
    "line_start": <int or null>,
    "line_end": <int or null>
  }}
]"""


def _extract_json(text: str) -> str:
    """Extract JSON from a response that may be wrapped in markdown code fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class Decomposer:
    """LLM-based prompt decomposer.

    Takes a prompt blob and produces a list of classified PromptBlocks.
    The decomposition is guided by the rule set — the LLM is told what
    scope dimensions to look for.
    """

    def __init__(self, rule_set: CompiledRuleSet) -> None:
        self._rule_set = rule_set

    def _build_scope_guidance(self) -> str:
        """Derive scope guidance from the rule set for the decomposer prompt."""
        lines = []
        for rule in self._rule_set.rules:
            lines.append(f"- {rule.name}: {rule.description}")
        if not lines:
            return "No specific scope guidance — classify all dimensions."
        return (
            "The evaluation rules care about these interference patterns. "
            "Pay attention to blocks that could trigger them:\n" + "\n".join(lines)
        )

    def build_prompt(self, prompt_text: str) -> str:
        """Build the decomposition prompt. Exposed for testing."""
        return _DECOMPOSE_PROMPT.format(
            scope_guidance=self._build_scope_guidance(),
            prompt_text=prompt_text,
        )

    def parse_response(self, raw: str, source: str) -> list[PromptBlock]:
        """Parse a decomposition response into PromptBlocks.

        Exposed as a separate method so callers can use any LLM backend
        (Anthropic, OpenAI-compatible, etc.) and just pass the raw response.
        """
        extracted = _extract_json(raw)

        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as e:
            raise DecompositionError(
                f"Decomposer returned unparseable response.\n"
                f"Raw response: {raw[:500]!r}\n"
                f"Parse error: {e}"
            ) from e

        if not isinstance(data, list):
            raise DecompositionError(
                f"Expected JSON array, got {type(data).__name__}"
            )

        blocks = []
        for i, item in enumerate(data):
            try:
                block = PromptBlock(
                    id=item.get("id", f"{source}/block-{i}"),
                    source=source,
                    tier=Tier(item["tier"]),
                    category=BlockCategory(item["category"]),
                    text=item["text"],
                    modality=Modality(item["modality"]),
                    scope=item.get("scope", []),
                    exports=item.get("exports", []),
                    imports=item.get("imports", []),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                )
                blocks.append(block)
            except (KeyError, ValueError) as e:
                raise DecompositionError(
                    f"Block {i} failed validation: {e}\n"
                    f"Block data: {item!r}"
                ) from e

        return blocks
