"""Automatic probe generation from PromptBlocks.

Given a block from a decomposed system prompt, generates a Probe that
can detect whether the block's instruction is being followed. This is
the missing piece that turns Arbiter from a research tool (hand-authored
probes for one specific prompt) into a diagnostic tool (point at any
prompt, get an ablation map).

The generator uses an LLM to create naturalistic user messages and
scoring rubrics. It does NOT make API calls directly — it produces
prompts that the caller runs through LLMCaller.

Scoring method selection heuristic:
    - Prohibition blocks → not_contains (check absence of violation patterns)
    - Format/style blocks → not_contains or length
    - Mandate blocks with concrete outputs → contains (check presence)
    - Complex behavioral blocks → llm_judge (needs LLM to evaluate)
"""

from __future__ import annotations

import json
import re
from typing import Any

from .probe import Probe


# ---------------------------------------------------------------------------
# Scoring method selection
# ---------------------------------------------------------------------------

def _select_scoring_method(
    modality: str,
    category: str,
    text: str,
) -> str:
    """Select the best scoring method based on block properties.

    Returns one of: "not_contains", "contains", "length", "llm_judge".
    """
    text_lower = text.lower()

    # Length/conciseness instructions always use length scoring
    if any(w in text_lower for w in ["concise", "brief", "short", "terse", "succinct"]):
        return "length"

    # Prohibitions are best tested by checking absence
    if modality == "prohibition":
        return "not_contains"

    # Format/style mandates with concrete markers
    if category in ("format", "tone", "style"):
        if any(w in text_lower for w in ["emoji", "colon", "markdown"]):
            return "not_contains"

    # Mandates with enumerable expected outputs
    if modality == "mandate":
        if any(w in text_lower for w in [
            "must include", "always use", "format as", "respond with",
        ]):
            return "contains"

    # Default: complex behavioral instructions need LLM judge
    return "llm_judge"


# ---------------------------------------------------------------------------
# Generation prompt
# ---------------------------------------------------------------------------

_GENERATION_PROMPT = """\
You are generating a behavioral probe for an ablation experiment on LLM system prompts.

A probe tests whether a model follows a specific instruction from its system prompt.
The probe consists of a user message that naturally triggers the instruction, plus
a scoring rubric.

## The instruction block to test

Block ID: {block_id}
Category: {category}
Modality: {modality} (mandate = must do, prohibition = must not do, mixed = both)
Scope: {scope}

Text:
{block_text}

## Scoring method assigned: {scoring_method}

{scoring_guidance}

## Requirements

1. **User message**: Write a natural, plausible user request that would trigger this
   instruction. The message should NOT mention the instruction itself — it should create
   a situation where the model must decide whether to follow or violate the instruction.
   Keep it 1-3 sentences. Make it specific enough that there's a clear right/wrong behavior.

2. **Expected behavior**: One sentence describing what a compliant response looks like.

3. **Violation indicator**: One sentence describing what a non-compliant response looks like.

4. **Scoring params**: {scoring_params_guidance}

## Output format

Respond with ONLY a JSON object:
{{
    "user_message": "...",
    "expected_behavior": "...",
    "violation_indicator": "...",
    "scoring_params": {scoring_params_schema}
}}
"""

_SCORING_GUIDANCE = {
    "not_contains": (
        "The `not_contains` method checks that the response does NOT contain specific "
        "patterns. Score is 1.0 if none are found, 0.0 if all are found.",
        "Provide a `patterns` list of 8-15 strings or simple regex patterns that would "
        "indicate violation of the instruction. Cast a wide net — false negatives "
        "(missing a violation) are worse than false positives here. Include common "
        "variations and synonyms.",
        '{"patterns": ["pattern1", "pattern2", "..."]}'
    ),
    "contains": (
        "The `contains` method checks that the response DOES contain specific patterns. "
        "Score is the fraction of patterns found.",
        "Provide a `patterns` list of 3-6 strings or regex patterns that would indicate "
        "compliance with the instruction. Use patterns that are specific enough to avoid "
        "false matches but general enough to catch reasonable variations.",
        '{"patterns": ["pattern1", "pattern2", "..."], "mode": "any"}'
    ),
    "length": (
        "The `length` method scores inversely proportional to response length. "
        "Score = 1.0 - (length / (multiplier * baseline_length)), clamped to [0, 1].",
        "Provide `baseline_length` (expected character count for a compliant response) "
        "and `multiplier` (how many times baseline before score hits 0, default 3.0). "
        "Be realistic about what a concise response looks like for this specific question.",
        '{"baseline_length": 300, "multiplier": 3.0}'
    ),
    "llm_judge": (
        "The `llm_judge` method sends the response to a separate LLM for evaluation. "
        "The judge sees only the expected behavior, violation indicator, and the response.",
        "No scoring_params needed for llm_judge — the expected_behavior and "
        "violation_indicator fields are the rubric. Make them specific and unambiguous.",
        '{}'
    ),
}


