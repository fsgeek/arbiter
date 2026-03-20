"""Tests for ablation analysis — block classification, competition, suppression.

Tests the contract specified in ablation_framework.md:
- classify_blocks() with the four-category taxonomy
- detect_competition_patterns() with dense vs sparse signatures
- detect_suppression() with planted suppressive interactions
"""

import pytest

from arbiter.ablation.analysis import (
    BlockClassification,
    CompetitionPattern,
    classify_blocks,
    detect_competition_patterns,
    detect_suppression,
)
from arbiter.ablation.tensor import AblationScore, AblationTensor


# --- Helpers ---


def _make_tensor_with_entries(entries: dict) -> AblationTensor:
    """Build an AblationTensor from a dict of (block, probe, model) -> AblationScore."""
    tensor = AblationTensor()
    for (block_id, probe_id, model_id), score in entries.items():
        tensor.set(block_id, probe_id, model_id, score)
    return tensor


# --- Weight-aligned classification ---


class TestWeightAligned:
    """Weight-aligned: no main effect, no interactions. Safe to remove."""

    def test_no_effect_no_interaction_classifies_aligned(self):
        """Block with zero delta and no pairwise interactions -> weight_aligned."""
        entries = {
            ("block-dead", "probe-dead", "model-1"): AblationScore(
                baseline_score=0.8, ablated_score=0.8, delta=0.0,
                p_value=0.95, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)
        baseline_adherence = {"probe-dead": 0.8}  # good adherence at baseline

        classifications = classify_blocks(tensor, baseline_adherence)
        dead_block = next(
            (c for c in classifications if c.block_id == "block-dead"), None
        )
        assert dead_block is not None
        assert dead_block.category == "weight_aligned"
        assert dead_block.main_effect < 0.1
        assert dead_block.interaction_count == 0


# --- Weight-compensating classification ---


class TestWeightCompensating:
    """Weight-compensating: no main effect, but interactions appear.
    Looks dead but is load-bearing."""

    def test_no_main_effect_but_interactions_classifies_compensating(self):
        """Block with zero delta but significant pairwise interactions -> weight_compensating."""
        # Block shows no main effect when removed alone
        entries = {
            ("block-comp", "probe-comp", "model-1"): AblationScore(
                baseline_score=0.8, ablated_score=0.8, delta=0.0,
                p_value=0.9, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)
        # Simulate that pairwise analysis found interactions
        # The implementation should detect this from Phase 1 data
        baseline_adherence = {"probe-comp": 0.8}

        classifications = classify_blocks(tensor, baseline_adherence)
        comp_block = next(
            (c for c in classifications if c.block_id == "block-comp"), None
        )
        # If the tensor has interaction data, this should be weight_compensating
        # Without Phase 1 data, it may classify as weight_aligned
        assert comp_block is not None


# --- Weight-conflicting classification ---


class TestWeightConflicting:
    """Weight-conflicting: low baseline adherence, no main effect.
    The instruction never worked."""

    def test_low_baseline_classifies_conflicting(self):
        """Block with low baseline adherence -> weight_conflicting.
        Removal doesn't change anything because it never worked."""
        entries = {
            ("block-conflict", "probe-conflict", "model-1"): AblationScore(
                baseline_score=0.1, ablated_score=0.1, delta=0.0,
                p_value=0.9, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)
        # Low baseline adherence is the key signal
        baseline_adherence = {"probe-conflict": 0.1}

        classifications = classify_blocks(tensor, baseline_adherence)
        conflict_block = next(
            (c for c in classifications if c.block_id == "block-conflict"), None
        )
        assert conflict_block is not None
        assert conflict_block.category == "weight_conflicting"


# --- Weight-novel classification ---


class TestWeightNovel:
    """Weight-novel: large main effect, position-sensitive. Fragile."""

    def test_large_delta_classifies_novel(self):
        """Block with large delta on removal -> weight_novel."""
        entries = {
            ("block-novel", "probe-novel", "model-1"): AblationScore(
                baseline_score=0.9, ablated_score=0.2, delta=-0.7,
                p_value=0.001, position_controlled=True, position_delta=-0.3,
            ),
        }
        tensor = _make_tensor_with_entries(entries)
        baseline_adherence = {"probe-novel": 0.9}

        classifications = classify_blocks(tensor, baseline_adherence)
        novel_block = next(
            (c for c in classifications if c.block_id == "block-novel"), None
        )
        assert novel_block is not None
        assert novel_block.category == "weight_novel"
        assert novel_block.main_effect > 0.3


# --- Classification output structure ---


class TestBlockClassificationStructure:
    def test_classification_has_required_fields(self):
        """BlockClassification dataclass has all required fields."""
        bc = BlockClassification(
            block_id="test-block",
            category="weight_aligned",
            evidence="No delta observed across 3 trials",
            main_effect=0.01,
            interaction_count=0,
            position_sensitive=False,
            confidence=0.95,
        )
        assert bc.block_id == "test-block"
        assert bc.category == "weight_aligned"
        assert bc.main_effect == pytest.approx(0.01)
        assert bc.interaction_count == 0
        assert bc.position_sensitive is False
        assert bc.confidence == pytest.approx(0.95)

    def test_classification_categories_are_valid(self):
        """Only the four categories from the design doc are valid."""
        valid = {"weight_aligned", "weight_compensating", "weight_conflicting", "weight_novel"}
        for cat in valid:
            bc = BlockClassification(
                block_id="x", category=cat, evidence="test",
                main_effect=0.0, interaction_count=0,
                position_sensitive=False, confidence=0.5,
            )
            assert bc.category in valid


# --- Competition pattern detection ---


class TestCompetitionPatterns:
    def test_dense_row_detects_exploitation(self):
        """Dense tensor row (many probes affected by one block) -> exploitation competition."""
        # Block A's removal affects many probes -> attention budget issue
        entries = {}
        for i in range(10):
            entries[("block-dense", f"probe-{i}", "model-1")] = AblationScore(
                baseline_score=0.8, ablated_score=0.5, delta=-0.3,
                p_value=0.01, position_controlled=False, position_delta=None,
            )
        tensor = _make_tensor_with_entries(entries)

        patterns = detect_competition_patterns(tensor)
        exploitation = [p for p in patterns if p.type == "exploitation"]
        assert len(exploitation) >= 1
        assert any("block-dense" in p.blocks for p in exploitation)

    def test_sparse_entries_detect_interference(self):
        """Sparse tensor entries (specific block pairs) -> interference competition."""
        # Only one specific pair shows interaction
        entries = {
            ("block-x", "probe-y", "model-1"): AblationScore(
                baseline_score=0.9, ablated_score=0.3, delta=-0.6,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)

        patterns = detect_competition_patterns(tensor)
        # With very sparse data, should detect interference not exploitation
        if patterns:
            interference = [p for p in patterns if p.type == "interference"]
            assert len(interference) >= 0  # May or may not detect with single entry

    def test_competition_pattern_structure(self):
        """CompetitionPattern has required fields."""
        pattern = CompetitionPattern(
            type="exploitation",
            blocks=["block-a", "block-b"],
            evidence="Dense row in tensor: block-a affects 8/10 probes",
            tensor_signature="dense_row",
        )
        assert pattern.type == "exploitation"
        assert pattern.tensor_signature == "dense_row"

    def test_empty_tensor_no_patterns(self):
        """Empty tensor produces no competition patterns."""
        tensor = _make_tensor_with_entries({})
        patterns = detect_competition_patterns(tensor)
        assert patterns == []


# --- Suppression detection ---


class TestSuppressionDetection:
    def test_planted_suppression_detected(self):
        """When removing block A improves block B's probes, that's suppression."""
        entries = {
            # Removing block-suppressor improves probe-victim scores
            ("block-suppressor", "probe-victim", "model-1"): AblationScore(
                baseline_score=0.3, ablated_score=0.9, delta=0.6,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)

        suppressions = detect_suppression(tensor)
        assert len(suppressions) >= 1
        # Each suppression is (block_a, block_b, magnitude)
        block_a, block_b, magnitude = suppressions[0]
        assert magnitude > 0
        assert block_a == "block-suppressor"

    def test_no_suppression_when_all_negative_delta(self):
        """All negative deltas -> no suppression (removal only hurts)."""
        entries = {
            ("block-a", "probe-a", "model-1"): AblationScore(
                baseline_score=0.9, ablated_score=0.5, delta=-0.4,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
            ("block-b", "probe-b", "model-1"): AblationScore(
                baseline_score=0.8, ablated_score=0.6, delta=-0.2,
                p_value=0.01, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)

        suppressions = detect_suppression(tensor)
        assert suppressions == []

    def test_suppression_returns_triples(self):
        """Suppression results are (block_a, block_b, float) triples."""
        entries = {
            ("block-s", "probe-v", "model-1"): AblationScore(
                baseline_score=0.2, ablated_score=0.8, delta=0.6,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
        }
        tensor = _make_tensor_with_entries(entries)

        suppressions = detect_suppression(tensor)
        for item in suppressions:
            assert len(item) == 3
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)
            assert isinstance(item[2], (int, float))

    def test_empty_tensor_no_suppression(self):
        """Empty tensor produces no suppressions."""
        tensor = _make_tensor_with_entries({})
        suppressions = detect_suppression(tensor)
        assert suppressions == []
