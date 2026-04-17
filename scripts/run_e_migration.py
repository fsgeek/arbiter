#!/usr/bin/env python3
"""
E-MIGRATION: Does the commit-restrictions bomb migrate to the dominant
Task-family policy block in a minimal synthetic prompt?

Parent: E-MINIMAL-BOMB (docs/research/e_minimal_bomb_analysis.md)
    In v2 (8 blocks, including both proactive-agents and explore-agent
    policy), the bomb drove PA 0.970 -> 0.150 — a +0.82 drop matching the
    canonical EA collapse magnitude on the full Claude Code prompt — but
    did NOT suppress EA. That was a single 10-trial observation.

Hypothesis
----------
The commit-restrictions register bomb suppresses whichever Task-family
policy block is most salient in surrounding context, not explore-agent
specifically. In Claude Code, EA happens to be the dominant receiver; in
v2 (with PA declared just above EA), PA absorbs the interference instead.

Design
------
Four conditions, 15 trials per condition per probe on Haiku 4.5:

  v2:baseline       — v2 (8 blocks) without the bomb
  v2:bomb-present   — v2 (8 blocks) with the bomb
  v2b:baseline      — v2 with PA removed (7 blocks), no bomb
  v2b:bomb-present  — v2b with the bomb

Probes: explore-agent-01, proactive-agents-01, use-task-for-search-01
Total: 4 × 3 × 15 = 180 probe calls + up to 180 judge calls (~$1-2).

Interpretation
--------------
Replication: v2:baseline PA ~= 0.97 and v2:bomb-present PA ~= 0.15 must
replicate to preserve the receiver-migration hypothesis.

Receiver migration: with PA removed in v2b, if the bomb returns to
suppressing EA (EA drops substantially baseline -> bomb-present), this
confirms the bomb targets whatever Task-family policy is dominant rather
than being wired to EA. If EA does NOT drop in v2b, either PA had unique
absorption properties, or v2b lacks sufficient context to make EA the
new dominant receiver.

Usage
-----
    python scripts/run_e_migration.py --dry-run
    python scripts/run_e_migration.py
    python scripts/run_e_migration.py --compare
"""

from __future__ import annotations

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

from arbiter.ablation.battery import load_battery, ProbeBattery
from arbiter.ablation.configuration import AblationConfig
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

from run_e_phase import MODEL_MAP, load_corpus

# ── Constants ────────────────────────────────────────────────────────

VARIANT_CORPUS_PATHS = {
    "v2":  project_root / "data" / "prompts" / "minimal-bomb" / "v2_blocks.json",
    "v2b": project_root / "data" / "prompts" / "minimal-bomb" / "v2b_blocks.json",
}

BOMB_BLOCK_ID = "minimal-bomb/tool-bash-commit-restrictions"

KEY_PROBE_IDS = [
    "probe-explore-agent-01",
    "probe-proactive-agents-01",
    "probe-use-task-for-search-01",
]

OUTPUT_DIR = project_root / "data" / "ablation" / "e_migration"


# ── Corpus helpers ───────────────────────────────────────────────────

def all_block_ids(corpus: PromptCorpus) -> list[str]:
    return [b.id for b in corpus.blocks]


def build_baseline_config(corpus: PromptCorpus, variant: str) -> AblationConfig:
    present = [bid for bid in all_block_ids(corpus) if bid != BOMB_BLOCK_ID]
    return AblationConfig(
        id=f"{variant}:baseline",
        phase="baseline",
        present_blocks=present,
        absent_blocks=[BOMB_BLOCK_ID],
        metadata={
            "variant": variant,
            "condition": "baseline",
            "description": f"{variant} corpus without commit-restrictions bomb",
        },
    )


def build_bomb_config(corpus: PromptCorpus, variant: str) -> AblationConfig:
    return AblationConfig(
        id=f"{variant}:bomb-present",
        phase="baseline",
        present_blocks=all_block_ids(corpus),
        absent_blocks=[],
        metadata={
            "variant": variant,
            "condition": "bomb-present",
            "description": f"{variant} corpus WITH commit-restrictions bomb",
        },
    )


def filter_battery_to_key_probes(battery: ProbeBattery) -> ProbeBattery:
    by_id = {p.id: p for p in battery.probes}
    missing = [pid for pid in KEY_PROBE_IDS if pid not in by_id]
    if missing:
        raise RuntimeError(
            f"Battery missing expected probes: {missing}. "
            f"Available: {[p.id for p in battery.probes]}"
        )
    return ProbeBattery(
        probes=[by_id[pid] for pid in KEY_PROBE_IDS],
        metadata={
            **battery.metadata,
            "filtered_from": "phase0_battery",
            "filtered_to": list(KEY_PROBE_IDS),
        },
    )


