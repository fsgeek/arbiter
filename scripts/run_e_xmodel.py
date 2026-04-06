#!/usr/bin/env python3
"""
E-XMODEL: Cross-model replication of the commit-restrictions register bomb.

E-PHASE-CONFIRM showed commit-restrictions as a lone imperative collapses
explore-agent on Haiku (1.00 → 0.20). Is this Haiku-specific or model-general?

Design: 3 conditions × 4 models (Haiku as baseline, 3 new)
  1. all-decl       — all declarative (baseline)
  2. only-cr-imp    — lone imperative commit-restrictions (the bomb)
  3. scoped-inline  — inline-scoped imperative CR (the fix from E-SCOPE)

Models: haiku (baseline data exists), gemini, deepseek, mistral

Predictions:
  If model-general:  only-cr-imp collapses explore-agent on all models
  If Haiku-specific: only-cr-imp collapses only on Haiku
  If fix generalizes: scoped-inline rescues explore-agent on all models

Usage:
    python scripts/run_e_xmodel.py --dry-run
    python scripts/run_e_xmodel.py
    python scripts/run_e_xmodel.py --compare
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
from run_e_scope import SCOPED_INLINE, CR_BLOCK_ID, build_scoped_condition
from run_e_phase_confirm import build_all_declarative, build_only_one_imperative

# ── Models to test ──────────────────────────────────────────────────────

# Haiku already has data. Run gemini, deepseek, mistral.
NEW_MODELS = ["gemini", "deepseek", "mistral"]
ALL_MODELS = ["haiku"] + NEW_MODELS

# ── Conditions ──────────────────────────────────────────────────────────

CONDITION_NAMES = ["all-decl", "only-cr-imp", "scoped-inline"]


def build_conditions(base_corpus_path: Path):
    """Build the 3 condition corpora."""
    conditions = {}

    # all-decl
    corpus = load_corpus(base_corpus_path)
    conditions["all-decl"] = build_all_declarative(corpus)

    # only-cr-imp
    corpus = load_corpus(base_corpus_path)
    conditions["only-cr-imp"] = build_only_one_imperative(
        corpus, CR_BLOCK_ID
    )

    # scoped-inline (from E-SCOPE)
    corpus = load_corpus(base_corpus_path)
    conditions["scoped-inline"] = build_scoped_condition(
        corpus, SCOPED_INLINE, "scoped-inline"
    )

    return conditions


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

    models_to_run = args.model or NEW_MODELS

    print(f"\nE-XMODEL: Cross-model replication of commit-restrictions register bomb")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(CONDITION_NAMES)}")
    print(f"  Models to run: {', '.join(models_to_run)}")
    print(f"  Trials: {args.trials}")

    n_calls_per_model = len(CONDITION_NAMES) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_per_model = len(CONDITION_NAMES) * n_judge * args.trials
    total_per_model = n_calls_per_model + n_judge_per_model
    total = total_per_model * len(models_to_run)

    print(f"  API calls per model: {n_calls_per_model} + {n_judge_per_model} judge = {total_per_model}")
    print(f"  Total API calls: {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Conditions:")
    print(f"    all-decl        all declarative (baseline)")
    print(f"    only-cr-imp     lone imperative commit-restrictions (the bomb)")
    print(f"    scoped-inline   inline-scoped imperative CR (the fix)")

    print(f"\n  Models:")
    for m in models_to_run:
        print(f"    {m:<12} {MODEL_MAP[m]}")

    print(f"\n  Haiku baselines (from E-PHASE-CONFIRM + E-SCOPE):")
    print(f"    all-decl:      explore-agent = 1.000")
    print(f"    only-cr-imp:   explore-agent = 0.200")
    print(f"    scoped-inline: explore-agent = 1.000")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_xmodel"
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = build_conditions(base_corpus_path)

    # Save design
    design = {
        "experiment": "e-xmodel",
        "date": "2026-03-29",
        "parent": "e-phase-confirm + e-scope",
        "question": "Is the commit-restrictions register bomb Haiku-specific or model-general?",
        "conditions": CONDITION_NAMES,
        "models": {m: MODEL_MAP[m] for m in ALL_MODELS},
        "models_to_run": models_to_run,
        "haiku_baselines": {
            "all-decl": {"explore-agent": 1.000},
            "only-cr-imp": {"explore-agent": 0.200},
            "scoped-inline": {"explore-agent": 1.000},
        },
    }
    with open(output_dir / "e_xmodel_design.json", "w") as f:
        json.dump(design, f, indent=2)

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    for model_key in models_to_run:
        model_id = MODEL_MAP[model_key]
        print(f"\n{'='*60}")
        print(f"  Model: {model_key} ({model_id})")
        print(f"{'='*60}")

        client = make_client("e-xmodel")
        from arbiter.llm_caller import LLMCaller
        caller = LLMCaller(client, model_id)
        runner = AblationRunner(caller=caller)

        configs = [
            AblationConfig(
                id=cond_name,
                phase="baseline",
                present_blocks=[b.id for b in conditions[cond_name].blocks],
                absent_blocks=[],
                metadata={"condition": cond_name, "model": model_key},
            )
            for cond_name in CONDITION_NAMES
        ]

        run_id = f"e-xmodel-{model_key}-{uuid.uuid4().hex[:8]}"
        run = AblationRun(
            id=run_id,
            configs=configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "experiment": "e-xmodel",
                "model": model_key,
                "model_id": model_id,
            },
        )

        for config in configs:
            cond_name = config.id
            corpus = conditions[cond_name]
            print(f"\n  Condition: {cond_name}")

            cond_run = AblationRun(
                id=f"{run_id}-{cond_name}",
                configs=[config],
                battery=battery,
                models=[model_id],
                trials_per_probe=args.trials,
                temperature=0.0,
                metadata={"condition": cond_name, "model": model_key},
            )

            try:
                asyncio.run(runner.run_phase(
                    cond_run, "baseline", corpus=corpus,
                    concurrency=args.concurrency, progress_callback=progress,
                ))
                print()
            except KeyboardInterrupt:
                print("\n\nInterrupted.")
                save_run(run, str(output_dir / f"run_{run.id}_partial.json"))
                return
            except Exception as e:
                print(f"\n  Error: {e}")
                continue

            run.results.extend(cond_run.results)

            # Quick inline for key probes
            ea_scores = [r.score for r in cond_run.results
                         if r.probe_id == "probe-explore-agent-01"]
            pa_scores = [r.score for r in cond_run.results
                         if r.probe_id == "probe-proactive-agents-01"]
            if ea_scores:
                print(f"    explore-agent: {statistics.mean(ea_scores):.3f}")
            if pa_scores:
                print(f"    proactive-agents: {statistics.mean(pa_scores):.3f}")

        save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
        print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Cross-model comparison of the register bomb."""
    output_dir = project_root / "data" / "ablation" / "e_xmodel"

    if not output_dir.exists():
        print("No E-XMODEL results found.")
        return

    # Load all run files
    runs_by_model = {}
    for run_file in sorted(output_dir.glob("run_e-xmodel-*.json")):
        run = load_run(str(run_file))
        model_key = run.metadata.get("model", "unknown")
        runs_by_model[model_key] = run

    # Load Haiku baselines from E-PHASE-CONFIRM and E-SCOPE
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    confirm_dir = project_root / "data" / "ablation" / "e_phase_confirm"
    scope_dir = project_root / "data" / "ablation" / "e_scope"

    haiku_results = defaultdict(list)

    # all-decl from E-PHASE (density-00)
    phase_files = sorted(phase_dir.glob("run_e-phase-haiku-*.json"))
    if phase_files:
        phase_run = load_run(str(phase_files[0]))
        haiku_results["all-decl"] = [r for r in phase_run.results
                                     if r.config_id == "density-00"]
        haiku_results["only-cr-imp"] = [r for r in phase_run.results
                                        if r.config_id == "density-01"]

    # scoped-inline from E-SCOPE
    scope_files = sorted(scope_dir.glob("run_e-scope-*.json"))
    if scope_files:
        scope_run = load_run(str(scope_files[0]))
        haiku_results["scoped-inline"] = [r for r in scope_run.results
                                          if r.config_id == "scoped-inline"]

    print("E-XMODEL: Cross-Model Register Bomb Replication")
    print("=" * 75)

    # Key probe comparison
    key_probes = [
        "probe-explore-agent-01",
        "probe-proactive-agents-01",
        "probe-use-task-for-search-01",
    ]

    for cond_name in CONDITION_NAMES:
        print(f"\n  Condition: {cond_name}")
        header = f"    {'Model':<12}"
        for pid in key_probes:
            short = pid.replace("probe-", "").replace("-01", "")
            header += f" {short:>22}"
        print(header)
        print(f"    {'-' * (12 + 23 * len(key_probes))}")

        # Haiku baseline
        row = f"    {'haiku':<12}"
        for pid in key_probes:
            scores = [r.score for r in haiku_results.get(cond_name, [])
                      if r.probe_id == pid]
            if scores:
                row += f" {statistics.mean(scores):>22.3f}"
            else:
                row += f" {'---':>22}"
        print(row)

        # Other models
        for model_key in NEW_MODELS:
            if model_key not in runs_by_model:
                continue
            run = runs_by_model[model_key]
            cond_results = [r for r in run.results if r.config_id == cond_name]
            row = f"    {model_key:<12}"
            for pid in key_probes:
                scores = [r.score for r in cond_results if r.probe_id == pid]
                if scores:
                    row += f" {statistics.mean(scores):>22.3f}"
                else:
                    row += f" {'---':>22}"
            print(row)

    # Verdict: bomb detonation matrix
    print(f"\n  BOMB DETONATION MATRIX (explore-agent scores):")
    print(f"    {'Model':<12} {'all-decl':>10} {'only-cr-imp':>12} {'scoped-inline':>14} {'Bomb?':>8} {'Fix?':>8}")
    print(f"    {'-' * 66}")

    # Haiku
    ea_decl = [r.score for r in haiku_results.get("all-decl", [])
               if r.probe_id == "probe-explore-agent-01"]
    ea_bomb = [r.score for r in haiku_results.get("only-cr-imp", [])
               if r.probe_id == "probe-explore-agent-01"]
    ea_fix = [r.score for r in haiku_results.get("scoped-inline", [])
              if r.probe_id == "probe-explore-agent-01"]
    decl_val = statistics.mean(ea_decl) if ea_decl else float('nan')
    bomb_val = statistics.mean(ea_bomb) if ea_bomb else float('nan')
    fix_val = statistics.mean(ea_fix) if ea_fix else float('nan')
    bomb_flag = "YES" if bomb_val < 0.5 else "no"
    fix_flag = "YES" if fix_val > 0.7 else "no"
    print(f"    {'haiku':<12} {decl_val:>10.3f} {bomb_val:>12.3f} {fix_val:>14.3f} {bomb_flag:>8} {fix_flag:>8}")

    for model_key in NEW_MODELS:
        if model_key not in runs_by_model:
            continue
        run = runs_by_model[model_key]
        ea_decl = [r.score for r in run.results
                   if r.config_id == "all-decl" and r.probe_id == "probe-explore-agent-01"]
        ea_bomb = [r.score for r in run.results
                   if r.config_id == "only-cr-imp" and r.probe_id == "probe-explore-agent-01"]
        ea_fix = [r.score for r in run.results
                  if r.config_id == "scoped-inline" and r.probe_id == "probe-explore-agent-01"]
        decl_val = statistics.mean(ea_decl) if ea_decl else float('nan')
        bomb_val = statistics.mean(ea_bomb) if ea_bomb else float('nan')
        fix_val = statistics.mean(ea_fix) if ea_fix else float('nan')
        bomb_flag = "YES" if bomb_val < 0.5 else "no"
        fix_flag = "YES" if fix_val > 0.7 else "no"
        print(f"    {model_key:<12} {decl_val:>10.3f} {bomb_val:>12.3f} {fix_val:>14.3f} {bomb_flag:>8} {fix_flag:>8}")

    # Overall
    n_bomb = 0
    n_fix = 0
    n_models = 0
    for model_key in ALL_MODELS:
        if model_key == "haiku":
            results = haiku_results
            ea_bomb = [r.score for r in results.get("only-cr-imp", [])
                       if r.probe_id == "probe-explore-agent-01"]
            ea_fix = [r.score for r in results.get("scoped-inline", [])
                      if r.probe_id == "probe-explore-agent-01"]
        elif model_key in runs_by_model:
            run = runs_by_model[model_key]
            ea_bomb = [r.score for r in run.results
                       if r.config_id == "only-cr-imp" and r.probe_id == "probe-explore-agent-01"]
            ea_fix = [r.score for r in run.results
                      if r.config_id == "scoped-inline" and r.probe_id == "probe-explore-agent-01"]
        else:
            continue
        n_models += 1
        if ea_bomb and statistics.mean(ea_bomb) < 0.5:
            n_bomb += 1
        if ea_fix and statistics.mean(ea_fix) > 0.7:
            n_fix += 1

    print(f"\n  SUMMARY:")
    print(f"    Models tested: {n_models}")
    print(f"    Bomb detonates: {n_bomb}/{n_models}")
    print(f"    Fix works: {n_fix}/{n_models}")
    if n_bomb == n_models:
        print(f"    → Register bomb is MODEL-GENERAL")
    elif n_bomb == 1:
        print(f"    → Register bomb is HAIKU-SPECIFIC")
    else:
        print(f"    → Register bomb is MODEL-DEPENDENT ({n_bomb}/{n_models})")

    if n_fix == n_models:
        print(f"    → Inline scoping fix is MODEL-GENERAL")
    elif n_fix < n_models:
        print(f"    → Inline scoping fix is MODEL-DEPENDENT ({n_fix}/{n_models})")


def main():
    parser = argparse.ArgumentParser(description="E-XMODEL: Cross-model register bomb replication")
    parser.add_argument("--model", action="append", choices=list(MODEL_MAP.keys()),
                        help="Model(s) to test (repeatable; default: gemini, deepseek, mistral)")
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
