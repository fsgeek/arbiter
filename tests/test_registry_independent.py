from __future__ import annotations

from unittest.mock import patch

import enum

import pytest
from pydantic import ValidationError

if not hasattr(enum, "StrEnum"):
    class _CompatStrEnum(str, enum.Enum):
        pass

    enum.StrEnum = _CompatStrEnum  # type: ignore[attr-defined]

from arbiter.evaluator import EnsembleEvaluator
from arbiter.registry import DomainScore, ModelProfile, ModelRegistry, Provider


def make_profile(
    name: str,
    *,
    provider: Provider = Provider.OPENROUTER,
    domains: dict[str, tuple[float, float]] | None = None,
    base_url: str | None = None,
    disqualified: bool = False,
    cost_per_million_input: float | None = 1.0,
    cost_per_million_output: float | None = 1.0,
    api_key_env: str | None = None,
) -> ModelProfile:
    domain_scores = {}
    if domains:
        for domain_name, (detection_rate, false_positive_rate) in domains.items():
            domain_scores[domain_name] = DomainScore(
                detection_rate=detection_rate,
                false_positive_rate=false_positive_rate,
                n_trials=10,
            )

    return ModelProfile(
        name=name,
        api_model_id=f"{name}-model",
        provider=provider,
        base_url=base_url,
        api_key_env=api_key_env or f"{name.upper()}_API_KEY",
        domain_scores=domain_scores,
        disqualified=disqualified,
        cost_per_million_input=cost_per_million_input,
        cost_per_million_output=cost_per_million_output,
    )


def test_model_profile_cost_estimation_and_attributes() -> None:
    profile = make_profile(
        "haiku-like",
        provider=Provider.ANTHROPIC,
        domains={"instruction": (0.9, 0.1)},
        cost_per_million_input=1.0,
        cost_per_million_output=2.0,
    )

    assert profile.domain_scores["instruction"].detection_rate == pytest.approx(0.9)

    cost = profile.estimated_cost_per_call(avg_input_tokens=2000, avg_output_tokens=1000)
    assert cost == pytest.approx(0.004)

    unknown_cost_profile = make_profile(
        "unknown",
        domains={"instruction": (0.5, 0.0)},
        cost_per_million_input=None,
        cost_per_million_output=None,
    )
    assert unknown_cost_profile.estimated_cost_per_call() is None


def test_model_profile_validation_enforces_domain_score_ranges() -> None:
    with pytest.raises(ValidationError):
        ModelProfile(
            name="invalid-score",
            api_model_id="invalid-model",
            provider=Provider.ANTHROPIC,
            api_key_env="INVALID_KEY",
            domain_scores={
                "instruction": {
                    "detection_rate": 1.5,
                    "false_positive_rate": 0.0,
                    "n_trials": 5,
                }
            },
        )


def test_registry_register_get_list_and_overwrite_behavior() -> None:
    registry = ModelRegistry()
    profile_a = make_profile("model-a", domains={"instruction": (0.8, 0.1)})
    profile_b = make_profile("model-b", domains={"instruction": (0.7, 0.0)})

    registry.register(profile_a)
    registry.register(profile_b)

    assert registry.get("model-a") is profile_a
    assert registry.list_profiles() == [profile_a, profile_b]

    replacement = make_profile("model-a", domains={"instruction": (0.9, 0.0)})
    registry.register(replacement)

    assert registry.get("model-a") is replacement
    assert registry.list_profiles()[0] is replacement


def test_registry_get_missing_includes_registered_names() -> None:
    registry = ModelRegistry()
    registry.register(make_profile("model-a"))

    with pytest.raises(KeyError) as excinfo:
        registry.get("missing")

    assert "Registered: ['model-a']" in str(excinfo.value)


def test_select_ranks_by_detection_rate_cost_and_unmeasured_domain_last() -> None:
    registry = ModelRegistry()
    high = make_profile("high", domains={"instruction": (0.9, 0.0)}, cost_per_million_input=1.0, cost_per_million_output=1.0)
    tie_cheaper = make_profile("tie-cheap", domains={"instruction": (0.8, 0.0)}, cost_per_million_input=1.0, cost_per_million_output=1.0)
    tie_expensive = make_profile("tie-expensive", domains={"instruction": (0.8, 0.0)}, cost_per_million_input=10.0, cost_per_million_output=10.0)
    unmeasured = make_profile("unmeasured", domains={})

    for profile in (high, tie_cheaper, tie_expensive, unmeasured):
        registry.register(profile)

    ranked = registry.select("instruction")
    assert [p.name for p in ranked[:3]] == ["high", "tie-cheap", "tie-expensive"]
    assert ranked[-1].name == "unmeasured"


def test_select_budget_filters_known_cost_and_allows_unknown_cost() -> None:
    registry = ModelRegistry()
    cheap = make_profile(
        "cheap",
        domains={"instruction": (0.8, 0.0)},
        cost_per_million_input=1.0,
        cost_per_million_output=1.0,
    )
    expensive = make_profile(
        "expensive",
        domains={"instruction": (0.95, 0.0)},
        cost_per_million_input=200.0,
        cost_per_million_output=200.0,
    )
    unknown = make_profile(
        "unknown-cost",
        domains={"instruction": (0.5, 0.0)},
        cost_per_million_input=None,
        cost_per_million_output=None,
    )

    for profile in (cheap, expensive, unknown):
        registry.register(profile)

    ranked = registry.select("instruction", budget_usd=0.01)
    assert [p.name for p in ranked] == ["cheap", "unknown-cost"]
    assert "expensive" not in [p.name for p in ranked]


