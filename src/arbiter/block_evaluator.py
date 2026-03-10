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

from .decision_policy import DeterministicDecisionPolicy
from .interference_tensor import (
    AdjudicationDecision,
    DrafterIdentity,
    InterferenceTensor,
    TensorDeclaredLoss,
    TensorEntry,
    TensorEntryV2,
)
from .prompt_blocks import PromptBlock, Severity, Tier
from .rules import CompiledRuleSet, EvaluationRule


class BlockScore(BaseModel):
    """Result of evaluating one block pair against one rule."""

    block_a: str = Field(description="Block A ID")
    block_b: str = Field(description="Block B ID")
    rule: str = Field(description="Rule name")
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str | None = None
    # Extended adjudication channels
    t: float | None = Field(default=None, ge=0.0, le=1.0)
    i: float | None = Field(default=None, ge=0.0, le=1.0)
    f: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_quality: float | None = Field(default=None, ge=0.0, le=1.0)
    declared_losses: list[TensorDeclaredLoss] = Field(default_factory=list)
    decision: AdjudicationDecision | None = None
    drafter_identity: DrafterIdentity = DrafterIdentity.unknown


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

    def __init__(
        self,
        structural_only: bool = False,
        decision_policy: DeterministicDecisionPolicy | None = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            structural_only: If True, skip LLM rules entirely.
                Useful for testing and for cheap first-pass analysis.
        """
        self._structural_only = structural_only
        self._decision_policy = decision_policy or DeterministicDecisionPolicy()
        self._parse_stats: dict[str, int] = {
            "llm_responses_total": 0,
            "json_parse_fail": 0,
            "optional_t_present": 0,
            "optional_i_present": 0,
            "optional_f_present": 0,
            "optional_evidence_quality_present": 0,
            "optional_declared_losses_present": 0,
            "optional_decision_present": 0,
            "optional_drafter_identity_present": 0,
            "malformed_declared_losses": 0,
        }

    @staticmethod
    def _default_tif(score: float, evidence_quality: float) -> tuple[float, float, float]:
        """Fallback deterministic T/I/F mapping."""
        f_val = score
        i_val = 1.0 - evidence_quality
        t_val = max(0.0, 1.0 - max(f_val, i_val))
        return t_val, i_val, f_val

    @staticmethod
    def _safe_tier(block: PromptBlock) -> Tier | None:
        """Return a block tier if available."""
        return getattr(block, "tier", None)

    def reset_parseability_stats(self) -> None:
        """Reset parseability counters."""
        for key in self._parse_stats:
            self._parse_stats[key] = 0

    def parseability_report(self) -> dict[str, float | int]:
        """Return parseability counters and rates for optional v2 fields."""
        total = self._parse_stats["llm_responses_total"]
        report: dict[str, float | int] = dict(self._parse_stats)
        if total > 0:
            report.update(
                {
                    "json_parse_fail_rate": self._parse_stats["json_parse_fail"] / total,
                    "optional_t_rate": self._parse_stats["optional_t_present"] / total,
                    "optional_i_rate": self._parse_stats["optional_i_present"] / total,
                    "optional_f_rate": self._parse_stats["optional_f_present"] / total,
                    "optional_evidence_quality_rate": (
                        self._parse_stats["optional_evidence_quality_present"] / total
                    ),
                    "optional_declared_losses_rate": (
                        self._parse_stats["optional_declared_losses_present"] / total
                    ),
                    "optional_decision_rate": (
                        self._parse_stats["optional_decision_present"] / total
                    ),
                    "optional_drafter_identity_rate": (
                        self._parse_stats["optional_drafter_identity_present"] / total
                    ),
                    "malformed_declared_losses_rate": (
                        self._parse_stats["malformed_declared_losses"] / total
                    ),
                }
            )
        else:
            report.update(
                {
                    "json_parse_fail_rate": 0.0,
                    "optional_t_rate": 0.0,
                    "optional_i_rate": 0.0,
                    "optional_f_rate": 0.0,
                    "optional_evidence_quality_rate": 0.0,
                    "optional_declared_losses_rate": 0.0,
                    "optional_decision_rate": 0.0,
                    "optional_drafter_identity_rate": 0.0,
                    "malformed_declared_losses_rate": 0.0,
                }
            )
        return report

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
        t_val, i_val, f_val = self._default_tif(score, evidence_quality=0.7)

        return BlockScore(
            block_a=block_a.id,
            block_b=block_b.id,
            rule=rule.name,
            score=score,
            severity=rule.severity,
            explanation=explanation,
            t=t_val,
            i=i_val,
            f=f_val,
            evidence_quality=0.7,
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
        self._parse_stats["llm_responses_total"] += 1

        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            # LLM didn't return parseable JSON — score as uncertain
            self._parse_stats["json_parse_fail"] += 1
            t_val, i_val, f_val = self._default_tif(0.5, evidence_quality=0.3)
            return BlockScore(
                block_a=block_a.id,
                block_b=block_b.id,
                rule=rule.name,
                score=0.5,
                severity=rule.severity,
                explanation=f"Unparseable LLM response: {raw[:200]}",
                t=t_val,
                i=i_val,
                f=f_val,
                evidence_quality=0.3,
            )

        score = float(data.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        explanation = data.get("explanation")
        evidence_quality = float(data.get("evidence_quality", 0.6))
        evidence_quality = max(0.0, min(1.0, evidence_quality))

        t_val = data.get("t")
        i_val = data.get("i")
        f_val = data.get("f")
        if t_val is not None:
            self._parse_stats["optional_t_present"] += 1
        if i_val is not None:
            self._parse_stats["optional_i_present"] += 1
        if f_val is not None:
            self._parse_stats["optional_f_present"] += 1
        if t_val is None or i_val is None or f_val is None:
            t_val, i_val, f_val = self._default_tif(score, evidence_quality)
        else:
            t_val = max(0.0, min(1.0, float(t_val)))
            i_val = max(0.0, min(1.0, float(i_val)))
            f_val = max(0.0, min(1.0, float(f_val)))

        losses_raw = data.get("declared_losses", [])
        if "declared_losses" in data:
            self._parse_stats["optional_declared_losses_present"] += 1
        declared_losses: list[TensorDeclaredLoss] = []
        if isinstance(losses_raw, list):
            for item in losses_raw:
                if not isinstance(item, dict):
                    self._parse_stats["malformed_declared_losses"] += 1
                    continue
                what = item.get("what")
                why = item.get("why")
                if not isinstance(what, str) or not isinstance(why, str):
                    self._parse_stats["malformed_declared_losses"] += 1
                    continue
                try:
                    severity = float(item.get("severity", 0.5))
                except (TypeError, ValueError):
                    self._parse_stats["malformed_declared_losses"] += 1
                    severity = 0.5
                declared_losses.append(
                    TensorDeclaredLoss(
                        what=what,
                        why=why,
                        severity=max(0.0, min(1.0, severity)),
                    )
                )

        decision_raw = data.get("decision")
        decision = None
        if isinstance(decision_raw, str):
            self._parse_stats["optional_decision_present"] += 1
            try:
                decision = AdjudicationDecision(decision_raw)
            except ValueError:
                decision = None

        drafter_identity_raw = data.get("drafter_identity")
        drafter_identity = DrafterIdentity.unknown
        if isinstance(drafter_identity_raw, str):
            self._parse_stats["optional_drafter_identity_present"] += 1
            try:
                drafter_identity = DrafterIdentity(drafter_identity_raw)
            except ValueError:
                drafter_identity = DrafterIdentity.unknown

        if "evidence_quality" in data:
            self._parse_stats["optional_evidence_quality_present"] += 1

        return BlockScore(
            block_a=block_a.id,
            block_b=block_b.id,
            rule=rule.name,
            score=score,
            severity=rule.severity,
            explanation=explanation,
            t=t_val,
            i=i_val,
            f=f_val,
            evidence_quality=evidence_quality,
            declared_losses=declared_losses,
            decision=decision,
            drafter_identity=drafter_identity,
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

        entries_v2 = []
        for score in scores:
            t_val = score.t
            i_val = score.i
            f_val = score.f
            evidence_quality = score.evidence_quality if score.evidence_quality is not None else 0.6
            if t_val is None or i_val is None or f_val is None:
                t_val, i_val, f_val = self._default_tif(score.score, evidence_quality)
            block_a = next((b for b in blocks if b.id == score.block_a), None)
            block_b = next((b for b in blocks if b.id == score.block_b), None)
            scope_tags = sorted(
                set((block_a.scope if block_a else []) + (block_b.scope if block_b else []))
            )
            entry_v2 = TensorEntryV2(
                block_a=score.block_a,
                block_b=score.block_b,
                rule=score.rule,
                score=score.score,
                severity=score.severity,
                explanation=score.explanation,
                t=t_val,
                i=i_val,
                f=f_val,
                tier_a=self._safe_tier(block_a) if block_a else None,
                tier_b=self._safe_tier(block_b) if block_b else None,
                scope_tags=scope_tags,
                canon_tags=[score.rule],
                drafter_identity=score.drafter_identity,
                evidence_quality=evidence_quality,
                declared_losses=list(score.declared_losses),
                decision=score.decision,
            )
            if entry_v2.decision is None:
                entry_v2.decision = self._decision_policy.decide(entry_v2)
            entries_v2.append(entry_v2)

        filtered_entries = [e for e in entries if e.score > threshold]
        filtered_entries_v2 = [e for e in entries_v2 if e.score > threshold]

        return InterferenceTensor(
            schema_version=2,
            block_ids=block_ids,
            rule_names=rule_names,
            entries=filtered_entries,
            entries_v2=filtered_entries_v2,
            migration_notes=[],
        )
