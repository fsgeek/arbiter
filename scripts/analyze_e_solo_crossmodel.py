#!/usr/bin/env python3
"""Cross-model analysis of E-SOLO.

Loads all E-SOLO run files and produces:
  - Per-model score tables across conditions × probes
  - Response-mode classification (tool invocations, AskUserQuestion, prose-only)
  - Bash-command-with-flag counts
  - Cross-model alignment: which pathways replicate on which models

Usage:
    python scripts/analyze_e_solo_crossmodel.py
    python scripts/analyze_e_solo_crossmodel.py --probe probe-explore-agent-01
"""
import argparse
import json
import glob
import re
import statistics
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).parent.parent

# Response-mode classifiers. Models emit tool calls in different formats.
TOOL_PATTERNS = {
    "Task-invoke": re.compile(r'<invoke name="Task"|Task\(description=|`Task`.{0,30}tool', re.I),
    "AskUserQuestion": re.compile(r'AskUserQuestion'),
    "Grep-invoke": re.compile(r'<invoke name="Grep"|Grep\(pattern='),
    "TodoWrite-markdown": re.compile(r'```tool_code\s*\n\s*TodoWrite:', re.I),
    "Bash-invoke": re.compile(r'<invoke name="Bash"'),
}
BASH_INLINE = re.compile(r'\b(grep|find|rg|cat|head|tail|ls)\s+-[\w-]+')

CONDITIONS = [
    "solo-explore", "solo-task", "solo-push", "solo-dash-i",
    "solo-no-edit", "solo-empty", "solo-heredoc", "solo-empty-cr",
]
KEY_PROBES = [
    "probe-explore-agent-01",
    "probe-use-task-for-search-01",
    "probe-proactive-agents-01",
    "probe-todowrite-repeated-01",
    "probe-todowrite-01",
    "probe-code-references-01",
]


def load_all():
    solo_dir = project_root / "data" / "ablation" / "e_solo"
    runs = {}
    for path in sorted(solo_dir.glob("run_e-solo-*.json")):
        # parse model from filename: run_e-solo-<model>-<hash>.json
        stem = path.stem
        parts = stem.split("-")
        model = parts[2] if len(parts) >= 3 else "unknown"
        with open(path) as f:
            runs[model] = json.load(f)
    return runs


def score_means(results):
    m = defaultdict(lambda: defaultdict(list))
    for r in results:
        if r.get('score') is None:
            continue
        m[r['config_id']][r['probe_id']].append(r['score'])
    return {c: {p: statistics.mean(s) for p, s in ps.items()} for c, ps in m.items()}


def classify_mode(text):
    """Return the first matching mode, or 'prose-or-other'."""
    for name, rx in TOOL_PATTERNS.items():
        if rx.search(text):
            return name
    return "prose-or-other"


def mode_counts(results, cond, probe):
    modes = []
    for r in results:
        if r['config_id'] == cond and r['probe_id'] == probe:
            modes.append(classify_mode(r.get('raw_response') or ''))
    return modes


def bash_count(results, cond, probe):
    xs = []
    for r in results:
        if r['config_id'] == cond and r['probe_id'] == probe:
            xs.append(len(BASH_INLINE.findall(r.get('raw_response') or '')))
    return statistics.mean(xs) if xs else 0.0


def print_score_table(runs):
    print("\n" + "=" * 90)
    print("SCORE TABLE — condition × probe, per model")
    print("=" * 90)
    for probe in KEY_PROBES:
        short = probe.replace('probe-', '').replace('-01', '')
        print(f"\n  {short}")
        header = f"    {'condition':<18}"
        for model in runs:
            header += f"{model:>10}"
        print(header)
        means = {m: score_means(runs[m]['results']) for m in runs}
        for cond in CONDITIONS:
            row = f"    {cond:<18}"
            for model in runs:
                v = means[model].get(cond, {}).get(probe)
                row += f"{v:>10.3f}" if v is not None else f"{'---':>10}"
            print(row)


def print_mode_table(runs, probe):
    print("\n" + "=" * 90)
    print(f"RESPONSE-MODE TABLE — probe={probe}")
    print("=" * 90)
    header = f"  {'condition':<18}"
    for model in runs:
        header += f"{model:>24}"
    print(header)
    for cond in CONDITIONS:
        row = f"  {cond:<18}"
        for model in runs:
            modes = mode_counts(runs[model]['results'], cond, probe)
            if not modes:
                row += f"{'---':>24}"
                continue
            # Dominant mode if unanimous; else report fractions
            s = set(modes)
            if len(s) == 1:
                row += f"{modes[0]:>24}"
            else:
                summary = ",".join(f"{m[:6]}={modes.count(m)}" for m in s)
                row += f"{summary:>24}"
        print(row)


def print_bash_table(runs, probe="probe-use-task-for-search-01"):
    print("\n" + "=" * 90)
    print(f"BASH-COMMAND-WITH-FLAG COUNTS — probe={probe} (mean per response)")
    print("=" * 90)
    header = f"  {'condition':<18}"
    for model in runs:
        header += f"{model:>10}"
    print(header)
    for cond in CONDITIONS:
        row = f"  {cond:<18}"
        for model in runs:
            c = bash_count(runs[model]['results'], cond, probe)
            row += f"{c:>10.2f}"
        print(row)


def summary(runs):
    print("\n" + "=" * 90)
    print("CROSS-MODEL SUMMARY")
    print("=" * 90)
    # Pathway A indicator: solo-task explore-agent score well below baseline
    # Pathway B indicator: solo-empty-cr explore-agent score well below baseline
    print(f"\n  Pathway A (Task-bullet → explore-agent suppression):")
    for model in runs:
        m = score_means(runs[model]['results'])
        v = m.get('solo-task', {}).get('probe-explore-agent-01')
        tag = "PRESENT" if v is not None and v < 0.4 else "ABSENT"
        print(f"    {model:<10}  solo-task explore-agent = {v:.3f}  [{tag}]" if v is not None else
              f"    {model:<10}  solo-task explore-agent = ---")
    print(f"\n  Pathway B (empty CR → explore-agent suppression):")
    for model in runs:
        m = score_means(runs[model]['results'])
        v = m.get('solo-empty-cr', {}).get('probe-explore-agent-01')
        tag = "PRESENT" if v is not None and v < 0.4 else "ABSENT"
        print(f"    {model:<10}  solo-empty-cr explore-agent = {v:.3f}  [{tag}]" if v is not None else
              f"    {model:<10}  solo-empty-cr explore-agent = ---")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", default=None,
                        help="Focus on one probe for mode table")
    args = parser.parse_args()

    runs = load_all()
    if not runs:
        print("No E-SOLO run files found.")
        return
    print(f"Loaded {len(runs)} model(s): {list(runs.keys())}")
    print_score_table(runs)
    print_bash_table(runs)
    for probe in (args.probe,) if args.probe else [
        "probe-explore-agent-01", "probe-use-task-for-search-01",
    ]:
        print_mode_table(runs, probe)
    summary(runs)


if __name__ == "__main__":
    main()
