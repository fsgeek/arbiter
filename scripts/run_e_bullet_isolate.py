#!/usr/bin/env python3
"""
E-BULLET-ISOLATE: Is the register bomb caused by a specific prohibition
clause that names the probed tool, or by register contrast generally?

Parent: T18 (E-COUNTERMANDATE), T17, T14 (E-PHASE-CONFIRM).

The original commit-restrictions text has 7 bullets. E-PHASE showed that making
the whole block imperative (only-cr-imp) collapses Task-using probes. This
experiment deletes one bullet at a time to test which bullet is doing the work.

Three conditions, each with commit-restrictions as the lone imperative block,
but with one bullet removed:

  1. cr-no-task    — remove "NEVER use the TodoWrite or Task tools"
                     Target: the bullet that names the probed tools.
  2. cr-no-explore — remove "NEVER run additional commands to read or explore..."
                     Tests: is it about exploration semantics generally?
  3. cr-no-heredoc — remove "ALWAYS pass the commit message via a HEREDOC"
                     Null control: structurally similar imperative, different
                     semantic territory, should have no effect on Task probes.

Baseline (from E-PHASE density-01): only-cr-imp → explore-agent = 0.200

Predictions:
  Specific-clause-names-probed-tool:  cr-no-task disarms; others detonate
  Any-exploration-related:            cr-no-task + cr-no-explore disarm
  Register bomb (general):            none disarm
  Any-bullet-weakening:               all three attenuate equally

Cost: 3 conditions × 22 probes × 3 trials = 198 calls + ~90 judge ≈ $0.30

Usage:
    python scripts/run_e_bullet_isolate.py --dry-run
    python scripts/run_e_bullet_isolate.py
    python scripts/run_e_bullet_isolate.py --compare
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

sys.path.insert(0, str(project_root / "scripts"))
from run_e_phase import (
    FREE_BLOCKS, MODEL_MAP, PROCEDURAL_BLOCKS_ORDERED, DECLARATIVE_REWRITES,
    load_corpus,
)

# ── Bullets to remove ─────────────────────────────────────────────────

CR_ID = "claude-code/tool-bash-commit-restrictions"

# Substrings identifying each bullet. Each must match exactly one line in the
# original CR block text. Verified against v2.1.50_blocks.json.
BULLET_REMOVALS = {
    "cr-no-task": "- NEVER use the TodoWrite or Task tools",
    "cr-no-explore": "- NEVER run additional commands to read or explore code, besides git bash commands",
    "cr-no-heredoc": "- ALWAYS pass the commit message via a HEREDOC",
}


def build_cr_with_bullet_removed(corpus: PromptCorpus, bullet_line: str) -> PromptCorpus:
    """All procedural blocks declarative except commit-restrictions imperative
    with one bullet line removed (exact match)."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id == CR_ID:
            # Remove the matching bullet line (and its trailing newline if any)
            original_text = b.text
            lines = original_text.split("\n")
            new_lines = [line for line in lines if line.strip() != bullet_line.strip()]
            if len(new_lines) == len(lines):
                raise ValueError(f"Bullet not found in CR text: {bullet_line!r}")
            new_blocks.append(b.model_copy(update={"text": "\n".join(new_lines)}))
        elif b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name + f"-cr-minus-bullet",
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


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

    print("\nE-BULLET-ISOLATE: Which bullet in commit-restrictions detonates?")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(BULLET_REMOVALS)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(BULLET_REMOVALS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(BULLET_REMOVALS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print("\n  Conditions:")
    for name, bullet in BULLET_REMOVALS.items():
        print(f"    {name:<16}  remove: {bullet}")

    print("\n  Baseline (from E-PHASE):")
    print("    only-cr-imp (d1):  explore-agent = 0.200")
    print("    all-decl    (d0):  explore-agent = 1.000")
    print("  Predictions:")
    print("    specific-clause : cr-no-task disarms; others detonate")
    print("    any-exploration : cr-no-task + cr-no-explore disarm")
    print("    register bomb   : none disarm")
    print("    any-bullet      : all three attenuate")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    # Verify bullets exist before running
    corpus = load_corpus(base_corpus_path)
    cr_block = next((b for b in corpus.blocks if b.id == CR_ID), None)
    if cr_block is None:
        print(f"ERROR: {CR_ID} not found in corpus")
        sys.exit(1)
    for name, bullet in BULLET_REMOVALS.items():
        if bullet.strip() not in [l.strip() for l in cr_block.text.split("\n")]:
            print(f"ERROR: bullet for {name} not found in CR text:\n  {bullet!r}")
            print(f"\nActual CR text:\n{cr_block.text}")
            sys.exit(1)

    output_dir = project_root / "data" / "ablation" / "e_bullet_isolate"
    output_dir.mkdir(parents=True, exist_ok=True)

    condition_corpora = {}
    configs = []

    for cond_name, bullet in BULLET_REMOVALS.items():
        corpus = build_cr_with_bullet_removed(load_corpus(base_corpus_path), bullet)
        condition_corpora[cond_name] = corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "removed_bullet": bullet,
                "builder": "cr_with_bullet_removed",
            },
        ))

    design = {
        "experiment": "e-bullet-isolate",
        "date": "2026-04-22",
        "parent": "e-countermandate",
        "cairn": "T18",
        "question": "Which bullet in commit-restrictions is responsible for the register bomb?",
        "conditions": [
            {"name": n, "removed_bullet": b} for n, b in BULLET_REMOVALS.items()
        ],
    }
    with open(output_dir / "e_bullet_isolate_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    client = make_client("e-bullet-isolate")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-bullet-isolate-haiku-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-bullet-isolate",
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

        for probe_id, label in [
            ("probe-explore-agent-01", "explore-agent"),
            ("probe-proactive-agents-01", "proactive-agents"),
            ("probe-use-task-for-search-01", "use-task-for-search"),
        ]:
            scores = [r.score for r in cond_run.results
                     if r.probe_id == probe_id and r.score is not None]
            if scores:
                print(f"    {label:<20} {statistics.mean(scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    bi_dir = project_root / "data" / "ablation" / "e_bullet_isolate"
    phase_dir = project_root / "data" / "ablation" / "e_phase"

    if not bi_dir.exists():
        print("No E-BULLET-ISOLATE results found.")
        return

    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    phase_run = load_run(str(phase_files[0])) if phase_files else None

    bi_files = sorted(bi_dir.glob("run_e-bullet-isolate-*.json"))
    if not bi_files:
        print("No result files found.")
        return
    bi_run = load_run(str(bi_files[0]))

    print("E-BULLET-ISOLATE: Which Bullet Detonates?")
    print("=" * 70)

    baselines = {}
    if phase_run:
        for config_id in ["density-00", "density-01"]:
            results = [r for r in phase_run.results if r.config_id == config_id]
            baselines[config_id] = results

    key_probes = [
        "probe-explore-agent-01",
        "probe-proactive-agents-01",
        "probe-use-task-for-search-01",
        "probe-todowrite-01",
    ]

    all_conditions = [
        ("all-decl (E-PHASE d0)", baselines.get("density-00", [])),
        ("only-cr-imp (E-PHASE d1)", baselines.get("density-01", [])),
    ]
    by_cond = defaultdict(list)
    for r in bi_run.results:
        by_cond[r.config_id].append(r)
    for cond_name in BULLET_REMOVALS:
        all_conditions.append((cond_name, by_cond.get(cond_name, [])))

    print(f"\n  {'Condition':<30}", end="")
    for pid in key_probes:
        short = pid.replace("probe-", "").replace("-01", "")
        print(f" {short:>20}", end="")
    print()
    print(f"  {'-' * 110}")

    for cond_name, results in all_conditions:
        print(f"  {cond_name:<30}", end="")
        for pid in key_probes:
            pr = [r for r in results if r.probe_id == pid and r.score is not None]
            if pr:
                mean = statistics.mean([r.score for r in pr])
                print(f" {mean:>20.3f}", end="")
            else:
                print(f" {'---':>20}", end="")
        print()

    # Verdict on explore-agent
    def mean_of(cond, probe):
        rs = [r.score for r in by_cond.get(cond, [])
              if r.probe_id == probe and r.score is not None]
        return statistics.mean(rs) if rs else None

    print("\n  VERDICT on explore-agent (baseline all-decl=1.00, only-cr-imp=0.20):")
    for cond in BULLET_REMOVALS:
        val = mean_of(cond, "probe-explore-agent-01")
        if val is None:
            print(f"    {cond}: no data")
            continue
        if val >= 0.85:
            tag = "DISARMED"
        elif val >= 0.50:
            tag = "attenuated"
        else:
            tag = "still detonates"
        print(f"    {cond:<16} {val:.3f}  {tag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
