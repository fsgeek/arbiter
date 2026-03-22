#!/usr/bin/env python3
"""
Hypothesis test: Do referential-binding instructions show higher
cross-linguistic variance than semantic-constraint instructions?

Classification scheme:
  - SEMANTIC: Instructions that constrain behavioral posture without
    referencing specific formal objects (tool names, API names, workflow steps)
  - REFERENTIAL: Instructions that bind natural-language directives to
    specific named tools, workflows, or formal procedures

The prediction: referential instructions will show significantly higher
variance across languages because translation preserves meaning but can
break name->object bindings.
"""

import json
import glob
import statistics
from pathlib import Path
from collections import defaultdict

# ── Classification of the 22 ablatable blocks ──────────────────────────
#
# Each classification includes a rationale.

BLOCK_CLASSIFICATION = {
    # SEMANTIC CONSTRAINTS — behavioral posture, no formal object references
    "tone-emoji": {
        "type": "semantic",
        "rationale": "Broad behavioral constraint: don't use emoji. No tool name, no API, no workflow."
    },
    "tone-concise": {
        "type": "semantic",
        "rationale": "Broad behavioral constraint: keep responses short. Pure style directive."
    },
    "tone-text-only-comms": {
        "type": "semantic",
        "rationale": "Communication mode: explain in prose, not code comments. No formal object."
    },
    "tone-no-new-files": {
        "type": "semantic",
        "rationale": "Behavioral preference: edit existing files over creating new ones. No tool name."
    },
    "tone-no-colon-before-tools": {
        "type": "semantic",
        "rationale": "Punctuation style rule. No formal object reference."
    },
    "professional-objectivity": {
        "type": "semantic",
        "rationale": "Behavioral posture: objective analysis, no enthusiasm. Pure attitude constraint."
    },
    "no-time-estimates": {
        "type": "semantic",
        "rationale": "Behavioral prohibition: never give time estimates. No tool or workflow reference."
    },
    "doing-tasks-read-first": {
        "type": "semantic",
        "rationale": "Process principle: understand before modifying. Could reference Read tool but the "
                     "instruction is about the principle, not the tool binding."
    },
    "doing-tasks-no-overengineering": {
        "type": "semantic",
        "rationale": "Behavioral constraint: keep solutions simple. No formal object."
    },
    "doing-tasks-no-compat-hacks": {
        "type": "semantic",
        "rationale": "Code style: no backwards-compatibility shims. No tool reference."
    },
    "code-references": {
        "type": "semantic",
        "rationale": "Output format: use file:line format. Pattern specification but no tool name binding."
    },

    # REFERENTIAL BINDINGS — instructions that name specific tools or workflows
    "task-management-todowrite": {
        "type": "referential",
        "rationale": "References 'TodoWrite' by name as the tool to use for task management."
    },
    "doing-tasks-plan-with-todo": {
        "type": "referential",
        "rationale": "References 'TodoWrite' by name as the planning tool."
    },
    "tool-policy-use-task-for-search": {
        "type": "referential",
        "rationale": "References 'Grep', 'Glob' tool names; contrasts with 'bash grep/find'."
    },
    "tool-policy-proactive-agents": {
        "type": "referential",
        "rationale": "References 'Agent' tool and 'subagent_type' parameter by name."
    },
    "tool-policy-parallel-calls": {
        "type": "referential",
        "rationale": "References tool call mechanics. Borderline — but names 'tool calls' as formal objects."
    },
    "tool-policy-dedicated-tools": {
        "type": "referential",
        "rationale": "Names specific tools: 'Read instead of cat', 'Edit instead of sed', 'Grep instead of grep'."
    },
    "tool-policy-explore-agent": {
        "type": "referential",
        "rationale": "Names 'Explore' agent specifically, plus 'subagent_type=Explore'."
    },
    "todowrite-importance-repeated": {
        "type": "referential",
        "rationale": "Reiterates 'TodoWrite' tool name binding."
    },
    "tool-bash-commit-workflow": {
        "type": "referential",
        "rationale": "Names specific git commands and workflow steps (git status, git diff, git log)."
    },
    "tool-bash-commit-restrictions": {
        "type": "referential",
        "rationale": "Names 'TodoWrite', 'Task' tools as things NOT to use during commits."
    },
    "tool-bash-pr-workflow": {
        "type": "referential",
        "rationale": "Names 'gh pr create' and specific workflow steps."
    },
}