def build_generation_prompt(
    block_id: str,
    block_text: str,
    category: str,
    modality: str,
    scope: str,
    scoring_method: str,
) -> str:
    """Build the LLM prompt for generating a probe.

    Args:
        block_id: The block's identifier.
        block_text: The instruction text.
        category: Block category (e.g., "tone", "workflow", "tool-policy").
        modality: Block modality ("mandate", "prohibition", "mixed").
        scope: Block scope description.
        scoring_method: Pre-selected scoring method.

    Returns:
        A prompt string to send to the LLM.
    """
    guidance, params_guidance, params_schema = _SCORING_GUIDANCE[scoring_method]

    return _GENERATION_PROMPT.format(
        block_id=block_id,
        block_text=block_text,
        category=category,
        modality=modality,
        scope=scope,
        scoring_method=scoring_method,
        scoring_guidance=guidance,
        scoring_params_guidance=params_guidance,
        scoring_params_schema=params_schema,
    )


# ---------------------------------------------------------------------------
# Parse LLM response into Probe
# ---------------------------------------------------------------------------

def parse_generated_probe(
    llm_response: str,
    block_id: str,
    scoring_method: str,
    probe_index: int = 1,
) -> Probe:
    """Parse an LLM-generated probe from JSON response.

    Args:
        llm_response: Raw LLM output (should contain a JSON object).
        block_id: The target block ID.
        scoring_method: The pre-selected scoring method.
        probe_index: Index for generating probe ID (default 1).

    Returns:
        A Probe instance.

    Raises:
        ValueError: If the response can't be parsed into a valid probe.
    """
    # Strip markdown code fences if present
    cleaned = llm_response.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        # Remove closing fence
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    # Extract JSON from response — find the outermost {...} block
    # Use a bracket-counting approach to handle nested objects
    start = cleaned.find("{")
    if start == -1:
        raise ValueError(
            f"No JSON object found in LLM response: {llm_response[:200]}"
        )

    depth = 0
    end = start
    in_string = False
    escape_next = False
    for i in range(start, len(cleaned)):
        c = cleaned[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            escape_next = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    json_str = cleaned[start:end]
    if not json_str or json_str == cleaned[start:start]:
        # Bracket counter didn't find a complete object — response truncated.
        # Try to repair by closing open braces.
        json_str = cleaned[start:]
        # Close any open braces
        open_braces = json_str.count("{") - json_str.count("}")
        if open_braces > 0:
            # Truncate at last complete value and close
            # Find last comma or complete value
            last_quote = json_str.rfind('"')
            if last_quote > 0:
                # Truncate after last complete string value
                after = json_str[last_quote + 1:].lstrip()
                if after and after[0] == ":":
                    # We're mid-key:value — drop the incomplete entry
                    last_comma = json_str[:last_quote].rfind(",")
                    if last_comma > 0:
                        json_str = json_str[:last_comma]
                json_str += "}" * open_braces

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}") from e

    # Validate required fields
    for field in ("user_message", "expected_behavior", "violation_indicator"):
        if field not in data or not data[field].strip():
            raise ValueError(f"Missing or empty field: {field}")

    # Build probe ID from block ID
    # claude-code/tone-emoji -> probe-tone-emoji-01
    short_id = block_id.split("/")[-1] if "/" in block_id else block_id
    probe_id = f"probe-{short_id}-{probe_index:02d}"

    scoring_params = data.get("scoring_params", {})
    if not isinstance(scoring_params, dict):
        scoring_params = {}

    return Probe(
        id=probe_id,
        target_block=block_id,
        user_message=data["user_message"].strip(),
        scoring_method=scoring_method,
        expected_behavior=data["expected_behavior"].strip(),
        violation_indicator=data["violation_indicator"].strip(),
        scoring_params=scoring_params,
    )


# ---------------------------------------------------------------------------
# Batch generation — the main entry point
# ---------------------------------------------------------------------------

def generate_probes_for_blocks(
    blocks: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    """Build generation prompts for a list of blocks.

    Does NOT make API calls. Returns (block_id, prompt) pairs for the
    caller to run through LLMCaller.

    Args:
        blocks: List of dicts with keys: id, text, category, modality, scope.
            (Matches PromptBlock fields.)

    Returns:
        List of (block_id, generation_prompt) tuples. Caller should run
        each prompt through an LLM, then pass the response to
        parse_generated_probe().
    """
    prompts = []

    for block in blocks:
        block_id = block["id"]
        text = block["text"]
        category = block.get("category", "unknown")
        modality = block.get("modality", "mixed")
        scope = block.get("scope", "unknown")

        scoring_method = _select_scoring_method(modality, category, text)

        prompt = build_generation_prompt(
            block_id=block_id,
            block_text=text,
            category=category,
            modality=modality,
            scope=scope,
            scoring_method=scoring_method,
        )

        prompts.append((block_id, scoring_method, prompt))

    return prompts
