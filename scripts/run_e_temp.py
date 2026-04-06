#!/usr/bin/env python3
"""
E-TEMP: Temperature sensitivity of the register bomb.

Does the commit-restrictions register bomb still detonate at temperature 0.7?
Minimal experiment: 2 conditions × 1 model × temperature 0.7.

Usage:
    python scripts/run_e_temp.py --dry-run
    python scripts/run_e_temp.py
    python scripts/run_e_temp.py --compare
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

from run_e_phase import MODEL_MAP, DECLARATIVE_REWRITES, load_corpus
from run_e_phase_confirm import build_all_declarative, build_only_one_imperative

CR_BLOCK_ID = "claude-code/tool-bash-commit-restrictions"

CONDITIONS = [
    ("all-decl", "all declarative"),
    ("only-cr-imp", "lone imperative commit-restrictions"),
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

    temp = args.temperature

    print(f"\nE-TEMP: Register bomb at temperature {temp}")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(CONDITIONS)}")
    print(f"  Trials: {args.trials}")
    print(f"  Temperature: {temp}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Baselines (temperature 0.0, from E-PHASE-CONFIRM):")
    print(f"    all-decl:      explore-agent = 1.000")
    print(f"    only-cr-imp:   explore-agent = 0.200")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_temp"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build corpora
    condition_corpora = {
        "all-decl": build_all_declarative(load_corpus(base_corpus_path)),
        "only-cr-imp": build_only_one_imperative(
            load_corpus(base_corpus_path), CR_BLOCK_ID
        ),
    }

    configs = [
        AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in condition_corpora[cond_name].blocks],
            absent_blocks=[],
            metadata={"condition": cond_name, "temperature": temp},
        )
        for cond_name, _ in CONDITIONS
    ]

    # Save design
    design = {
        "experiment": "e-temp",
        "date": "2026-03-29",
        "parent": "e-phase-confirm",
        "question": f"Does the register bomb detonate at temperature {temp}?",
        "temperature": temp,
        "conditions": [{"name": n, "description": d} for n, d in CONDITIONS],
    }
    with open(output_dir / f"e_temp_design_t{temp}.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    client = make_client("e-temp")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-temp-haiku-t{temp}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=temp,
        metadata={
            "experiment": "e-temp",
            "model": "haiku",
            "model_id": model_id,
            "temperature": temp,
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
            temperature=temp,
            metadata={"condition": cond_name, "temperature": temp},
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
                     if r.probe_id == "probe-explore-agent-01"]
        pa_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-proactive-agents-01"]
        if ea_scores:
            print(f"    explore-agent: {statistics.mean(ea_scores):.3f} (trials: {ea_scores})")
        if pa_scores:
            print(f"    proactive-agents: {statistics.mean(pa_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")

    # Quick verdict
    ea_decl = [r.score for r in run.results
               if r.config_id == "all-decl" and r.probe_id == "probe-explore-agent-01"]
    ea_bomb = [r.score for r in run.results
               if r.config_id == "only-cr-imp" and r.probe_id == "probe-explore-agent-01"]
    if ea_decl and ea_bomb:
        d = statistics.mean(ea_decl)
        b = statistics.mean(ea_bomb)
        print(f"\n  VERDICT (temperature {temp}):")
        print(f"    all-decl explore-agent:    {d:.3f}")
        print(f"    only-cr-imp explore-agent: {b:.3f}")
        if b < 0.5 and d > 0.7:
            print(f"    → BOMB DETONATES at temperature {temp}")
        elif b > 0.7:
            print(f"    → Bomb DOES NOT detonate at temperature {temp}")
        else:
            print(f"    → ATTENUATED (baseline {d:.3f}, bomb {b:.3f})")


def main():
    parser = argparse.ArgumentParser(description="E-TEMP: Temperature sensitivity")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--trials", type=int, default=5,
                        help="More trials needed at non-zero temperature (default: 5)")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_experiment(args)


if __name__ == "__main__":
    main()
