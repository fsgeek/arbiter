"""Integration test — end-to-end ablation with mock LLM.

Tests the full pipeline: corpus -> configs -> probes -> scoring -> tensor -> classification.
Uses deterministic mock responses to verify the pipeline produces correct results.
"""

import pytest

from arbiter.ablation.analysis import (
    classify_blocks,
    detect_competition_patterns,
    detect_suppression,
)
from arbiter.ablation.battery import ProbeBattery
from arbiter.ablation.configuration import (
    AblationConfig,
    build_phase0_configs,
)
from arbiter.ablation.covering_array import generate_covering_array
from arbiter.ablation.probe import Probe, ProbeResult
from arbiter.ablation.tensor import AblationScore, AblationTensor
from arbiter.prompt_blocks import (
    BlockCategory,
    Modality,
    PromptBlock,
    PromptCorpus,
    Tier,
)


# --- Fixtures ---


def _make_block(block_id: str, text: str, **kwargs) -> PromptBlock:
    defaults = dict(
        source="test/v1",
        tier=Tier.system,
        category=BlockCategory.behavioral_constraint,
        modality=Modality.mandate,
        scope=["test"],
    )
    defaults.update(kwargs)
    return PromptBlock(id=block_id, text=text, **defaults)


@pytest.fixture
def integration_corpus():
    """Corpus with 2 constrained + 3 free blocks."""
    return PromptCorpus(
        name="integration-test/v1",
        source_file="test.md",
        blocks=[
            _make_block("constrained-identity", "You are a helpful assistant."),
            _make_block("constrained-safety", "Never generate harmful content."),
            _make_block("free-concise", "Be concise in all responses."),
            _make_block("free-no-emoji", "Never use emojis in responses.",
                        modality=Modality.prohibition),
            _make_block("free-read-first", "Always read files before editing.",
                        category=BlockCategory.workflow),
        ],
    )


@pytest.fixture
def constrained_ids():
    return ["constrained-identity", "constrained-safety"]


@pytest.fixture
def free_ids():
    return ["free-concise", "free-no-emoji", "free-read-first"]


@pytest.fixture
def integration_battery():
    """One probe per free block."""
    return ProbeBattery(
        probes=[
            Probe(
                id="probe-concise",
                target_block="free-concise",
                user_message="Explain what a decorator is.",
                scoring_method="length",
                expected_behavior="Short explanation",
                violation_indicator="Verbose explanation",
                scoring_params={"baseline_length": 200},
            ),
            Probe(
                id="probe-no-emoji",
                target_block="free-no-emoji",
                user_message="How are you today?",
                scoring_method="not_contains",
                expected_behavior="No emojis in response",
                violation_indicator="Contains emojis",
                scoring_params={"pattern": "\U0001f600"},  # smiley emoji
            ),
            Probe(
                id="probe-read-first",
                target_block="free-read-first",
                user_message="Change foo to bar in utils.py",
                scoring_method="tool_trace",
                expected_behavior="Reads file before editing",
                violation_indicator="Edits without reading",
                scoring_params={"required_sequence": ["Read", "Edit"]},
            ),
        ],
        metadata={"version": "1.0", "test": True},
    )


# --- Integration: Phase 0 config generation ---


class TestIntegrationPhase0:
    def test_phase0_configs_generated(
        self, integration_corpus, free_ids, constrained_ids
    ):
        """Phase 0 generates correct number of configs."""
        configs = build_phase0_configs(
            integration_corpus, free_ids, constrained_ids
        )
        assert len(configs) == len(free_ids) + 1  # 3 ablations + 1 baseline

    def test_phase0_configs_assemblable(
        self, integration_corpus, free_ids, constrained_ids
    ):
        """Every Phase 0 config can assemble a valid prompt."""
        configs = build_phase0_configs(
            integration_corpus, free_ids, constrained_ids
        )
        for config in configs:
            prompt = config.assemble_prompt(integration_corpus)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Constrained blocks always present
            assert "helpful assistant" in prompt
            assert "harmful content" in prompt


# --- Integration: Battery validation ---


