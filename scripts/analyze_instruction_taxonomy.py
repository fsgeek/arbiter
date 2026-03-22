#!/usr/bin/env python3
"""
Refined taxonomy analysis: What property of instructions predicts
cross-linguistic fragility?

Initial hypothesis (semantic vs referential) showed 1.95x ratio but
p=0.117. The anomalies point to a richer taxonomy:

1. BEHAVIORAL POSTURE — "be concise", "no emoji", "no time estimates"
   Broad dispositional constraints. No specific procedure or referent.
   Prediction: translation-robust.

2. TOOL MAPPING — "use Read instead of cat", "use Edit instead of sed"
   Referential but with contrastive anchoring: the new name is paired
   with a known name, creating a redundant binding.
   Prediction: translation-robust.

3. WORKFLOW PROCEDURE — "when committing: first git status, then diff,
   then commit, and NEVER use TodoWrite during commits"
   Specifies sequenced steps with conditional logic. The procedure is
   a structured program embedded in natural language.
   Prediction: translation-fragile, because procedural structure is
   harder to preserve than simple mappings.

4. NAME-CONCEPT COLLISION — "use the Explore agent"
   The tool name is a common word in the target language. Translation
   preserves meaning but creates competition between the proper-noun
   and common-word interpretations.
   Prediction: translation-fragile in languages where the name is a
   common word.

5. DELEGATION PATTERN — "use agents proactively", "make parallel calls"
   References a meta-capability (delegating work, parallelizing) rather
   than a specific tool. The concept exists in all languages but the
   specific mechanism may not map clearly.
   Prediction: variable — depends on whether the model has the concept
   anchored in its training regardless of language.
"""

import json
import glob
import statistics
from pathlib import Path
from collections import defaultdict

BLOCK_TAXONOMY = {
    # BEHAVIORAL POSTURE — dispositional constraints
    "tone-emoji":                    "posture",
    "tone-concise":                  "posture",
    "tone-text-only-comms":          "posture",
    "tone-no-new-files":             "posture",
    "tone-no-colon-before-tools":    "posture",
    "professional-objectivity":      "posture",
    "no-time-estimates":             "posture",
    "doing-tasks-read-first":        "posture",      # "understand before modifying" — principle
    "doing-tasks-no-overengineering":"posture",
    "doing-tasks-no-compat-hacks":   "posture",
    "code-references":               "posture",      # output format convention

    # TOOL MAPPING — contrastive name->replacement bindings
    "tool-policy-dedicated-tools":   "mapping",      # "Read not cat, Edit not sed"
    "tool-policy-use-task-for-search":"mapping",      # "Grep/Glob not bash grep"

    # WORKFLOW PROCEDURE — sequenced multi-step processes
    "tool-bash-commit-workflow":     "workflow",      # git status → diff → log → commit
    "tool-bash-commit-restrictions": "workflow",      # conditional: NEVER TodoWrite during commits
    "tool-bash-pr-workflow":         "workflow",      # multi-step PR creation

    # NAME-CONCEPT COLLISION — tool name is a common word
    "tool-policy-explore-agent":     "collision",     # "Explore" = verb in target languages

    # DELEGATION PATTERN — meta-capability reference
    "tool-policy-proactive-agents":  "delegation",    # "use agents proactively"
    "tool-policy-parallel-calls":    "delegation",    # "make parallel tool calls"

    # REPEATED EMPHASIS — tool name is preserved but instruction is about behavior
    "task-management-todowrite":     "tool-behavior", # use TodoWrite for task management
    "doing-tasks-plan-with-todo":    "tool-behavior", # plan with TodoWrite
    "todowrite-importance-repeated": "tool-behavior", # TodoWrite is important (repeated)
}

TAXONOMY_DESCRIPTIONS = {
    "posture":       "Behavioral posture (dispositional constraints)",
    "mapping":       "Tool mapping (contrastive name bindings)",
    "workflow":      "Workflow procedure (sequenced steps)",
    "collision":     "Name-concept collision (tool name = common word)",
    "delegation":    "Delegation pattern (meta-capability)",
    "tool-behavior": "Tool-linked behavior (named tool, behavioral instruction)",
}

