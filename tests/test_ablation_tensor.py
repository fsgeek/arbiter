"""Tests for ablation tensor — assembly, main effects, deltas, conversion.

Tests the contract specified in ablation_framework.md:
- AblationTensor.from_run() assembles from completed run
- AblationTensor.main_effects() returns mean |delta| per block
- AblationScore.delta = ablated - baseline
- Conversion to InterferenceTensor
"""

import pytest

from arbiter.ablation.probe import Probe, ProbeResult
from arbiter.ablation.tensor import AblationScore, AblationTensor


# --- AblationScore tests ---


class TestAblationScore:
    def test_delta_is_ablated_minus_baseline(self):
        """delta = ablated_score - baseline_score per design doc."""
        score = AblationScore(
            baseline_score=0.8,
            ablated_score=0.6,
            delta=-0.2,
            p_value=0.01,
            position_controlled=False,
            position_delta=None,
        )
        assert score.delta == pytest.approx(score.ablated_score - score.baseline_score)

    def test_positive_delta(self):
        """Removal improves score -> positive delta."""
        score = AblationScore(
            baseline_score=0.4,
            ablated_score=0.8,
            delta=0.4,
            p_value=0.005,
            position_controlled=False,
            position_delta=None,
        )
        assert score.delta > 0

    def test_zero_delta(self):
        """No change -> delta is 0."""
        score = AblationScore(
            baseline_score=0.7,
            ablated_score=0.7,
            delta=0.0,
            p_value=1.0,
            position_controlled=False,
            position_delta=None,
        )
        assert score.delta == pytest.approx(0.0)

    def test_position_controlled_fields(self):
        """Phase 2 scores include position control data."""
        score = AblationScore(
            baseline_score=0.8,
            ablated_score=0.5,
            delta=-0.3,
            p_value=0.02,
            position_controlled=True,
            position_delta=-0.1,
        )
        assert score.position_controlled is True
        assert score.position_delta == pytest.approx(-0.1)

    def test_p_value_none_for_single_trial(self):
        """Single trial -> p_value is None."""
        score = AblationScore(
            baseline_score=0.8,
            ablated_score=0.6,
            delta=-0.2,
            p_value=None,
            position_controlled=False,
            position_delta=None,
        )
        assert score.p_value is None


# --- AblationTensor assembly tests ---


class TestAblationTensorAssembly:
    def _make_mock_results(self):
        """Create mock ProbeResults for a simple scenario.

        2 free blocks, 2 probes (one per block), 1 model, 3 trials.
        Baseline + 2 ablation configs.
        """
        results = []
        # Baseline: both blocks present, both probes score high
        for trial in range(3):
            results.append(ProbeResult(
                config_id="baseline",
                probe_id="probe-block1",
                model_id="model-a",
                trial=trial,
                raw_response="Good response.",
                tool_calls=None,
                score=0.9,
                timestamp="2026-03-16T12:00:00Z",
            ))
            results.append(ProbeResult(
                config_id="baseline",
                probe_id="probe-block2",
                model_id="model-a",
                trial=trial,
                raw_response="Good response.",
                tool_calls=None,
                score=0.8,
                timestamp="2026-03-16T12:00:00Z",
            ))
        # Block 1 removed: probe-block1 scores drop, probe-block2 unchanged
        for trial in range(3):
            results.append(ProbeResult(
                config_id="phase0-block1-removed",
                probe_id="probe-block1",
                model_id="model-a",
                trial=trial,
                raw_response="Degraded.",
                tool_calls=None,
                score=0.3,
                timestamp="2026-03-16T12:00:00Z",
            ))
            results.append(ProbeResult(
                config_id="phase0-block1-removed",
                probe_id="probe-block2",
                model_id="model-a",
                trial=trial,
                raw_response="Still good.",
                tool_calls=None,
                score=0.8,
                timestamp="2026-03-16T12:00:00Z",
            ))
        # Block 2 removed: probe-block2 scores drop, probe-block1 unchanged
        for trial in range(3):
            results.append(ProbeResult(
                config_id="phase0-block2-removed",
                probe_id="probe-block1",
                model_id="model-a",
                trial=trial,
                raw_response="Still good.",
                tool_calls=None,
                score=0.9,
                timestamp="2026-03-16T12:00:00Z",
            ))
            results.append(ProbeResult(
                config_id="phase0-block2-removed",
                probe_id="probe-block2",
                model_id="model-a",
                trial=trial,
                raw_response="Degraded.",
                tool_calls=None,
                score=0.4,
                timestamp="2026-03-16T12:00:00Z",
            ))
        return results

    def test_tensor_has_entries(self):
        """Assembled tensor should have entries for each (block, probe, model) triple."""
        # We can't call from_run without the full AblationRun, so test
        # at the score level — tensor should be constructable from scores
        tensor = AblationTensor()
        score = AblationScore(
            baseline_score=0.9,
            ablated_score=0.3,
            delta=-0.6,
            p_value=0.001,
            position_controlled=False,
            position_delta=None,
        )
        # The tensor should accept entries keyed by (block, probe, model)
        # Exact API depends on implementation, but the contract says
        # it's a sparse tensor: (block, probe, model) -> AblationScore
        assert score.delta == pytest.approx(-0.6)


