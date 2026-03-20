#!/usr/bin/env python3
"""Autoresearch loop for prompt ablation — adapted from Karpathy's autoresearch.

The idea: give an AI agent the ablation infrastructure and a program.md,
let it run experiments autonomously. It proposes a prompt edit, runs the
battery, checks if the result improved, keeps or discards, and repeats.

Adapted from: https://github.com/karpathy/autoresearch

Files:
    program.md          — research direction (human-edited)
    data/prompts/...    — prompt corpus (agent-modified)
    data/ablation/...   — battery + results (read-only for agent)
    results.tsv         — experiment log (append-only)

Usage:
    # Establish baseline
    python scripts/autoresearch.py baseline --model haiku

    # Run one experiment (for agent integration)
    python scripts/autoresearch.py run --model haiku --tag "remove dead block"

    # Compare against baseline
    python scripts/autoresearch.py compare --run-a baseline --run-b latest

    # Show results log
    python scripts/autoresearch.py log
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.battery import ProbeBattery, load_battery
from arbiter.ablation.configuration import build_phase0_configs
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.ablation.tensor import AblationTensor

# ---------------------------------------------------------------------------
# Constants — the equivalent of prepare.py (do not modify)
# ---------------------------------------------------------------------------

CORPUS_PATH = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
BATTERY_PATH = project_root / "data" / "ablation" / "phase0_battery.json"
RESULTS_DIR = project_root / "data" / "ablation" / "autoresearch"
RESULTS_TSV = RESULTS_DIR / "results.tsv"

FREE_BLOCKS = [
    "claude-code/tone-emoji",
    "claude-code/tone-concise",
    "claude-code/tone-text-only-comms",
    "claude-code/tone-no-new-files",
    "claude-code/tone-no-colon-before-tools",
    "claude-code/professional-objectivity",
    "claude-code/no-time-estimates",
    "claude-code/task-management-todowrite",
    "claude-code/doing-tasks-read-first",
    "claude-code/doing-tasks-plan-with-todo",
    "claude-code/doing-tasks-no-overengineering",
    "claude-code/doing-tasks-no-compat-hacks",
    "claude-code/tool-policy-use-task-for-search",
    "claude-code/tool-policy-proactive-agents",
    "claude-code/tool-policy-parallel-calls",
    "claude-code/tool-policy-dedicated-tools",
    "claude-code/tool-policy-explore-agent",
    "claude-code/todowrite-importance-repeated",
    "claude-code/code-references",
    "claude-code/tool-bash-commit-workflow",
    "claude-code/tool-bash-commit-restrictions",
    "claude-code/tool-bash-pr-workflow",
]

MODEL_MAP = {
    "haiku": "anthropic/claude-haiku-4-5",
    "gemini": "google/gemini-2.0-flash-001",
    "qwen": "qwen/qwen-2.5-72b-instruct",
}


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_corpus(path: Path):
    """Load block corpus from JSON."""
    from arbiter.prompt_blocks import PromptBlock, PromptCorpus

    with open(path) as f:
        data = json.load(f)

    blocks = []
    for b in data["blocks"]:
        blocks.append(PromptBlock(
            id=b["id"],
            source=b["source"],
            tier=b["tier"],
            category=b["category"],
            text=b["text"],
            modality=b["modality"],
            scope=b["scope"],
            exports=b.get("exports", []),
            imports=b.get("imports", []),
            line_start=b.get("line_start", 0),
            line_end=b.get("line_end", 0),
        ))

    return PromptCorpus(
        name=data["name"],
        source_file=data.get("source_file", "unknown"),
        blocks=blocks,
    )


# ---------------------------------------------------------------------------
# Metrics — the keep/discard decision
# ---------------------------------------------------------------------------

def compute_summary(tensor: AblationTensor) -> dict:
    """Collapse tensor to summary metrics for keep/discard decisions.

    Returns dict with:
        mean_adherence: mean baseline score across all probes
        interference_density: fraction of entries with |delta| > 0.1
        suppression_count: number of positive deltas > 0.1 (removal helps)
        dependency_count: number of negative deltas < -0.1 (removal hurts)
        max_suppression: largest positive delta (biggest improvement from removal)
        max_dependency: largest negative delta (biggest loss from removal)
        priority_scores: dict of probe_id -> baseline score for priority probes
    """
    baselines = []
    suppressions = []
    dependencies = []

    for key, score in tensor.entries.items():
        baselines.append(score.baseline_score)
        if score.delta > 0.1:
            suppressions.append(score.delta)
        if score.delta < -0.1:
            dependencies.append(score.delta)

    n_entries = len(tensor.entries)
    n_significant = len(suppressions) + len(dependencies)

    return {
        "mean_adherence": sum(baselines) / len(baselines) if baselines else 0.0,
        "interference_density": n_significant / n_entries if n_entries else 0.0,
        "suppression_count": len(suppressions),
        "dependency_count": len(dependencies),
        "max_suppression": max(suppressions) if suppressions else 0.0,
        "max_dependency": min(dependencies) if dependencies else 0.0,
        "n_entries": n_entries,
    }


def format_summary(summary: dict) -> str:
    """Format summary for printing — like autoresearch's val_bpb output."""
    return (
        f"---\n"
        f"mean_adherence:      {summary['mean_adherence']:.4f}\n"
        f"interference_density: {summary['interference_density']:.4f}\n"
        f"suppression_count:   {summary['suppression_count']}\n"
        f"dependency_count:    {summary['dependency_count']}\n"
        f"max_suppression:     {summary['max_suppression']:+.4f}\n"
        f"max_dependency:      {summary['max_dependency']:+.4f}\n"
        f"tensor_entries:      {summary['n_entries']}\n"
        f"---"
    )