# Copy probe mapping from previous script
PROBE_TO_BLOCK = {
    "probe-emoji-01": "tone-emoji",
    "probe-concise-01": "tone-concise",
    "probe-text-only-comms-01": "tone-text-only-comms",
    "probe-no-new-files-01": "tone-no-new-files",
    "probe-no-colon-01": "tone-no-colon-before-tools",
    "probe-objectivity-01": "professional-objectivity",
    "probe-no-time-estimates-01": "no-time-estimates",
    "probe-todowrite-01": "task-management-todowrite",
    "probe-read-first-01": "doing-tasks-read-first",
    "probe-plan-with-todo-01": "doing-tasks-plan-with-todo",
    "probe-no-overengineering-01": "doing-tasks-no-overengineering",
    "probe-no-compat-hacks-01": "doing-tasks-no-compat-hacks",
    "probe-use-task-for-search-01": "tool-policy-use-task-for-search",
    "probe-proactive-agents-01": "tool-policy-proactive-agents",
    "probe-parallel-calls-01": "tool-policy-parallel-calls",
    "probe-dedicated-tools-01": "tool-policy-dedicated-tools",
    "probe-explore-agent-01": "tool-policy-explore-agent",
    "probe-todowrite-repeated-01": "todowrite-importance-repeated",
    "probe-code-references-01": "code-references",
    "probe-commit-workflow-01": "tool-bash-commit-workflow",
    "probe-commit-restrictions-01": "tool-bash-commit-restrictions",
    "probe-pr-workflow-01": "tool-bash-pr-workflow",
}


def load_all_baseline_data():
    data = {}
    files = glob.glob("data/ablation/cross_linguistic/run_xling-*.json")
    for fpath in files:
        parts = Path(fpath).stem.split("-")
        lang, model = parts[1], parts[2]
        with open(fpath) as f:
            d = json.load(f)
        probe_scores = defaultdict(list)
        for result in d["results"]:
            probe_scores[result["probe_id"]].append(result["score"])
        data[(model, lang)] = {pid: statistics.mean(scores) for pid, scores in probe_scores.items()}
    return data


def compute_variance_by_block(data):
    """Compute cross-linguistic variance for each block, per model and overall."""
    by_model_probe = defaultdict(dict)
    for (model, lang), probes in data.items():
        for pid, score in probes.items():
            by_model_probe[(model, pid)][lang] = score

    block_data = defaultdict(lambda: {"per_model": {}, "all_scores": []})
    for (model, pid), lang_scores in by_model_probe.items():
        block = PROBE_TO_BLOCK.get(pid)
        if not block:
            continue
        scores = list(lang_scores.values())
        if len(scores) >= 2:
            var = statistics.variance(scores)
            rng = max(scores) - min(scores)
            block_data[block]["per_model"][model] = {
                "variance": var, "range": rng, "scores": lang_scores,
                "mean": statistics.mean(scores),
            }
            block_data[block]["all_scores"].extend(scores)

    # Compute overall stats per block
    for block, bd in block_data.items():
        model_vars = [m["variance"] for m in bd["per_model"].values()]
        model_ranges = [m["range"] for m in bd["per_model"].values()]
        bd["mean_variance"] = statistics.mean(model_vars) if model_vars else 0
        bd["mean_range"] = statistics.mean(model_ranges) if model_ranges else 0
        bd["overall_mean"] = statistics.mean(bd["all_scores"]) if bd["all_scores"] else 0

    return block_data


def analyze_model_specificity(data, block_data):
    """Check if variance is driven by specific models or is model-general."""
    print("\n" + "=" * 72)
    print("MODEL-SPECIFICITY OF VARIANCE")
    print("=" * 72)
    print("\nFor each high-variance block, is the variance concentrated in one model")
    print("or distributed across models?\n")

    # Sort by mean variance
    sorted_blocks = sorted(block_data.items(), key=lambda x: x[1]["mean_variance"], reverse=True)

    for block, bd in sorted_blocks[:10]:
        tax = BLOCK_TAXONOMY.get(block, "?")
        print(f"\n  [{tax}] {block} (mean var: {bd['mean_variance']:.4f})")
        for model in sorted(bd["per_model"].keys()):
            md = bd["per_model"][model]
            scores_str = " ".join(f"{l}={s:.2f}" for l, s in sorted(md["scores"].items()))
            var_bar = "█" * int(md["variance"] * 100)
            print(f"    {model:>8}: var={md['variance']:.4f} {var_bar}  ({scores_str})")


