"""Ablation tensor — empirical behavioral measurements in tensor form.

Extends the concept from InterferenceTensor with empirical measurements
(ablation deltas, p-values, position controls) rather than analytical
scores from static/LLM evaluation.

Dimensions:
    axis 0: block_id (free blocks)
    axis 1: probe_id
    axis 2: model_id

Cell value: AblationScore with baseline, ablated, delta, significance.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from ..interference_tensor import InterferenceTensor, TensorEntry
from ..prompt_blocks import Severity
from .configuration import AblationConfig
from .probe import ProbeResult


# ---------------------------------------------------------------------------
# AblationScore
# ---------------------------------------------------------------------------


class AblationScore(BaseModel):
    """Score for a single (block, probe, model) cell in the ablation tensor."""

    baseline_score: float = Field(description="Mean score with all blocks present")
    ablated_score: float = Field(description="Mean score with this block removed")
    delta: float = Field(description="ablated - baseline (negative = removal hurts)")
    p_value: float | None = Field(
        default=None,
        description="Statistical significance across trials (None if single trial)",
    )
    n_baseline_trials: int = Field(default=0)
    n_ablated_trials: int = Field(default=0)
    position_controlled: bool = Field(default=False)
    position_delta: float | None = Field(
        default=None,
        description="Delta from position-only condition (Phase 2)",
    )


# ---------------------------------------------------------------------------
# AblationTensor
# ---------------------------------------------------------------------------


class AblationTensor(BaseModel):
    """Sparse tensor: (block, probe, model) -> AblationScore.

    Extends the concept of InterferenceTensor with empirical
    measurements rather than analytical scores.
    """

    block_ids: list[str] = Field(default_factory=list)
    probe_ids: list[str] = Field(default_factory=list)
    model_ids: list[str] = Field(default_factory=list)
    entries: dict[str, AblationScore] = Field(
        default_factory=dict,
        description="Sparse entries keyed by 'block|probe|model'",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def _key(block_id: str, probe_id: str, model_id: str) -> str:
        return f"{block_id}|{probe_id}|{model_id}"

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str, str]:
        parts = key.split("|", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid tensor key: {key!r}")
        return parts[0], parts[1], parts[2]

    def get(
        self, block_id: str, probe_id: str, model_id: str
    ) -> AblationScore | None:
        """Look up a specific cell."""
        return self.entries.get(self._key(block_id, probe_id, model_id))

    def set(
        self, block_id: str, probe_id: str, model_id: str, score: AblationScore
    ) -> None:
        """Set a specific cell value."""
        key = self._key(block_id, probe_id, model_id)
        self.entries[key] = score

        # Maintain dimension lists
        if block_id not in self.block_ids:
            self.block_ids.append(block_id)
        if probe_id not in self.probe_ids:
            self.probe_ids.append(probe_id)
        if model_id not in self.model_ids:
            self.model_ids.append(model_id)

    @classmethod
    def from_run(
        cls,
        baseline_results: list[ProbeResult],
        phase0_results: list[ProbeResult],
        phase0_configs: list[AblationConfig],
        *,
        phase2_results: list[ProbeResult] | None = None,
    ) -> AblationTensor:
        """Assemble tensor from completed ablation run results.

        Args:
            baseline_results: Results from baseline configuration.
            phase0_results: Results from Phase 0 (single-block removal).
            phase0_configs: Phase 0 configs (each removes one block).
                The removed block is derived from config.absent_blocks[0]
                or config.metadata["removed_block"].
            phase2_results: Optional Phase 2 results for position control.

        Returns:
            An assembled AblationTensor.
        """
        tensor = cls()

        # Build config_id -> removed_block_id mapping from actual configs
        config_to_block: dict[str, str] = {}
        for config in phase0_configs:
            if config.metadata.get("removed_block"):
                removed = config.metadata["removed_block"]
            elif config.absent_blocks:
                removed = config.absent_blocks[0]
            else:
                continue
            config_to_block[config.id] = removed

        # Index baseline scores: (probe_id, model_id) -> list[float]
        baseline_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
        for r in baseline_results:
            baseline_scores[(r.probe_id, r.model_id)].append(r.score)

        # Index phase0 scores: (config_id, probe_id, model_id) -> list[float]
        phase0_scores: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        for r in phase0_results:
            phase0_scores[(r.config_id, r.probe_id, r.model_id)].append(r.score)

        # Index phase2 scores if available
        phase2_scores: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        if phase2_results:
            for r in phase2_results:
                phase2_scores[(r.config_id, r.probe_id, r.model_id)].append(r.score)

        # Build tensor entries from actual config IDs
        for config_id, block_id in config_to_block.items():
            for (probe_id, model_id), b_scores in baseline_scores.items():
                a_scores = phase0_scores.get(
                    (config_id, probe_id, model_id), []
                )
                if not a_scores:
                    continue

                baseline_mean = statistics.mean(b_scores)
                ablated_mean = statistics.mean(a_scores)
                delta = ablated_mean - baseline_mean

                p_value = _welch_t_test_p(b_scores, a_scores)

                # Check for position control data
                position_controlled = False
                position_delta = None
                if phase2_results:
                    ws_config_id = f"phase2-{block_id}-whitespace"
                    ws_scores = phase2_scores.get(
                        (ws_config_id, probe_id, model_id), []
                    )
                    if ws_scores:
                        position_controlled = True
                        ws_mean = statistics.mean(ws_scores)
                        position_delta = ws_mean - baseline_mean

                score = AblationScore(
                    baseline_score=baseline_mean,
                    ablated_score=ablated_mean,
                    delta=delta,
                    p_value=p_value,
                    n_baseline_trials=len(b_scores),
                    n_ablated_trials=len(a_scores),
                    position_controlled=position_controlled,
                    position_delta=position_delta,
                )

                tensor.set(block_id, probe_id, model_id, score)

        return tensor

    @classmethod
    def from_ablation_run(cls, run: object) -> AblationTensor:
        """Assemble tensor directly from an AblationRun.

        Handles the decomposition of run.results into baseline/phase0/phase2
        groups and extracts free_block_ids from the configs.

        Args:
            run: An AblationRun instance (typed as object to avoid circular
                import at module level; validated at runtime).

        Returns:
            An assembled AblationTensor.

        Raises:
            TypeError: If run is not an AblationRun.
            RuntimeError: If no baseline config is found.
        """
        from .runner import AblationRun as _AblationRun

        if not isinstance(run, _AblationRun):
            raise TypeError(
                f"Expected AblationRun, got {type(run).__name__}"
            )

        # Separate configs by phase
        baseline_config_ids: set[str] = set()
        phase0_configs: list[AblationConfig] = []
        phase1_config_ids: set[str] = set()
        phase2_config_ids: set[str] = set()

        for config in run.configs:
            if config.phase == "baseline":
                baseline_config_ids.add(config.id)
            elif config.phase == "phase0":
                phase0_configs.append(config)
            elif config.phase == "phase1":
                phase1_config_ids.add(config.id)
            elif config.phase == "phase2":
                phase2_config_ids.add(config.id)

        if not baseline_config_ids:
            raise RuntimeError("No baseline config found in run")

        # Separate results by phase
        baseline_results = [
            r for r in run.results if r.config_id in baseline_config_ids
        ]
        phase0_results = [
            r for r in run.results
            if any(r.config_id == c.id for c in phase0_configs)
        ]
        phase1_results = [
            r for r in run.results if r.config_id in phase1_config_ids
        ]
        phase2_results = [
            r for r in run.results if r.config_id in phase2_config_ids
        ] or None

        tensor = cls.from_run(
            baseline_results=baseline_results,
            phase0_results=phase0_results,
            phase0_configs=phase0_configs,
            phase2_results=phase2_results,
        )

        # Attach Phase 1 data for pairwise_interactions() if present
        if phase1_results:
            tensor._phase1_results = phase1_results
            tensor._baseline_results = baseline_results

        return tensor

    def main_effects(
        self, significance: float = 0.05, fdr: bool = True
    ) -> dict[str, float]:
        """Mean |delta| per block, filtered by p_value.

        Args:
            significance: Significance threshold. When fdr=True, this is
                the FDR-controlled q-value threshold (Benjamini-Hochberg).
                When fdr=False, it is a raw p-value threshold per-test.
            fdr: Apply Benjamini-Hochberg FDR correction (default True).
                With hundreds of tests, uncorrected p-values produce
                many false positives.

        Returns:
            Dict mapping block_id -> mean |delta| across probes and models.
        """
        # Collect all entries with p-values for FDR correction
        entries_with_p: list[tuple[str, AblationScore]] = []
        entries_without_p: list[tuple[str, AblationScore]] = []

        for key, score in self.entries.items():
            if score.p_value is not None:
                entries_with_p.append((key, score))
            else:
                entries_without_p.append((key, score))

        # Determine which entries pass significance filter
        if fdr and entries_with_p:
            significant_keys = _benjamini_hochberg(
                [(k, s.p_value) for k, s in entries_with_p],
                alpha=significance,
            )
        else:
            significant_keys = {
                k for k, s in entries_with_p
                if s.p_value is not None and s.p_value <= significance
            }

        # Include entries without p-values (e.g., single-trial)
        significant_keys.update(k for k, _ in entries_without_p)

        block_deltas: dict[str, list[float]] = defaultdict(list)
        for key, score in self.entries.items():
            if key not in significant_keys:
                continue
            block_id, _, _ = self._parse_key(key)
            block_deltas[block_id].append(abs(score.delta))

        return {
            block_id: statistics.mean(deltas)
            for block_id, deltas in block_deltas.items()
            if deltas
        }

    def pairwise_interactions(
        self,
        phase1_results: list[ProbeResult],
        baseline_results: list[ProbeResult],
        free_block_ids: list[str],
        covering_array: list[list[int]],
    ) -> dict[tuple[str, str], float]:
        """Compute interaction effects from Phase 1 data.

        interaction(a,b) = delta(both_removed) - delta(a_only) - delta(b_only)

        Where delta(X) = mean score in configs where X is removed - baseline.

        This requires Phase 0 results already in the tensor (for single
        block deltas) and Phase 1 results for pair deltas.

        Args:
            phase1_results: Results from Phase 1 covering array configs.
            baseline_results: Baseline results for reference.
            free_block_ids: Ordered list of free block IDs.
            covering_array: The covering array used for Phase 1.

        Returns:
            Dict mapping (block_a, block_b) -> interaction effect.
            Non-zero values indicate the blocks interact.
        """
        from itertools import combinations

        # Index baseline by (probe, model) -> mean
        baseline_means: dict[tuple[str, str], float] = {}
        bl_groups: dict[tuple[str, str], list[float]] = defaultdict(list)
        for r in baseline_results:
            bl_groups[(r.probe_id, r.model_id)].append(r.score)
        for k, v in bl_groups.items():
            baseline_means[k] = statistics.mean(v)

        # Index Phase 1 results by (config_id, probe, model) -> mean
        p1_groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        for r in phase1_results:
            p1_groups[(r.config_id, r.probe_id, r.model_id)].append(r.score)
        p1_means: dict[tuple[str, str, str], float] = {
            k: statistics.mean(v) for k, v in p1_groups.items()
        }

        interactions: dict[tuple[str, str], float] = {}

        for i, j in combinations(range(len(free_block_ids)), 2):
            block_a = free_block_ids[i]
            block_b = free_block_ids[j]

            # Find configs where both are absent
            both_absent_deltas: list[float] = []
            for row_idx, row in enumerate(covering_array):
                if row[i] == 0 and row[j] == 0:
                    config_id = f"phase1-row{row_idx:03d}"
                    for (cid, pid, mid), mean_score in p1_means.items():
                        if cid == config_id:
                            bl = baseline_means.get((pid, mid))
                            if bl is not None:
                                both_absent_deltas.append(mean_score - bl)

            if not both_absent_deltas:
                continue

            both_delta = statistics.mean(both_absent_deltas)

            # Get single-block deltas from Phase 0 tensor
            a_deltas = [
                s.delta
                for key, s in self.entries.items()
                if self._parse_key(key)[0] == block_a
            ]
            b_deltas = [
                s.delta
                for key, s in self.entries.items()
                if self._parse_key(key)[0] == block_b
            ]

            if not a_deltas or not b_deltas:
                continue

            a_delta = statistics.mean(a_deltas)
            b_delta = statistics.mean(b_deltas)

            # Interaction = joint effect - sum of individual effects
            interaction = both_delta - a_delta - b_delta
            interactions[(block_a, block_b)] = interaction

        return interactions

    def to_interference_tensor(self) -> InterferenceTensor:
        """Convert empirical ablation results to standard InterferenceTensor.

        Maps ablation deltas to interference scores. A large |delta| when
        removing block A that affects probe for block B indicates interference
        between A and B.

        The mapping:
        - score = |delta| (clamped to [0, 1])
        - severity based on |delta| thresholds: >0.5 critical, >0.2 major, else minor
        - explanation includes the empirical evidence
        """
        entries: list[TensorEntry] = []
        block_id_set: set[str] = set()

        for key, ablation_score in self.entries.items():
            block_id, probe_id, model_id = self._parse_key(key)
            block_id_set.add(block_id)

            abs_delta = abs(ablation_score.delta)
            if abs_delta < 0.01:
                # Skip negligible effects
                continue

            score = min(1.0, abs_delta)

            if abs_delta > 0.5:
                severity = Severity.critical
            elif abs_delta > 0.2:
                severity = Severity.major
            else:
                severity = Severity.minor

            # In the interference tensor, block_a = ablated block,
            # block_b = probe's target block (from probe_id)
            explanation = (
                f"Removing {block_id} changed {probe_id} score by "
                f"{ablation_score.delta:+.3f} on {model_id} "
                f"(baseline={ablation_score.baseline_score:.3f}, "
                f"ablated={ablation_score.ablated_score:.3f}"
            )
            if ablation_score.p_value is not None:
                explanation += f", p={ablation_score.p_value:.4f}"
            explanation += ")"

            entries.append(
                TensorEntry(
                    block_a=block_id,
                    block_b=probe_id,
                    rule="ablation_delta",
                    score=score,
                    severity=severity,
                    explanation=explanation,
                )
            )

        return InterferenceTensor.from_scores(
            block_ids=sorted(block_id_set),
            rule_names=["ablation_delta"],
            entries=entries,
        )

    def shape(self) -> tuple[int, int, int]:
        """Logical shape: (n_blocks, n_probes, n_models)."""
        return (len(self.block_ids), len(self.probe_ids), len(self.model_ids))


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------


def _welch_t_test_p(
    group_a: list[float], group_b: list[float]
) -> float | None:
    """Welch's t-test p-value for two independent samples.

    Returns None if either group has fewer than 2 observations.
    Uses the regularized incomplete beta function for the t-distribution
    CDF, which is accurate even at small sample sizes (n=3).
    """
    if len(group_a) < 2 or len(group_b) < 2:
        return None

    n_a = len(group_a)
    n_b = len(group_b)
    mean_a = statistics.mean(group_a)
    mean_b = statistics.mean(group_b)
    var_a = statistics.variance(group_a)
    var_b = statistics.variance(group_b)

    # Welch's t-statistic
    se = (var_a / n_a + var_b / n_b) ** 0.5
    if se == 0:
        return 1.0  # No variance — means are identical

    t_stat = abs(mean_a - mean_b) / se

    # Welch-Satterthwaite degrees of freedom
    num = (var_a / n_a + var_b / n_b) ** 2
    denom = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    if denom == 0:
        return 1.0
    df = num / denom

    # Two-tailed p-value from t-distribution
    p_value = 2.0 * (1.0 - _t_cdf(t_stat, df))
    return p_value


def _t_cdf(t: float, df: float) -> float:
    """CDF of the t-distribution using the regularized incomplete beta function.

    t_cdf(t, df) = 1 - 0.5 * I_x(df/2, 1/2)  where x = df/(df + t^2)

    This is exact (no normal approximation) and works correctly at small df
    (e.g., df=2-4 typical of n=3 Welch tests).
    """
    import math

    x = df / (df + t * t)
    # I_x(a, b) = regularized incomplete beta function
    return 1.0 - 0.5 * _regularized_incomplete_beta(x, df / 2.0, 0.5)


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b) via continued fraction.

    Uses the continued fraction from Numerical Recipes (betacf).
    Accurate to ~1e-10 for typical ablation parameters (a=1-2, b=0.5).
    """
    import math

    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    # Use the symmetry relation if x > (a+1)/(a+b+2) for better convergence
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _regularized_incomplete_beta(1.0 - x, b, a)

    # Prefix: x^a * (1-x)^b / (a * B(a,b))
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    prefix = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta) / a

    # Continued fraction (Numerical Recipes betacf)
    FPMIN = 1e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0

    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d

    for m in range(1, 200):
        m2 = 2 * m
        # Even coefficient
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c

        # Odd coefficient
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return prefix * h


def _benjamini_hochberg(
    entries: list[tuple[str, float]],
    alpha: float = 0.05,
) -> set[str]:
    """Benjamini-Hochberg FDR correction.

    Given a list of (key, p_value) pairs, returns the set of keys that
    are significant after controlling the false discovery rate at level alpha.

    This is critical for multiple testing: with m tests at alpha=0.05,
    we expect m*0.05 false positives without correction.
    """
    if not entries:
        return set()

    m = len(entries)
    # Sort by p-value ascending
    sorted_entries = sorted(entries, key=lambda x: x[1])

    # Find the largest k where p_(k) <= (k/m) * alpha
    significant: set[str] = set()
    max_k = 0
    for k, (key, p_val) in enumerate(sorted_entries, start=1):
        threshold = (k / m) * alpha
        if p_val <= threshold:
            max_k = k

    # All entries up to max_k are significant
    for k, (key, _) in enumerate(sorted_entries, start=1):
        if k <= max_k:
            significant.add(key)

    return significant
