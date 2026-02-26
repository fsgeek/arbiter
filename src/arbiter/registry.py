"""Model registry — profile-driven evaluator selection and construction.

Maps empirical characterization data (from docs/cairn/) to evaluator
construction. The registry answers "what model should I use for this
domain?" and builds the evaluator automatically.

One-liner usage:
    registry = ModelRegistry.with_defaults()
    evaluator = registry.make_evaluator("instruction")
    result = evaluator.evaluate(system, domain, query)

All built-in profile numbers are empirical, from human-audited
characterization runs (sessions 1-3, 1,850 data points).
"""

from __future__ import annotations

import os
from enum import StrEnum

from pydantic import BaseModel, Field

from .evaluator import (
    AnthropicEvaluator,
    EnsembleEvaluator,
    EvaluatorProtocol,
    OpenAICompatibleEvaluator,
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class Provider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class DomainScore(BaseModel):
    """Empirical performance on a specific domain."""

    detection_rate: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)
    n_trials: int = Field(gt=0)


class ModelProfile(BaseModel):
    """Everything the registry knows about one model."""

    # Identity
    name: str
    api_model_id: str
    provider: Provider
    base_url: str | None = None
    api_key_env: str

    # Performance (from characterization data)
    domain_scores: dict[str, DomainScore] = Field(default_factory=dict)
    format_sensitivity: float | None = None
    known_issues: list[str] = Field(default_factory=list)
    disqualified: bool = False

    # Cost (per million tokens)
    cost_per_million_input: float | None = None
    cost_per_million_output: float | None = None

    def estimated_cost_per_call(
        self,
        avg_input_tokens: int = 1500,
        avg_output_tokens: int = 500,
    ) -> float | None:
        """Estimate cost of a single evaluate() call.

        Returns None if pricing is unknown. Default token counts are
        typical for Arbiter's judge prompt + response.
        """
        if self.cost_per_million_input is None or self.cost_per_million_output is None:
            return None
        return (
            self.cost_per_million_input * avg_input_tokens / 1_000_000
            + self.cost_per_million_output * avg_output_tokens / 1_000_000
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ModelRegistry:
    """Registry of model profiles with domain-aware selection."""

    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}

    # -- Core operations --

    def register(self, profile: ModelProfile) -> None:
        """Add or overwrite a model profile."""
        self._profiles[profile.name] = profile

    def get(self, name: str) -> ModelProfile:
        """Retrieve a profile by name. Raises KeyError if missing."""
        try:
            return self._profiles[name]
        except KeyError:
            raise KeyError(
                f"No model profile named {name!r}. "
                f"Registered: {sorted(self._profiles)}"
            ) from None

    def list_profiles(self) -> list[ModelProfile]:
        """All registered profiles, in insertion order."""
        return list(self._profiles.values())

    # -- Selection --

    def select(
        self,
        domain: str,
        *,
        budget_usd: float | None = None,
        min_detection_rate: float = 0.0,
        max_false_positive_rate: float = 1.0,
        exclude_disqualified: bool = True,
    ) -> list[ModelProfile]:
        """Rank models for a domain, best first.

        Filtering:
        - Disqualified models excluded by default.
        - Budget filters on estimated_cost_per_call (unknown cost passes).
        - min_detection_rate / max_false_positive_rate filter on domain scores
          (unmeasured domains pass — we don't penalize lack of data).

        Sorting:
        - Models with domain scores sort by detection_rate desc, then cost asc.
        - Unmeasured models sort to the end.
        """
        candidates: list[ModelProfile] = []

        for profile in self._profiles.values():
            if exclude_disqualified and profile.disqualified:
                continue

            if budget_usd is not None:
                cost = profile.estimated_cost_per_call()
                if cost is not None and cost > budget_usd:
                    continue

            score = profile.domain_scores.get(domain)
            if score is not None:
                if score.detection_rate < min_detection_rate:
                    continue
                if score.false_positive_rate > max_false_positive_rate:
                    continue

            candidates.append(profile)

        def sort_key(p: ModelProfile) -> tuple[int, float, float]:
            score = p.domain_scores.get(domain)
            if score is None:
                # Unmeasured: sort to end (has_score=1 > 0)
                return (1, 0.0, 0.0)
            cost = p.estimated_cost_per_call() or 0.0
            # has_score=0 (sorts first), -detection (desc), +cost (asc)
            return (0, -score.detection_rate, cost)

        candidates.sort(key=sort_key)
        return candidates

    # -- Evaluator construction --

    def make_evaluator(
        self,
        domain: str,
        *,
        budget_usd: float | None = None,
        model_name: str | None = None,
    ) -> EvaluatorProtocol:
        """Build an evaluator for the best model on this domain.

        If model_name is given, uses that profile directly.
        Otherwise, selects the top-ranked model via select().

        Reads the API key from os.environ at construction time.
        Raises ValueError if the key is missing or no models qualify.
        """
        if model_name is not None:
            profile = self.get(model_name)
        else:
            ranked = self.select(domain, budget_usd=budget_usd)
            if not ranked:
                raise ValueError(
                    f"No models qualify for domain {domain!r} "
                    f"with budget_usd={budget_usd}"
                )
            profile = ranked[0]

        return self._build_evaluator(profile)

    def make_ensemble(
        self,
        domain: str,
        *,
        budget_usd: float | None = None,
        model_names: list[str] | None = None,
        max_models: int = 2,
    ) -> EnsembleEvaluator:
        """Build an ensemble evaluator for a domain.

        If model_names is given, uses those profiles.
        Otherwise, selects the top N models via select().
        """
        if model_names is not None:
            profiles = [self.get(name) for name in model_names]
        else:
            ranked = self.select(domain, budget_usd=budget_usd)
            if not ranked:
                raise ValueError(
                    f"No models qualify for domain {domain!r} "
                    f"with budget_usd={budget_usd}"
                )
            profiles = ranked[:max_models]

        evaluators = [self._build_evaluator(p) for p in profiles]
        return EnsembleEvaluator(evaluators)

    def _build_evaluator(self, profile: ModelProfile) -> EvaluatorProtocol:
        """Construct a single evaluator from a profile."""
        api_key = os.environ.get(profile.api_key_env)
        if not api_key:
            raise ValueError(
                f"API key not found: set {profile.api_key_env} in environment "
                f"(required for model {profile.name!r})"
            )

        if profile.provider == Provider.ANTHROPIC:
            return AnthropicEvaluator(
                model=profile.api_model_id,
                api_key=api_key,
            )
        else:
            # OPENAI and OPENROUTER both use OpenAI-compatible API
            kwargs: dict = {
                "model": profile.api_model_id,
                "api_key": api_key,
            }
            if profile.base_url is not None:
                kwargs["base_url"] = profile.base_url
            return OpenAICompatibleEvaluator(**kwargs)

    # -- Factory --

    @classmethod
    def with_defaults(cls) -> ModelRegistry:
        """Create a registry pre-loaded with built-in model profiles.

        All numbers are empirical, from human-audited characterization
        runs (docs/cairn/). See MEMORY.md for session details.
        """
        registry = cls()
        for profile in _DEFAULT_PROFILES:
            registry.register(profile)
        return registry


