#!/usr/bin/env python3
"""
E-SCOPE: Test whether explicit scoping prevents register interference.

E-PHASE-CONFIRM showed that commit-restrictions as a lone imperative in a
declarative field collapses explore-agent from 1.00 → 0.20. The scope
hypothesis: "NEVER use TodoWrite or Task tools" is scoped to commit workflow,
but when it's the sole imperative surrounded by declaratives, the model
reads it as a universal prohibition. Explicit scoping should prevent bleed.

Design: 3 new conditions + 2 baselines from E-PHASE-CONFIRM
  1. all-decl         (baseline, already have data) → explore-agent = 1.00
  2. only-cr-imp      (baseline, already have data) → explore-agent = 0.20
  3. scoped-prefix    (NEW: imperative text with scope prefix)
  4. scoped-inline    (NEW: each prohibition with inline scope)
  5. hybrid-decl-never (NEW: declarative format but "NEVER" on key prohibition)

Predictions:
  If scope hypothesis correct: scoped-prefix & scoped-inline → explore-agent ~1.00
  If it's purely register (not scope): all three new conditions similar to only-cr-imp
  hybrid-decl-never tests: is the word "NEVER" itself the trigger regardless of register?

Usage:
    python scripts/run_e_scope.py --dry-run
    python scripts/run_e_scope.py
    python scripts/run_e_scope.py --compare
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import uuid
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))

from arbiter.ablation.battery import load_battery
from arbiter.ablation.configuration import AblationConfig
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

from run_e_phase import (
    FREE_BLOCKS, MODEL_MAP, PROCEDURAL_BLOCKS_ORDERED, DECLARATIVE_REWRITES,
    load_corpus,
)

# ── Scoped variants of commit-restrictions ──────────────────────────────

# Original imperative (causes collapse):
# "Important notes:
#  - NEVER run additional commands to read or explore code, besides git bash commands
#  - NEVER use the TodoWrite or Task tools
#  - DO NOT push to the remote repository unless the user explicitly asks you to do so
#  - IMPORTANT: Never use git commands with the -i flag
#  - IMPORTANT: Do not use --no-edit with git rebase commands
#  - If there are no changes to commit, do not create an empty commit
#  - ALWAYS pass the commit message via a HEREDOC"

SCOPED_PREFIX = (
    "During git commit workflows only — the following restrictions apply "
    "exclusively when creating commits, not during other tasks:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- NEVER use the TodoWrite or Task tools\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC"
)

SCOPED_INLINE = (
    "Important notes for git commit workflows:\n"
    "- When committing, NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- When committing, NEVER use the TodoWrite or Task tools (these tools remain available for non-commit tasks)\n"
    "- When committing, DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- When committing, never use git commands with the -i flag\n"
    "- When committing, do not use --no-edit with git rebase commands\n"
    "- When committing, if there are no changes to commit, do not create an empty commit\n"
    "- When committing, ALWAYS pass the commit message via a HEREDOC"
)

HYBRID_DECL_NEVER = (
    "Commit context tool restrictions:\n"
    "- Allowed tools: git bash commands only\n"
    "- NEVER use the TodoWrite or Task tools during commits\n"
    "- Push policy: requires explicit user request\n"
    "- Git flags: -i flag unsupported; --no-edit unsupported for rebase\n"
    "- Empty commits: not created\n"
    "- Commit message format: HEREDOC"
)

CR_BLOCK_ID = "claude-code/tool-bash-commit-restrictions"

# ── Condition builders ──────────────────────────────────────────────────

def build_scoped_condition(corpus: PromptCorpus, cr_text: str, condition_name: str) -> PromptCorpus:
    """All procedural blocks declarative EXCEPT commit-restrictions uses given text."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id == CR_BLOCK_ID:
            new_blocks.append(b.model_copy(update={"text": cr_text}))
        elif b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name + f"-{condition_name}",
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


# ── Conditions ──────────────────────────────────────────────────────────

CONDITIONS = [
    ("scoped-prefix", "imperative CR with explicit scope prefix", SCOPED_PREFIX),
    ("scoped-inline", "imperative CR with inline scope on each prohibition", SCOPED_INLINE),
    ("hybrid-decl-never", "declarative format but NEVER on key prohibition", HYBRID_DECL_NEVER),
]


def make_client(experiment_id: str):
    import openai
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": f"arbiter-{experiment_id}",
            "HTTP-Referer": "https://github.com/fsgeek/arbiter",
        },
    )


