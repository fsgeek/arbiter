#!/usr/bin/env python3
"""
E-PHASE-CONFIRM: Isolate whether register interference is block-specific
or a "lone wolf" effect.

E-PHASE found that switching commit-restrictions to imperative (density 0→1)
collapses explore-agent from 1.00 → 0.20. But is this because:
  (A) commit-restrictions specifically interferes with explore-agent, or
  (B) ANY single imperative block in an otherwise declarative field causes collapse?

Design: 6 conditions
  1. all-declarative          (= E-PHASE density 0, already have data)
  2. only-cr-imperative       (= E-PHASE density 1, already have data)
  3. only-ea-imperative       (all declarative except explore-agent stays imperative)
  4. only-tw-imperative       (all declarative except todowrite stays imperative)
  5. all-imperative-except-cr (all imperative except commit-restrictions is declarative)
  6. all-imperative           (= E-PHASE density 11, already have data)

Predictions:
  If (A) block-specific: condition 3 and 4 should NOT collapse explore-agent
  If (B) lone wolf: conditions 3 and 4 WILL collapse explore-agent too
  Condition 5 tests the inverse: if cr is the culprit, removing only cr
  from all-imperative should NOT restore explore-agent (because density 11
  has explore-agent at 1.00, so there's nothing to restore)

Usage:
    python scripts/run_e_phase_confirm.py --dry-run
    python scripts/run_e_phase_confirm.py
    python scripts/run_e_phase_confirm.py --compare
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

from arbiter.ablation.battery import load_battery
from arbiter.ablation.configuration import AblationConfig
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

# ── Constants ─────────────────────────────────────────────────────────

# Import from e_phase
sys.path.insert(0, str(project_root / "scripts"))
from run_e_phase import (
    FREE_BLOCKS, MODEL_MAP, PROCEDURAL_BLOCKS_ORDERED, DECLARATIVE_REWRITES,
    load_corpus,
)

# ── Condition builders ───────────────────────────────────────────────

def build_all_declarative(corpus: PromptCorpus) -> PromptCorpus:
    """All procedural blocks rewritten to declarative."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name + "-all-declarative",
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


def build_only_one_imperative(corpus: PromptCorpus, keep_imperative: str) -> PromptCorpus:
    """All procedural blocks declarative EXCEPT one kept imperative."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id in DECLARATIVE_REWRITES and b.id != keep_imperative:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name + f"-only-{keep_imperative.split('/')[-1]}-imperative",
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


def build_all_imperative_except(corpus: PromptCorpus, make_declarative: str) -> PromptCorpus:
    """All procedural blocks imperative (original) EXCEPT one rewritten to declarative."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id == make_declarative and b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name + f"-all-except-{make_declarative.split('/')[-1]}",
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


# ── Conditions ───────────────────────────────────────────────────────