# ---------------------------------------------------------------------------
# Built-in profiles — empirical data from characterization sessions 1-3
# ---------------------------------------------------------------------------

_DEFAULT_PROFILES: list[ModelProfile] = [
    ModelProfile(
        name="anthropic/haiku-4.5",
        api_model_id="claude-haiku-4-5-20251001",
        provider=Provider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        domain_scores={
            "instruction": DomainScore(
                detection_rate=1.0,
                false_positive_rate=0.0,
                n_trials=25,  # system_prompt_characterization: 20/20 + 5/5 clean
            ),
            "semantic_db": DomainScore(
                detection_rate=0.56,  # 14/25 across format variants
                false_positive_rate=0.0,
                n_trials=25,
            ),
            "adversarial": DomainScore(
                detection_rate=0.33,  # 5/15 (tier3 only)
                false_positive_rate=0.0,
                n_trials=15,
            ),
        },
        format_sensitivity=1.0,  # 0-100% across formats
        known_issues=[
            "Extreme format sensitivity: 0% to 100% depending on prompt format.",
            "Adversarial: only catches tier 3 (meta-cognitive cue).",
        ],
        cost_per_million_input=0.80,
        cost_per_million_output=4.00,
    ),
    ModelProfile(
        name="google/gemini-2.0-flash",
        api_model_id="google/gemini-2.0-flash-001",
        provider=Provider.OPENROUTER,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        domain_scores={
            "instruction": DomainScore(
                detection_rate=0.85,  # 17/20 on system prompt
                false_positive_rate=0.0,
                n_trials=25,
            ),
            "semantic_db": DomainScore(
                detection_rate=1.0,  # 20/20
                false_positive_rate=0.0,
                n_trials=20,
            ),
            "adversarial": DomainScore(
                detection_rate=1.0,  # 15/15
                false_positive_rate=0.0,
                n_trials=15,
            ),
        },
        format_sensitivity=0.0,
        known_issues=[
            "Content-filters may reject some prompts.",
            "Rationalizes nuanced instruction conflicts (85%, not 100%).",
        ],
        cost_per_million_input=0.10,
        cost_per_million_output=0.40,
    ),
    ModelProfile(
        name="x-ai/grok-3-mini",
        api_model_id="x-ai/grok-3-mini-beta",
        provider=Provider.OPENROUTER,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        domain_scores={
            "instruction": DomainScore(
                detection_rate=0.75,  # 15/20 on system prompt
                false_positive_rate=0.0,
                n_trials=25,
            ),
            "semantic_db": DomainScore(
                detection_rate=1.0,  # 20/20
                false_positive_rate=0.0,
                n_trials=20,
            ),
            "adversarial": DomainScore(
                detection_rate=1.0,  # 15/15
                false_positive_rate=0.0,
                n_trials=15,
            ),
        },
        format_sensitivity=0.0,
        known_issues=[
            "Rationalizes nuanced conflicts as complementary conditions.",
            "Instruction domain: misses task-search and proactive-vs-scope.",
        ],
        cost_per_million_input=0.30,
        cost_per_million_output=0.50,
    ),
    ModelProfile(
        name="openai/gpt-4o-mini",
        api_model_id="openai/gpt-4o-mini",
        provider=Provider.OPENROUTER,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        domain_scores={
            "instruction": DomainScore(
                detection_rate=1.0,   # 20/20, but 100% FP
                false_positive_rate=1.0,  # 5/5 clean-control flagged
                n_trials=25,
            ),
            "semantic_db": DomainScore(
                detection_rate=1.0,  # 20/20
                false_positive_rate=0.0,
                n_trials=20,
            ),
            "adversarial": DomainScore(
                detection_rate=0.60,  # 9/15 (misses tier2-buried)
                false_positive_rate=0.0,
                n_trials=15,
            ),
        },
        format_sensitivity=0.0,
        disqualified=True,
        known_issues=[
            "DISQUALIFIED: 100% false positive rate on instruction domain.",
            "Fabricates plausible conflict narratives for non-conflicts.",
            "Same pattern as ai-honesty self-report inversion.",
        ],
        cost_per_million_input=0.15,
        cost_per_million_output=0.60,
    ),
    ModelProfile(
        name="qwen/qwen-2.5-72b",
        api_model_id="qwen/qwen-2.5-72b-instruct",
        provider=Provider.OPENROUTER,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        domain_scores={
            "semantic_db": DomainScore(
                detection_rate=0.60,  # 12/20
                false_positive_rate=0.0,
                n_trials=20,
            ),
            "adversarial": DomainScore(
                detection_rate=0.40,  # 6/15
                false_positive_rate=0.0,
                n_trials=15,
            ),
        },
        format_sensitivity=1.0,  # 0-100% inverse of Haiku
        known_issues=[
            "Extreme format sensitivity: inverse of Haiku (colon-labels kills it).",
            "Not tested on instruction domain.",
        ],
        cost_per_million_input=0.90,
        cost_per_million_output=0.90,
    ),
]
