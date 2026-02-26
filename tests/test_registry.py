"""Model registry — unit tests (no API calls).

Tests profile construction, registry operations, domain-aware selection,
and evaluator construction (with mocked environment).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from arbiter.registry import (
    DomainScore,
    ModelProfile,
    ModelRegistry,
    Provider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(
    name: str = "test/model",
    *,
    provider: Provider = Provider.OPENROUTER,
    api_key_env: str = "TEST_API_KEY",
    detection: dict[str, float] | None = None,
    fp: dict[str, float] | None = None,
    disqualified: bool = False,
    cost_input: float | None = None,
    cost_output: float | None = None,
) -> ModelProfile:
    """Build a ModelProfile with minimal boilerplate."""
    domain_scores: dict[str, DomainScore] = {}
    if detection:
        for domain, rate in detection.items():
            fp_rate = (fp or {}).get(domain, 0.0)
            domain_scores[domain] = DomainScore(
                detection_rate=rate,
                false_positive_rate=fp_rate,
                n_trials=10,
            )
    return ModelProfile(
        name=name,
        api_model_id=f"{name}-id",
        provider=provider,
        api_key_env=api_key_env,
        domain_scores=domain_scores,
        disqualified=disqualified,
        cost_per_million_input=cost_input,
        cost_per_million_output=cost_output,
    )


# ---------------------------------------------------------------------------
# ModelProfile
# ---------------------------------------------------------------------------


class TestModelProfile:
    def test_construction(self):
        p = _make_profile("test/a", detection={"foo": 0.8})
        assert p.name == "test/a"
        assert p.api_model_id == "test/a-id"
        assert p.domain_scores["foo"].detection_rate == 0.8

    def test_validation_detection_rate_bounds(self):
        with pytest.raises(Exception):
            DomainScore(detection_rate=1.5, false_positive_rate=0.0, n_trials=10)
        with pytest.raises(Exception):
            DomainScore(detection_rate=-0.1, false_positive_rate=0.0, n_trials=10)

    def test_validation_n_trials_positive(self):
        with pytest.raises(Exception):
            DomainScore(detection_rate=0.5, false_positive_rate=0.0, n_trials=0)

    def test_cost_estimation(self):
        p = _make_profile(cost_input=1.0, cost_output=2.0)
        # 1500 input tokens, 500 output tokens (defaults)
        cost = p.estimated_cost_per_call()
        assert cost is not None
        expected = 1.0 * 1500 / 1_000_000 + 2.0 * 500 / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_cost_estimation_custom_tokens(self):
        p = _make_profile(cost_input=1.0, cost_output=2.0)
        cost = p.estimated_cost_per_call(avg_input_tokens=1000, avg_output_tokens=1000)
        expected = 1.0 * 1000 / 1_000_000 + 2.0 * 1000 / 1_000_000
        assert cost is not None
        assert abs(cost - expected) < 1e-10

    def test_cost_estimation_unknown(self):
        p = _make_profile()  # no cost data
        assert p.estimated_cost_per_call() is None

    def test_cost_estimation_partial_unknown(self):
        p = _make_profile(cost_input=1.0)  # output unknown
        assert p.estimated_cost_per_call() is None


# ---------------------------------------------------------------------------
# Registry core
# ---------------------------------------------------------------------------


class TestRegistryCore:
    def test_register_and_get(self):
        reg = ModelRegistry()
        p = _make_profile("test/a")
        reg.register(p)
        assert reg.get("test/a") is p

    def test_get_missing_raises(self):
        reg = ModelRegistry()
        with pytest.raises(KeyError, match="test/missing"):
            reg.get("test/missing")

    def test_overwrite(self):
        reg = ModelRegistry()
        p1 = _make_profile("test/a", detection={"x": 0.5})
        p2 = _make_profile("test/a", detection={"x": 0.9})
        reg.register(p1)
        reg.register(p2)
        assert reg.get("test/a").domain_scores["x"].detection_rate == 0.9

    def test_list_profiles_empty(self):
        reg = ModelRegistry()
        assert reg.list_profiles() == []

    def test_list_profiles(self):
        reg = ModelRegistry()
        reg.register(_make_profile("test/a"))
        reg.register(_make_profile("test/b"))
        names = [p.name for p in reg.list_profiles()]
        assert names == ["test/a", "test/b"]


# ---------------------------------------------------------------------------
# Selection logic
# ---------------------------------------------------------------------------


class TestSelection:
    def _registry_with_models(self) -> ModelRegistry:
        """Registry with three models for selection tests."""
        reg = ModelRegistry()
        reg.register(_make_profile(
            "model/high",
            detection={"instruction": 1.0, "adversarial": 0.5},
            cost_input=0.80, cost_output=4.00,
        ))
        reg.register(_make_profile(
            "model/mid",
            detection={"instruction": 0.85, "adversarial": 1.0},
            cost_input=0.10, cost_output=0.40,
        ))
        reg.register(_make_profile(
            "model/low",
            detection={"instruction": 0.60},
            cost_input=0.30, cost_output=0.50,
        ))
        return reg

    def test_domain_ranking(self):
        reg = self._registry_with_models()
        ranked = reg.select("instruction")
        names = [p.name for p in ranked]
        assert names[0] == "model/high"   # 1.0
        assert names[1] == "model/mid"    # 0.85
        assert names[2] == "model/low"    # 0.60

    def test_domain_ranking_adversarial(self):
        reg = self._registry_with_models()
        ranked = reg.select("adversarial")
        names = [p.name for p in ranked]
        # model/mid is 1.0, model/high is 0.5, model/low unmeasured (last)
        assert names[0] == "model/mid"
        assert names[1] == "model/high"
        assert names[2] == "model/low"

    def test_unmeasured_domain_at_end(self):
        reg = self._registry_with_models()
        ranked = reg.select("adversarial")
        # model/low has no adversarial score → sorted last
        assert ranked[-1].name == "model/low"

    def test_budget_filtering(self):
        reg = self._registry_with_models()
        # model/high costs ~0.0032 per call, model/mid costs ~0.00035
        ranked = reg.select("instruction", budget_usd=0.001)
        names = [p.name for p in ranked]
        assert "model/high" not in names  # too expensive
        assert "model/mid" in names

    def test_unknown_cost_passes_budget_filter(self):
        reg = ModelRegistry()
        reg.register(_make_profile("model/nocost", detection={"x": 0.9}))
        ranked = reg.select("x", budget_usd=0.0001)
        assert len(ranked) == 1  # unknown cost → not filtered

    def test_disqualified_excluded(self):
        reg = ModelRegistry()
        reg.register(_make_profile("model/good", detection={"x": 1.0}))
        reg.register(_make_profile("model/bad", detection={"x": 1.0}, disqualified=True))
        ranked = reg.select("x")
        names = [p.name for p in ranked]
        assert "model/good" in names
        assert "model/bad" not in names

    def test_disqualified_included_when_requested(self):
        reg = ModelRegistry()
        reg.register(_make_profile("model/bad", detection={"x": 1.0}, disqualified=True))
        ranked = reg.select("x", exclude_disqualified=False)
        assert len(ranked) == 1

    def test_min_detection_rate(self):
        reg = self._registry_with_models()
        ranked = reg.select("instruction", min_detection_rate=0.9)
        names = [p.name for p in ranked]
        assert "model/high" in names    # 1.0 ≥ 0.9
        assert "model/mid" not in names  # 0.85 < 0.9
        # model/low: 0.60 < 0.9, excluded
        assert "model/low" not in names

    def test_max_false_positive_rate(self):
        reg = ModelRegistry()
        reg.register(_make_profile(
            "model/precise", detection={"x": 0.8}, fp={"x": 0.0},
        ))
        reg.register(_make_profile(
            "model/noisy", detection={"x": 1.0}, fp={"x": 0.5},
        ))
        ranked = reg.select("x", max_false_positive_rate=0.1)
        names = [p.name for p in ranked]
        assert "model/precise" in names
        assert "model/noisy" not in names

    def test_unmeasured_passes_detection_filter(self):
        """Models with no score for a domain pass min/max filters."""
        reg = ModelRegistry()
        reg.register(_make_profile("model/unknown"))  # no domain scores
        ranked = reg.select("anything", min_detection_rate=0.9)
        assert len(ranked) == 1

    def test_cost_tiebreaker(self):
        """Equal detection rate → cheaper model first."""
        reg = ModelRegistry()
        reg.register(_make_profile(
            "model/expensive",
            detection={"x": 1.0},
            cost_input=10.0, cost_output=10.0,
        ))
        reg.register(_make_profile(
            "model/cheap",
            detection={"x": 1.0},
            cost_input=0.1, cost_output=0.1,
        ))
        ranked = reg.select("x")
        assert ranked[0].name == "model/cheap"

    def test_empty_registry_returns_empty(self):
        reg = ModelRegistry()
        assert reg.select("anything") == []


# ---------------------------------------------------------------------------
# Default profiles
# ---------------------------------------------------------------------------


class TestDefaultProfiles:
    def test_with_defaults_loads_profiles(self):
        reg = ModelRegistry.with_defaults()
        profiles = reg.list_profiles()
        assert len(profiles) >= 5

    def test_haiku_first_for_instruction(self):
        reg = ModelRegistry.with_defaults()
        ranked = reg.select("instruction")
        assert ranked[0].name == "anthropic/haiku-4.5"

    def test_gemini_or_grok_first_for_adversarial(self):
        reg = ModelRegistry.with_defaults()
        ranked = reg.select("adversarial")
        # Both are 100%; Gemini is cheaper → Gemini first
        assert ranked[0].name == "google/gemini-2.0-flash"
        assert ranked[1].name == "x-ai/grok-3-mini"

    def test_gpt4o_mini_disqualified(self):
        reg = ModelRegistry.with_defaults()
        ranked = reg.select("instruction")
        names = [p.name for p in ranked]
        assert "openai/gpt-4o-mini" not in names

    def test_gpt4o_mini_profile_exists(self):
        """Profile exists even though it's disqualified."""
        reg = ModelRegistry.with_defaults()
        p = reg.get("openai/gpt-4o-mini")
        assert p.disqualified

    def test_semantic_db_ranking(self):
        reg = ModelRegistry.with_defaults()
        ranked = reg.select("semantic_db")
        # Gemini and Grok at 100%, then Qwen at 60%, then Haiku at 56%
        assert ranked[0].name in ("google/gemini-2.0-flash", "x-ai/grok-3-mini")
        # Haiku has lower detection than Qwen on semantic_db
        haiku_idx = next(i for i, p in enumerate(ranked) if p.name == "anthropic/haiku-4.5")
        qwen_idx = next(i for i, p in enumerate(ranked) if p.name == "qwen/qwen-2.5-72b")
        assert haiku_idx > qwen_idx


