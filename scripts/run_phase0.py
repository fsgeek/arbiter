#!/usr/bin/env python3
"""Run Phase 0 of the ablation study: single-block removal.

Loads the v2.1.50 block corpus and probe battery, builds Phase 0
configurations (one block removed at a time + baseline), and runs
the probe battery against each configuration.

This is the easy falsification gate. If it shows nothing, we've
spent ~$50 learning that either system prompts are more robust
than we thought or our probes aren't sensitive enough.

Usage:
    python scripts/run_phase0.py --dry-run          # Cost estimate only
    python scripts/run_phase0.py --model haiku       # Run with Haiku
    python scripts/run_phase0.py --model gemini      # Run with Gemini Flash
    python scripts/run_phase0.py --trials 3          # 3 trials per probe
    python scripts/run_phase0.py --resume RUN_ID     # Resume interrupted run
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.configuration import (
    build_baseline_config,
    build_phase0_configs,
)
from arbiter.ablation.battery import ProbeBattery, load_battery
from arbiter.ablation.probe import Probe, ProbeResult
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.ablation.tensor import AblationTensor
from arbiter.ablation.analysis import classify_blocks, detect_suppression, generate_report
from arbiter.prompt_blocks import PromptBlock, PromptCorpus


# Block classification: which are free (ablatable) vs constrained
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

# Model shortcuts
MODEL_MAP = {
    "haiku": "anthropic/claude-haiku-4-5",
    "gemini": "google/gemini-2.0-flash-001",
    "qwen": "qwen/qwen-2.5-72b-instruct",
}


def load_corpus(path: Path) -> PromptCorpus:
    """Load the block corpus from JSON."""
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


def main():
    parser = argparse.ArgumentParser(description="Run Phase 0 ablation study")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost only")
    parser.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()),
                        help="Model to test (default: haiku)")
    parser.add_argument("--trials", type=int, default=3, help="Trials per probe (default: 3)")
    parser.add_argument("--resume", type=str, help="Resume run from saved state")
    parser.add_argument("--output", type=str, default="data/ablation/phase0_results",
                        help="Output directory for results")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    args = parser.parse_args()

    # Paths
    corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    output_dir = project_root / args.output

    # Load data
    print(f"Loading corpus from {corpus_path}")
    corpus = load_corpus(corpus_path)
    print(f"  {len(corpus.blocks)} blocks loaded")

    print(f"Loading battery from {battery_path}")
    battery = load_battery(battery_path)
    print(f"  {len(battery.probes)} probes loaded")

    # Validate battery coverage
    missing = battery.validate(FREE_BLOCKS)
    if missing:
        print(f"  WARNING: {len(missing)} free blocks have no probes: {missing}")

    # Classify blocks
    constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]
    print(f"  {len(FREE_BLOCKS)} free blocks, {len(constrained)} constrained blocks")

    # Build configurations
    configs = build_phase0_configs(corpus, FREE_BLOCKS, constrained)
    print(f"  {len(configs)} configurations (1 baseline + {len(FREE_BLOCKS)} ablations)")

    # Model
    model_id = MODEL_MAP[args.model]
    print(f"Model: {model_id}")

    # Cost estimate
    n_calls = len(configs) * len(battery.probes) * args.trials
    # Conservative estimates per model
    cost_per_call = {
        "haiku": 0.001,
        "gemini": 0.0003,
        "qwen": 0.002,
    }
    est_cost = n_calls * cost_per_call[args.model]
    print(f"\nCost estimate:")
    print(f"  {len(configs)} configs × {len(battery.probes)} probes × {args.trials} trials = {n_calls} API calls")
    print(f"  Estimated cost: ${est_cost:.2f} ({args.model} at ${cost_per_call[args.model]}/call)")

    if args.dry_run:
        print("\n--dry-run: stopping here.")

        # Show what would be tested
        print(f"\nConfigurations:")
        for c in configs[:5]:
            removed = c.absent_blocks[0] if c.absent_blocks else "(none — baseline)"
            print(f"  {c.id}: removed {removed}")
        if len(configs) > 5:
            print(f"  ... and {len(configs) - 5} more")

        print(f"\nProbes:")
        for p in battery.probes[:5]:
            print(f"  {p.id}: targets {p.target_block} ({p.scoring_method})")
        if len(battery.probes) > 5:
            print(f"  ... and {len(battery.probes) - 5} more")

        print(f"\nHypotheses being tested:")
        print(f"  H1: Do blocks have main effects? (NIST predicts ~60% of interactions)")
        print(f"  H2: Does removing any block IMPROVE other blocks? (hidden suppression)")
        print(f"  H5: Do the 4 critical TodoWrite contradictions show behavioral effects?")
        return

    # Wire up API client
    import os
    import openai

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\nERROR: OPENROUTER_API_KEY not set. Export it and retry.")
        print("  export OPENROUTER_API_KEY=your-key-here")
        sys.exit(1)

    from arbiter.llm_caller import LLMCaller

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-ablation-phase0",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )
    caller = LLMCaller(client, model_id)

    runner = AblationRunner(caller=caller)

    # Build or resume run
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.resume:
        print(f"\nResuming run from {args.resume}")
        run = load_run(args.resume)
    else:
        import uuid
        run_id = f"phase0-{args.model}-{uuid.uuid4().hex[:8]}"
        run = AblationRun(
            id=run_id,
            configs=configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "phase": "phase0",
                "model": args.model,
                "model_id": model_id,
                "corpus": "claude-code/v2.1.50",
                "hypotheses": ["H1", "H2", "H5"],
            },
        )

    # Progress display
    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    # Run
    print(f"\nStarting Phase 0 ({n_calls} API calls)...")
    print(f"  Output: {output_dir}")

    try:
        # Run baseline first
        asyncio.run(runner.run_phase(
            run, "baseline", corpus=corpus,
            concurrency=args.concurrency, progress_callback=progress,
        ))
        print()  # newline after progress

        # Run Phase 0 ablations
        asyncio.run(runner.run_phase(
            run, "phase0", corpus=corpus,
            concurrency=args.concurrency, progress_callback=progress,
        ))
        print()  # newline after progress

    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving partial results...")
    except Exception as e:
        print(f"\n\nError: {e}. Saving partial results...")

    # Save results
    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\nResults saved to {save_path}")
    print(f"  {len(run.results)} results collected")

    # Quick summary if we have results
    if run.results:
        from arbiter.ablation.tensor import AblationTensor
        try:
            tensor = AblationTensor.from_ablation_run(run)
            effects = tensor.main_effects()
            if effects:
                print(f"\nMain effects (mean |delta| per block):")
                for block_id, effect in sorted(effects.items(), key=lambda x: -x[1]):
                    marker = " ***" if effect > 0.3 else " *" if effect > 0.1 else ""
                    print(f"  {block_id:50s} {effect:.3f}{marker}")
        except Exception as e:
            print(f"\nCould not compute tensor: {e}")
            print("Run analysis manually on the saved results.")


if __name__ == "__main__":
    main()
