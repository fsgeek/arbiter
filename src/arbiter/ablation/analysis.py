"""Ablation analysis — derived analyses from the ablation tensor.

Classifies blocks using the four-category taxonomy (weight-aligned,
weight-compensating, weight-conflicting, weight-novel), detects
competition patterns (exploitation vs interference), and identifies
hidden suppressive interactions.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from .tensor import AblationScore, AblationTensor


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class BlockClassification(BaseModel):
    """Classification of a single block based on ablation evidence."""

    block_id: str
    category: Literal[
        "weight_aligned",
        "weight_compensating",
        "weight_conflicting",
        "weight_novel",
    ]
    evidence: str = Field(description="Why this classification was assigned")
    main_effect: float = Field(description="Mean |delta| across probes and models")
    interaction_count: int = Field(
        default=0,
        description="Number of significant pairwise interactions",
    )
    position_sensitive: bool = Field(default=False)
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Classification confidence (based on p-values, trial count)",
    )


class CompetitionPattern(BaseModel):
    """A detected competition pattern between blocks."""

    type: Literal["exploitation", "interference"]
    blocks: list[str] = Field(description="Block IDs involved")
    evidence: str
    tensor_signature: Literal["dense_row", "sparse_entry"] = Field(
        description="Whether this is a dense row (exploitation) or sparse entry (interference)"
    )


# ---------------------------------------------------------------------------
# Block classification
# ---------------------------------------------------------------------------


def classify_blocks(
    tensor: AblationTensor,
    baseline_adherence: dict[str, float],
    *,
    main_effect_threshold: float = 0.1,
    baseline_adherence_threshold: float = 0.5,
    position_delta_threshold: float = 0.1,
    interactions: dict[tuple[str, str], float] | None = None,
    interaction_significance: float = 0.1,
) -> list[BlockClassification]:
    """Classify each block using the four-category taxonomy.

    Categories:
    - weight_aligned: No main effect, no interactions. Safe to remove.
    - weight_compensating: No main effect, but has interactions. Looks dead
      but is load-bearing through its interactions with other blocks.
    - weight_conflicting: No delta under ablation, but probe shows
      non-adherence even at baseline. The instruction never worked.
    - weight_novel: Large main effect. The instruction actively shapes behavior.
      If position-sensitive, it's fragile (depends on context window position).

    Args:
        tensor: The assembled ablation tensor.
        baseline_adherence: Per-probe scores from baseline config. Maps
            probe_id -> mean baseline score. Used to detect weight-conflicting
            blocks (low adherence even with block present).
        main_effect_threshold: |delta| below this is "no main effect".
        baseline_adherence_threshold: Baseline score below this indicates
            the instruction isn't being followed even when present.
        position_delta_threshold: Position delta above this indicates
            position sensitivity.
        interactions: Pairwise interaction dict from tensor.pairwise_interactions().
            If None, interaction_count is set to 0 for all blocks.
        interaction_significance: Interaction |value| above this counts as
            significant.

    Returns:
        Classification for each block in the tensor.
    """
    # Compute main effects
    main_effects = tensor.main_effects(significance=1.0)  # No filtering for classification

    # Count interactions per block
    interaction_counts: dict[str, int] = defaultdict(int)
    if interactions:
        for (block_a, block_b), value in interactions.items():
            if abs(value) >= interaction_significance:
                interaction_counts[block_a] += 1
                interaction_counts[block_b] += 1

    # Compute per-block position sensitivity
    position_sensitive: dict[str, bool] = {}
    for key, score in tensor.entries.items():
        block_id, _, _ = tensor._parse_key(key)
        if score.position_controlled and score.position_delta is not None:
            if abs(score.position_delta) > position_delta_threshold:
                position_sensitive[block_id] = True

    # Compute per-block confidence from p-values and trial counts
    block_confidence: dict[str, float] = {}
    for block_id in tensor.block_ids:
        scores_for_block = [
            s for key, s in tensor.entries.items()
            if tensor._parse_key(key)[0] == block_id
        ]
        if not scores_for_block:
            block_confidence[block_id] = 0.0
            continue

        # Confidence from trial count (more trials = more confidence)
        avg_trials = statistics.mean(
            [s.n_baseline_trials + s.n_ablated_trials for s in scores_for_block]
        )
        trial_confidence = min(1.0, avg_trials / 10.0)

        # Confidence from p-values (lower p = more confidence)
        p_values = [s.p_value for s in scores_for_block if s.p_value is not None]
        if p_values:
            mean_p = statistics.mean(p_values)
            p_confidence = max(0.0, 1.0 - mean_p)
        else:
            p_confidence = 0.3  # No p-values available — low confidence

        block_confidence[block_id] = (trial_confidence + p_confidence) / 2.0

    # Classify each block
    classifications: list[BlockClassification] = []

    for block_id in tensor.block_ids:
        main_effect = main_effects.get(block_id, 0.0)
        n_interactions = interaction_counts.get(block_id, 0)
        is_position_sensitive = position_sensitive.get(block_id, False)
        confidence = block_confidence.get(block_id, 0.0)

        # Check baseline adherence for probes targeting this block
        # Use probe_id matching: probe IDs typically contain the block ID
        relevant_probes = [
            pid for pid in tensor.probe_ids
            if any(
                tensor._parse_key(k)[0] == block_id
                and tensor._parse_key(k)[1] == pid
                for k in tensor.entries
            )
        ]
        baseline_scores_for_block = [
            baseline_adherence.get(pid, 1.0) for pid in relevant_probes
        ]
        mean_baseline = (
            statistics.mean(baseline_scores_for_block)
            if baseline_scores_for_block
            else 1.0
        )

        has_main_effect = main_effect >= main_effect_threshold
        has_interactions = n_interactions > 0
        baseline_adherent = mean_baseline >= baseline_adherence_threshold

        if not baseline_adherent and not has_main_effect:
            # Low baseline adherence + no delta = never worked
            category: str = "weight_conflicting"
            evidence = (
                f"Baseline adherence {mean_baseline:.2f} below threshold "
                f"{baseline_adherence_threshold:.2f}, and main effect "
                f"{main_effect:.3f} below threshold {main_effect_threshold:.3f}. "
                f"The instruction is not being followed even when present."
            )
        elif has_main_effect:
            # Active block
            category = "weight_novel"
            evidence = (
                f"Main effect {main_effect:.3f} exceeds threshold "
                f"{main_effect_threshold:.3f}."
            )
            if is_position_sensitive:
                evidence += " Position-sensitive: behavioral change is partly or wholly due to position."
            if n_interactions > 0:
                evidence += f" Has {n_interactions} significant pairwise interaction(s)."
        elif has_interactions:
            # No main effect but interacts with other blocks
            category = "weight_compensating"
            evidence = (
                f"Main effect {main_effect:.3f} below threshold "
                f"{main_effect_threshold:.3f}, but {n_interactions} significant "
                f"pairwise interaction(s) detected. Block appears dead in "
                f"isolation but is load-bearing through interactions."
            )
        else:
            # No main effect, no interactions
            category = "weight_aligned"
            evidence = (
                f"Main effect {main_effect:.3f} below threshold "
                f"{main_effect_threshold:.3f}, no significant interactions. "
                f"Block's behavior is weight-aligned: the model would do this "
                f"anyway without the instruction."
            )

        classifications.append(
            BlockClassification(
                block_id=block_id,
                category=category,
                evidence=evidence,
                main_effect=main_effect,
                interaction_count=n_interactions,
                position_sensitive=is_position_sensitive,
                confidence=confidence,
            )
        )

    return classifications


# ---------------------------------------------------------------------------
# Competition pattern detection
# ---------------------------------------------------------------------------


def detect_competition_patterns(
    tensor: AblationTensor,
    density_threshold: float = 0.3,
) -> list[CompetitionPattern]:
    """Identify exploitation vs interference competition.

    Exploitation competition (dense rows): Removing one block affects
    many probes. This block is consuming attention budget that other
    blocks need.

    Interference competition (sparse entries): Removing one block
    affects specific other blocks. These blocks have semantic conflicts.

    Args:
        tensor: The assembled ablation tensor.
        density_threshold: Fraction of probes affected above which a
            block is classified as exploitation competition.

    Returns:
        List of detected competition patterns.
    """
    patterns: list[CompetitionPattern] = []

    # Count significant effects per block (across all probes and models)
    block_effect_counts: dict[str, int] = defaultdict(int)
    block_affected_probes: dict[str, set[str]] = defaultdict(set)
    total_probes = len(tensor.probe_ids)

    significant_entries: dict[str, list[tuple[str, str, float]]] = defaultdict(list)

    for key, score in tensor.entries.items():
        block_id, probe_id, model_id = tensor._parse_key(key)
        if abs(score.delta) >= 0.1:  # Meaningful effect
            block_effect_counts[block_id] += 1
            block_affected_probes[block_id].add(probe_id)
            significant_entries[block_id].append((probe_id, model_id, score.delta))

    if total_probes == 0:
        return patterns

    for block_id, affected_probes in block_affected_probes.items():
        density = len(affected_probes) / total_probes

        if density >= density_threshold:
            # Exploitation competition: affects many probes
            patterns.append(
                CompetitionPattern(
                    type="exploitation",
                    blocks=[block_id],
                    evidence=(
                        f"Block {block_id} affects {len(affected_probes)}/{total_probes} "
                        f"probes ({density:.0%}), exceeding density threshold "
                        f"({density_threshold:.0%}). This suggests attention budget "
                        f"competition rather than semantic conflict."
                    ),
                    tensor_signature="dense_row",
                )
            )
        elif len(affected_probes) > 0:
            # Check for interference competition: specific targeted effects
            # Look for blocks that affect probes for OTHER specific blocks
            for probe_id, model_id, delta in significant_entries[block_id]:
                if abs(delta) >= 0.2:  # Stronger threshold for interference
                    patterns.append(
                        CompetitionPattern(
                            type="interference",
                            blocks=[block_id, probe_id],
                            evidence=(
                                f"Removing {block_id} changes {probe_id} score by "
                                f"{delta:+.3f} on {model_id}. Sparse, targeted effect "
                                f"suggests semantic interference rather than attention "
                                f"budget competition."
                            ),
                            tensor_signature="sparse_entry",
                        )
                    )

    return patterns


# ---------------------------------------------------------------------------
# Suppression detection
# ---------------------------------------------------------------------------


def detect_suppression(
    tensor: AblationTensor,
    threshold: float = 0.1,
) -> list[tuple[str, str, float]]:
    """Find hidden suppressive interactions (Tekin et al. pattern).

    Suppression: removing block A *improves* adherence to block B's probes.
    This means A was actively suppressing B — a hidden interaction that
    only ablation reveals.

    Args:
        tensor: The assembled ablation tensor.
        threshold: Minimum positive delta to count as suppression.

    Returns:
        List of (block_a, block_b, suppression_magnitude) triples where
        removing block_a improves adherence to block_b's probes.
        Sorted by magnitude descending.
    """
    suppressions: list[tuple[str, str, float]] = []

    for key, score in tensor.entries.items():
        block_id, probe_id, model_id = tensor._parse_key(key)

        # Positive delta means removing the block improved the score
        if score.delta > threshold:
            # Check statistical significance if available
            if score.p_value is not None and score.p_value > 0.05:
                continue

            suppressions.append((block_id, probe_id, score.delta))

    # Deduplicate: keep the largest magnitude for each (block, probe) pair
    best: dict[tuple[str, str], float] = {}
    for block_id, probe_id, magnitude in suppressions:
        pair = (block_id, probe_id)
        if pair not in best or magnitude > best[pair]:
            best[pair] = magnitude

    result = [(b, p, m) for (b, p), m in best.items()]
    result.sort(key=lambda x: -x[2])
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    tensor: AblationTensor,
    classifications: list[BlockClassification],
    patterns: list[CompetitionPattern],
    suppressions: list[tuple[str, str, float]],
) -> str:
    """Generate a human-readable analysis report.

    Args:
        tensor: The ablation tensor.
        classifications: Block classifications.
        patterns: Detected competition patterns.
        suppressions: Detected suppressive interactions.

    Returns:
        Formatted report string.
    """
    lines: list[str] = []

    # Header
    shape = tensor.shape()
    lines.append("=" * 72)
    lines.append("ABLATION ANALYSIS REPORT")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"Tensor shape: {shape[0]} blocks x {shape[1]} probes x {shape[2]} models")
    lines.append(f"Total entries: {len(tensor.entries)}")
    lines.append("")

    # Block classifications summary
    lines.append("-" * 72)
    lines.append("BLOCK CLASSIFICATIONS")
    lines.append("-" * 72)
    lines.append("")

    by_category: dict[str, list[BlockClassification]] = defaultdict(list)
    for c in classifications:
        by_category[c.category].append(c)

    category_labels = {
        "weight_aligned": "Weight-Aligned (safe to remove)",
        "weight_compensating": "Weight-Compensating (looks dead, is load-bearing)",
        "weight_conflicting": "Weight-Conflicting (never worked)",
        "weight_novel": "Weight-Novel (actively shapes behavior)",
    }

    for category in ["weight_novel", "weight_compensating", "weight_conflicting", "weight_aligned"]:
        blocks = by_category.get(category, [])
        label = category_labels.get(category, category)
        lines.append(f"  {label}: {len(blocks)} block(s)")
        for c in sorted(blocks, key=lambda x: -x.main_effect):
            pos_marker = " [position-sensitive]" if c.position_sensitive else ""
            int_marker = f" [{c.interaction_count} interactions]" if c.interaction_count else ""
            lines.append(
                f"    {c.block_id}: main_effect={c.main_effect:.3f}, "
                f"confidence={c.confidence:.2f}{pos_marker}{int_marker}"
            )
        lines.append("")

    # Competition patterns
    if patterns:
        lines.append("-" * 72)
        lines.append("COMPETITION PATTERNS")
        lines.append("-" * 72)
        lines.append("")

        exploitation = [p for p in patterns if p.type == "exploitation"]
        interference = [p for p in patterns if p.type == "interference"]

        if exploitation:
            lines.append(f"  Exploitation competition (attention budget): {len(exploitation)}")
            for p in exploitation:
                lines.append(f"    Blocks: {', '.join(p.blocks)}")
                lines.append(f"    {p.evidence}")
                lines.append("")

        if interference:
            lines.append(f"  Interference competition (semantic conflict): {len(interference)}")
            for p in interference[:10]:  # Cap at 10 for readability
                lines.append(f"    Blocks: {', '.join(p.blocks)}")
                lines.append(f"    {p.evidence}")
                lines.append("")
            if len(interference) > 10:
                lines.append(f"    ... and {len(interference) - 10} more")
                lines.append("")

    # Suppressions
    if suppressions:
        lines.append("-" * 72)
        lines.append("HIDDEN SUPPRESSIVE INTERACTIONS (Tekin et al.)")
        lines.append("-" * 72)
        lines.append("")
        lines.append(
            "  Removing block A improves adherence to block B's probes."
        )
        lines.append(
            "  This means A was actively suppressing B."
        )
        lines.append("")
        for block_a, probe_b, magnitude in suppressions[:15]:
            lines.append(
                f"    {block_a} suppresses {probe_b}: "
                f"removal improves score by {magnitude:+.3f}"
            )
        if len(suppressions) > 15:
            lines.append(f"    ... and {len(suppressions) - 15} more")
        lines.append("")

    # Summary
    lines.append("-" * 72)
    lines.append("SUMMARY")
    lines.append("-" * 72)
    lines.append("")

    n_novel = len(by_category.get("weight_novel", []))
    n_compensating = len(by_category.get("weight_compensating", []))
    n_conflicting = len(by_category.get("weight_conflicting", []))
    n_aligned = len(by_category.get("weight_aligned", []))
    total = len(classifications)

    if total > 0:
        lines.append(
            f"  {n_novel}/{total} blocks actively shape behavior "
            f"({n_novel/total:.0%})"
        )
        lines.append(
            f"  {n_aligned}/{total} blocks are weight-aligned / removable "
            f"({n_aligned/total:.0%})"
        )
        if n_compensating:
            lines.append(
                f"  {n_compensating}/{total} blocks look dead but are load-bearing "
                f"({n_compensating/total:.0%})"
            )
        if n_conflicting:
            lines.append(
                f"  {n_conflicting}/{total} blocks never worked "
                f"({n_conflicting/total:.0%})"
            )
    if suppressions:
        lines.append(f"  {len(suppressions)} hidden suppressive interaction(s) found")
    if patterns:
        lines.append(
            f"  {len([p for p in patterns if p.type == 'exploitation'])} "
            f"exploitation competition pattern(s)"
        )
        lines.append(
            f"  {len([p for p in patterns if p.type == 'interference'])} "
            f"interference competition pattern(s)"
        )

    lines.append("")
    lines.append("=" * 72)

    return "\n".join(lines)