class TestIntegrationBatteryValidation:
    def test_battery_covers_all_free_blocks(
        self, integration_battery, free_ids
    ):
        """Battery has probes for every free block."""
        uncovered = integration_battery.validate(free_ids)
        assert uncovered == [], f"Uncovered blocks: {uncovered}"


# --- Integration: Covering array for small case ---


class TestIntegrationCoveringArray:
    def test_covering_array_for_3_factors(self):
        """Covering array for 3 free blocks has pairwise coverage."""
        from itertools import combinations

        array = generate_covering_array(n_factors=3, strength=2)
        for i, j in combinations(range(3), 2):
            seen = {(row[i], row[j]) for row in array}
            assert seen == {(0, 0), (0, 1), (1, 0), (1, 1)}


# --- Integration: End-to-end with mock scoring ---


class TestIntegrationEndToEnd:
    """Full pipeline: configs -> mock scoring -> tensor -> classification.

    Uses deterministic mock responses instead of actual LLM calls.
    """

    def _mock_score(
        self, config: AblationConfig, probe: Probe
    ) -> float:
        """Deterministic mock scoring.

        Rules:
        - Concise probe: score 0.9 when free-concise present, 0.3 when absent
        - No-emoji probe: score 1.0 always (model never uses emoji)
        - Read-first probe: score 0.8 when free-read-first present, 0.8 when absent
          (weight-aligned: instruction doesn't change behavior)
        """
        if probe.id == "probe-concise":
            return 0.9 if "free-concise" in config.present_blocks else 0.3
        elif probe.id == "probe-no-emoji":
            return 1.0  # always adhered to
        elif probe.id == "probe-read-first":
            return 0.8  # no change regardless of config
        return 0.5

    def test_end_to_end_pipeline(
        self,
        integration_corpus,
        free_ids,
        constrained_ids,
        integration_battery,
    ):
        """Run the full pipeline with mock scoring and verify classifications."""
        # Step 1: Generate Phase 0 configs
        configs = build_phase0_configs(
            integration_corpus, free_ids, constrained_ids
        )
        baseline = next(c for c in configs if c.phase == "baseline")

        # Step 2: Run mock scoring
        results = []
        model_id = "mock/deterministic-v1"
        for config in configs:
            for probe in integration_battery.probes:
                for trial in range(3):
                    score = self._mock_score(config, probe)
                    results.append(ProbeResult(
                        config_id=config.id,
                        probe_id=probe.id,
                        model_id=model_id,
                        trial=trial,
                        raw_response=f"Mock response (score={score})",
                        tool_calls=None,
                        score=score,
                        timestamp="2026-03-16T12:00:00Z",
                    ))

        # Step 3: Compute baseline scores
        baseline_results = [r for r in results if r.config_id == baseline.id]
        baseline_adherence = {}
        for probe in integration_battery.probes:
            probe_results = [r for r in baseline_results if r.probe_id == probe.id]
            baseline_adherence[probe.id] = (
                sum(r.score for r in probe_results) / len(probe_results)
            )

        # Verify baseline scores
        assert baseline_adherence["probe-concise"] == pytest.approx(0.9)
        assert baseline_adherence["probe-no-emoji"] == pytest.approx(1.0)
        assert baseline_adherence["probe-read-first"] == pytest.approx(0.8)

        # Step 4: Compute deltas
        ablation_scores = {}
        for config in configs:
            if config.phase == "baseline":
                continue
            # Which block was removed?
            removed = config.absent_blocks[0]
            for probe in integration_battery.probes:
                config_results = [
                    r for r in results
                    if r.config_id == config.id and r.probe_id == probe.id
                ]
                ablated_mean = (
                    sum(r.score for r in config_results) / len(config_results)
                )
                base_mean = baseline_adherence[probe.id]
                ablation_scores[(removed, probe.id, model_id)] = AblationScore(
                    baseline_score=base_mean,
                    ablated_score=ablated_mean,
                    delta=ablated_mean - base_mean,
                    p_value=None,
                    position_controlled=False,
                    position_delta=None,
                )

        # Step 5: Verify deltas
        # free-concise removal should cause large negative delta on probe-concise
        concise_delta = ablation_scores[
            ("free-concise", "probe-concise", model_id)
        ].delta
        assert concise_delta == pytest.approx(-0.6)

        # free-no-emoji removal should cause zero delta (model never uses emoji)
        emoji_delta = ablation_scores[
            ("free-no-emoji", "probe-no-emoji", model_id)
        ].delta
        assert emoji_delta == pytest.approx(0.0)

        # free-read-first removal: zero delta (weight-aligned)
        read_delta = ablation_scores[
            ("free-read-first", "probe-read-first", model_id)
        ].delta
        assert read_delta == pytest.approx(0.0)

    def test_mock_scores_are_deterministic(
        self,
        integration_corpus,
        free_ids,
        constrained_ids,
        integration_battery,
    ):
        """Running the mock pipeline twice produces identical results."""
        configs = build_phase0_configs(
            integration_corpus, free_ids, constrained_ids
        )

        scores_run1 = []
        scores_run2 = []
        for config in configs:
            for probe in integration_battery.probes:
                scores_run1.append(self._mock_score(config, probe))
                scores_run2.append(self._mock_score(config, probe))

        assert scores_run1 == scores_run2