# ---------------------------------------------------------------------------
# Evaluator construction
# ---------------------------------------------------------------------------


class TestEvaluatorConstruction:
    def test_missing_api_key_raises(self):
        reg = ModelRegistry()
        reg.register(_make_profile("test/model", api_key_env="NONEXISTENT_KEY_12345"))
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="NONEXISTENT_KEY_12345"):
                reg.make_evaluator("anything", model_name="test/model")

    def test_anthropic_provider_makes_anthropic_evaluator(self):
        reg = ModelRegistry()
        reg.register(_make_profile(
            "test/claude",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_ANTHROPIC_KEY",
            detection={"x": 1.0},
        ))
        with patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "sk-test-fake"}):
            evaluator = reg.make_evaluator("x", model_name="test/claude")
        from arbiter.evaluator import AnthropicEvaluator
        assert isinstance(evaluator, AnthropicEvaluator)

    def test_openrouter_provider_makes_openai_evaluator(self):
        reg = ModelRegistry()
        reg.register(ModelProfile(
            name="test/openrouter",
            api_model_id="test-model",
            provider=Provider.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key_env="TEST_OR_KEY",
            domain_scores={"x": DomainScore(
                detection_rate=1.0, false_positive_rate=0.0, n_trials=10,
            )},
        ))
        with patch.dict(os.environ, {"TEST_OR_KEY": "sk-test-fake"}):
            evaluator = reg.make_evaluator("x", model_name="test/openrouter")
        from arbiter.evaluator import OpenAICompatibleEvaluator
        assert isinstance(evaluator, OpenAICompatibleEvaluator)

    def test_empty_registry_make_evaluator_raises(self):
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="No models qualify"):
            reg.make_evaluator("anything")

    def test_make_evaluator_selects_best(self):
        reg = ModelRegistry()
        reg.register(_make_profile(
            "model/best",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_KEY",
            detection={"x": 1.0},
        ))
        reg.register(_make_profile(
            "model/worse",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_KEY",
            detection={"x": 0.5},
        ))
        with patch.dict(os.environ, {"TEST_KEY": "sk-test-fake"}):
            evaluator = reg.make_evaluator("x")
        # Should have picked model/best
        assert evaluator._model == "model/best-id"

    def test_make_ensemble(self):
        reg = ModelRegistry()
        reg.register(_make_profile(
            "model/a",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_KEY",
            detection={"x": 1.0},
        ))
        reg.register(_make_profile(
            "model/b",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_KEY",
            detection={"x": 0.8},
        ))
        with patch.dict(os.environ, {"TEST_KEY": "sk-test-fake"}):
            ensemble = reg.make_ensemble("x")
        from arbiter.evaluator import EnsembleEvaluator
        assert isinstance(ensemble, EnsembleEvaluator)
        assert len(ensemble._evaluators) == 2

    def test_make_ensemble_explicit_models(self):
        reg = ModelRegistry()
        reg.register(_make_profile(
            "model/a",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_KEY",
        ))
        reg.register(_make_profile(
            "model/b",
            provider=Provider.ANTHROPIC,
            api_key_env="TEST_KEY",
        ))
        with patch.dict(os.environ, {"TEST_KEY": "sk-test-fake"}):
            ensemble = reg.make_ensemble("x", model_names=["model/b", "model/a"])
        assert len(ensemble._evaluators) == 2

    def test_make_ensemble_empty_raises(self):
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="No models qualify"):
            reg.make_ensemble("anything")
