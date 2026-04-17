#!/usr/bin/env python3
"""
E-MINIMAL-BOMB: Can a 6-block synthetic prompt reproduce the register-bomb signature?

Prior work (E-PHASE, E-PHASE-CONFIRM, E-RESTORATION) established that the
Claude Code system prompt's `commit-restrictions` block — an imperative
prohibition embedded inside a procedural commit block — causes over-
generalization on Haiku 4.5: the explore-agent (EA) adherence drops
from ~1.0 to ~0.2.

Before shipping this to cross-family models (OLMo-3, Llama-3.1, Qwen-2.5)
we need a MINIMAL synthetic prompt that reproduces the bomb. Otherwise
"bomb doesn't transfer" confounds with "Claude-shaped prompt doesn't
transfer".

Design
------
Two conditions run against `anthropic/claude-haiku-4-5` via OpenRouter.

Corpus: data/prompts/minimal-bomb/v1_blocks.json

    minimal-bomb/identity                        (identity, realistic)
    minimal-bomb/tone                            (behavioral-constraint)
    minimal-bomb/tool-policy-search              (context: grep/glob)
    minimal-bomb/tool-policy-explore-agent       (the MEASURED block;
                                                  declarative, positive)
    minimal-bomb/tool-bash-commit-workflow       (commit workflow,
                                                  declarative)
    minimal-bomb/tool-bash-commit-restrictions   (THE BOMB — imperative
                                                  prohibition block
                                                  modelled on the Claude
                                                  Code original)

Conditions:
    baseline       present=[all 5 non-bomb blocks]          absent=[bomb]
    bomb-present   present=[all 6 blocks]                   absent=[]

Probes: probe-explore-agent-01 (primary), plus probe-proactive-agents-01
and probe-use-task-for-search-01 for signature confirmation.

Trials: 10 per condition (3 probes × 10 trials × 2 conditions = 60
probe calls + up to 60 judge calls ≈ $0.12).

Success criterion
-----------------
EA baseline ≥ 0.7 AND EA bomb-present ≤ 0.4 — same shape as E-PHASE.
Null result (EA stays high even with bomb) is a legitimate outcome:
it tells us the bomb requires more contextual machinery than 6 blocks
provide. Do NOT iterate to fit.

Usage:
    python scripts/run_e_minimal_bomb.py --dry-run
    python scripts/run_e_minimal_bomb.py
    python scripts/run_e_minimal_bomb.py --compare
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

# Reuse MODEL_MAP + load_corpus from the established E-PHASE pipeline.
from run_e_phase import MODEL_MAP, load_corpus

# ── Constants ────────────────────────────────────────────────────────

MINIMAL_CORPUS_PATH = project_root / "data" / "prompts" / "minimal-bomb" / "v1_blocks.json"

BOMB_BLOCK_ID = "minimal-bomb/tool-bash-commit-restrictions"

# The three probes we measure. explore-agent is the primary signal; the
# other two travel with it in prior experiments and provide signature
# confirmation (so we can tell "bomb reproduced" from "EA noisy").
KEY_PROBE_IDS = [
    "probe-explore-agent-01",
    "probe-proactive-agents-01",
    "probe-use-task-for-search-01",
]

# ── Corpus builders ──────────────────────────────────────────────────

def all_block_ids(corpus: PromptCorpus) -> list[str]:
    return [b.id for b in corpus.blocks]


def build_baseline_config(corpus: PromptCorpus) -> AblationConfig:
    """Baseline: every block present EXCEPT the bomb."""
    present = [bid for bid in all_block_ids(corpus) if bid != BOMB_BLOCK_ID]
    return AblationConfig(
        id="baseline",
        phase="baseline",
        present_blocks=present,
        absent_blocks=[BOMB_BLOCK_ID],
        metadata={
            "condition": "baseline",
            "description": "minimal corpus without commit-restrictions bomb",
        },
    )


def build_bomb_config(corpus: PromptCorpus) -> AblationConfig:
    """Bomb-present: every block in the corpus, including the bomb."""
    return AblationConfig(
        id="bomb-present",
        phase="baseline",
        present_blocks=all_block_ids(corpus),
        absent_blocks=[],
        metadata={
            "condition": "bomb-present",
            "description": "minimal corpus WITH commit-restrictions bomb",
        },
    )


def filter_battery_to_key_probes(battery: ProbeBattery) -> ProbeBattery:
    """Keep only the three key probes; preserves order from KEY_PROBE_IDS."""
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
    # Load probe battery (full) and filter to our key probes.
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    full_battery = load_battery(battery_path)
    battery = filter_battery_to_key_probes(full_battery)

    # Load the minimal synthetic corpus.
    if not MINIMAL_CORPUS_PATH.exists():
        print(f"ERROR: minimal corpus not found at {MINIMAL_CORPUS_PATH}")
        sys.exit(1)
    corpus = load_corpus(MINIMAL_CORPUS_PATH)

    configs = [
        build_baseline_config(corpus),
        build_bomb_config(corpus),
    ]

    print("\nE-MINIMAL-BOMB: 6-block synthetic prompt — does it reproduce the bomb?")
    print(f"  Corpus:        {corpus.name} ({len(corpus.blocks)} blocks)")
    print(f"  Corpus path:   {MINIMAL_CORPUS_PATH.relative_to(project_root)}")
    print(f"  Probes:        {[p.id for p in battery.probes]}")
    print(f"  Trials:        {args.trials}")
    print(f"  Conditions:    {[c.id for c in configs]}")

    n_calls = len(configs) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(configs) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls:     {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Est. cost:     ${total * 0.001:.2f}")

    print("\n  Success criterion:")
    print("    EA (baseline)     >= 0.7")
    print("    EA (bomb-present) <= 0.4")
    print("    (If not met after this run, report null result — do not iterate.)")

    if args.dry_run:
        # Sanity check: assemble both prompts and show block headers only.
        print("\n  --dry-run: assembling prompts to verify corpus wiring.")
        for cfg in configs:
            asm = cfg.assemble_prompt(corpus)
            header = asm.splitlines()[0][:80] if asm else "<empty>"
            print(f"    {cfg.id:<14} {len(asm):>5} chars  first_line={header!r}")
        return

    output_dir = project_root / "data" / "ablation" / "e_minimal_bomb"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Persist the experimental design alongside results for provenance.
    design = {
        "experiment": "e-minimal-bomb",
        "parent": "e-phase-confirm",
        "question": (
            "Does a 6-block synthetic prompt (identity + tone + 2 tool-policy "
            "blocks + commit-workflow + commit-restrictions bomb) reproduce "
            "the EA collapse signature seen against the full Claude Code "
            "prompt on Haiku 4.5?"
        ),
        "corpus": corpus.name,
        "corpus_file": str(MINIMAL_CORPUS_PATH.relative_to(project_root)),
        "bomb_block_id": BOMB_BLOCK_ID,
        "conditions": [
            {
                "id": c.id,
                "present_blocks": c.present_blocks,
                "absent_blocks": c.absent_blocks,
                "metadata": c.metadata,
            }
            for c in configs
        ],
        "probes": [p.id for p in battery.probes],
        "trials": args.trials,
        "model": MODEL_MAP["haiku"],
    }
    with open(output_dir / "e_minimal_bomb_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-minimal-bomb")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-minimal-bomb-haiku-{uuid.uuid4().hex[:8]}"

    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-minimal-bomb",
            "model": "haiku",
            "model_id": model_id,
            "corpus": corpus.name,
            "bomb_block_id": BOMB_BLOCK_ID,
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    for config in configs:
        print(f"\n  Condition: {config.id}")

        cond_run = AblationRun(
            id=f"{run_id}-{config.id}",
            configs=[config],
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={"condition": config.id},
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

        # Inline per-probe means for quick visibility while the run proceeds.
        for probe_id in KEY_PROBE_IDS:
            scores = [r.score for r in cond_run.results if r.probe_id == probe_id]
            if scores:
                mean = statistics.mean(scores)
                short = probe_id.replace("probe-", "").replace("-01", "")
                print(f"    {short:<22} mean={mean:.3f}  n={len(scores)}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")

    # Verdict
    by_cond_probe: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in run.results:
        by_cond_probe[(r.config_id, r.probe_id)].append(r.score)

    ea = "probe-explore-agent-01"
    ea_base = by_cond_probe.get(("baseline", ea), [])
    ea_bomb = by_cond_probe.get(("bomb-present", ea), [])
    if ea_base and ea_bomb:
        ea_base_mean = statistics.mean(ea_base)
        ea_bomb_mean = statistics.mean(ea_bomb)
        drop = ea_base_mean - ea_bomb_mean
        print("\n  Primary signal (explore-agent):")
        print(f"    baseline      EA = {ea_base_mean:.3f}  (n={len(ea_base)})")
        print(f"    bomb-present  EA = {ea_bomb_mean:.3f}  (n={len(ea_bomb)})")
        print(f"    drop          Δ  = {drop:+.3f}")
        if ea_base_mean >= 0.7 and ea_bomb_mean <= 0.4:
            print("    VERDICT: bomb signature reproduced in the 6-block minimal prompt.")
        elif ea_bomb_mean < ea_base_mean - 0.2:
            print("    VERDICT: partial drop. Signature weaker than the full Claude Code prompt.")
        else:
            print("    VERDICT: null — minimal context insufficient to reproduce the bomb.")


def compare(args):
    """Summarise latest minimal-bomb run alongside prior bomb baselines."""
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    mb_dir = project_root / "data" / "ablation" / "e_minimal_bomb"
    for f in sorted(mb_dir.glob("run_*.json")) if mb_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[f"mb:{r.config_id}"][r.probe_id].append(r.score)

    # E-PHASE anchors (Claude Code prompt, same probe battery, Haiku).
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    for f in sorted(phase_dir.glob("run_*.json")) if phase_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            if r.config_id == "density-00":
                scores["cc:all-decl"][r.probe_id].append(r.score)
            elif r.config_id == "density-01":
                scores["cc:only-cr-imp"][r.probe_id].append(r.score)

    if not scores:
        print("No results found.")
        return

    key_probes = [
        ("probe-explore-agent-01", "EA"),
        ("probe-proactive-agents-01", "PA"),
        ("probe-use-task-for-search-01", "TS"),
    ]

    print(f"\n{'=' * 74}")
    print("E-MINIMAL-BOMB vs Claude Code (E-PHASE) on Haiku 4.5")
    print(f"{'=' * 74}\n")

    order = [
        "cc:all-decl",
        "cc:only-cr-imp",
        "mb:baseline",
        "mb:bomb-present",
    ]
    present = [c for c in order if c in scores]

    header = f"{'Condition':<24}"
    for _, lbl in key_probes:
        header += f"  {lbl:>8}"
    print(header)
    print("-" * len(header))

    for cond in present:
        row = f"  {cond:<22}"
        for pid, _ in key_probes:
            vals = scores[cond].get(pid, [])
            if vals:
                row += f"  {statistics.mean(vals):>8.3f}"
            else:
                row += f"  {'---':>8}"
        print(row)

    ea = "probe-explore-agent-01"
    cc_drop = (
        statistics.mean(scores.get("cc:all-decl", {}).get(ea, [0]))
        - statistics.mean(scores.get("cc:only-cr-imp", {}).get(ea, [0]))
        if ("cc:all-decl" in scores and "cc:only-cr-imp" in scores)
        else None
    )
    mb_base = scores.get("mb:baseline", {}).get(ea, [])
    mb_bomb = scores.get("mb:bomb-present", {}).get(ea, [])

    print()
    if cc_drop is not None:
        print(f"  Claude Code EA drop (all-decl → only-cr-imp): Δ = {cc_drop:+.3f}")
    if mb_base and mb_bomb:
        mb_drop = statistics.mean(mb_base) - statistics.mean(mb_bomb)
        print(f"  Minimal-bomb EA drop (baseline → bomb-present): Δ = {mb_drop:+.3f}")


def main():
    parser = argparse.ArgumentParser(description="E-MINIMAL-BOMB")
    parser.add_argument("--trials", type=int, default=10,
                        help="trials per probe per condition (default 10)")
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