# Map probe IDs to block short names
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
    """Load all cross-linguistic baseline results into a structured dict.

    Returns: {(model_short, lang): {probe_id: mean_score}}
    """
    data = {}
    files = glob.glob("data/ablation/cross_linguistic/run_xling-*.json")

    for fpath in files:
        fname = Path(fpath).stem
        # Format: run_xling-{lang}-{model}-{hash}
        # Split on "-" gives: ['run_xling', lang, model, hash]
        parts = fname.split("-")
        lang = parts[1]
        model = parts[2]

        with open(fpath) as f:
            d = json.load(f)

        # Aggregate trials per probe
        probe_scores = defaultdict(list)
        for result in d["results"]:
            probe_scores[result["probe_id"]].append(result["score"])

        # Mean per probe
        means = {pid: statistics.mean(scores) for pid, scores in probe_scores.items()}
        data[(model, lang)] = means

    return data


def compute_cross_linguistic_variance(data):
    """For each model and probe, compute variance across languages.

    Returns: {(model, probe_id): {"variance": float, "scores": {lang: score}, "range": float}}
    """
    # Reorganize: {(model, probe): {lang: score}}
    by_model_probe = defaultdict(dict)
    for (model, lang), probes in data.items():
        for pid, score in probes.items():
            by_model_probe[(model, pid)][lang] = score

    results = {}
    for (model, pid), lang_scores in by_model_probe.items():
        scores = list(lang_scores.values())
        if len(scores) >= 2:
            var = statistics.variance(scores)
            rng = max(scores) - min(scores)
            results[(model, pid)] = {
                "variance": var,
                "range": rng,
                "scores": lang_scores,
                "n_langs": len(scores),
            }
    return results


