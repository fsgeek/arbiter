#!/usr/bin/env python3
"""
E-SURVEY: Lone-imperative detonation survey across all 11 procedural blocks.

E-PHASE-CONFIRM tested 3 blocks as lone imperatives:
  - commit-restrictions → BOMB (explore-agent = 0.200)
  - explore-agent       → no bomb (1.000)
  - todowrite           → no bomb (0.983)

This experiment tests the remaining 8 blocks to answer:
  "How many register bombs exist in this corpus?"
  "What properties distinguish bombs from non-bombs?"

Design: 8 new conditions (one per untested block as lone imperative)
  Each condition: all blocks declarative except one kept imperative.

Usage:
    python scripts/run_e_survey.py --dry-run
    python scripts/run_e_survey.py
    python scripts/run_e_survey.py --compare
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
from arbiter.prompt_blocks import PromptCorpus

from run_e_phase import (
    FREE_BLOCKS, MODEL_MAP, PROCEDURAL_BLOCKS_ORDERED, DECLARATIVE_REWRITES,
    load_corpus,
)
from run_e_phase_confirm import build_all_declarative, build_only_one_imperative

# Already tested in E-PHASE-CONFIRM
ALREADY_TESTED = {
    "claude-code/tool-bash-commit-restrictions",  # BOMB
    "claude-code/tool-policy-explore-agent",       # no bomb
    "claude-code/task-management-todowrite",        # no bomb
}

# The 8 untested blocks
UNTESTED_BLOCKS = [
    b for b in PROCEDURAL_BLOCKS_ORDERED if b not in ALREADY_TESTED
]

# Key probes — the ones affected by the known bomb
KEY_PROBES = [
    "probe-explore-agent-01",
    "probe-proactive-agents-01",
    "probe-use-task-for-search-01",
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


def short_name(block_id: str) -> str:
    return block_id.split("/")[-1]


def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"

    print(f"\nE-SURVEY: Lone-imperative detonation survey")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Untested blocks: {len(UNTESTED_BLOCKS)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(UNTESTED_BLOCKS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(UNTESTED_BLOCKS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Blocks to test:")
    for b in UNTESTED_BLOCKS:
        print(f"    {short_name(b)}")

    print(f"\n  Already tested (E-PHASE-CONFIRM):")
    print(f"    commit-restrictions → BOMB (explore-agent = 0.200)")
    print(f"    explore-agent       → no bomb (1.000)")
    print(f"    todowrite           → no bomb (0.983)")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_survey"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build conditions
    conditions = []
    condition_corpora = {}
    for block_id in UNTESTED_BLOCKS:
        cond_name = f"only-{short_name(block_id)}-imp"
        corpus = build_only_one_imperative(
            load_corpus(base_corpus_path), block_id
        )
        condition_corpora[cond_name] = corpus
        conditions.append((cond_name, block_id))

    configs = [
        AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in condition_corpora[cond_name].blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "lone_imperative": block_id,
            },
        )
        for cond_name, block_id in conditions
    ]

    # Save design
    design = {
        "experiment": "e-survey",
        "date": "2026-04-01",
        "parent": "e-phase-confirm",
        "question": "How many of the 11 procedural blocks are register bombs?",
        "blocks_tested": [
            {"id": b, "short": short_name(b)} for b in UNTESTED_BLOCKS
        ],
        "already_tested": {
            "commit-restrictions": "BOMB (0.200)",
            "explore-agent": "no bomb (1.000)",
            "todowrite": "no bomb (0.983)",
        },
    }
    with open(output_dir / "e_survey_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    client = make_client("e-survey")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-survey-haiku-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-survey",
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

        # Report key probes inline
        for pid in KEY_PROBES:
            scores = [r.score for r in cond_run.results if r.probe_id == pid]
            if scores:
                short_pid = pid.replace("probe-", "").replace("-01", "")
                mean = statistics.mean(scores)
                flag = " *** BOMB?" if mean < 0.5 else ""
                print(f"    {short_pid}: {mean:.3f}{flag}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")

    # Summary table
    print_summary(run)


def print_summary(run):
    """Print the full 11-block detonation matrix."""
    print(f"\n{'=' * 70}")
    print(f"E-SURVEY: DETONATION MATRIX")
    print(f"{'=' * 70}")

    # Combine with known results
    known = {
        "commit-restrictions": {"explore-agent": 0.200, "proactive-agents": 0.150, "use-task-for-search": 0.000},
        "explore-agent": {"explore-agent": 1.000, "proactive-agents": 0.833, "use-task-for-search": None},
        "todowrite": {"explore-agent": 0.983, "proactive-agents": 0.750, "use-task-for-search": None},
    }

    by_cond = defaultdict(list)
    for r in run.results:
        by_cond[r.config_id].append(r)

    header = f"  {'Block (lone imperative)':<35} {'explore-agent':>14} {'proactive':>10} {'use-task':>10} {'Bomb?':>6}"
    print(header)
    print(f"  {'-' * len(header)}")

    # Known results first
    for block_short, scores in known.items():
        ea = scores.get("explore-agent")
        pa = scores.get("proactive-agents")
        ut = scores.get("use-task-for-search")
        bomb = "YES" if ea is not None and ea < 0.5 else "no"
        ea_s = f"{ea:.3f}" if ea is not None else "---"
        pa_s = f"{pa:.3f}" if pa is not None else "---"
        ut_s = f"{ut:.3f}" if ut is not None else "---"
        print(f"  {block_short:<35} {ea_s:>14} {pa_s:>10} {ut_s:>10} {bomb:>6}")

    # New results
    for block_id in UNTESTED_BLOCKS:
        cond_name = f"only-{short_name(block_id)}-imp"
        results = by_cond.get(cond_name, [])
        scores = {}
        for pid in KEY_PROBES:
            probe_scores = [r.score for r in results if r.probe_id == pid]
            if probe_scores:
                scores[pid] = statistics.mean(probe_scores)

        ea = scores.get("probe-explore-agent-01")
        pa = scores.get("probe-proactive-agents-01")
        ut = scores.get("probe-use-task-for-search-01")
        bomb = "YES" if ea is not None and ea < 0.5 else "no" if ea is not None else "?"
        ea_s = f"{ea:.3f}" if ea is not None else "---"
        pa_s = f"{pa:.3f}" if pa is not None else "---"
        ut_s = f"{ut:.3f}" if ut is not None else "---"
        print(f"  {short_name(block_id):<35} {ea_s:>14} {pa_s:>10} {ut_s:>10} {bomb:>6}")

    # Count
    bomb_count = sum(1 for v in known.values() if v.get("explore-agent", 1.0) < 0.5)
    for block_id in UNTESTED_BLOCKS:
        cond_name = f"only-{short_name(block_id)}-imp"
        results = by_cond.get(cond_name, [])
        ea_scores = [r.score for r in results if r.probe_id == "probe-explore-agent-01"]
        if ea_scores and statistics.mean(ea_scores) < 0.5:
            bomb_count += 1

    print(f"\n  TOTAL BOMBS: {bomb_count} / 11 blocks")


def compare(args):
    """Load and display results."""
    output_dir = project_root / "data" / "ablation" / "e_survey"
    files = sorted(output_dir.glob("run_e-survey-*.json"))
    if not files:
        print("No E-SURVEY results found.")
        return
    run = load_run(str(files[-1]))
    print_summary(run)


def main():
    parser = argparse.ArgumentParser(description="E-SURVEY: Lone-imperative detonation survey")
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