CONDITIONS = [
    # (name, description, builder_func, builder_arg)
    ("only-ea-imp", "all declarative except explore-agent imperative",
     "only_one", "claude-code/tool-policy-explore-agent"),
    ("only-tw-imp", "all declarative except todowrite imperative",
     "only_one", "claude-code/task-management-todowrite"),
    ("all-except-cr", "all imperative except commit-restrictions declarative",
     "all_except", "claude-code/tool-bash-commit-restrictions"),
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

    print(f"\nE-PHASE-CONFIRM: Block-specific vs lone-wolf register interference")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  New conditions: {len(CONDITIONS)}")
    print(f"  (3 conditions already have data from E-PHASE)")
    print(f"  Trials: {args.trials}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Conditions (new):")
    for name, desc, _, _ in CONDITIONS:
        print(f"    {name:<20} {desc}")
    print(f"\n  Conditions (from E-PHASE, already have data):")
    print(f"    {'all-decl':<20} all declarative (density-0)")
    print(f"    {'only-cr-imp':<20} only commit-restrictions imperative (density-1)")
    print(f"    {'all-imp':<20} all imperative/original (density-11)")

    print(f"\n  Key probe: explore-agent")
    print(f"  Predictions:")
    print(f"    Block-specific:  only-ea-imp & only-tw-imp have explore-agent ~1.00")
    print(f"    Lone-wolf:       only-ea-imp & only-tw-imp have explore-agent ~0.20")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_phase_confirm"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build condition corpora and configs
    condition_corpora = {}
    configs = []

    for cond_name, cond_desc, builder_type, builder_arg in CONDITIONS:
        if builder_type == "only_one":
            corpus = build_only_one_imperative(load_corpus(base_corpus_path), builder_arg)
        elif builder_type == "all_except":
            corpus = build_all_imperative_except(load_corpus(base_corpus_path), builder_arg)
        else:
            raise ValueError(f"Unknown builder: {builder_type}")

        condition_corpora[cond_name] = corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "description": cond_desc,
                "builder": builder_type,
                "builder_arg": builder_arg,
            },
        ))

    # Save design
    design = {
        "experiment": "e-phase-confirm",
        "date": "2026-03-28",
        "parent": "e-phase",
        "question": "Is commit-restrictions→explore-agent interference block-specific or lone-wolf?",
        "conditions": [
            {"name": n, "description": d, "builder": b, "arg": a}
            for n, d, b, a in CONDITIONS
        ],
    }
    with open(output_dir / "e_phase_confirm_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    client = make_client("e-phase-confirm")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-phase-confirm-haiku-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-phase-confirm",
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

        # Quick inline for key probe
        ea_scores = [r.score for r in cond_run.results if r.probe_id == "probe-explore-agent-01"]
        pa_scores = [r.score for r in cond_run.results if r.probe_id == "probe-proactive-agents-01"]
        if ea_scores:
            print(f"    explore-agent: {statistics.mean(ea_scores):.3f}")
        if pa_scores:
            print(f"    proactive-agents: {statistics.mean(pa_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare confirmation results against E-PHASE baselines."""
    confirm_dir = project_root / "data" / "ablation" / "e_phase_confirm"
    phase_dir = project_root / "data" / "ablation" / "e_phase"

    if not confirm_dir.exists():
        print("No confirmation results found.")
        return

    # Load E-PHASE baselines
    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    phase_run = load_run(str(phase_files[0])) if phase_files else None

    # Load confirmation
    confirm_files = sorted(confirm_dir.glob("run_e-phase-confirm-*.json"))
    if not confirm_files:
        print("No confirmation result files found.")
        return

    confirm_run = load_run(str(confirm_files[0]))

    print("E-PHASE-CONFIRM: Block-Specific vs Lone-Wolf Analysis")
    print("=" * 70)

    # Get E-PHASE baselines
    baselines = {}
    if phase_run:
        for config_id in ["density-00", "density-01", "density-11"]:
            results = [r for r in phase_run.results if r.config_id == config_id]
            baselines[config_id] = results

    # Key probes
    key_probes = [
        "probe-explore-agent-01",
        "probe-proactive-agents-01",
        "probe-use-task-for-search-01",
        "probe-plan-with-todo-01",
    ]

    # Build comparison table
    all_conditions = [
        ("all-decl (E-PHASE d0)", baselines.get("density-00", [])),
        ("only-cr-imp (E-PHASE d1)", baselines.get("density-01", [])),
    ]

    # Add confirmation conditions
    by_cond = defaultdict(list)
    for r in confirm_run.results:
        by_cond[r.config_id].append(r)

    for cond_name, _, _, _ in CONDITIONS:
        all_conditions.append((cond_name, by_cond.get(cond_name, [])))

    all_conditions.append(("all-imp (E-PHASE d11)", baselines.get("density-11", [])))

    print(f"\n  KEY PROBES BY CONDITION:")
    header = f"  {'Condition':<28}"
    for pid in key_probes:
        short = pid.replace("probe-", "").replace("-01", "")
        header += f" {short:>18}"
    print(header)
    print(f"  {'-' * len(header)}")

    for cond_name, results in all_conditions:
        row = f"  {cond_name:<28}"
        for pid in key_probes:
            probe_results = [r for r in results if r.probe_id == pid]
            if probe_results:
                mean = statistics.mean([r.score for r in probe_results])
                row += f" {mean:>18.3f}"
            else:
                row += f" {'---':>18}"
        print(row)

    # Verdict
    print(f"\n  VERDICT:")
    # Check only-ea-imp explore-agent score
    ea_only_ea = [r.score for r in by_cond.get("only-ea-imp", [])
                  if r.probe_id == "probe-explore-agent-01"]
    ea_only_tw = [r.score for r in by_cond.get("only-tw-imp", [])
                  if r.probe_id == "probe-explore-agent-01"]

    if ea_only_ea:
        ea_mean = statistics.mean(ea_only_ea)
        if ea_mean > 0.7:
            print(f"    only-ea-imp explore-agent={ea_mean:.3f} → HIGH")
            print(f"    → When explore-agent itself is the lone imperative, it's fine.")
        else:
            print(f"    only-ea-imp explore-agent={ea_mean:.3f} → LOW")
            print(f"    → Even explore-agent's own imperative form causes collapse!")

    if ea_only_tw:
        tw_mean = statistics.mean(ea_only_tw)
        if tw_mean > 0.7:
            print(f"    only-tw-imp explore-agent={tw_mean:.3f} → HIGH")
            print(f"    → Todowrite as lone imperative does NOT collapse explore-agent.")
            print(f"    → BLOCK-SPECIFIC: commit-restrictions is the specific culprit.")
        elif tw_mean < 0.4:
            print(f"    only-tw-imp explore-agent={tw_mean:.3f} → LOW")
            print(f"    → ANY lone imperative collapses explore-agent → LONE-WOLF effect.")
        else:
            print(f"    only-tw-imp explore-agent={tw_mean:.3f} → MIXED")


def main():
    parser = argparse.ArgumentParser(description="E-PHASE-CONFIRM")
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