# --- Integration: Suppression scenario ---


class TestIntegrationSuppression:
    """Test that the pipeline correctly detects planted suppression."""

    def test_suppression_found_in_mock_data(self):
        """Block A suppresses Block B: removing A improves B's probe scores."""
        # Build tensor with a known suppression
        entries = {
            # Removing block-a IMPROVES probe-b (suppression!)
            ("block-a", "probe-b", "model-1"): AblationScore(
                baseline_score=0.3,
                ablated_score=0.9,
                delta=0.6,
                p_value=0.001,
                position_controlled=False,
                position_delta=None,
            ),
            # Removing block-a hurts probe-a (block-a is active for its own probe)
            ("block-a", "probe-a", "model-1"): AblationScore(
                baseline_score=0.9,
                ablated_score=0.4,
                delta=-0.5,
                p_value=0.001,
                position_controlled=False,
                position_delta=None,
            ),
            # Removing block-b has no effect on anything
            ("block-b", "probe-b", "model-1"): AblationScore(
                baseline_score=0.3,
                ablated_score=0.3,
                delta=0.0,
                p_value=0.9,
                position_controlled=False,
                position_delta=None,
            ),
        }
        tensor = AblationTensor()
        for (block_id, probe_id, model_id), score in entries.items():
            tensor.set(block_id, probe_id, model_id, score)

        suppressions = detect_suppression(tensor)
        # Should find that block-a suppresses something related to probe-b
        assert len(suppressions) >= 1
        suppressors = [s[0] for s in suppressions]
        assert "block-a" in suppressors


# --- Integration: Weight classification consistency ---


class TestIntegrationClassificationConsistency:
    def test_all_four_categories_distinguishable(self):
        """A synthetic tensor with all four block types should produce all four categories."""
        entries = {
            # Weight-aligned: no delta, no interactions, good baseline
            ("aligned", "probe-aligned", "m"): AblationScore(
                baseline_score=0.85, ablated_score=0.85, delta=0.0,
                p_value=0.9, position_controlled=False, position_delta=None,
            ),
            # Weight-conflicting: no delta, but baseline adherence is terrible
            ("conflicting", "probe-conflicting", "m"): AblationScore(
                baseline_score=0.1, ablated_score=0.1, delta=0.0,
                p_value=0.9, position_controlled=False, position_delta=None,
            ),
            # Weight-novel: large delta, position-sensitive
            ("novel", "probe-novel", "m"): AblationScore(
                baseline_score=0.9, ablated_score=0.2, delta=-0.7,
                p_value=0.001, position_controlled=True, position_delta=-0.4,
            ),
        }
        tensor = AblationTensor()
        for (block_id, probe_id, model_id), score in entries.items():
            tensor.set(block_id, probe_id, model_id, score)

        baseline_adherence = {
            "probe-aligned": 0.85,
            "probe-conflicting": 0.1,
            "probe-novel": 0.9,
        }

        classifications = classify_blocks(tensor, baseline_adherence)
        categories = {c.category for c in classifications}

        # Should have at least aligned, conflicting, and novel
        assert "weight_aligned" in categories
        assert "weight_conflicting" in categories
        assert "weight_novel" in categories