def analyze_ceiling_floor_effects(block_data):
    """High-adherence blocks can't show variance. Control for this."""
    print("\n" + "=" * 72)
    print("CEILING/FLOOR CONTROL")
    print("=" * 72)
    print("\nBlocks near ceiling (mean > 0.9) or floor (mean < 0.1) have limited")
    print("room for variance. Controlling for this:\n")

    midrange_blocks = []
    extreme_blocks = []

    for block, bd in block_data.items():
        mean = bd["overall_mean"]
        var = bd["mean_variance"]
        tax = BLOCK_TAXONOMY.get(block, "?")

        if 0.15 < mean < 0.85:
            midrange_blocks.append((block, tax, var, mean))
        else:
            extreme_blocks.append((block, tax, var, mean))

    print(f"Mid-range blocks (0.15 < mean < 0.85): {len(midrange_blocks)}")
    print(f"Ceiling/floor blocks: {len(extreme_blocks)}")

    if midrange_blocks:
        print(f"\nMid-range blocks by taxonomy:")
        by_tax = defaultdict(list)
        for block, tax, var, mean in midrange_blocks:
            by_tax[tax].append((block, var, mean))

        for tax in sorted(by_tax.keys()):
            blocks = by_tax[tax]
            mean_var = statistics.mean([v for _, v, _ in blocks])
            print(f"  {tax}: n={len(blocks)}, mean var={mean_var:.4f}")
            for b, v, m in sorted(blocks, key=lambda x: -x[1]):
                print(f"    {b}: var={v:.4f}, mean={m:.2f}")

    print(f"\nCeiling/floor blocks (variance constrained):")
    for b, t, v, m in sorted(extreme_blocks, key=lambda x: -x[2]):
        flag = "CEILING" if m >= 0.85 else "FLOOR"
        print(f"  [{flag}] [{t}] {b}: var={v:.4f}, mean={m:.2f}")


def analyze_inversion_patterns(data):
    """Find probes where models show OPPOSITE language effects.

    This is the strongest evidence for model×language interaction —
    not just different magnitudes but different signs.
    """
    print("\n" + "=" * 72)
    print("INVERSION PATTERNS (opposite effects across models)")
    print("=" * 72)

    # For each probe, find cases where one model improves and another degrades
    by_probe = defaultdict(dict)
    for (model, lang), probes in data.items():
        for pid, score in probes.items():
            block = PROBE_TO_BLOCK.get(pid)
            if block:
                if block not in by_probe:
                    by_probe[block] = {}
                if model not in by_probe[block]:
                    by_probe[block][model] = {}
                by_probe[block][model][lang] = score

    inversions = []
    for block, model_data in by_probe.items():
        models = list(model_data.keys())
        for i, m1 in enumerate(models):
            for m2 in models[i+1:]:
                # Compare each non-English language to English
                if "en" not in model_data[m1] or "en" not in model_data[m2]:
                    continue
                for lang in ["zh", "fr", "es"]:
                    if lang not in model_data[m1] or lang not in model_data[m2]:
                        continue
                    # Change from English for each model
                    delta1 = model_data[m1][lang] - model_data[m1]["en"]
                    delta2 = model_data[m2][lang] - model_data[m2]["en"]
                    # Inversion: one improves significantly, other degrades significantly
                    if abs(delta1) >= 0.3 and abs(delta2) >= 0.3 and delta1 * delta2 < 0:
                        inversions.append({
                            "block": block,
                            "lang": lang,
                            "m1": m1, "d1": delta1,
                            "m2": m2, "d2": delta2,
                            "m1_scores": model_data[m1],
                            "m2_scores": model_data[m2],
                            "taxonomy": BLOCK_TAXONOMY.get(block, "?"),
                        })

    print(f"\nFound {len(inversions)} inversions (|Δ| >= 0.3 for both, opposite sign)")

    for inv in sorted(inversions, key=lambda x: -(abs(x["d1"]) + abs(x["d2"]))):
        print(f"\n  [{inv['taxonomy']}] {inv['block']} in {inv['lang']}:")
        m1_str = " ".join(f"{l}={s:.2f}" for l, s in sorted(inv["m1_scores"].items()))
        m2_str = " ".join(f"{l}={s:.2f}" for l, s in sorted(inv["m2_scores"].items()))
        print(f"    {inv['m1']:>8}: Δ={inv['d1']:+.2f}  ({m1_str})")
        print(f"    {inv['m2']:>8}: Δ={inv['d2']:+.2f}  ({m2_str})")

    # Count inversions by taxonomy
    tax_counts = defaultdict(int)
    for inv in inversions:
        tax_counts[inv["taxonomy"]] += 1

    print(f"\nInversions by taxonomy:")
    for tax, count in sorted(tax_counts.items(), key=lambda x: -x[1]):
        desc = TAXONOMY_DESCRIPTIONS.get(tax, tax)
        print(f"  {tax}: {count} inversions — {desc}")


