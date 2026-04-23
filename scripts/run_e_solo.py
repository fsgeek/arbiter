#!/usr/bin/env python3
"""
E-SOLO: Per-Bullet Isolated Contribution Map

Parent: T19 (E-BULLET-ISOLATE), T21 (super-additive bash promotion)

E-BULLET-ISOLATE tested "remove one bullet, rest present" for 3 of 7 CR bullets.
T21's reanalysis found super-additive interaction: removing either Task or Explore
bullet cuts bash-command emission on use-task-for-search, but both present together
produces ~3x the bash-command emission of either alone. Super-additivity suggests
interaction, not independent additive pressure.

E-SOLO inverts the frame: keep only ONE bullet in the CR block; replace all other
procedural blocks with declarative equivalents. This isolates each bullet's
independent contribution with no other imperative interference.

7 conditions, one per CR bullet:
  1. solo-explore   — NEVER run additional commands to read or explore code...
  2. solo-task      — NEVER use the TodoWrite or Task tools
  3. solo-push      — DO NOT push to the remote repository unless...
  4. solo-dash-i    — IMPORTANT: Never use git commands with the -i flag
  5. solo-no-edit   — IMPORTANT: Do not use --no-edit with git rebase
  6. solo-empty     — If there are no changes to commit, do not create an empty commit
  7. solo-heredoc   — ALWAYS pass the commit message via a HEREDOC

8th condition (baseline): solo-empty-cr — CR block replaced with just the heading
"Important notes:" and no bullets (null imperative CR). Tests whether the block
structure itself contributes anything versus its content.

For comparison baselines, we reuse:
  - only-cr-imp from E-PHASE density-01 (all 7 bullets)
  - all-decl from E-PHASE density-00 (no imperative CR at all)

Cost: 8 conditions × 22 probes × 3 trials = 528 calls + ~120 judge ≈ $0.55

Predicted outcomes (T21's mechanism hypothesis):
  - solo-task    : explore-agent collapses (Task mentions suppressed);
                   use-task-for-search bash-cmd count low (no super-additive boost)
  - solo-explore : use-task-for-search bash-cmd count moderate;
                   exploration/read-first probes unchanged (category promotion
                   surfaces only when probe primes it)
  - solo-push    : null-ish (behavior-category naming git push specifically;
                   no probe directly tests push-related behavior in non-commit ctx)
  - solo-dash-i  : null-ish (flag-name; no probe tests -i flag behavior)
  - solo-no-edit : null-ish (flag-name; no probe tests --no-edit behavior)
  - solo-empty   : null-ish (conditional behavior; no probe tests empty-commit)
  - solo-heredoc : null-ish (alternate-form preference; HEREDOC only matters in
                   commit message construction, no test)
  - solo-empty-cr: null (sanity check — minimal CR block, no bullets)

Outcomes that would invalidate T21's hypothesis:
  - If solo-task + solo-explore sum equals only-cr-imp effect on use-task-for-search
    bash counts, then super-additivity was noise and no interaction exists.
  - If any of the null-predicted bullets (solo-push, solo-dash-i etc.) produces
    a substantial probe shift, the mechanism is more diffuse than "clause names
    subject → reach to that subject."

Usage:
    python scripts/run_e_solo.py --dry-run
    python scripts/run_e_solo.py
    python scripts/run_e_solo.py --compare
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

CR_ID = "claude-code/tool-bash-commit-restrictions"

# Each bullet's exact line text. Verified against v2.1.50_blocks.json.
CR_BULLETS = {
    "solo-explore":  "- NEVER run additional commands to read or explore code, besides git bash commands",
    "solo-task":     "- NEVER use the TodoWrite or Task tools",
    "solo-push":     "- DO NOT push to the remote repository unless the user explicitly asks you to do so",
    "solo-dash-i":   "- IMPORTANT: Never use git commands with the -i flag",
    "solo-no-edit":  "- IMPORTANT: Do not use --no-edit with git rebase commands",
    "solo-empty":    "- If there are no changes to commit, do not create an empty commit",
    "solo-heredoc":  "- ALWAYS pass the commit message via a HEREDOC",
}


def build_cr_solo(corpus: PromptCorpus, kept_bullet: str | None) -> PromptCorpus:
    """All procedural blocks declarative except CR, which is replaced with just
    'Important notes:' header plus the single specified bullet (imperative register).
    If kept_bullet is None, CR becomes header-only (solo-empty-cr).
    Special: kept_bullet == '__all_decl__' → CR is also made declarative (baseline)."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id == CR_ID:
            if kept_bullet == "__all_decl__":
                new_text = DECLARATIVE_REWRITES[CR_ID]
            elif kept_bullet is None:
                new_text = "Important notes:"
            else:
                new_text = "Important notes:\n" + kept_bullet
            new_blocks.append(b.model_copy(update={"text": new_text}))
        elif b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name + "-cr-solo",
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

    conditions = list(CR_BULLETS.items()) + [("solo-empty-cr", None)]
    if args.baseline_only:
        conditions = [("all-decl", "__all_decl__")]
    elif args.include_baseline:
        conditions = [("all-decl", "__all_decl__")] + conditions

    print("\nE-SOLO: Per-Bullet Isolated Contribution Map")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(conditions)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(conditions) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(conditions) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Est. cost: ${total * 0.001:.2f}")

    print("\n  Conditions:")
    for name, bullet in conditions:
        label = bullet if bullet else "(empty CR: header only)"
        print(f"    {name:<16}  {label[:80]}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    # Verify each bullet exists in the original CR text
    corpus = load_corpus(base_corpus_path)
    cr_block = next((b for b in corpus.blocks if b.id == CR_ID), None)
    if cr_block is None:
        print(f"ERROR: {CR_ID} not found in corpus")
        sys.exit(1)
    cr_lines_stripped = [l.strip() for l in cr_block.text.split("\n")]
    for name, bullet in CR_BULLETS.items():
        if bullet.strip() not in cr_lines_stripped:
            print(f"ERROR: bullet for {name} not found in CR text:\n  {bullet!r}")
            print(f"\nActual CR text:\n{cr_block.text}")
            sys.exit(1)

    output_dir = project_root / "data" / "ablation" / "e_solo"
    output_dir.mkdir(parents=True, exist_ok=True)

    condition_corpora = {}
    configs = []

    for cond_name, bullet in conditions:
        solo_corpus = build_cr_solo(load_corpus(base_corpus_path), bullet)
        condition_corpora[cond_name] = solo_corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in solo_corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "kept_bullet": bullet,
                "builder": "cr_solo",
            },
        ))

    design = {
        "experiment": "e-solo",
        "date": "2026-04-23",
        "parent": "e-bullet-isolate",
        "cairn": "T21",
        "question": "What is each CR bullet's independent contribution under register isolation?",
        "conditions": [
            {"name": n, "kept_bullet": b} for n, b in conditions
        ],
    }
    with open(output_dir / "e_solo_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_key = args.model
    model_id = MODEL_MAP[model_key]
    client = make_client(f"e-solo-{model_key}")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-solo-{model_key}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-solo",
            "model": model_key,
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

        # Quick view of the same probes T19 tracked
        for probe_id, label in [
            ("probe-explore-agent-01", "explore-agent"),
            ("probe-use-task-for-search-01", "use-task-for-search"),
            ("probe-proactive-agents-01", "proactive-agents"),
            ("probe-todowrite-repeated-01", "todowrite-repeated"),
        ]:
            scores = [r.score for r in cond_run.results
                     if r.probe_id == probe_id and r.score is not None]
            if scores:
                print(f"    {label:<22} {statistics.mean(scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    solo_dir = project_root / "data" / "ablation" / "e_solo"
    phase_dir = project_root / "data" / "ablation" / "e_phase"

    if not solo_dir.exists():
        print("No E-SOLO results found.")
        return

    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    phase_run = load_run(str(phase_files[0])) if phase_files else None
    solo_files = sorted(solo_dir.glob("run_e-solo-*.json"))
    if not solo_files:
        print("No result files found.")
        return
    solo_run = load_run(str(solo_files[-1]))

    print("E-SOLO: Per-Bullet Contribution Map")
    print("=" * 80)

    key_probes = [
        "probe-explore-agent-01",
        "probe-use-task-for-search-01",
        "probe-proactive-agents-01",
        "probe-todowrite-repeated-01",
        "probe-todowrite-01",
        "probe-code-references-01",
    ]

    all_conds = []
    if phase_run:
        all_conds.append(("all-decl (d0)", [r for r in phase_run.results if r.config_id == "density-00"]))
        all_conds.append(("only-cr-imp (d1)", [r for r in phase_run.results if r.config_id == "density-01"]))
    by_cond = defaultdict(list)
    for r in solo_run.results:
        by_cond[r.config_id].append(r)
    for c in list(CR_BULLETS) + ["solo-empty-cr"]:
        all_conds.append((c, by_cond.get(c, [])))

    print(f"\n  {'Condition':<22}", end="")
    for pid in key_probes:
        short = pid.replace("probe-", "").replace("-01", "")[:11]
        print(f" {short:>11}", end="")
    print()
    print("  " + "-" * (22 + 12 * len(key_probes)))
    for name, results in all_conds:
        print(f"  {name:<22}", end="")
        for pid in key_probes:
            pr = [r for r in results if r.probe_id == pid and r.score is not None]
            if pr:
                print(f" {statistics.mean([r.score for r in pr]):>11.3f}", end="")
            else:
                print(f" {'---':>11}", end="")
        print()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--model", choices=list(MODEL_MAP.keys()), default="haiku")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--include-baseline", action="store_true",
                        help="Prepend all-decl condition (no imperative CR)")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Run ONLY the all-decl condition (cross-model baseline fill-in)")
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
