"""Interference tensor — structured output from block-level evaluation.

The tensor is sparse over (block_a, block_b, rule) → score.
Each dimension on axis 2 corresponds to an evaluation rule.
Adding a new rule extends axis 2 without invalidating existing dimensions.

The tensor is the core output artifact: it tells you where interference
exists, how severe it is, and what rule detected it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .prompt_blocks import Severity, Tier


class TensorEntry(BaseModel):
    """A single entry in the interference tensor."""

    block_a: str
    block_b: str
    rule: str
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str | None = None


class AdjudicationDecision(str, Enum):
    """Tier-gated runtime decision for a tensor entry."""

    accept = "accept"
    clarify = "clarify"
    rewrite = "rewrite"
    reject = "reject"


class DrafterIdentity(str, Enum):
    """Who authored the ambiguous clause under adjudication."""

    provider = "provider"
    operator = "operator"
    user = "user"
    unknown = "unknown"


class TensorDeclaredLoss(BaseModel):
    """Structured declared loss attached to an adjudication entry."""

    what: str
    why: str
    severity: float = Field(ge=0.0, le=1.0)


class TensorEntryV2(BaseModel):
    """Extended tensor entry with T/I/F channels and adjudication context."""

    # Backward-compatible core
    block_a: str
    block_b: str
    rule: str
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str | None = None

    # Neutrosophic-style channels for normative adjudication
    t: float = Field(ge=0.0, le=1.0)
    i: float = Field(ge=0.0, le=1.0)
    f: float = Field(ge=0.0, le=1.0)

    # Context and governance
    tier_a: Tier | None = None
    tier_b: Tier | None = None
    scope_tags: list[str] = Field(default_factory=list)
    canon_tags: list[str] = Field(default_factory=list)
    drafter_identity: DrafterIdentity = DrafterIdentity.unknown
    evidence_quality: float = Field(default=0.5, ge=0.0, le=1.0)

    # Loss channel
    declared_losses: list[TensorDeclaredLoss] = Field(default_factory=list)

    # Optional routing output
    decision: AdjudicationDecision | None = None


class InterferenceTensor(BaseModel):
    """Sparse tensor over (block_a, block_b, rule) → score.

    Axes:
      0, 1: block IDs (symmetric — order doesn't matter)
      2: rule names

    Only non-zero entries are stored. This is the natural representation
    for prompt analysis where most block pairs don't interfere.
    """

    schema_version: int = Field(default=1, description="Tensor schema version (1 = scalar, 2 = extended)")
    block_ids: list[str] = Field(default_factory=list, description="All block IDs (axes 0 and 1)")
    rule_names: list[str] = Field(default_factory=list, description="All rule names (axis 2)")
    entries: list[TensorEntry] = Field(default_factory=list, description="Sparse non-zero entries")
    entries_v2: list[TensorEntryV2] = Field(
        default_factory=list,
        description="Extended schema entries with T/I/F channels",
    )
    migration_notes: list[str] = Field(
        default_factory=list,
        description="Optional notes describing schema migration assumptions",
    )

    @classmethod
    def from_scores(
        cls,
        block_ids: list[str],
        rule_names: list[str],
        entries: list[TensorEntry],
        *,
        threshold: float = 0.0,
    ) -> InterferenceTensor:
        """Construct from evaluation results, filtering by threshold."""
        filtered = [e for e in entries if e.score > threshold]
        return cls(
            schema_version=1,
            block_ids=block_ids,
            rule_names=rule_names,
            entries=filtered,
        )

    @classmethod
    def from_scores_v2(
        cls,
        block_ids: list[str],
        rule_names: list[str],
        entries_v2: list[TensorEntryV2],
        *,
        threshold: float = 0.0,
    ) -> InterferenceTensor:
        """Construct a schema v2 tensor from extended entries."""
        filtered = [e for e in entries_v2 if e.score > threshold]
        return cls(
            schema_version=2,
            block_ids=block_ids,
            rule_names=rule_names,
            entries_v2=filtered,
        )

    def to_v2_entries(
        self,
        *,
        default_evidence_quality: float = 0.5,
    ) -> list[TensorEntryV2]:
        """Deterministically map v1 entries to v2 entries.

        Mapping:
          f = score
          i = 1 - evidence_quality
          t = max(0, 1 - max(f, i))
        """
        i_value = 1.0 - default_evidence_quality
        result: list[TensorEntryV2] = []
        for entry in self.entries:
            f_value = entry.score
            t_value = max(0.0, 1.0 - max(f_value, i_value))
            result.append(
                TensorEntryV2(
                    block_a=entry.block_a,
                    block_b=entry.block_b,
                    rule=entry.rule,
                    score=entry.score,
                    severity=entry.severity,
                    explanation=entry.explanation,
                    t=t_value,
                    i=i_value,
                    f=f_value,
                    evidence_quality=default_evidence_quality,
                )
            )
        return result

    def to_v2_tensor(
        self,
        *,
        default_evidence_quality: float = 0.5,
    ) -> InterferenceTensor:
        """Create a schema v2 tensor while preserving v1 entries."""
        v2_entries = self.to_v2_entries(
            default_evidence_quality=default_evidence_quality
        )
        note = (
            "Auto-migrated from schema v1: "
            "f=score, i=1-evidence_quality, t=max(0,1-max(f,i))."
        )
        return InterferenceTensor(
            schema_version=2,
            block_ids=list(self.block_ids),
            rule_names=list(self.rule_names),
            entries=list(self.entries),
            entries_v2=v2_entries,
            migration_notes=[note],
        )

    def summary_score(self) -> float:
        """Aggregate score: max severity-weighted score across all entries.

        Weighting: critical=1.0, major=0.6, minor=0.3.
        Returns 0.0 if no entries.
        """
        if not self.entries:
            return 0.0
        weights = {Severity.critical: 1.0, Severity.major: 0.6, Severity.minor: 0.3}
        return max(e.score * weights.get(e.severity, 0.5) for e in self.entries)

    def by_severity(self) -> dict[Severity, list[TensorEntry]]:
        """Group entries by severity level."""
        result: dict[Severity, list[TensorEntry]] = {}
        for entry in self.entries:
            result.setdefault(entry.severity, []).append(entry)
        return result

    def by_rule(self) -> dict[str, list[TensorEntry]]:
        """Group entries by rule name."""
        result: dict[str, list[TensorEntry]] = {}
        for entry in self.entries:
            result.setdefault(entry.rule, []).append(entry)
        return result

    def by_block(self, block_id: str) -> list[TensorEntry]:
        """All entries involving a specific block."""
        return [e for e in self.entries if e.block_a == block_id or e.block_b == block_id]

    def top_n(self, n: int = 10) -> list[TensorEntry]:
        """Top N entries by severity-weighted score, descending."""
        weights = {Severity.critical: 1.0, Severity.major: 0.6, Severity.minor: 0.3}
        return sorted(
            self.entries,
            key=lambda e: e.score * weights.get(e.severity, 0.5),
            reverse=True,
        )[:n]

    def shape(self) -> tuple[int, int, int]:
        """Logical shape: (n_blocks, n_blocks, n_rules)."""
        n = len(self.block_ids)
        r = len(self.rule_names)
        return (n, n, r)

    def density(self) -> float:
        """Fraction of tensor cells that have non-zero entries.

        For a symmetric tensor with no self-pairs, the total possible
        entries are n*(n-1)/2 * r.
        """
        n = len(self.block_ids)
        r = len(self.rule_names)
        possible = n * (n - 1) // 2 * r
        if possible == 0:
            return 0.0
        return len(self.entries) / possible

    def to_json(self) -> str:
        """Serializable JSON representation."""
        return self.model_dump_json(indent=2)

    def summary_report(self) -> str:
        """Human-readable summary of interference findings."""
        if not self.entries:
            return "No interference detected."

        lines = []
        lines.append(f"Interference tensor: {self.shape()} shape, {len(self.entries)} entries")
        lines.append(f"Summary score: {self.summary_score():.2f}")
        lines.append(f"Density: {self.density():.1%}")
        lines.append("")

        by_sev = self.by_severity()
        for sev in [Severity.critical, Severity.major, Severity.minor]:
            entries = by_sev.get(sev, [])
            if entries:
                lines.append(f"  {sev.value}: {len(entries)} finding(s)")
                for e in sorted(entries, key=lambda x: -x.score)[:5]:
                    lines.append(f"    {e.block_a} <-> {e.block_b} [{e.rule}]: {e.score:.2f}")
                    if e.explanation:
                        lines.append(f"      {e.explanation[:120]}")

        return "\n".join(lines)
