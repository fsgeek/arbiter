"""Block-pair evaluator — evaluates prompt block pairs against rules.

Two evaluation modes:
- Structural: Python predicates, no LLM call, no cost.
- LLM: uses the rule's prompt_template, returns JSON score + explanation.

Pre-filtering prunes the O(n^2 * R) space using rule metadata
(scope overlap, modality). The evaluator only runs on triples
that pass pre-filtering.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from pydantic import BaseModel, Field

from .interference_tensor import InterferenceTensor, TensorEntry
from .prompt_blocks import PromptBlock, Severity
from .rules import CompiledRuleSet, EvaluationRule


class BlockScore(BaseModel):
    """Result of evaluating one block pair against one rule."""

    block_a: str = Field(description="Block A ID")
    block_b: str = Field(description="Block B ID")
    rule: str = Field(description="Rule name")
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str | None = None


def _extract_json(text: str) -> str:
    """Extract JSON from a response that may be wrapped in markdown code fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


# ---------------------------------------------------------------------------
# Structural evaluators (Python predicates, no LLM)
# ---------------------------------------------------------------------------

_PRIORITY_MARKERS = re.compile(
    r"\b(IMPORTANT|CRITICAL|MUST|NEVER|ALWAYS|REQUIRED)\b", re.IGNORECASE
)


def _evaluate_priority_marker_ambiguity(
    block_a: PromptBlock, block_b: PromptBlock
) -> float:
    """Structural check: do both blocks use priority markers?

    Score based on how many markers each block uses. High scores when
    both blocks use multiple markers on potentially competing instructions.
    """
    markers_a = set(_PRIORITY_MARKERS.findall(block_a.text.upper()))
    markers_b = set(_PRIORITY_MARKERS.findall(block_b.text.upper()))

    if not markers_a or not markers_b:
        return 0.0

    # Shared markers suggest competing priority claims
    shared = markers_a & markers_b
    if not shared:
        return 0.1  # Different markers, mild ambiguity

    # Both use the same priority markers — higher ambiguity
    return min(0.3 + 0.1 * len(shared), 1.0)


def _evaluate_verbatim_duplication(
    block_a: PromptBlock, block_b: PromptBlock
) -> float:
    """Structural check: how similar are the two blocks' text?

    Uses SequenceMatcher ratio. Returns high score for near-identical text.
    """
    ratio = SequenceMatcher(None, block_a.text, block_b.text).ratio()
    if ratio < 0.5:
        return 0.0
    # Scale: 0.5 similarity → 0.0 score, 1.0 similarity → 1.0 score
    return (ratio - 0.5) * 2.0


_STRUCTURAL_EVALUATORS: dict[str, callable] = {
    "priority-marker-ambiguity": _evaluate_priority_marker_ambiguity,
    "verbatim-duplication": _evaluate_verbatim_duplication,
}


# ---------------------------------------------------------------------------
# Block evaluator
# ---------------------------------------------------------------------------


class BlockEvaluator:
    """Evaluates block pairs against rules.

    Handles both structural (Python predicate) and LLM-based evaluation.
    Pre-filters block pairs using rule metadata to avoid unnecessary work.
    """

    def __init__(self, structural_only: bool = False) -> None:
        """Initialize the evaluator.

        Args:
            structural_only: If True, skip LLM rules entirely.
                Useful for testing and for cheap first-pass analysis.
        """
        self._structural_only = structural_only

    def evaluate_pair_structural(
        self, block_a: PromptBlock, block_b: PromptBlock, rule: EvaluationRule
    ) -> BlockScore | None:
        """Evaluate a block pair using a structural rule.

        Returns None if no structural evaluator exists for this rule.
        """
        evaluator_fn = _STRUCTURAL_EVALUATORS.get(rule.name)
        if evaluator_fn is None:
            return None

        score = evaluator_fn(block_a, block_b)
        explanation = None
        if score > 0:
            explanation = f"Structural check: {rule.name}"

        return BlockScore(
            block_a=block_a.id,
            block_b=block_b.id,
            rule=rule.name,
            score=score,
            severity=rule.severity,
            explanation=explanation,
        )

    def parse_llm_score(
        self,
        raw: str,
        block_a: PromptBlock,
        block_b: PromptBlock,
        rule: EvaluationRule,
    ) -> BlockScore:
        """Parse an LLM evaluation response into a BlockScore.

        Exposed as a separate method so callers can use any LLM backend
        and just pass the raw response text.
        """
        extracted = _extract_json(raw)

        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            # LLM didn't return parseable JSON — score as uncertain
            return BlockScore(
                block_a=block_a.id,
                block_b=block_b.id,
                rule=rule.name,
                score=0.5,
                severity=rule.severity,
                explanation=f"Unparseable LLM response: {raw[:200]}",
            )

        score = float(data.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        explanation = data.get("explanation")

        return BlockScore(
            block_a=block_a.id,
            block_b=block_b.id,
            rule=rule.name,
            score=score,
            severity=rule.severity,
            explanation=explanation,
        )

    def build_llm_prompt(
        self, block_a: PromptBlock, block_b: PromptBlock, rule: EvaluationRule
    ) -> str | None:
        """Build the LLM prompt for evaluating a block pair.

        Returns None if the rule is structural (no LLM needed).
        """
        if not rule.requires_llm or rule.prompt_template is None:
            return None
        return rule.prompt_template.format(
            block_a_text=block_a.text,
            block_b_text=block_b.text,
        )

    def evaluate_all_structural(
        self,
        blocks: list[PromptBlock],
        rule_set: CompiledRuleSet,
    ) -> list[BlockScore]:
        """Evaluate all structural rules on all applicable block pairs.

        This is the cheap first pass — no LLM calls, runs in milliseconds.
        """
        scores = []
        for block_a, block_b, rule in rule_set.applicable_pairs(blocks):
            if not rule.requires_llm:
                result = self.evaluate_pair_structural(block_a, block_b, rule)
                if result is not None and result.score > 0:
                    scores.append(result)
        return scores

    def pending_llm_evaluations(
        self,
        blocks: list[PromptBlock],
        rule_set: CompiledRuleSet,
    ) -> list[tuple[PromptBlock, PromptBlock, EvaluationRule, str]]:
        """Return all (block_a, block_b, rule, prompt) tuples needing LLM evaluation.

        Callers use this to batch LLM calls through their preferred backend.
        """
        if self._structural_only:
            return []

        pending = []
        for block_a, block_b, rule in rule_set.applicable_pairs(blocks):
            if rule.requires_llm:
                prompt = self.build_llm_prompt(block_a, block_b, rule)
                if prompt is not None:
                    pending.append((block_a, block_b, rule, prompt))
        return pending

    def assemble_tensor(
        self,
        blocks: list[PromptBlock],
        rule_set: CompiledRuleSet,
        scores: list[BlockScore],
        *,
        threshold: float = 0.0,
    ) -> InterferenceTensor:
        """Assemble an InterferenceTensor from evaluation scores."""
        block_ids = [b.id for b in blocks]
        rule_names = [r.name for r in rule_set.rules]

        entries = [
            TensorEntry(
                block_a=s.block_a,
                block_b=s.block_b,
                rule=s.rule,
                score=s.score,
                severity=s.severity,
                explanation=s.explanation,
            )
            for s in scores
        ]

        return InterferenceTensor.from_scores(
            block_ids=block_ids,
            rule_names=rule_names,
            entries=entries,
            threshold=threshold,
        )
