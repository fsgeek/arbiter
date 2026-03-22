#!/usr/bin/env python3
"""
Ceiling-effect control for taxonomy analysis.

The concern: posture instructions may show low variance simply because
they score near 1.0 everywhere, leaving no room for variance. If we
control for overall adherence level, does the taxonomy still predict
cross-linguistic fragility?

Two approaches:
1. Restrict analysis to mid-range blocks only (0.15 < mean < 0.85)
2. Use coefficient of variation (CV = σ/μ) instead of raw variance,
   which normalizes for the mean. But CV is problematic near zero.
3. Use a variance-to-maximum-possible-variance ratio. For a score
   with mean μ, the maximum variance is μ(1-μ) (the Bernoulli bound).
   Normalized variance = observed_var / μ(1-μ) measures what fraction
   of the available variance is realized.
"""

import json
import glob
import statistics
import random
from pathlib import Path
from collections import defaultdict

# Import taxonomy and mappings
from analyze_instruction_taxonomy import (
    BLOCK_TAXONOMY, TAXONOMY_DESCRIPTIONS,
    PROBE_TO_BLOCK, load_all_baseline_data
)


def compute_block_stats(data):
    """Compute per-block statistics across all model×language cells."""
    by_block = defaultdict(lambda: {"per_model_lang": {}, "per_model": defaultdict(dict)})

    for (model, lang), probes in data.items():
        for pid, score in probes.items():
            block = PROBE_TO_BLOCK.get(pid)
            if block:
                by_block[block]["per_model_lang"][(model, lang)] = score
                by_block[block]["per_model"][model][lang] = score

    results = {}
    for block, bd in by_block.items():
        all_scores = list(bd["per_model_lang"].values())
        overall_mean = statistics.mean(all_scores)

        # Cross-linguistic variance per model
        model_vars = []
        for model, lang_scores in bd["per_model"].items():
            scores = list(lang_scores.values())
            if len(scores) >= 2:
                model_vars.append(statistics.variance(scores))

        mean_xling_var = statistics.mean(model_vars) if model_vars else 0

        # Normalized variance: what fraction of maximum possible variance?
        # Max variance for mean μ is μ(1-μ)
        max_var = overall_mean * (1 - overall_mean)
        norm_var = mean_xling_var / max_var if max_var > 0.01 else None  # skip extreme ceiling/floor

        results[block] = {
            "overall_mean": overall_mean,
            "mean_xling_var": mean_xling_var,
            "max_possible_var": max_var,
            "normalized_var": norm_var,
            "n_cells": len(all_scores),
        }

    return results