def test_select_filters_by_detection_false_positive_and_disqualification() -> None:
    registry = ModelRegistry()
    qualified = make_profile("qualified", domains={"instruction": (0.8, 0.1)})
    low_detection = make_profile("low-detection", domains={"instruction": (0.3, 0.1)})
    high_fp = make_profile("high-fp", domains={"instruction": (0.9, 0.4)})
    disqualified = make_profile("dq", domains={"instruction": (0.95, 0.0)}, disqualified=True)

    for profile in (qualified, low_detection, high_fp, disqualified):
        registry.register(profile)

    ranked = registry.select(
        "instruction",
        min_detection_rate=0.5,
        max_false_positive_rate=0.2,
    )
    assert [p.name for p in ranked] == ["qualified"]

    ranked_with_disqualified = registry.select(
        "instruction",
        min_detection_rate=0.5,
        max_false_positive_rate=0.2,
        exclude_disqualified=False,
    )
    assert [p.name for p in ranked_with_disqualified] == ["dq", "qualified"]


def test_unmeasured_domain_passes_filters_and_sorts_last() -> None:
    registry = ModelRegistry()
    measured = make_profile("measured", domains={"semantic_db": (0.7, 0.0)})
    unmeasured = make_profile("unmeasured")
    registry.register(measured)
    registry.register(unmeasured)

    ranked = registry.select("instruction")
    assert ranked[-1].name == "unmeasured"
    assert measured in ranked


def test_with_defaults_expected_ranking_and_disqualification() -> None:
    registry = ModelRegistry.with_defaults()

    instruction_ranked = registry.select("instruction")
    assert instruction_ranked[0].name == "anthropic/haiku-4.5"
    assert "openai/gpt-4o-mini" not in [p.name for p in instruction_ranked]

    adversarial_ranked = registry.select("adversarial")
    assert adversarial_ranked[0].name == "google/gemini-2.0-flash"
    assert adversarial_ranked[1].name == "x-ai/grok-3-mini"


def test_make_evaluator_missing_api_key_raises_value_error() -> None:
    registry = ModelRegistry()
    registry.register(make_profile("needs-key", provider=Provider.ANTHROPIC, domains={"instruction": (0.8, 0.0)}, api_key_env="NEEDED_KEY"))

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            registry.make_evaluator("instruction")

    assert "NEEDED_KEY" in str(excinfo.value)


def test_make_evaluator_anthropic_provider_uses_anthropic_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ModelRegistry()
    profile = make_profile(
        "anthropic",
        provider=Provider.ANTHROPIC,
        domains={"instruction": (0.8, 0.0)},
        api_key_env="ANTHROPIC_API_KEY",
    )
    registry.register(profile)

    class StubAnthropicEvaluator:
        def __init__(self, *, model: str, api_key: str) -> None:
            self.model = model
            self.api_key = api_key

    monkeypatch.setattr("arbiter.registry.AnthropicEvaluator", StubAnthropicEvaluator)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "secret"}, clear=True):
        evaluator = registry.make_evaluator("instruction", model_name="anthropic")

    assert isinstance(evaluator, StubAnthropicEvaluator)
    assert evaluator.model == profile.api_model_id
    assert evaluator.api_key == "secret"


def test_make_evaluator_openrouter_provider_uses_openai_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ModelRegistry()
    profile = make_profile(
        "openrouter",
        provider=Provider.OPENROUTER,
        base_url="https://custom.example",
        domains={"instruction": (0.8, 0.0)},
        api_key_env="OPENROUTER_KEY",
    )
    registry.register(profile)

    class StubOpenAICompatible:
        def __init__(self, *, model: str, api_key: str, base_url: str | None = None) -> None:
            self.model = model
            self.api_key = api_key
            self.base_url = base_url

    monkeypatch.setattr("arbiter.registry.OpenAICompatibleEvaluator", StubOpenAICompatible)

    with patch.dict("os.environ", {"OPENROUTER_KEY": "token"}, clear=True):
        evaluator = registry.make_evaluator("instruction", model_name="openrouter")

    assert isinstance(evaluator, StubOpenAICompatible)
    assert evaluator.model == profile.api_model_id
    assert evaluator.api_key == "token"
    assert evaluator.base_url == profile.base_url


def test_make_ensemble_returns_ensemble_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ModelRegistry()
    first = make_profile("first", domains={"instruction": (0.9, 0.0)})
    second = make_profile("second", domains={"instruction": (0.8, 0.0)})
    registry.register(first)
    registry.register(second)

    class DummyEvaluator:
        def __init__(self, name: str) -> None:
            self.name = name

    def fake_build(self, profile: ModelProfile) -> DummyEvaluator:
        return DummyEvaluator(profile.name)

    monkeypatch.setattr(ModelRegistry, "_build_evaluator", fake_build, raising=False)

    ensemble = registry.make_ensemble("instruction", max_models=2)
    assert isinstance(ensemble, EnsembleEvaluator)
    assert [ev.name for ev in ensemble._evaluators] == ["first", "second"]


def test_make_evaluator_and_ensemble_raise_when_no_models_available() -> None:
    registry = ModelRegistry()

    with pytest.raises(ValueError):
        registry.make_evaluator("instruction")

    with pytest.raises(ValueError):
        registry.make_ensemble("instruction")
