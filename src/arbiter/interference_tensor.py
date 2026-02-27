"""Interference tensor — structured output from block-level evaluation.

The tensor is sparse over (block_a, block_b, rule) → score.
Each dimension on axis 2 corresponds to an evaluation rule.
Adding a new rule extends axis 2 without invalidating existing dimensions.

The tensor is the core output artifact: it tells you where interference
exists, how severe it is, and what rule detected it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .prompt_blocks import Severity


class TensorEntry(BaseModel):
    """A single entry in the interference tensor."""

    block_a: str
    block_b: str
    rule: str
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str | None = None


class InterferenceTensor(BaseModel):
    """Sparse tensor over (block_a, block_b, rule) → score.

    Axes:
      0, 1: block IDs (symmetric — order doesn't matter)
      2: rule names

    Only non-zero entries are stored. This is the natural representation
    for prompt analysis where most block pairs don't interfere.
    """

    block_ids: list[str] = Field(default_factory=list, description="All block IDs (axes 0 and 1)")
    rule_names: list[str] = Field(default_factory=list, description="All rule names (axis 2)")
    entries: list[TensorEntry] = Field(default_factory=list, description="Sparse non-zero entries")

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
        return cls(block_ids=block_ids, rule_names=rule_names, entries=filtered)

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