def run_analysis():
    print("=" * 72)
    print("SEMANTIC vs REFERENTIAL: Cross-Linguistic Variance Analysis")
    print("=" * 72)
    print()

    # Classification summary
    semantic_blocks = [b for b, c in BLOCK_CLASSIFICATION.items() if c["type"] == "semantic"]
    referential_blocks = [b for b, c in BLOCK_CLASSIFICATION.items() if c["type"] == "referential"]
    print(f"Classification: {len(semantic_blocks)} semantic, {len(referential_blocks)} referential")
    print(f"  Semantic:     {', '.join(sorted(semantic_blocks))}")
    print(f"  Referential:  {', '.join(sorted(referential_blocks))}")
    print()

    # Load data
    data = load_all_baseline_data()
    models = sorted(set(m for m, _ in data.keys()))
    langs = sorted(set(l for _, l in data.keys()))
    print(f"Models: {models}")
    print(f"Languages: {langs}")
    print(f"Total model×lang cells: {len(data)}")
    print()

    # Compute variance
    variance_data = compute_cross_linguistic_variance(data)

    # ── Per-block analysis ──
    # For each probe, collect variance across all models
    block_variances = defaultdict(list)  # block_name -> [variance across models]
    block_ranges = defaultdict(list)

    for (model, pid), vdata in variance_data.items():
        block = PROBE_TO_BLOCK.get(pid)
        if block:
            block_variances[block].append(vdata["variance"])
            block_ranges[block].append(vdata["range"])

    # Compute mean variance per block
    print("─" * 72)
    print("Per-Block Cross-Linguistic Variance (averaged across models)")
    print("─" * 72)
    print(f"{'Block':<40} {'Type':<12} {'Mean Var':>10} {'Mean Range':>10}")
    print("─" * 72)

    block_summary = []
    for block in sorted(BLOCK_CLASSIFICATION.keys()):
        btype = BLOCK_CLASSIFICATION[block]["type"]
        if block in block_variances:
            mean_var = statistics.mean(block_variances[block])
            mean_range = statistics.mean(block_ranges[block])
            block_summary.append((block, btype, mean_var, mean_range))
            print(f"{block:<40} {btype:<12} {mean_var:>10.4f} {mean_range:>10.4f}")

    # ── Group comparison ──
    print()
    print("=" * 72)
    print("GROUP COMPARISON")
    print("=" * 72)

    sem_variances = [mv for _, bt, mv, _ in block_summary if bt == "semantic"]
    ref_variances = [mv for _, bt, mv, _ in block_summary if bt == "referential"]
    sem_ranges = [mr for _, bt, _, mr in block_summary if bt == "semantic"]
    ref_ranges = [mr for _, bt, _, mr in block_summary if bt == "referential"]

    print(f"\nSemantic constraints (n={len(sem_variances)}):")
    print(f"  Mean variance:  {statistics.mean(sem_variances):.4f}")
    print(f"  Median variance: {statistics.median(sem_variances):.4f}")
    print(f"  Mean range:     {statistics.mean(sem_ranges):.4f}")

    print(f"\nReferential bindings (n={len(ref_variances)}):")
    print(f"  Mean variance:  {statistics.mean(ref_variances):.4f}")
    print(f"  Median variance: {statistics.median(ref_variances):.4f}")
    print(f"  Mean range:     {statistics.mean(ref_ranges):.4f}")

    ratio = statistics.mean(ref_variances) / statistics.mean(sem_variances) if statistics.mean(sem_variances) > 0 else float('inf')
    print(f"\nVariance ratio (referential / semantic): {ratio:.2f}x")

    # ── Permutation test ──
    # Is the difference in mean variance significant?
    import random
    random.seed(42)

    all_variances = [(btype, mv) for _, btype, mv, _ in block_summary]
    observed_diff = statistics.mean(ref_variances) - statistics.mean(sem_variances)

    n_sem = len(sem_variances)
    n_ref = len(ref_variances)
    n_total = n_sem + n_ref
    all_vals = [v for _, v in all_variances]

    n_perms = 100_000
    count_ge = 0
    for _ in range(n_perms):
        random.shuffle(all_vals)
        perm_sem = all_vals[:n_sem]
        perm_ref = all_vals[n_sem:]
        perm_diff = statistics.mean(perm_ref) - statistics.mean(perm_sem)
        if perm_diff >= observed_diff:
            count_ge += 1

    p_value = count_ge / n_perms

    print(f"\n{'─' * 72}")
    print("PERMUTATION TEST (one-sided: referential > semantic)")
    print(f"{'─' * 72}")
    print(f"Observed difference in mean variance: {observed_diff:.4f}")
    print(f"Permutations: {n_perms:,}")
    print(f"p-value: {p_value:.5f}")
    if p_value < 0.001:
        print("*** Highly significant")
    elif p_value < 0.01:
        print("** Significant")
    elif p_value < 0.05:
        print("* Marginally significant")
    else:
        print("Not significant at α=0.05")

    # ── Per-model breakdown ──
    print(f"\n{'=' * 72}")
    print("PER-MODEL BREAKDOWN")
    print(f"{'=' * 72}")

    for model in models:
        sem_v = []
        ref_v = []
        for (m, pid), vdata in variance_data.items():
            if m != model:
                continue
            block = PROBE_TO_BLOCK.get(pid)
            if not block:
                continue
            btype = BLOCK_CLASSIFICATION[block]["type"]
            if btype == "semantic":
                sem_v.append(vdata["variance"])
            else:
                ref_v.append(vdata["variance"])

        if sem_v and ref_v:
            r = statistics.mean(ref_v) / statistics.mean(sem_v) if statistics.mean(sem_v) > 0 else float('inf')
            print(f"\n{model}:")
            print(f"  Semantic mean var:    {statistics.mean(sem_v):.4f} (n={len(sem_v)})")
            print(f"  Referential mean var: {statistics.mean(ref_v):.4f} (n={len(ref_v)})")
            print(f"  Ratio: {r:.2f}x")

    # ── Detailed probe-level view ──
    print(f"\n{'=' * 72}")
    print("PROBE-LEVEL DETAIL (sorted by mean variance, descending)")
    print(f"{'=' * 72}")

    sorted_blocks = sorted(block_summary, key=lambda x: x[2], reverse=True)
    for block, btype, mean_var, mean_range in sorted_blocks:
        marker = "REF" if btype == "referential" else "SEM"
        print(f"\n  [{marker}] {block}: var={mean_var:.4f}, range={mean_range:.4f}")
        # Show per-model language scores
        for model in models:
            for (m, pid), vdata in variance_data.items():
                b = PROBE_TO_BLOCK.get(pid)
                if b == block and m == model:
                    scores_str = ", ".join(f"{l}={s:.2f}" for l, s in sorted(vdata["scores"].items()))
                    print(f"    {model}: {scores_str}")

    # ── Misclassification check ──
    # Are there blocks I classified as semantic that behave like referential, or vice versa?
    print(f"\n{'=' * 72}")
    print("CLASSIFICATION ANOMALIES")
    print(f"{'=' * 72}")

    sem_median = statistics.median(sem_variances)
    ref_median = statistics.median(ref_variances)
    threshold = (sem_median + ref_median) / 2

    print(f"\nThreshold (midpoint of medians): {threshold:.4f}")

    for block, btype, mean_var, mean_range in sorted_blocks:
        if btype == "semantic" and mean_var > threshold:
            print(f"  ANOMALY: {block} classified SEMANTIC but variance {mean_var:.4f} > threshold")
            print(f"    Rationale: {BLOCK_CLASSIFICATION[block]['rationale']}")
        elif btype == "referential" and mean_var < threshold:
            print(f"  ANOMALY: {block} classified REFERENTIAL but variance {mean_var:.4f} < threshold")
            print(f"    Rationale: {BLOCK_CLASSIFICATION[block]['rationale']}")

    return block_summary, variance_data


if __name__ == "__main__":
    run_analysis()
