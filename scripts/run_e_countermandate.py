#!/usr/bin/env python3
"""
E-COUNTERMANDATE: Does a co-registered mandate disarm the register bomb?

Parent: E-PHASE-CONFIRM (T14), E-SCOPE (T15), T17 cairn.

Finding to test: In E-PHASE, explore-agent collapses at d1 (only commit-restrictions
imperative) and fully rescues at d9 (when todowrite block becomes imperative alongside
6 others). The T17 hypothesis is that making todowrite's mandate imperative puts it
in same-register conflict with commit-restrictions' prohibition. Mandate and
prohibition compete, and the prohibition's scope snaps back to commit-only.

Three conditions, each two-block imperative (everything else declarative):
  1. cr+tw-imp   (core):  commit-restrictions + todowrite imperative
  2. cr+ea-imp   (control): commit-restrictions + explore-agent imperative
                  - EA is a permission, not a mandate. Tests "any second imperative".
  3. cr+text-imp (control): commit-restrictions + text-only-comms imperative
                  - Unrelated content. Tests "register uniformity alone".

Baselines already exist from E-PHASE:
  density-00 (all-decl):     explore-agent = 1.000
  density-01 (only-cr-imp):  explore-agent = 0.200

Predictions:
  If competing-mandate is the mechanism:
    cr+tw-imp   : explore-agent ≥ 0.85  (rescue)
    cr+ea-imp   : explore-agent 0.20–0.85  (at best partial self-rescue)
    cr+text-imp : explore-agent ≈ 0.20  (no rescue)

  If cumulative register-uniformity is the mechanism:
    all three conditions rescue explore-agent similarly

  If self-rescue dominates:
    cr+ea-imp rescues; cr+tw-imp does not (TW isn't the probe's own block)

Cost estimate: 3 conditions × 22 probes × 3 trials = 198 calls + ~90 judge calls
               ≈ $0.30

Usage:
    python scripts/run_e_countermandate.py --dry-run
    python scripts/run_e_countermandate.py
    python scripts/run_e_countermandate.py --compare
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

# ── Condition builder ────────────────────────────────────────────────

def build_selected_imperative(corpus: PromptCorpus, keep_imperative: list[str]) -> PromptCorpus:
    """All procedural blocks rewritten to declarative EXCEPT the listed blocks."""
    keep = set(keep_imperative)
    new_blocks = []
    for b in corpus.blocks:
        if b.id in DECLARATIVE_REWRITES and b.id not in keep:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    short = "+".join(k.split("/")[-1][:6] for k in keep_imperative)
    return PromptCorpus(
        name=corpus.name + f"-imp-{short}",
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


# ── Conditions ───────────────────────────────────────────────────────

CR = "claude-code/tool-bash-commit-restrictions"
TW = "claude-code/task-management-todowrite"
EA = "claude-code/tool-policy-explore-agent"
TEXT = "claude-code/tone-text-only-comms"

CONDITIONS = [
    ("cr+tw-imp",   "commit-restrictions + todowrite imperative (core test: competing mandate)",
     [CR, TW]),
    ("cr+ea-imp",   "commit-restrictions + explore-agent imperative (control: self-rescue)",
     [CR, EA]),
    ("cr+text-imp", "commit-restrictions + text-only-comms imperative (control: register uniformity)",
     [CR, TEXT]),
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

    print(f"\nE-COUNTERMANDATE: Does a co-registered mandate disarm the bomb?")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(CONDITIONS)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Conditions:")
    for name, desc, keep in CONDITIONS:
        print(f"    {name:<14} {desc}")
        for b in keep:
            print(f"       imperative: {b}")

    print(f"\n  Key probe: probe-explore-agent-01")
    print(f"  Baselines (from E-PHASE):")
    print(f"    all-decl      (d0) : explore-agent = 1.000")
    print(f"    only-cr-imp   (d1) : explore-agent = 0.200")
    print(f"  Predictions (competing-mandate):")
    print(f"    cr+tw-imp     : explore-agent ≥ 0.85   (rescue)")
    print(f"    cr+ea-imp     : explore-agent 0.20–0.85 (at best partial self-rescue)")
    print(f"    cr+text-imp   : explore-agent ≈ 0.20    (no rescue)")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_countermandate"
    output_dir.mkdir(parents=True, exist_ok=True)

    condition_corpora = {}
    configs = []

    for cond_name, cond_desc, keep in CONDITIONS:
        corpus = build_selected_imperative(load_corpus(base_corpus_path), keep)
        condition_corpora[cond_name] = corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "description": cond_desc,
                "builder": "selected_imperative",
                "imperative_blocks": keep,
            },
        ))

    # Save design
    design = {
        "experiment": "e-countermandate",
        "date": "2026-04-22",
        "parent": "e-phase-confirm",
        "cairn": "T17",
        "question": "Does a co-registered mandate disarm the commit-restrictions register bomb?",
        "conditions": [
            {"name": n, "description": d, "imperative_blocks": k}
            for n, d, k in CONDITIONS
        ],
    }
    with open(output_dir / "e_countermandate_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    client = make_client("e-countermandate")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-countermandate-haiku-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-countermandate",
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

        ea_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-explore-agent-01" and r.score is not None]
        pa_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-proactive-agents-01" and r.score is not None]
        ut_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-use-task-for-search-01" and r.score is not None]
        tw_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-todowrite-01" and r.score is not None]
        if ea_scores:
            print(f"    explore-agent:         {statistics.mean(ea_scores):.3f}")
        if pa_scores:
            print(f"    proactive-agents:      {statistics.mean(pa_scores):.3f}")
        if ut_scores:
            print(f"    use-task-for-search:   {statistics.mean(ut_scores):.3f}")
        if tw_scores:
            print(f"    todowrite:             {statistics.mean(tw_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare E-COUNTERMANDATE results against E-PHASE baselines."""
    cm_dir = project_root / "data" / "ablation" / "e_countermandate"
    phase_dir = project_root / "data" / "ablation" / "e_phase"

    if not cm_dir.exists():
        print("No E-COUNTERMANDATE results found.")
        return

    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    phase_run = load_run(str(phase_files[0])) if phase_files else None

    cm_files = sorted(cm_dir.glob("run_e-countermandate-*.json"))
    if not cm_files:
        print("No result files found.")
        return
    cm_run = load_run(str(cm_files[0]))

    print("E-COUNTERMANDATE: Competing-Mandate Analysis")
    print("=" * 70)

    baselines = {}
    if phase_run:
        for config_id in ["density-00", "density-01", "density-09"]:
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
    for r in cm_run.results:
        by_cond[r.config_id].append(r)
    for cond_name, _, _ in CONDITIONS:
        all_conditions.append((cond_name, by_cond.get(cond_name, [])))
    all_conditions.append(("+TW at d9 (E-PHASE d9)", baselines.get("density-09", [])))

    print(f"\n  KEY PROBES BY CONDITION:")
    header = f"  {'Condition':<28}"
    for pid in key_probes:
        short = pid.replace("probe-", "").replace("-01", "")
        header += f" {short:>20}"
    print(header)
    print(f"  {'-' * len(header)}")

    for cond_name, results in all_conditions:
        row = f"  {cond_name:<28}"
        for pid in key_probes:
            pr = [r for r in results if r.probe_id == pid and r.score is not None]
            if pr:
                mean = statistics.mean([r.score for r in pr])
                row += f" {mean:>20.3f}"
            else:
                row += f" {'---':>20}"
        print(row)

    # Verdict
    def mean_of(cond, probe):
        rs = [r.score for r in by_cond.get(cond, [])
              if r.probe_id == probe and r.score is not None]
        return statistics.mean(rs) if rs else None

    ea_cm_tw = mean_of("cr+tw-imp", "probe-explore-agent-01")
    ea_cm_ea = mean_of("cr+ea-imp", "probe-explore-agent-01")
    ea_cm_tx = mean_of("cr+text-imp", "probe-explore-agent-01")

    print(f"\n  VERDICT on explore-agent (baseline all-decl=1.00, only-cr-imp=0.20):")
    for label, val in [("cr+tw-imp", ea_cm_tw), ("cr+ea-imp", ea_cm_ea), ("cr+text-imp", ea_cm_tx)]:
        if val is None:
            print(f"    {label}: no data")
            continue
        if val >= 0.85:
            tag = "STRONG RESCUE"
        elif val >= 0.50:
            tag = "partial rescue"
        else:
            tag = "no rescue"
        print(f"    {label}: {val:.3f}  {tag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true", help="Analyze existing results")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