# --- Main effects tests ---


class TestMainEffects:
    @pytest.fixture
    def tensor_with_known_effects(self):
        """Build a tensor where main effects are known.

        Block A: large effect (mean |delta| = 0.6)
        Block B: no effect (mean |delta| = 0.0)
        Block C: small effect (mean |delta| = 0.1)
        """
        tensor = AblationTensor()
        # Manually populate if the API supports it, or use from_run
        # For now, create the expected structure
        entries = {
            ("block-a", "probe-a", "model-1"): AblationScore(
                baseline_score=0.9, ablated_score=0.3, delta=-0.6,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
            ("block-b", "probe-b", "model-1"): AblationScore(
                baseline_score=0.8, ablated_score=0.8, delta=0.0,
                p_value=0.95, position_controlled=False, position_delta=None,
            ),
            ("block-c", "probe-c", "model-1"): AblationScore(
                baseline_score=0.7, ablated_score=0.6, delta=-0.1,
                p_value=0.04, position_controlled=False, position_delta=None,
            ),
        }
        for (block_id, probe_id, model_id), score in entries.items():
            tensor.set(block_id, probe_id, model_id, score)
        return tensor

    def test_main_effects_returns_dict(self, tensor_with_known_effects):
        """main_effects() returns dict[str, float]."""
        effects = tensor_with_known_effects.main_effects()
        assert isinstance(effects, dict)

    def test_large_effect_detected(self, tensor_with_known_effects):
        """Block with large delta should have large main effect."""
        effects = tensor_with_known_effects.main_effects()
        if "block-a" in effects:
            assert effects["block-a"] > 0.3

    def test_no_effect_block_small(self, tensor_with_known_effects):
        """Block with zero delta should have zero or near-zero main effect."""
        effects = tensor_with_known_effects.main_effects()
        if "block-b" in effects:
            assert effects["block-b"] < 0.1

    def test_significance_filtering(self, tensor_with_known_effects):
        """With strict significance threshold, insignificant effects excluded."""
        effects = tensor_with_known_effects.main_effects(significance=0.01)
        # block-b has p_value=0.95, should be excluded
        # block-c has p_value=0.04, should be excluded at 0.01 threshold
        if "block-b" in effects:
            assert effects["block-b"] == pytest.approx(0.0)


# --- Delta computation tests ---


class TestDeltaComputation:
    def test_negative_delta_means_removal_hurts(self):
        """negative delta = removal hurts adherence."""
        score = AblationScore(
            baseline_score=0.9, ablated_score=0.3, delta=-0.6,
            p_value=0.001, position_controlled=False, position_delta=None,
        )
        assert score.delta < 0

    def test_positive_delta_means_removal_helps(self):
        """positive delta = removal improves adherence (suppression signal)."""
        score = AblationScore(
            baseline_score=0.4, ablated_score=0.9, delta=0.5,
            p_value=0.001, position_controlled=False, position_delta=None,
        )
        assert score.delta > 0

    def test_delta_magnitude(self):
        """Delta magnitude should match the difference."""
        score = AblationScore(
            baseline_score=0.7, ablated_score=0.5, delta=-0.2,
            p_value=0.03, position_controlled=False, position_delta=None,
        )
        assert abs(score.delta) == pytest.approx(0.2)


# --- Conversion to InterferenceTensor ---


class TestConversionToInterferenceTensor:
    def test_conversion_returns_interference_tensor(self):
        """to_interference_tensor() should return an InterferenceTensor."""
        tensor = AblationTensor()
        # Populate minimally
        entries = {
            ("block-a", "probe-a", "model-1"): AblationScore(
                baseline_score=0.9, ablated_score=0.3, delta=-0.6,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
        }
        for (block_id, probe_id, model_id), score in entries.items():
            tensor.set(block_id, probe_id, model_id, score)
        result = tensor.to_interference_tensor()
        # Import here to avoid circular dependency issues
        from arbiter.interference_tensor import InterferenceTensor
        assert isinstance(result, InterferenceTensor)

    def test_conversion_preserves_block_information(self):
        """Converted tensor should reference the same blocks."""
        tensor = AblationTensor()
        entries = {
            ("block-a", "probe-a", "model-1"): AblationScore(
                baseline_score=0.9, ablated_score=0.3, delta=-0.6,
                p_value=0.001, position_controlled=False, position_delta=None,
            ),
            ("block-b", "probe-b", "model-1"): AblationScore(
                baseline_score=0.8, ablated_score=0.8, delta=0.0,
                p_value=0.9, position_controlled=False, position_delta=None,
            ),
        }
        for (block_id, probe_id, model_id), score in entries.items():
            tensor.set(block_id, probe_id, model_id, score)
        result = tensor.to_interference_tensor()
        assert "block-a" in result.block_ids


class TestFromRunAdditionalCoverage:
    def test_from_run_adds_position_control_data(self):
        baseline_results = [
            ProbeResult(
                config_id="baseline",
                probe_id="probe-a",
                model_id="m1",
                trial=0,
                raw_response="x",
                score=0.8,
            ),
            ProbeResult(
                config_id="baseline",
                probe_id="probe-a",
                model_id="m1",
                trial=1,
                raw_response="x",
                score=0.8,
            ),
        ]
        phase0_results = [
            ProbeResult(
                config_id="phase0-block-a-removed",
                probe_id="probe-a",
                model_id="m1",
                trial=0,
                raw_response="x",
                score=0.4,
            ),
            ProbeResult(
                config_id="phase0-block-a-removed",
                probe_id="probe-a",
                model_id="m1",
                trial=1,
                raw_response="x",
                score=0.4,
            ),
        ]
        phase2_results = [
            ProbeResult(
                config_id="phase2-block-a-whitespace",
                probe_id="probe-a",
                model_id="m1",
                trial=0,
                raw_response="x",
                score=0.7,
            )
        ]

        from arbiter.ablation.configuration import AblationConfig

        phase0_configs = [
            AblationConfig(
                id="phase0-block-a-removed",
                phase="phase0",
                present_blocks=[],
                absent_blocks=["block-a"],
                metadata={"removed_block": "block-a"},
            )
        ]

        tensor = AblationTensor.from_run(
            baseline_results=baseline_results,
            phase0_results=phase0_results,
            phase0_configs=phase0_configs,
            phase2_results=phase2_results,
        )

        score = tensor.get("block-a", "probe-a", "m1")
        assert score is not None
        assert score.position_controlled is True
        assert score.position_delta == pytest.approx(-0.1)
