#!/usr/bin/env python3
"""
E-AMBIGUITY: Pathway-B Trigger Decomposition

Parent: T22 (E-SOLO discrete response modes)

T22 identified pathway B: imperative CR block with empty or "insufficient/
unrelated" content triggers mode-2 (AskUserQuestion) on Haiku at T=0. But
the E-SOLO conditions conflated several dimensions:

  - solo-empty triggers mode 2: bullet is "If there are no changes to
    commit, do not create an empty commit" — conditional + unrelated +
    weak action.
  - solo-push, solo-no-edit, solo-heredoc, solo-dash-i do NOT trigger
    mode 2: their bullets are unconditional flat prohibitions/mandates,
    each unrelated to exploration.

Hypothesis: pathway B's trigger is not "imperative + unrelated content"
broadly but more specifically "imperative + content that fails to bind
response shape" — most cleanly characterized as conditional/weak-action
content. E-AMBIGUITY varies content along constraint-strength × type
axes, holding register isolation fixed, to test which feature predicts
mode 2.

8 conditions:

  Replications / controls (cross-experiment validation):
    rep-empty-cr              header only, no bullet  [predict mode 2]
    rep-conditional-unrelated solo-empty's bullet     [predict mode 2]
    rep-strong-unrelated      solo-push's bullet      [predict mode 1]

  Hypothesis tests:
    test-unconditional-empty   "Do not create empty commits"
       — removes the "If" from rep-conditional-unrelated.
       Mode 1 if conditional framing was the trigger;
       mode 2 if weak-action content alone is enough.

    test-vague-flat            "Be careful with commit operations"
       — vague + unconditional + unrelated.
       Mode 2 if "non-binding content" without conditional is enough;
       mode 1 if conditional framing is required.

    test-conditional-strong    "If you encounter problems, abort the
                                operation immediately"
       — conditional + strong action.
       Mode 2 if conditional alone triggers regardless of action
       strength; mode 1 if strong-action overrides.

    test-strong-flat-unrelated "Always use atomic file operations for
                                data safety"
       — strong + unconditional + non-git unrelated.
       Mode 1 confirms strong-flat is rescue regardless of git-specificity
       (controls for solo-push/no-edit/etc being git-coded).

    test-conditional-task      "If you need to explore the codebase,
                                NEVER use the TodoWrite or Task tools"
       — conditional + RELATED to exploration (pathway A test).
       Mode 2 if conditional framing disrupts pathway A's clause-level
       mechanism; mode 3 (prose-strategy) if pathway A is robust to
       conditional framing.

Cost: 8 conditions × 22 probes × 3 trials = 528 calls + ~120 judge ≈ $0.55.

Mode classification is post-hoc from raw responses. Score signal alone is
not sufficient: pathway A (mode 3) and pathway B (mode 2) both produce
~0.15 scores on explore-agent. Distinguishing requires looking at the
opening tokens and response structure.

Usage:
    python scripts/run_e_ambiguity.py --dry-run
    python scripts/run_e_ambiguity.py
    python scripts/run_e_ambiguity.py --compare
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

# kept_bullet=None means header-only (no bullet at all).
# kept_bullet="__all_decl__" is reserved for the all-decl baseline (handled below).
AMBIGUITY_BULLETS = {
    "rep-empty-cr":               None,
    "rep-conditional-unrelated":  "- If there are no changes to commit, do not create an empty commit",
    "rep-strong-unrelated":       "- DO NOT push to the remote repository unless the user explicitly asks you to do so",
    "test-unconditional-empty":   "- Do not create empty commits",
    "test-vague-flat":            "- Be careful with commit operations",
    "test-conditional-strong":    "- If you encounter problems, abort the operation immediately",
    "test-strong-flat-unrelated": "- Always use atomic file operations for data safety",
    "test-conditional-task":      "- If you need to explore the codebase, NEVER use the TodoWrite or Task tools",
}


def build_cr_solo(corpus: PromptCorpus, kept_bullet: str | None) -> PromptCorpus:
    """All procedural blocks declarative except CR, replaced with 'Important
    notes:' header plus optional single bullet (imperative register).
    kept_bullet=None  -> header only.
    kept_bullet='__all_decl__' -> CR is also declarative (baseline)."""
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
        name=corpus.name + "-cr-ambiguity",
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

    conditions = list(AMBIGUITY_BULLETS.items())
    if args.include_baseline:
        conditions = [("all-decl", "__all_decl__")] + conditions

    print("\nE-AMBIGUITY: Pathway-B Trigger Decomposition")
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
        if bullet == "__all_decl__":
            label = "(CR fully declarative — baseline)"
        print(f"    {name:<30}  {label[:80]}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    # Sanity: corpus must have CR block
    corpus = load_corpus(base_corpus_path)
    cr_block = next((b for b in corpus.blocks if b.id == CR_ID), None)
    if cr_block is None:
        print(f"ERROR: {CR_ID} not found in corpus")
        sys.exit(1)

    output_dir = project_root / "data" / "ablation" / "e_ambiguity"
    output_dir.mkdir(parents=True, exist_ok=True)

    condition_corpora = {}
    configs = []

    for cond_name, bullet in conditions:
        amb_corpus = build_cr_solo(load_corpus(base_corpus_path), bullet)
        condition_corpora[cond_name] = amb_corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in amb_corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "kept_bullet": bullet,
                "builder": "cr_ambiguity",
            },
        ))

    design = {
        "experiment": "e-ambiguity",
        "date": "2026-04-28",
        "parent": "e-solo",
        "cairn": "T22",
        "question": (
            "Does pathway B's mode-2 trigger require conditional framing "
            "specifically, or any non-binding content in imperative register?"
        ),
        "conditions": [
            {"name": n, "kept_bullet": b} for n, b in conditions
        ],
    }
    with open(output_dir / "e_ambiguity_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_key = args.model
    model_id = MODEL_MAP[model_key]
    client = make_client(f"e-ambiguity-{model_key}")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-ambiguity-{model_key}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-ambiguity",
            "model": model_key,
            "model_id": model_id,
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    for config in configs:
        cond_name = config.id
        cond_corpus = condition_corpora[cond_name]
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
                cond_run, "baseline", corpus=cond_corpus,
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
    amb_dir = project_root / "data" / "ablation" / "e_ambiguity"
    if not amb_dir.exists():
        print("No E-AMBIGUITY results found.")
        return
    files = sorted(amb_dir.glob("run_e-ambiguity-*.json"))
    if not files:
        print("No result files found.")
        return
    run = load_run(str(files[-1]))

    print("E-AMBIGUITY: Per-Condition Score Map")
    print("=" * 80)

    key_probes = [
        "probe-explore-agent-01",
        "probe-use-task-for-search-01",
        "probe-proactive-agents-01",
        "probe-todowrite-repeated-01",
    ]

    by_cond = defaultdict(list)
    for r in run.results:
        by_cond[r.config_id].append(r)

    print(f"\n  {'Condition':<30}", end="")
    for pid in key_probes:
        short = pid.replace("probe-", "").replace("-01", "")[:11]
        print(f" {short:>11}", end="")
    print()
    print("  " + "-" * (30 + 12 * len(key_probes)))
    for c in AMBIGUITY_BULLETS:
        print(f"  {c:<30}", end="")
        for pid in key_probes:
            pr = [r for r in by_cond.get(c, []) if r.probe_id == pid and r.score is not None]
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
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