# ---------------------------------------------------------------------------
# Results TSV — the experiment log
# ---------------------------------------------------------------------------

def init_tsv():
    """Create results.tsv with header if it doesn't exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w") as f:
            f.write("run_id\tmean_adherence\tinterference_density\tsuppression\tdependency\tstatus\tdescription\n")


def append_tsv(run_id: str, summary: dict, status: str, description: str):
    """Append one row to results.tsv."""
    with open(RESULTS_TSV, "a") as f:
        f.write(
            f"{run_id}\t"
            f"{summary.get('mean_adherence', 0.0):.4f}\t"
            f"{summary.get('interference_density', 0.0):.4f}\t"
            f"{summary.get('suppression_count', 0)}\t"
            f"{summary.get('dependency_count', 0)}\t"
            f"{status}\t"
            f"{description}\n"
        )


# ---------------------------------------------------------------------------
# Run an experiment
# ---------------------------------------------------------------------------

def make_caller(model_key: str):
    """Create LLMCaller from environment."""
    import openai
    from arbiter.llm_caller import LLMCaller

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    model_id = MODEL_MAP[model_key]
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-autoresearch",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )
    return LLMCaller(client, model_id), model_id


def run_experiment(
    model_key: str,
    trials: int = 3,
    concurrency: int = 5,
    tag: str = "",
) -> tuple[str, AblationTensor, dict]:
    """Run one full Phase 0 ablation and return (run_id, tensor, summary).

    This is the equivalent of `uv run train.py` in autoresearch.
    """
    corpus = load_corpus(CORPUS_PATH)
    battery = load_battery(BATTERY_PATH)
    caller, model_id = make_caller(model_key)
    runner = AblationRunner(caller=caller)

    constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]
    configs = build_phase0_configs(corpus, FREE_BLOCKS, constrained)

    run_id = f"ar-{model_key}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=trials,
        temperature=0.0,
        metadata={
            "tag": tag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    print(f"Running experiment: {run_id}")
    print(f"  Model: {model_id}")
    print(f"  Tag: {tag or '(baseline)'}")

    try:
        asyncio.run(runner.run_phase(
            run, "baseline", corpus=corpus,
            concurrency=concurrency, progress_callback=progress,
        ))
        print()
        asyncio.run(runner.run_phase(
            run, "phase0", corpus=corpus,
            concurrency=concurrency, progress_callback=progress,
        ))
        print()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")

    # Save raw results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = save_run(run, str(RESULTS_DIR / f"run_{run_id}.json"))
    print(f"  Saved: {save_path}")

    # Assemble tensor and compute summary
    tensor = AblationTensor.from_ablation_run(run)
    summary = compute_summary(tensor)

    print(format_summary(summary))
    return run_id, tensor, summary


# ---------------------------------------------------------------------------
# Compare — the keep/discard decision
# ---------------------------------------------------------------------------

def compare_summaries(baseline: dict, current: dict) -> tuple[str, str]:
    """Compare two summaries. Returns (status, reason).

    Keep if: interference_density decreased OR mean_adherence increased
             AND no catastrophic regression (dependency_count didn't double)
    Discard otherwise.
    """
    density_improved = current["interference_density"] < baseline["interference_density"]
    adherence_improved = current["mean_adherence"] > baseline["mean_adherence"] + 0.01
    dependency_exploded = current["dependency_count"] > baseline["dependency_count"] * 2

    if dependency_exploded:
        return "discard", "dependency count exploded"

    if density_improved or adherence_improved:
        reasons = []
        if density_improved:
            d = baseline["interference_density"] - current["interference_density"]
            reasons.append(f"density -{d:.4f}")
        if adherence_improved:
            d = current["mean_adherence"] - baseline["mean_adherence"]
            reasons.append(f"adherence +{d:.4f}")
        return "keep", "; ".join(reasons)

    return "discard", "no improvement"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_baseline(args):
    """Establish the baseline — run the unmodified prompt."""
    init_tsv()
    run_id, tensor, summary = run_experiment(
        model_key=args.model,
        trials=args.trials,
        concurrency=args.concurrency,
        tag="baseline",
    )
    append_tsv(run_id, summary, "baseline", "unmodified prompt — baseline")
    # Save baseline summary for future comparisons
    with open(RESULTS_DIR / "baseline_summary.json", "w") as f:
        json.dump({"run_id": run_id, **summary}, f, indent=2)
    print(f"\nBaseline established: {run_id}")


def cmd_run(args):
    """Run one experiment and compare against baseline."""
    init_tsv()

    # Load baseline
    baseline_path = RESULTS_DIR / "baseline_summary.json"
    if not baseline_path.exists():
        print("ERROR: No baseline. Run `autoresearch.py baseline` first.")
        sys.exit(1)
    with open(baseline_path) as f:
        baseline = json.load(f)

    # Run experiment
    run_id, tensor, summary = run_experiment(
        model_key=args.model,
        trials=args.trials,
        concurrency=args.concurrency,
        tag=args.tag,
    )

    # Keep or discard
    status, reason = compare_summaries(baseline, summary)
    print(f"\nDecision: {status.upper()} ({reason})")
    append_tsv(run_id, summary, status, f"{args.tag} — {reason}")


def cmd_compare(args):
    """Compare two saved runs."""
    run_a = load_run(str(RESULTS_DIR / f"run_{args.run_a}.json"))
    run_b = load_run(str(RESULTS_DIR / f"run_{args.run_b}.json"))

    tensor_a = AblationTensor.from_ablation_run(run_a)
    tensor_b = AblationTensor.from_ablation_run(run_b)

    summary_a = compute_summary(tensor_a)
    summary_b = compute_summary(tensor_b)

    print(f"Run A ({args.run_a}):")
    print(format_summary(summary_a))
    print(f"\nRun B ({args.run_b}):")
    print(format_summary(summary_b))

    status, reason = compare_summaries(summary_a, summary_b)
    print(f"\nDecision: {status.upper()} ({reason})")


def cmd_log(args):
    """Show results log."""
    if not RESULTS_TSV.exists():
        print("No results yet.")
        return
    with open(RESULTS_TSV) as f:
        print(f.read())


def main():
    parser = argparse.ArgumentParser(
        description="Autoresearch loop for prompt ablation",
        epilog="Adapted from https://github.com/karpathy/autoresearch",
    )
    sub = parser.add_subparsers(dest="command")

    # baseline
    p_base = sub.add_parser("baseline", help="Establish baseline")
    p_base.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()))
    p_base.add_argument("--trials", type=int, default=3)
    p_base.add_argument("--concurrency", type=int, default=5)
    p_base.set_defaults(func=cmd_baseline)

    # run
    p_run = sub.add_parser("run", help="Run one experiment")
    p_run.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()))
    p_run.add_argument("--trials", type=int, default=3)
    p_run.add_argument("--concurrency", type=int, default=5)
    p_run.add_argument("--tag", default="", help="Short description of what changed")
    p_run.set_defaults(func=cmd_run)

    # compare
    p_cmp = sub.add_parser("compare", help="Compare two runs")
    p_cmp.add_argument("--run-a", required=True, help="First run ID")
    p_cmp.add_argument("--run-b", required=True, help="Second run ID")
    p_cmp.set_defaults(func=cmd_compare)

    # log
    p_log = sub.add_parser("log", help="Show results log")
    p_log.set_defaults(func=cmd_log)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
