#!/usr/bin/env python3
"""
E-MFS: Minimum Failure Set — backward greedy elimination.

Starting from the bomb-firing configuration (E-PHASE-CONFIRM only-cr-imp:
commit-restrictions imperative + all other procedural blocks declarative),
iteratively remove blocks while the bomb remains firing (EA < threshold).

The remaining blocks after convergence = Minimum Failure Set (MFS), the
smallest subset that still produces the explore-agent collapse.

Algorithm:
  1. Start with all 56 blocks present.
  2. For each currently-present block B, try removing B alone; measure EA (k trials).
  3. Identify "safely-removable" blocks: EA_after < threshold (bomb still firing).
  4. Pick the "most-removable" block: the one whose removal least raises EA
     (ties broken by lowest EA_after, then block_id for determinism).
  5. Commit that removal; repeat from step 2 with the smaller prompt.
  6. Stop when no block is safely removable.

Threshold: EA < 0.4 (baseline-firing ≈ 0.20; baseline-defused ≈ 1.00).

Only the EA probe is measured; this is an MFS-specific battery to keep costs
down. The judge is the same LLM as the generator (OpenRouter/Haiku) so we
use the standard llm_judge scoring pipeline from the battery.

Usage:
    python scripts/run_e_mfs.py --dry-run
    python scripts/run_e_mfs.py --confirm-baseline
    python scripts/run_e_mfs.py                 # full iterative elimination
    python scripts/run_e_mfs.py --analyze       # summarize decision log

Epistemic requirements:
  - Stop on API budget exhaustion.
  - Stop if baseline EA is not ≈ 0.2 (report it; do not tune thresholds).
  - Report non-monotonic behavior explicitly if it occurs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))

from arbiter.ablation.battery import ProbeBattery, load_battery
from arbiter.ablation.configuration import AblationConfig
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run
from arbiter.prompt_blocks import PromptCorpus

from run_e_phase import (  # noqa: E402
    DECLARATIVE_REWRITES,
    MODEL_MAP,
    load_corpus,
)

# ── Constants ─────────────────────────────────────────────────────────

CR_BLOCK_ID = "claude-code/tool-bash-commit-restrictions"
EA_PROBE_ID = "probe-explore-agent-01"

# Bomb-firing threshold: EA < 0.4 means bomb still firing.
# Baseline-firing is ~0.20 (E-PHASE-CONFIRM only-cr-imp); baseline-defused is ~1.00.
# 0.4 is conservative midpoint heavily biased toward "still firing."
THRESHOLD = 0.4

# Cost guardrail (hard stop).
MAX_API_SPEND_USD = 20.0
COST_PER_CALL_USD = 0.001  # Haiku, conservative for accounting

# ── Corpus builders ───────────────────────────────────────────────────


def build_only_cr_imperative_corpus(base_corpus: PromptCorpus) -> PromptCorpus:
    """The E-PHASE-CONFIRM only-cr-imp starting configuration.

    commit-restrictions stays in its original imperative form; every OTHER
    procedural block listed in DECLARATIVE_REWRITES is rewritten to declarative.
    """
    new_blocks = []
    for b in base_corpus.blocks:
        if b.id != CR_BLOCK_ID and b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=base_corpus.name + "-only-cr-imp",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


def ea_only_battery(full_battery: ProbeBattery) -> ProbeBattery:
    """Battery filtered to only the explore-agent probe."""
    ea_probes = [p for p in full_battery.probes if p.id == EA_PROBE_ID]
    if not ea_probes:
        raise RuntimeError(f"No {EA_PROBE_ID} in battery")
    return ProbeBattery(
        probes=ea_probes,
        metadata={**getattr(full_battery, "metadata", {}), "filtered_to": EA_PROBE_ID},
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


# ── Iteration state + logging ────────────────────────────────────────


@dataclass
class CandidateResult:
    block_id: str
    ea_mean: float
    ea_trials: list[float]
    config_id: str


@dataclass
class IterationRecord:
    step: int
    present_before: list[str]
    ea_before: float
    candidates: list[CandidateResult]
    removed_block: Optional[str]
    ea_after: Optional[float]
    reason: str  # "removed", "halt_no_safe_removal", "halt_budget", "halt_error"

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "present_before_count": len(self.present_before),
            "present_before": self.present_before,
            "ea_before": self.ea_before,
            "candidates": [
                {
                    "block_id": c.block_id,
                    "ea_mean": c.ea_mean,
                    "ea_trials": c.ea_trials,
                    "config_id": c.config_id,
                }
                for c in self.candidates
            ],
            "removed_block": self.removed_block,
            "ea_after": self.ea_after,
            "reason": self.reason,
        }


# ── Runner helpers ───────────────────────────────────────────────────


def measure_ea(
    *,
    runner: AblationRunner,
    corpus: PromptCorpus,
    present_blocks: list[str],
    config_id: str,
    battery: ProbeBattery,
    model_id: str,
    trials: int,
    concurrency: int,
) -> tuple[float, list[float], list]:
    """Return (mean_ea, trial_scores, raw_results) for given present_blocks."""
    config = AblationConfig(
        id=config_id,
        phase="baseline",
        present_blocks=present_blocks,
        absent_blocks=[],
        metadata={"measure": "ea_only"},
    )
    run = AblationRun(
        id=config_id,
        configs=[config],
        battery=battery,
        models=[model_id],
        trials_per_probe=trials,
        temperature=0.0,
    )
    asyncio.run(
        runner.run_phase(
            run,
            "baseline",
            corpus=corpus,
            concurrency=concurrency,
            progress_callback=None,
        )
    )
    scores = [r.score for r in run.results if r.probe_id == EA_PROBE_ID]
    if not scores:
        raise RuntimeError(f"No EA scores collected for {config_id}")
    return statistics.mean(scores), scores, run.results


# ── Budget tracking ──────────────────────────────────────────────────


class BudgetTracker:
    def __init__(self, max_usd: float):
        self.max_usd = max_usd
        self.calls = 0  # includes gen + judge
        self.start = time.time()

    def add_calls(self, n: int) -> None:
        self.calls += n

    def spent_usd(self) -> float:
        return self.calls * COST_PER_CALL_USD

    def remaining_usd(self) -> float:
        return self.max_usd - self.spent_usd()

    def check(self) -> bool:
        return self.spent_usd() < self.max_usd

    def summary(self) -> str:
        elapsed = time.time() - self.start
        return (
            f"{self.calls} calls ≈ ${self.spent_usd():.2f} "
            f"(elapsed {elapsed/60:.1f}m)"
        )


# ── Experiment ───────────────────────────────────────────────────────


def run_experiment(args):
    output_dir = project_root / "data" / "ablation" / "e_mfs"
    output_dir.mkdir(parents=True, exist_ok=True)

    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    full_battery = load_battery(battery_path)
    battery = ea_only_battery(full_battery)

    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)
    starting_corpus = build_only_cr_imperative_corpus(base_corpus)

    all_block_ids = [b.id for b in starting_corpus.blocks]
    n_blocks = len(all_block_ids)

    print("\nE-MFS: Minimum Failure Set (backward greedy elimination)")
    print(f"  Starting corpus: {starting_corpus.name}  ({n_blocks} blocks)")
    print(f"  Probe: {EA_PROBE_ID}  (llm_judge)")
    print(f"  Trials per candidate: {args.trials}")
    print(f"  Threshold: EA < {THRESHOLD}  (bomb still firing)")
    print(f"  Budget cap: ${MAX_API_SPEND_USD:.2f} of API spend")
    print(f"  Concurrency: {args.concurrency}")

    # Worst-case cost: sum_{k=1..N} k * trials * 2_calls (gen+judge)
    worst_candidates = sum(range(1, n_blocks + 1))
    worst_calls = worst_candidates * args.trials * 2
    print(
        f"  Worst-case eval cost (if MFS=1): "
        f"{worst_candidates} candidate-evals × {args.trials} trials × 2 calls "
        f"= {worst_calls} ≈ ${worst_calls * COST_PER_CALL_USD:.2f}"
    )

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    # Build LLM caller + runner
    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller

    client = make_client("e-mfs")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    budget = BudgetTracker(MAX_API_SPEND_USD)
    decision_log: list[IterationRecord] = []
    design = {
        "experiment": "e-mfs",
        "date": "2026-04-17",
        "parent": "e-phase-confirm",
        "question": "What is the Minimum Failure Set — smallest subset of blocks that keeps the explore-agent bomb firing?",
        "model": "haiku",
        "model_id": model_id,
        "probe": EA_PROBE_ID,
        "threshold": THRESHOLD,
        "trials_per_candidate": args.trials,
        "starting_blocks": all_block_ids,
        "n_starting_blocks": n_blocks,
        "baseline_configuration": "only-cr-imp: CR imperative, all other procedural blocks declarative",
    }
    with open(output_dir / "e_mfs_design.json", "w") as f:
        json.dump(design, f, indent=2)

    # Step 0: confirm baseline
    print("\n─── Baseline confirmation ───")
    ea_before, trials_before, raw_base = measure_ea(
        runner=runner,
        corpus=starting_corpus,
        present_blocks=all_block_ids,
        config_id="mfs-baseline",
        battery=battery,
        model_id=model_id,
        trials=args.trials,
        concurrency=args.concurrency,
    )
    budget.add_calls(len(trials_before) * 2)  # gen + judge each trial
    print(f"  Full prompt EA = {ea_before:.3f}  (trials={trials_before})  [{budget.summary()}]")

    # Save baseline run
    baseline_run = AblationRun(
        id="mfs-baseline",
        configs=[
            AblationConfig(
                id="mfs-baseline",
                phase="baseline",
                present_blocks=all_block_ids,
                absent_blocks=[],
                metadata={"step": 0, "role": "baseline"},
            )
        ],
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        results=raw_base,
        metadata={"experiment": "e-mfs", "step": 0},
    )
    save_run(baseline_run, str(output_dir / "run_step000_baseline.json"))

    if ea_before >= THRESHOLD:
        print(
            f"\n  ABORT: baseline EA={ea_before:.3f} ≥ threshold {THRESHOLD}. "
            f"Bomb is NOT firing on the starting prompt. Something has changed "
            f"(model update? corpus drift?). Report and halt without tuning."
        )
        decision_log.append(
            IterationRecord(
                step=0,
                present_before=all_block_ids,
                ea_before=ea_before,
                candidates=[],
                removed_block=None,
                ea_after=None,
                reason="halt_baseline_not_firing",
            )
        )
        with open(output_dir / "decision_log.json", "w") as f:
            json.dump(
                {
                    "design": design,
                    "budget": budget.summary(),
                    "steps": [r.to_dict() for r in decision_log],
                },
                f,
                indent=2,
            )
        return

    if args.confirm_baseline_only:
        print("\n  --confirm-baseline: baseline confirmed; stopping.")
        return

    # Iterative elimination
    present_blocks = list(all_block_ids)
    ea_current = ea_before
    step = 0

    while True:
        step += 1
        print(f"\n─── Step {step}: {len(present_blocks)} blocks present, EA_current={ea_current:.3f} ───")
        print(f"  Budget so far: {budget.summary()}")
        if not budget.check():
            print("  Budget exhausted; halting.")
            decision_log.append(
                IterationRecord(
                    step=step,
                    present_before=list(present_blocks),
                    ea_before=ea_current,
                    candidates=[],
                    removed_block=None,
                    ea_after=None,
                    reason="halt_budget",
                )
            )
            break

        # Evaluate each candidate removal
        candidates: list[CandidateResult] = []
        all_step_results = []
        for i, cand in enumerate(present_blocks):
            if not budget.check():
                print(f"  Budget exhausted mid-step at candidate {i}/{len(present_blocks)}")
                break
            trial_present = [b for b in present_blocks if b != cand]
            cfg_id = f"mfs-s{step:02d}-drop-{cand.replace('/', '_')}"
            try:
                ea_mean, trial_scores, raw = measure_ea(
                    runner=runner,
                    corpus=starting_corpus,
                    present_blocks=trial_present,
                    config_id=cfg_id,
                    battery=battery,
                    model_id=model_id,
                    trials=args.trials,
                    concurrency=args.concurrency,
                )
            except Exception as e:
                print(f"    {i+1:>2}/{len(present_blocks)} {cand:<60}  ERROR: {e}")
                continue
            budget.add_calls(len(trial_scores) * 2)
            candidates.append(
                CandidateResult(
                    block_id=cand,
                    ea_mean=ea_mean,
                    ea_trials=trial_scores,
                    config_id=cfg_id,
                )
            )
            all_step_results.extend(raw)
            marker = " <-- safely removable" if ea_mean < THRESHOLD else ""
            print(
                f"    {i+1:>2}/{len(present_blocks)} {cand:<60}  "
                f"EA={ea_mean:.3f}{marker}"
            )

        # Save per-step raw results
        step_run = AblationRun(
            id=f"mfs-step{step:03d}",
            configs=[
                AblationConfig(
                    id=c.config_id,
                    phase="baseline",
                    present_blocks=[b for b in present_blocks if b != c.block_id],
                    absent_blocks=[c.block_id],
                    metadata={"step": step, "candidate": c.block_id},
                )
                for c in candidates
            ],
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            results=all_step_results,
            metadata={"experiment": "e-mfs", "step": step},
        )
        save_run(step_run, str(output_dir / f"run_step{step:03d}.json"))

        # Choose the block to remove
        safely_removable = [c for c in candidates if c.ea_mean < THRESHOLD]

        if not safely_removable:
            print(
                f"  No safely-removable block (all removals push EA ≥ {THRESHOLD}). "
                f"MFS reached: {len(present_blocks)} blocks."
            )
            decision_log.append(
                IterationRecord(
                    step=step,
                    present_before=list(present_blocks),
                    ea_before=ea_current,
                    candidates=candidates,
                    removed_block=None,
                    ea_after=None,
                    reason="halt_no_safe_removal",
                )
            )
            break

        # Most-removable: LEAST rise in EA (lowest ea_mean is most deeply "firing")
        # Tie-break: lower ea_mean, then alphabetical block_id.
        safely_removable.sort(key=lambda c: (c.ea_mean, c.block_id))
        chosen = safely_removable[0]

        # Non-monotonic check: did removing a block DROP EA compared to current?
        # Not strictly non-monotonic (we remove one block at a time), but
        # if ea_chosen < ea_current, we note it as an interaction signal.
        if chosen.ea_mean < ea_current - 0.05:
            print(
                f"  NOTE: Removing {chosen.block_id} LOWERED EA "
                f"({ea_current:.3f} -> {chosen.ea_mean:.3f}). "
                f"Possible interaction: this block was slightly defusing the bomb."
            )

        print(
            f"  CHOSEN: remove {chosen.block_id}  "
            f"(EA {ea_current:.3f} -> {chosen.ea_mean:.3f}, "
            f"Δ={chosen.ea_mean - ea_current:+.3f})"
        )

        decision_log.append(
            IterationRecord(
                step=step,
                present_before=list(present_blocks),
                ea_before=ea_current,
                candidates=candidates,
                removed_block=chosen.block_id,
                ea_after=chosen.ea_mean,
                reason="removed",
            )
        )

        present_blocks = [b for b in present_blocks if b != chosen.block_id]
        ea_current = chosen.ea_mean

        # Persist decision log after each step for resumability / partial results
        with open(output_dir / "decision_log.json", "w") as f:
            json.dump(
                {
                    "design": design,
                    "budget": budget.summary(),
                    "budget_usd": budget.spent_usd(),
                    "current_mfs_candidate": present_blocks,
                    "current_mfs_size": len(present_blocks),
                    "ea_current": ea_current,
                    "threshold": THRESHOLD,
                    "steps": [r.to_dict() for r in decision_log],
                },
                f,
                indent=2,
            )

    # Final write
    final_mfs = list(present_blocks)
    with open(output_dir / "decision_log.json", "w") as f:
        json.dump(
            {
                "design": design,
                "budget": budget.summary(),
                "budget_usd": budget.spent_usd(),
                "final_mfs": final_mfs,
                "final_mfs_size": len(final_mfs),
                "ea_final": ea_current,
                "threshold": THRESHOLD,
                "steps": [r.to_dict() for r in decision_log],
            },
            f,
            indent=2,
        )

    print(f"\n{'='*60}\n  MFS result: {len(final_mfs)} blocks")
    print(f"  Final EA: {ea_current:.3f}")
    print(f"  Budget: {budget.summary()}")
    for b in final_mfs:
        print(f"    {b}")


# ── Analyze existing log ─────────────────────────────────────────────


def analyze(args):
    log_path = project_root / "data" / "ablation" / "e_mfs" / "decision_log.json"
    if not log_path.exists():
        print("No decision_log.json found. Run the experiment first.")
        return

    with open(log_path) as f:
        log = json.load(f)

    print("E-MFS Analysis")
    print("=" * 80)
    print(f"Starting blocks: {log['design']['n_starting_blocks']}")
    print(f"Threshold: EA < {log['threshold']}")
    print(f"Budget: {log['budget']}")
    if "final_mfs" in log:
        print(f"\nFinal MFS size: {log['final_mfs_size']}")
        print(f"Final EA: {log['ea_final']:.3f}")
        print(f"\nMFS blocks:")
        for b in log["final_mfs"]:
            print(f"  - {b}")

    print("\nPer-step summary:")
    print(
        f"  {'Step':>4} {'PresentN':>9} {'EA_before':>10} "
        f"{'Removed':<56} {'EA_after':>9}"
    )
    for s in log["steps"]:
        removed = s["removed_block"] or "(halted)"
        eaa = f"{s['ea_after']:.3f}" if s["ea_after"] is not None else "---"
        eab = f"{s['ea_before']:.3f}" if s["ea_before"] is not None else "---"
        print(
            f"  {s['step']:>4} {s['present_before_count']:>9} {eab:>10} "
            f"{removed:<56} {eaa:>9}"
        )


def main():
    parser = argparse.ArgumentParser(description="E-MFS: Minimum Failure Set")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm-baseline-only",
        action="store_true",
        help="Run only the baseline confirmation and stop.",
    )
    parser.add_argument("--analyze", action="store_true", help="Summarize decision_log.json")
    args = parser.parse_args()

    if args.analyze:
        analyze(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
