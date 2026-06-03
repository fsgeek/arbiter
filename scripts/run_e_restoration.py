#!/usr/bin/env python3
"""
E-RESTORATION: Does a restoration clause in imperative register defuse the bomb?

The simplest possible test of the bomb-scoped finding from E-NARRATIVE-V2.
If adding "After the commit, these tools are available again" to the
imperative CR defuses the bomb, then narrative framing is unnecessary —
the mechanism is the restoration clause alone.

One condition. ~$0.12. Answers the question before we build more theory.

Usage:
    python scripts/run_e_restoration.py --dry-run
    python scripts/run_e_restoration.py
    python scripts/run_e_restoration.py --compare
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

# ── The one condition ───────────────────────────────────────────────────

CR_BLOCK_ID = "claude-code/tool-bash-commit-restrictions"

# Original imperative + restoration clause
CR_IMP_WITH_RESTORATION = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- NEVER use the TodoWrite or Task tools\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC\n"
    "\n"
    "After the commit is complete, all tools (including TodoWrite and Task) "
    "are available again for normal use."
)

# Also test: inline-scoped imperative without narrative (combines E-SCOPE fix
# with restoration, still pure imperative register)
CR_IMP_SCOPED_WITH_RESTORATION = (
    "Important notes for commit workflows:\n"
    "- During commits, NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- During commits, NEVER use the TodoWrite or Task tools\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC\n"
    "\n"
    "After the commit is complete, all tools (including TodoWrite and Task) "
    "are available again for normal use."
)

CONDITIONS = [
    ("cr-imp-restoration",
     "Original imperative CR + restoration clause",
     CR_IMP_WITH_RESTORATION),
    ("cr-imp-scoped-restoration",
     "Inline-scoped imperative CR + restoration clause",
     CR_IMP_SCOPED_WITH_RESTORATION),
]


def build_condition_corpus(base_corpus, cr_text):
    """All procedural blocks declarative except CR with given text."""
    new_blocks = []
    for b in base_corpus.blocks:
        if b.id == CR_BLOCK_ID:
            new_blocks.append(b.model_copy(update={"text": cr_text}))
        elif b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=base_corpus.name + "-modified",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


def make_client(experiment_id):
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

    print(f"\nE-RESTORATION: Restoration clause in imperative register")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(CONDITIONS)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    for name, desc, _ in CONDITIONS:
        print(f"    {name}: {desc}")

    print(f"\n  Question: Does a restoration clause defuse the bomb without narrative?")
    print(f"  If EA ≈ 1.000: narrative was unnecessary, restoration is the mechanism")
    print(f"  If EA ≈ 0.200: narrative framing contributed beyond the restoration clause")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_restoration"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-restoration")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-restoration-haiku-{uuid.uuid4().hex[:8]}"

    configs = []
    condition_corpora = {}
    for name, desc, cr_text in CONDITIONS:
        corpus = build_condition_corpus(load_corpus(base_corpus_path), cr_text)
        condition_corpora[name] = corpus
        configs.append(AblationConfig(
            id=name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={"condition": name, "description": desc},
        ))

    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={"experiment": "e_restoration"},
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
            import traceback
            traceback.print_exc()
            continue

        run.results.extend(cond_run.results)

        for probe_name in ["explore-agent", "proactive-agents", "use-task-for-search"]:
            probe_scores = [r.score for r in cond_run.results
                           if probe_name in r.probe_id]
            if probe_scores:
                print(f"    {probe_name}: {statistics.mean(probe_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare restoration results against all prior bomb conditions."""
    scores = defaultdict(lambda: defaultdict(list))

    # Load restoration data
    rest_dir = project_root / "data" / "ablation" / "e_restoration"
    for f in sorted(rest_dir.glob("run_*.json")) if rest_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[r.config_id][r.probe_id].append(r.score)

    # Load baselines
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    for f in sorted(phase_dir.glob("run_*.json")) if phase_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            if r.config_id == "density-00":
                scores["all-decl"][r.probe_id].append(r.score)
            elif r.config_id == "density-01":
                scores["only-cr-imp"][r.probe_id].append(r.score)

    # Load E-LEXBRIDGE inline-scoped (for comparison)
    lb_dir = project_root / "data" / "ablation" / "e_lexbridge"
    for f in sorted(lb_dir.glob("run_*.json")) if lb_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[r.config_id][r.probe_id].append(r.score)

    # Load bomb-scoped from V2
    v2_dir = project_root / "data" / "ablation" / "e_narrative_v2"
    for f in sorted(v2_dir.glob("run_*p2*.json")) if v2_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            if r.config_id == "bomb-scoped":
                scores["bomb-scoped"][r.probe_id].append(r.score)

    if not scores:
        print("No results found.")
        return

    # Compare all bomb-related conditions
    conditions = [
        "all-decl",
        "only-cr-imp",
        "cr-imp-restoration",
        "cr-imp-scoped-restoration",
        "bomb-scoped",
    ]
    present = [c for c in conditions if c in scores]

    key_probes = [
        ("probe-explore-agent-01", "EA"),
        ("probe-proactive-agents-01", "PA"),
        ("probe-use-task-for-search-01", "TS"),
    ]

    print(f"\n{'=' * 80}")
    print("RESTORATION CLAUSE TEST")
    print(f"{'=' * 80}\n")

    header = f"{'Condition':<30}"
    for _, label in key_probes:
        header += f"  {label:>8}"
    header += f"  {'Mean':>8}"
    print(header)
    print("-" * 60)

    for cond in present:
        all_vals = [s for vals in scores[cond].values() for s in vals]
        mean = statistics.mean(all_vals) if all_vals else 0
        row = f"  {cond:<28}"
        for probe_id, _ in key_probes:
            vals = scores[cond].get(probe_id, [])
            row += f"  {statistics.mean(vals):>8.3f}" if vals else f"  {'---':>8}"
        row += f"  {mean:>8.3f}"
        print(row)

    # Verdict
    ea = "probe-explore-agent-01"
    bomb = statistics.mean(scores["only-cr-imp"].get(ea, [0]))
    rest = scores.get("cr-imp-restoration", {}).get(ea, [])
    scoped_rest = scores.get("cr-imp-scoped-restoration", {}).get(ea, [])
    narrative = scores.get("bomb-scoped", {}).get(ea, [])

    print(f"\n{'=' * 80}")
    print("VERDICT")
    print(f"{'=' * 80}")
    print(f"\n  Bomb baseline:                EA = {bomb:.3f}")

    if rest:
        r = statistics.mean(rest)
        print(f"  Imperative + restoration:     EA = {r:.3f}  (Δ={r-bomb:+.3f})")
        if r > bomb + 0.3:
            print(f"  → RESTORATION CLAUSE ALONE DEFUSES THE BOMB")
            print(f"    Narrative framing was unnecessary. The mechanism is")
            print(f"    the restoration clause, not the register.")
        elif r < bomb + 0.1:
            print(f"  → RESTORATION CLAUSE ALONE IS INSUFFICIENT")
            print(f"    The narrative-scoped protection comes from the")
            print(f"    narrative framing, not just the restoration clause.")

    if scoped_rest:
        s = statistics.mean(scoped_rest)
        print(f"  Scoped imperative + restore:  EA = {s:.3f}  (Δ={s-bomb:+.3f})")

    if narrative:
        n = statistics.mean(narrative)
        print(f"  Narrative-scoped (V2):        EA = {n:.3f}  (Δ={n-bomb:+.3f})")


def main():
    parser = argparse.ArgumentParser(description="E-RESTORATION")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