# ── API wiring ───────────────────────────────────────────────────────

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


# ── Experiment ───────────────────────────────────────────────────────

def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    full_battery = load_battery(battery_path)
    battery = filter_battery_to_key_probes(full_battery)

    variants = args.variants or ["v2", "v2b"]

    all_configs: list[tuple[str, PromptCorpus, AblationConfig]] = []
    for variant in variants:
        corpus_path = VARIANT_CORPUS_PATHS[variant]
        if not corpus_path.exists():
            print(f"ERROR: corpus not found at {corpus_path}")
            sys.exit(1)
        corpus = load_corpus(corpus_path)
        all_configs.append((variant, corpus, build_baseline_config(corpus, variant)))
        all_configs.append((variant, corpus, build_bomb_config(corpus, variant)))

    print(f"\nE-MIGRATION: does the bomb migrate to the dominant Task-family block?")
    print(f"  Variants:    {variants}")
    for variant, corpus, cfg in all_configs:
        print(f"    {cfg.id:<22} {len(cfg.present_blocks)} blocks present  "
              f"(from {corpus.name})")
    print(f"  Probes:      {[p.id for p in battery.probes]}")
    print(f"  Trials:      {args.trials}")

    n_calls = len(all_configs) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(all_configs) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls:   {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Est. cost:   ~${total * 0.008:.2f} (upper estimate)")

    if args.dry_run:
        print("\n  --dry-run: assembling prompts to verify corpus wiring.")
        for variant, corpus, cfg in all_configs:
            asm = cfg.assemble_prompt(corpus)
            header = asm.splitlines()[0][:80] if asm else "<empty>"
            print(f"    {cfg.id:<22} {len(asm):>5} chars  first_line={header!r}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Persist design
    design = {
        "experiment": "e-migration",
        "parent": "e-minimal-bomb (v2 PA migration observation)",
        "question": (
            "Does the commit-restrictions bomb suppress whichever "
            "Task-family policy block is dominant? Replicate v2 "
            "(PA-dominant) and compare to v2b (PA removed, should re-"
            "expose EA as the receiver if migration is real)."
        ),
        "bomb_block_id": BOMB_BLOCK_ID,
        "variants": variants,
        "conditions": [
            {
                "id": cfg.id,
                "variant": variant,
                "corpus": corpus.name,
                "present_blocks": cfg.present_blocks,
                "absent_blocks": cfg.absent_blocks,
                "metadata": cfg.metadata,
            }
            for variant, corpus, cfg in all_configs
        ],
        "probes": [p.id for p in battery.probes],
        "trials": args.trials,
        "model": MODEL_MAP["haiku"],
    }
    with open(OUTPUT_DIR / "e_migration_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-migration")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-migration-haiku-{uuid.uuid4().hex[:8]}"

    # Single aggregate run for provenance.
    run = AblationRun(
        id=run_id,
        configs=[cfg for _, _, cfg in all_configs],
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-migration",
            "model": "haiku",
            "model_id": model_id,
            "variants": variants,
            "bomb_block_id": BOMB_BLOCK_ID,
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    for variant, corpus, config in all_configs:
        print(f"\n  Condition: {config.id}")

        cond_run = AblationRun(
            id=f"{run_id}-{config.id.replace(':', '-')}",
            configs=[config],
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={"condition": config.id, "variant": variant},
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
            import traceback
            traceback.print_exc()
            continue

        run.results.extend(cond_run.results)

        # Inline per-probe summary.
        for probe_id in KEY_PROBE_IDS:
            scores = [r.score for r in cond_run.results if r.probe_id == probe_id]
            if scores:
                mean = statistics.mean(scores)
                stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0
                short = probe_id.replace("probe-", "").replace("-01", "")
                print(f"    {short:<22} mean={mean:.3f}  stdev={stdev:.3f}  n={len(scores)}")

    save_path = save_run(run, str(OUTPUT_DIR / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")

    _print_verdict(run)


def _print_verdict(run: AblationRun) -> None:
    by_cond_probe: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in run.results:
        by_cond_probe[(r.config_id, r.probe_id)].append(r.score)

    def mean_sd(vals: list[float]) -> tuple[float, float, int]:
        if not vals:
            return (float("nan"), float("nan"), 0)
        if len(vals) == 1:
            return (vals[0], 0.0, 1)
        return (statistics.mean(vals), statistics.stdev(vals), len(vals))

    labels = {
        "probe-explore-agent-01": "EA",
        "probe-proactive-agents-01": "PA",
        "probe-use-task-for-search-01": "TS",
    }

    print("\n  Per-probe summary (mean +/- stdev, n):")
    header = f"    {'Condition':<22}"
    for _, lbl in labels.items():
        header += f"  {lbl:>14}"
    print(header)
    for cond_id in sorted({k[0] for k in by_cond_probe}):
        row = f"    {cond_id:<22}"
        for pid in labels:
            m, s, n = mean_sd(by_cond_probe.get((cond_id, pid), []))
            row += f"  {m:.3f}+/-{s:.3f}"
        print(row)

    # Deltas by variant
    for variant in ("v2", "v2b"):
        print(f"\n  {variant} baseline -> bomb-present deltas (positive = suppression):")
        for pid, lbl in labels.items():
            base = by_cond_probe.get((f"{variant}:baseline", pid), [])
            bomb = by_cond_probe.get((f"{variant}:bomb-present", pid), [])
            if base and bomb:
                d = statistics.mean(base) - statistics.mean(bomb)
                print(f"    {lbl}: Δ = {d:+.3f}  "
                      f"(baseline={statistics.mean(base):.3f}, "
                      f"bomb={statistics.mean(bomb):.3f})")


def compare(args):
    """Summarise latest migration run alongside parent E-MINIMAL-BOMB v2 data."""
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    if OUTPUT_DIR.exists():
        for f in sorted(OUTPUT_DIR.glob("run_*.json")):
            run = load_run(str(f))
            for r in run.results:
                scores[f"mig:{r.config_id}"][r.probe_id].append(r.score)

    # Bring in the prior v2 run for replication comparison.
    prior_dir = project_root / "data" / "ablation" / "e_minimal_bomb"
    if prior_dir.exists():
        for f in sorted(prior_dir.glob("run_e-minimal-bomb-v2-*.json")):
            run = load_run(str(f))
            for r in run.results:
                scores[f"orig:v2:{r.config_id}"][r.probe_id].append(r.score)

    if not scores:
        print("No results found.")
        return

    key_probes = [
        ("probe-explore-agent-01", "EA"),
        ("probe-proactive-agents-01", "PA"),
        ("probe-use-task-for-search-01", "TS"),
    ]

    print(f"\n{'=' * 78}")
    print("E-MIGRATION vs E-MINIMAL-BOMB v2 (prior) on Haiku 4.5")
    print(f"{'=' * 78}\n")

    order = [
        "orig:v2:baseline",
        "orig:v2:bomb-present",
        "mig:v2:baseline",
        "mig:v2:bomb-present",
        "mig:v2b:baseline",
        "mig:v2b:bomb-present",
    ]
    present = [c for c in order if c in scores]

    header = f"{'Condition':<24}"
    for _, lbl in key_probes:
        header += f"  {lbl:>16}"
    print(header)
    print("-" * len(header))

    for cond in present:
        row = f"  {cond:<22}"
        for pid, _ in key_probes:
            vals = scores[cond].get(pid, [])
            if vals:
                if len(vals) > 1:
                    m = statistics.mean(vals)
                    s = statistics.stdev(vals)
                    row += f"  {m:5.3f}+/-{s:5.3f}"
                else:
                    row += f"  {vals[0]:5.3f}+/-0.000"
            else:
                row += f"  {'---':>16}"
        print(row)

    # Deltas
    print("\n  Deltas (baseline -> bomb-present):")
    blocks = [("orig", "v2"), ("mig", "v2"), ("mig", "v2b")]
    for prefix, variant in blocks:
        base_key = f"{prefix}:{variant}:baseline"
        bomb_key = f"{prefix}:{variant}:bomb-present"
        if base_key not in scores or bomb_key not in scores:
            continue
        deltas = []
        for pid, lbl in key_probes:
            b = scores[base_key].get(pid, [])
            bp = scores[bomb_key].get(pid, [])
            if b and bp:
                d = statistics.mean(b) - statistics.mean(bp)
                deltas.append(f"{lbl}Δ={d:+.3f}")
        print(f"    {prefix}:{variant:<4}  {'  '.join(deltas)}")


def main():
    parser = argparse.ArgumentParser(description="E-MIGRATION")
    parser.add_argument("--variants", nargs="+", choices=list(VARIANT_CORPUS_PATHS),
                        default=None,
                        help="variants to run (default: v2 and v2b)")
    parser.add_argument("--trials", type=int, default=15,
                        help="trials per probe per condition (default 15)")
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