def run_taxonomy_test(block_data):
    """Kruskal-Wallis style permutation test across taxonomy categories."""
    print("\n" + "=" * 72)
    print("TAXONOMY PERMUTATION TEST")
    print("=" * 72)

    # Group variances by taxonomy
    by_tax = defaultdict(list)
    for block, bd in block_data.items():
        tax = BLOCK_TAXONOMY.get(block)
        if tax:
            by_tax[tax].append(bd["mean_variance"])

    print("\nMean cross-linguistic variance by taxonomy category:")
    for tax in sorted(by_tax.keys()):
        vals = by_tax[tax]
        desc = TAXONOMY_DESCRIPTIONS.get(tax, tax)
        print(f"  {tax:<15} n={len(vals):>2}  mean_var={statistics.mean(vals):.4f}  "
              f"median={statistics.median(vals):.4f}  {desc}")

    # Permutation test: is the between-group variance of means significant?
    import random
    random.seed(42)

    all_vals = []
    group_sizes = []
    for tax in sorted(by_tax.keys()):
        vals = by_tax[tax]
        all_vals.extend(vals)
        group_sizes.append(len(vals))

    # Observed test statistic: variance of group means
    group_means = [statistics.mean(by_tax[t]) for t in sorted(by_tax.keys())]
    observed_stat = statistics.variance(group_means)

    n_perms = 100_000
    count_ge = 0
    for _ in range(n_perms):
        random.shuffle(all_vals)
        perm_groups = []
        idx = 0
        for size in group_sizes:
            perm_groups.append(all_vals[idx:idx + size])
            idx += size
        perm_means = [statistics.mean(g) for g in perm_groups]
        perm_stat = statistics.variance(perm_means)
        if perm_stat >= observed_stat:
            count_ge += 1

    p_value = count_ge / n_perms
    print(f"\nBetween-group variance of means: {observed_stat:.6f}")
    print(f"Permutation p-value: {p_value:.5f}")
    if p_value < 0.05:
        print("* Significant: taxonomy categories differ in cross-linguistic variance")
    else:
        print(f"Not significant at α=0.05 (but with {len(by_tax)} groups of sizes "
              f"{group_sizes}, power is limited)")

    # Pairwise: which categories differ?
    print("\nPairwise comparisons (workflow+collision vs posture+mapping):")
    fragile = []
    robust = []
    for tax, vals in by_tax.items():
        if tax in ("workflow", "collision", "delegation"):
            fragile.extend(vals)
        elif tax in ("posture", "mapping"):
            robust.extend(vals)

    if fragile and robust:
        diff = statistics.mean(fragile) - statistics.mean(robust)
        all_combined = fragile + robust
        n_fragile = len(fragile)

        count_ge = 0
        for _ in range(n_perms):
            random.shuffle(all_combined)
            perm_fragile = all_combined[:n_fragile]
            perm_robust = all_combined[n_fragile:]
            perm_diff = statistics.mean(perm_fragile) - statistics.mean(perm_robust)
            if perm_diff >= diff:
                count_ge += 1

        p2 = count_ge / n_perms
        print(f"  Fragile (workflow+collision+delegation): n={len(fragile)}, "
              f"mean var={statistics.mean(fragile):.4f}")
        print(f"  Robust (posture+mapping): n={len(robust)}, "
              f"mean var={statistics.mean(robust):.4f}")
        print(f"  Ratio: {statistics.mean(fragile)/statistics.mean(robust):.2f}x")
        print(f"  Observed difference: {diff:.4f}")
        print(f"  p-value: {p2:.5f}")


def main():
    print("=" * 72)
    print("INSTRUCTION TAXONOMY AND CROSS-LINGUISTIC FRAGILITY")
    print("=" * 72)
    print()
    print("Taxonomy:")
    for tax, desc in sorted(TAXONOMY_DESCRIPTIONS.items()):
        blocks = [b for b, t in BLOCK_TAXONOMY.items() if t == tax]
        print(f"  {tax:<15} ({len(blocks):>2}) — {desc}")
    print()

    data = load_all_baseline_data()
    block_data = compute_variance_by_block(data)

    # Main taxonomy results
    print("─" * 72)
    print("VARIANCE BY BLOCK AND TAXONOMY")
    print("─" * 72)
    print(f"{'Block':<40} {'Tax':<12} {'MeanVar':>8} {'MeanRng':>8} {'OverallM':>8}")
    print("─" * 72)
    for block in sorted(block_data.keys()):
        bd = block_data[block]
        tax = BLOCK_TAXONOMY.get(block, "?")
        print(f"{block:<40} {tax:<12} {bd['mean_variance']:>8.4f} "
              f"{bd['mean_range']:>8.4f} {bd['overall_mean']:>8.2f}")

    run_taxonomy_test(block_data)
    analyze_ceiling_floor_effects(block_data)
    analyze_model_specificity(data, block_data)
    analyze_inversion_patterns(data)


if __name__ == "__main__":
    main()
