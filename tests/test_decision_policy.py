"""Tests for deterministic tensor-entry decision policy."""

import pytest

from arbiter.decision_policy import DecisionPolicyConfig, DeterministicDecisionPolicy
from arbiter.interference_tensor import (
    AdjudicationDecision,
    DrafterIdentity,
    TensorEntryV2,
)
from arbiter.prompt_blocks import Severity, Tier


def _entry(**kwargs) -> TensorEntryV2:
    base = {
        "block_a": "a",
        "block_b": "b",
        "rule": "mandate-prohibition-conflict",
        "score": 0.5,
        "severity": Severity.major,
        "t": 0.2,
        "i": 0.3,
        "f": 0.5,
        "tier_a": Tier.system,
        "tier_b": Tier.application,
        "scope_tags": ["workflow"],
        "canon_tags": ["higher-tier-over-lower-tier"],
        "drafter_identity": DrafterIdentity.unknown,
        "evidence_quality": 0.7,
    }
    base.update(kwargs)
    return TensorEntryV2(**base)


class TestDeterministicDecisionPolicy:
    def test_reject_for_high_conflict_critical(self):
        policy = DeterministicDecisionPolicy()
        decision = policy.decide(
            _entry(
                severity=Severity.critical,
                f=0.9,
                i=0.2,
            )
        )
        assert decision == AdjudicationDecision.reject

    def test_clarify_for_high_indeterminacy_unknown_drafter(self):
        policy = DeterministicDecisionPolicy()
        decision = policy.decide(
            _entry(
                i=0.8,
                f=0.3,
                drafter_identity=DrafterIdentity.unknown,
            )
        )
        assert decision == AdjudicationDecision.clarify

    def test_rewrite_for_moderate_conflict(self):
        policy = DeterministicDecisionPolicy()
        decision = policy.decide(
            _entry(
                i=0.2,
                f=0.5,
                severity=Severity.minor,
                drafter_identity=DrafterIdentity.user,
            )
        )
        assert decision == AdjudicationDecision.rewrite

    def test_accept_for_low_conflict_and_low_i(self):
        policy = DeterministicDecisionPolicy()
        decision = policy.decide(
            _entry(
                i=0.1,
                f=0.2,
                severity=Severity.minor,
                drafter_identity=DrafterIdentity.user,
            )
        )
        assert decision == AdjudicationDecision.accept

    def test_custom_thresholds(self):
        policy = DeterministicDecisionPolicy(
            DecisionPolicyConfig(
                tau_reject=0.95,
                tau_clarify=0.7,
                tau_rewrite=0.55,
            )
        )
        decision = policy.decide(
            _entry(
                i=0.54,
                f=0.54,
                severity=Severity.minor,
                drafter_identity=DrafterIdentity.user,
            )
        )
        # With stricter thresholds, this no longer rewrites/clarifies.
        assert decision == AdjudicationDecision.accept


class TestDecisionPolicyConfig:
    def test_threshold_validation(self):
        with pytest.raises(Exception):
            DecisionPolicyConfig(tau_reject=1.5)
