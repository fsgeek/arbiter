"""Deterministic decision policy for tensor-entry adjudication.

This module defines configurable routing logic for tensor v2 entries:
`accept`, `clarify`, `rewrite`, `reject`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .interference_tensor import AdjudicationDecision, DrafterIdentity, TensorEntryV2
from .prompt_blocks import Severity, Tier


class DecisionPolicyConfig(BaseModel):
    """Thresholds and knobs for deterministic adjudication decisions."""

    tau_reject: float = Field(default=0.80, ge=0.0, le=1.0)
    tau_clarify: float = Field(default=0.60, ge=0.0, le=1.0)
    tau_rewrite: float = Field(default=0.45, ge=0.0, le=1.0)
    high_risk_scopes: list[str] = Field(
        default_factory=lambda: [
            "safety",
            "security",
            "privacy",
            "data-loss",
            "financial",
            "deployment",
        ]
    )


def _tier_rank(tier: Tier | None) -> int:
    if tier == Tier.system:
        return 3
    if tier == Tier.domain:
        return 2
    if tier == Tier.application:
        return 1
    return 0


class DeterministicDecisionPolicy:
    """Deterministic, auditable decision policy for tensor v2 entries."""

    def __init__(self, config: DecisionPolicyConfig | None = None) -> None:
        self._config = config or DecisionPolicyConfig()

    @property
    def config(self) -> DecisionPolicyConfig:
        return self._config

    def decide(self, entry: TensorEntryV2) -> AdjudicationDecision:
        """Compute routing decision for one tensor entry."""
        high_risk_scope = self._is_high_risk_scope(entry)
        precedence_crossing = self._is_precedence_crossing(entry)

        # Hard reject conditions: high conflict on critical or high-risk paths.
        if (
            entry.f >= self._config.tau_reject
            and (
                entry.severity == Severity.critical
                or high_risk_scope
                or precedence_crossing
            )
        ):
            return AdjudicationDecision.reject

        # Clarify for high indeterminacy in risky/critical contexts.
        if entry.i >= self._config.tau_clarify and (
            high_risk_scope
            or entry.severity in (Severity.major, Severity.critical)
            or entry.drafter_identity == DrafterIdentity.unknown
        ):
            return AdjudicationDecision.clarify

        # Rewrite for moderate conflict/ambiguity when not hard reject/clarify.
        if entry.f >= self._config.tau_rewrite or entry.i >= self._config.tau_rewrite:
            return AdjudicationDecision.rewrite

        return AdjudicationDecision.accept

    def _is_precedence_crossing(self, entry: TensorEntryV2) -> bool:
        """True when conflict spans unequal precedence tiers."""
        return _tier_rank(entry.tier_a) != _tier_rank(entry.tier_b)

    def _is_high_risk_scope(self, entry: TensorEntryV2) -> bool:
        scopes = " ".join(entry.scope_tags).lower()
        return any(tag in scopes for tag in self._config.high_risk_scopes)