def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    print(f"\nE-SCOPE: Explicit scoping prevents register interference?")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  New conditions: {len(CONDITIONS)}")
    print(f"  (2 conditions already have data from E-PHASE-CONFIRM)")
    print(f"  Trials: {args.trials}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Conditions (new):")
    for name, desc, _ in CONDITIONS:
        print(f"    {name:<22} {desc}")
    print(f"\n  Baselines (from E-PHASE-CONFIRM):")
    print(f"    {'all-decl':<22} all declarative → explore-agent = 1.000")
    print(f"    {'only-cr-imp':<22} unscoped imperative CR → explore-agent = 0.200")

    print(f"\n  Predictions (scope hypothesis):")
    print(f"    scoped-prefix:       explore-agent ~1.00 (scope prevents bleed)")
    print(f"    scoped-inline:       explore-agent ~1.00 (scope prevents bleed)")
    print(f"    hybrid-decl-never:   explore-agent ~1.00 (declarative register protects)")
    print(f"    If ALL three ~0.20:  scope hypothesis falsified, it's the word NEVER itself")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_scope"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build condition corpora and configs
    condition_corpora = {}
    configs = []

    for cond_name, cond_desc, cr_text in CONDITIONS:
        corpus = build_scoped_condition(load_corpus(base_corpus_path), cr_text, cond_name)
        condition_corpora[cond_name] = corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "description": cond_desc,
                "cr_text": cr_text,
            },
        ))

    # Save design
    design = {
        "experiment": "e-scope",
        "date": "2026-03-28",
        "parent": "e-phase-confirm",
        "question": "Does explicit scoping prevent register interference from commit-restrictions?",
        "hypothesis": "Imperative prohibitions lose scope when register-isolated; explicit scoping prevents bleed",
        "conditions": [
            {"name": n, "description": d, "cr_text": t}
            for n, d, t in CONDITIONS
        ],
        "baselines": {
            "all-decl": "explore-agent = 1.000 (from E-PHASE-CONFIRM)",
            "only-cr-imp": "explore-agent = 0.200 (from E-PHASE-CONFIRM)",
        },
    }
    with open(output_dir / "e_scope_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    client = make_client("e-scope")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-scope-haiku-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-scope",
            "model": "haiku",
            "model_id": model_id,
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    for config in configs:
        cond_name = config.id
        corpus = condition_corpora[cond_name]
        print(f"\n  Condition: {cond_name}")

        cond_run = AblationRun(
            id=f"{run_id}-{cond_name}",
            configs=[config],
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={"condition": cond_name},
        )

        try:
            asyncio.run(runner.run_phase(
                cond_run, "baseline", corpus=corpus,
                concurrency=args.concurrency, progress_callback=progress,
            ))
            print()
        except KeyboardInterrupt:
            print("\n\nInterrupted.")
            break
        except Exception as e:
            print(f"\n  Error: {e}")
            continue

        run.results.extend(cond_run.results)

        # Quick inline for key probes
        ea_scores = [r.score for r in cond_run.results if r.probe_id == "probe-explore-agent-01"]
        pa_scores = [r.score for r in cond_run.results if r.probe_id == "probe-proactive-agents-01"]
        ts_scores = [r.score for r in cond_run.results if r.probe_id == "probe-use-task-for-search-01"]
        if ea_scores:
            print(f"    explore-agent: {statistics.mean(ea_scores):.3f}")
        if pa_scores:
            print(f"    proactive-agents: {statistics.mean(pa_scores):.3f}")
        if ts_scores:
            print(f"    use-task-for-search: {statistics.mean(ts_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare E-SCOPE results against E-PHASE-CONFIRM baselines."""
    scope_dir = project_root / "data" / "ablation" / "e_scope"
    confirm_dir = project_root / "data" / "ablation" / "e_phase_confirm"
    phase_dir = project_root / "data" / "ablation" / "e_phase"

    if not scope_dir.exists():
        print("No E-SCOPE results found.")
        return

    # Load E-PHASE baselines (all-decl = density-00, only-cr-imp = density-01)
    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    phase_run = load_run(str(phase_files[0])) if phase_files else None

    # Load E-PHASE-CONFIRM (for additional baselines)
    confirm_files = sorted(confirm_dir.glob("run_e-phase-confirm-*.json"))
    confirm_run = load_run(str(confirm_files[0])) if confirm_files else None

    # Load E-SCOPE results
    scope_files = sorted(scope_dir.glob("run_e-scope-*.json"))
    if not scope_files:
        print("No E-SCOPE result files found.")
        return
    scope_run = load_run(str(scope_files[0]))

    print("E-SCOPE: Does Explicit Scoping Prevent Register Interference?")
    print("=" * 75)

    # Get baselines
    baselines = {}
    if phase_run:
        for config_id in ["density-00", "density-01"]:
            results = [r for r in phase_run.results if r.config_id == config_id]
            baselines[config_id] = results

    # Key probes — the ones affected by the commit-restrictions bomb
    key_probes = [
        "probe-explore-agent-01",
        "probe-proactive-agents-01",
        "probe-use-task-for-search-01",
        "probe-plan-with-todo-01",
    ]

    # Build comparison table
    all_conditions = [
        ("all-decl (baseline)", baselines.get("density-00", [])),
        ("only-cr-imp (baseline)", baselines.get("density-01", [])),
    ]

    # Add E-SCOPE conditions
    by_cond = defaultdict(list)
    for r in scope_run.results:
        by_cond[r.config_id].append(r)

    for cond_name, _, _ in CONDITIONS:
        all_conditions.append((cond_name, by_cond.get(cond_name, [])))

    print(f"\n  KEY PROBES BY CONDITION:")
    header = f"  {'Condition':<28}"
    for pid in key_probes:
        short = pid.replace("probe-", "").replace("-01", "")
        header += f" {short:>20}"
    print(header)
    print(f"  {'-' * (28 + 20 * len(key_probes) + len(key_probes) * 1)}")

    for cond_name, results in all_conditions:
        row = f"  {cond_name:<28}"
        for pid in key_probes:
            probe_results = [r for r in results if r.probe_id == pid]
            if probe_results:
                mean = statistics.mean([r.score for r in probe_results])
                row += f" {mean:>20.3f}"
            else:
                row += f" {'---':>20}"
        print(row)

    # Verdict
    print(f"\n  VERDICT:")
    ea_baseline_collapse = 0.200  # from E-PHASE-CONFIRM

    for cond_name, _, _ in CONDITIONS:
        ea_scores = [r.score for r in by_cond.get(cond_name, [])
                     if r.probe_id == "probe-explore-agent-01"]
        if ea_scores:
            ea_mean = statistics.mean(ea_scores)
            if ea_mean > 0.7:
                print(f"    {cond_name}: explore-agent={ea_mean:.3f} → RESCUED (scope prevents bleed)")
            elif ea_mean < 0.4:
                print(f"    {cond_name}: explore-agent={ea_mean:.3f} → STILL COLLAPSED (scope doesn't help)")
            else:
                print(f"    {cond_name}: explore-agent={ea_mean:.3f} → PARTIAL (attenuated but not prevented)")

    # Overall
    scoped_means = []
    for cond_name in ["scoped-prefix", "scoped-inline"]:
        ea_scores = [r.score for r in by_cond.get(cond_name, [])
                     if r.probe_id == "probe-explore-agent-01"]
        if ea_scores:
            scoped_means.append(statistics.mean(ea_scores))

    if len(scoped_means) == 2:
        avg = statistics.mean(scoped_means)
        if avg > 0.7:
            print(f"\n  SCOPE HYPOTHESIS SUPPORTED: explicit scoping rescues explore-agent")
            print(f"  (avg scoped = {avg:.3f} vs unscoped baseline = {ea_baseline_collapse:.3f})")
        elif avg < 0.4:
            print(f"\n  SCOPE HYPOTHESIS FALSIFIED: explicit scoping does not prevent collapse")
            print(f"  (avg scoped = {avg:.3f} vs unscoped baseline = {ea_baseline_collapse:.3f})")
        else:
            print(f"\n  SCOPE HYPOTHESIS PARTIALLY SUPPORTED: scoping attenuates but doesn't prevent")
            print(f"  (avg scoped = {avg:.3f} vs unscoped baseline = {ea_baseline_collapse:.3f})")

    # Full probe comparison
    print(f"\n  ALL PROBES (mean across trials):")
    all_probe_ids = sorted(set(r.probe_id for r in scope_run.results))
    header = f"  {'Probe':<40}"
    cond_names = ["all-decl", "only-cr-imp"] + [n for n, _, _ in CONDITIONS]
    for cn in cond_names:
        short = cn[:12]
        header += f" {short:>12}"
    print(header)
    print(f"  {'-' * (40 + 12 * len(cond_names) + len(cond_names))}")

    all_results_by_cond = {}
    all_results_by_cond["all-decl"] = baselines.get("density-00", [])
    all_results_by_cond["only-cr-imp"] = baselines.get("density-01", [])
    all_results_by_cond.update(by_cond)

    for pid in all_probe_ids:
        short = pid.replace("probe-", "").replace("-01", "")
        row = f"  {short:<40}"
        for cn in cond_names:
            probe_results = [r for r in all_results_by_cond.get(cn, []) if r.probe_id == pid]
            if probe_results:
                mean = statistics.mean([r.score for r in probe_results])
                row += f" {mean:>12.3f}"
            else:
                row += f" {'---':>12}"
        print(row)


def main():
    parser = argparse.ArgumentParser(description="E-SCOPE: Explicit scoping experiment")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