def main():
    random.seed(42)
    data = load_all_baseline_data()
    stats = compute_block_stats(data)

    print("=" * 80)
    print("CEILING-CONTROLLED TAXONOMY ANALYSIS")
    print("=" * 80)

    # ── Table: all blocks with normalized variance ──
    print(f"\n{'Block':<38} {'Tax':<12} {'Mean':>5} {'XLVar':>7} {'MaxVar':>7} {'NormV':>7}")
    print("─" * 80)

    for block in sorted(stats.keys()):
        s = stats[block]
        tax = BLOCK_TAXONOMY.get(block, "?")
        nv = f"{s['normalized_var']:.3f}" if s['normalized_var'] is not None else "ceil/fl"
        print(f"{block:<38} {tax:<12} {s['overall_mean']:>5.2f} "
              f"{s['mean_xling_var']:>7.4f} {s['max_possible_var']:>7.4f} {nv:>7}")

    # ── Normalized variance by taxonomy (excluding ceiling/floor) ──
    print(f"\n{'=' * 80}")
    print("NORMALIZED VARIANCE BY TAXONOMY (ceiling/floor excluded)")
    print(f"{'=' * 80}")

    by_tax_norm = defaultdict(list)
    by_tax_raw = defaultdict(list)
    excluded = []

    for block, s in stats.items():
        tax = BLOCK_TAXONOMY.get(block)
        if not tax:
            continue
        if s["normalized_var"] is not None:
            by_tax_norm[tax].append(s["normalized_var"])
            by_tax_raw[tax].append(s["mean_xling_var"])
        else:
            excluded.append((block, tax, s["overall_mean"]))

    print(f"\nExcluded (ceiling/floor, max_var < 0.01):")
    for b, t, m in excluded:
        print(f"  {b} [{t}]: mean={m:.2f}")

    print(f"\nNormalized variance by taxonomy:")
    for tax in sorted(by_tax_norm.keys()):
        vals = by_tax_norm[tax]
        desc = TAXONOMY_DESCRIPTIONS.get(tax, tax)
        if len(vals) > 1:
            med = statistics.median(vals)
        else:
            med = vals[0]
        print(f"  {tax:<15} n={len(vals):>2}  mean_norm_var={statistics.mean(vals):.4f}  "
              f"median={med:.4f}  {desc}")

    # ── Permutation test on normalized variance ──
    print(f"\n{'─' * 80}")
    print("PERMUTATION TEST: fragile vs robust (on normalized variance)")
    print(f"{'─' * 80}")

    fragile_nv = []
    robust_nv = []
    for tax, vals in by_tax_norm.items():
        if tax in ("workflow", "collision", "delegation"):
            fragile_nv.extend(vals)
        elif tax in ("posture", "mapping"):
            robust_nv.extend(vals)

    if not fragile_nv or not robust_nv:
        print("Insufficient data after ceiling/floor exclusion")
        return

    diff = statistics.mean(fragile_nv) - statistics.mean(robust_nv)
    all_nv = fragile_nv + robust_nv
    n_fragile = len(fragile_nv)

    n_perms = 100_000
    count_ge = 0
    for _ in range(n_perms):
        random.shuffle(all_nv)
        perm_diff = statistics.mean(all_nv[:n_fragile]) - statistics.mean(all_nv[n_fragile:])
        if perm_diff >= diff:
            count_ge += 1

    p = count_ge / n_perms
    print(f"  Fragile: n={len(fragile_nv)}, mean norm var={statistics.mean(fragile_nv):.4f}")
    print(f"  Robust:  n={len(robust_nv)}, mean norm var={statistics.mean(robust_nv):.4f}")
    print(f"  Ratio: {statistics.mean(fragile_nv)/statistics.mean(robust_nv):.2f}x" if statistics.mean(robust_nv) > 0 else "  Ratio: inf")
    print(f"  Observed diff: {diff:.4f}")
    print(f"  Permutation p: {p:.5f}")

    # ── Mid-range only analysis ──
    print(f"\n{'=' * 80}")
    print("MID-RANGE BLOCKS ONLY (0.15 < mean < 0.85)")
    print(f"{'=' * 80}")

    mid_fragile = []
    mid_robust = []
    for block, s in stats.items():
        tax = BLOCK_TAXONOMY.get(block)
        if not tax:
            continue
        if 0.15 < s["overall_mean"] < 0.85:
            if tax in ("workflow", "collision", "delegation"):
                mid_fragile.append((block, s["mean_xling_var"]))
            elif tax in ("posture", "mapping", "tool-behavior"):
                mid_robust.append((block, s["mean_xling_var"]))

    print(f"\nFragile mid-range blocks:")
    for b, v in sorted(mid_fragile, key=lambda x: -x[1]):
        print(f"  {b}: var={v:.4f}")

    print(f"\nRobust mid-range blocks:")
    for b, v in sorted(mid_robust, key=lambda x: -x[1]):
        print(f"  {b}: var={v:.4f}")

    if mid_fragile and mid_robust:
        f_vals = [v for _, v in mid_fragile]
        r_vals = [v for _, v in mid_robust]
        diff_mid = statistics.mean(f_vals) - statistics.mean(r_vals)
        all_mid = f_vals + r_vals
        n_f = len(f_vals)

        count_ge = 0
        for _ in range(n_perms):
            random.shuffle(all_mid)
            if statistics.mean(all_mid[:n_f]) - statistics.mean(all_mid[n_f:]) >= diff_mid:
                count_ge += 1

        p_mid = count_ge / n_perms
        print(f"\n  Fragile: n={len(f_vals)}, mean var={statistics.mean(f_vals):.4f}")
        print(f"  Robust:  n={len(r_vals)}, mean var={statistics.mean(r_vals):.4f}")
        print(f"  Observed diff: {diff_mid:.4f}")
        print(f"  Permutation p: {p_mid:.5f}")

    # ── Correlation: mean adherence vs variance ──
    print(f"\n{'=' * 80}")
    print("ADHERENCE-VARIANCE CORRELATION")
    print(f"{'=' * 80}")
    print("\nDoes mean adherence predict cross-linguistic variance?")
    print("(If so, ceiling effects may explain the taxonomy result)\n")

    means = []
    vars_ = []
    labels = []
    for block, s in stats.items():
        means.append(s["overall_mean"])
        vars_.append(s["mean_xling_var"])
        labels.append(block)

    # Pearson correlation
    n = len(means)
    mean_m = statistics.mean(means)
    mean_v = statistics.mean(vars_)
    cov = sum((m - mean_m) * (v - mean_v) for m, v in zip(means, vars_)) / (n - 1)
    sd_m = statistics.stdev(means)
    sd_v = statistics.stdev(vars_)
    r = cov / (sd_m * sd_v) if sd_m > 0 and sd_v > 0 else 0

    print(f"  Pearson r = {r:.3f}")
    print(f"  Direction: {'higher adherence → lower variance' if r < 0 else 'higher adherence → higher variance'}")

    # Partial analysis: within mid-range, does taxonomy still matter?
    mid_means = []
    mid_vars = []
    mid_taxes = []
    for block, s in stats.items():
        if 0.15 < s["overall_mean"] < 0.85:
            mid_means.append(s["overall_mean"])
            mid_vars.append(s["mean_xling_var"])
            mid_taxes.append(BLOCK_TAXONOMY.get(block, "?"))

    if len(mid_means) >= 3:
        mean_mm = statistics.mean(mid_means)
        mean_mv = statistics.mean(mid_vars)
        cov_m = sum((m - mean_mm) * (v - mean_mv) for m, v in zip(mid_means, mid_vars)) / (len(mid_means) - 1)
        sd_mm = statistics.stdev(mid_means)
        sd_mv = statistics.stdev(mid_vars)
        r_mid = cov_m / (sd_mm * sd_mv) if sd_mm > 0 and sd_mv > 0 else 0
        print(f"\n  Mid-range only: Pearson r = {r_mid:.3f}")
        print(f"  Within the mid-range, adherence {'does' if abs(r_mid) > 0.3 else 'does not'} "
              f"strongly predict variance")

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print("""
Three mechanisms of cross-linguistic fragility identified:

1. PROCEDURAL FRAGILITY: Multi-step workflows embedded in natural language
   break under translation. The sequential/conditional structure is harder
   to preserve than declarative constraints.
   - Evidence: workflow category has highest variance
   - Strongest case: commit-restrictions (var=0.157)

2. NAME-CONCEPT COLLISION: Tool names that are common words in target
   languages lose their proper-noun reference.
   - Evidence: explore-agent (var=0.050), "Explore" → "explorar"
   - Counter-evidence: tool-policy-dedicated-tools (var=0.000) —
     contrastive mappings ("Read instead of cat") are robust

3. DELEGATION ABSTRACTION: Meta-capability instructions ("use agents",
   "parallelize") reference concepts that may not map clearly across
   the model's language-specific training.
   - Evidence: proactive-agents (var=0.073), parallel-calls (var=0.076)
   - These may be training-distribution effects, not translation effects

Confound: Ceiling effects partially explain the pattern — posture
instructions tend to score near 1.0, limiting variance. The ceiling-
controlled analysis determines whether the effect survives.
""")


if __name__ == "__main__":
    main()
