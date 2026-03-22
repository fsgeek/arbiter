#!/usr/bin/env python3
"""Run Phase 1 of the ablation study: pairwise block interactions.

Phase 0 found main effects (every block matters) and hidden suppression
(concise suppresses search-tool adherence by +0.77). Phase 1 uses NIST
covering arrays to test pairwise combinations — does removing blocks A+B
together produce effects beyond the sum of removing each alone?

NIST data: 30% of software failures come from pairwise interactions,
invisible to single-factor testing. The pharmacology parallel (Tekin 2021):
54% of 5-drug combinations contain hidden suppression visible only when
testing lower-order combinations.

Usage:
    python scripts/run_phase1.py --dry-run          # Cost estimate only
    python scripts/run_phase1.py --model haiku       # Run with Haiku
    python scripts/run_phase1.py --resume RUN_ID     # Resume interrupted run
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.configuration import (
    build_baseline_config,
    build_phase1_configs,
)
from arbiter.ablation.covering_array import (
    generate_covering_array,
    verify_coverage,
    save_covering_array,
)
from arbiter.ablation.battery import ProbeBattery, load_battery
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.ablation.tensor import AblationTensor
from arbiter.ablation.analysis import (
    classify_blocks,
    detect_suppression,
    detect_competition_patterns,
    generate_report,
)
from arbiter.prompt_blocks import PromptBlock, PromptCorpus


# Same free blocks as Phase 0 — these are the ablatable behavioral blocks
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
    parser = argparse.ArgumentParser(description="Run Phase 1 pairwise ablation study")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost only")
    parser.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()),
                        help="Model to test (default: haiku)")
    parser.add_argument("--trials", type=int, default=3, help="Trials per probe (default: 3)")
    parser.add_argument("--resume", type=str, help="Resume run from saved state")
    parser.add_argument("--output", type=str, default="data/ablation/phase1_results",
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

    # Generate covering array for pairwise testing
    print(f"\nGenerating pairwise covering array for {len(FREE_BLOCKS)} factors...")
    covering_array = generate_covering_array(
        n_factors=len(FREE_BLOCKS),
        strength=2,  # Pairwise: all 4 states for every pair
    )
    print(f"  {len(covering_array)} configurations generated")

    # Verify pairwise coverage
    if verify_coverage(covering_array, n_factors=len(FREE_BLOCKS), strength=2):
        print("  Pairwise coverage verified")
    else:
        print("  ERROR: Covering array does not achieve pairwise coverage!")
        sys.exit(1)

    # Persist covering array for reproducibility
    output_dir.mkdir(parents=True, exist_ok=True)
    ca_path = output_dir / "phase1_covering_array.json"
    save_covering_array(covering_array, ca_path)
    print(f"  Covering array saved to {ca_path}")

    # Build Phase 1 configurations from the covering array
    configs = build_phase1_configs(corpus, FREE_BLOCKS, constrained, covering_array)
    print(f"  {len(configs)} ablation configurations built")

    # Also include baseline for reference
    baseline = build_baseline_config(corpus, FREE_BLOCKS, constrained)
    all_configs = [baseline] + configs
    print(f"  +1 baseline = {len(all_configs)} total configurations")

    # Model
    model_id = MODEL_MAP[args.model]
    print(f"Model: {model_id}")

    # Cost estimate
    n_calls = len(all_configs) * len(battery.probes) * args.trials
    cost_per_call = {
        "haiku": 0.001,
        "gemini": 0.0003,
        "qwen": 0.002,
    }
    est_cost = n_calls * cost_per_call[args.model]
    print(f"\nCost estimate:")
    print(f"  {len(all_configs)} configs × {len(battery.probes)} probes × {args.trials} trials = {n_calls} API calls")
    print(f"  Estimated cost: ${est_cost:.2f} ({args.model} at ${cost_per_call[args.model]}/call)")

    if args.dry_run:
        print("\n--dry-run: stopping here.")

        # Show covering array statistics
        print(f"\nCovering array statistics:")
        present_counts = [sum(row) for row in covering_array]
        absent_counts = [len(FREE_BLOCKS) - s for s in present_counts]
        print(f"  Blocks present per config: min={min(present_counts)}, max={max(present_counts)}, "
              f"mean={sum(present_counts)/len(present_counts):.1f}")
        print(f"  Blocks absent per config:  min={min(absent_counts)}, max={max(absent_counts)}, "
              f"mean={sum(absent_counts)/len(absent_counts):.1f}")

        # Show sample configurations
        print(f"\nSample configurations:")
        for c in configs[:5]:
            n_absent = len(c.absent_blocks)
            sample_absent = c.absent_blocks[:3]
            suffix = f"... +{n_absent - 3} more" if n_absent > 3 else ""
            print(f"  {c.id}: {n_absent} blocks removed [{', '.join(b.split('/')[-1] for b in sample_absent)}{suffix}]")
        if len(configs) > 5:
            print(f"  ... and {len(configs) - 5} more")

        # Key pairs to watch (from Phase 0 findings)
        print(f"\nKey pairs to watch (from Phase 0 suppression findings):")
        print(f"  tone-concise × use-task-for-search  (suppression: +0.77)")
        print(f"  proactive-agents × no-compat-hacks  (suppression: +0.33)")
        print(f"  plan-with-todo × commit-restrictions (suppression: +0.15)")
        print(f"  todowrite × commit-restrictions      (suppression: +0.13)")
        print(f"\n  Phase 1 tests: are these truly pairwise, or mediated by a third block?")
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
            "X-Title": "arbiter-ablation-phase1",
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
        run_id = f"phase1-{args.model}-{uuid.uuid4().hex[:8]}"
        run = AblationRun(
            id=run_id,
            configs=all_configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "phase": "phase1",
                "model": args.model,
                "model_id": model_id,
                "corpus": "claude-code/v2.1.50",
                "covering_array_size": len(covering_array),
                "covering_array_strength": 2,
                "n_free_blocks": len(FREE_BLOCKS),
                "hypotheses": [
                    "H2-refined: which pairs suppress/amplify each other?",
                    "Is concise×search suppression truly pairwise or mediated?",
                    "Do commit-restrictions suppressors compound?",
                ],
            },
        )

    # Progress display
    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    # Run
    print(f"\nStarting Phase 1 ({n_calls} API calls)...")
    print(f"  Output: {output_dir}")

    try:
        # Run baseline
        print("\nPhase: baseline")
        asyncio.run(runner.run_phase(
            run, "baseline", corpus=corpus,
            concurrency=args.concurrency, progress_callback=progress,
        ))
        print()

        # Run Phase 1 covering array configurations
        print("Phase: phase1 (pairwise covering array)")
        asyncio.run(runner.run_phase(
            run, "phase1", corpus=corpus,
            concurrency=args.concurrency, progress_callback=progress,
        ))
        print()

    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving partial results...")
    except Exception as e:
        print(f"\n\nError: {e}. Saving partial results...")

    # Save results
    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\nResults saved to {save_path}")
    print(f"  {len(run.results)} results collected")

    # Analysis
    if run.results:
        try:
            tensor = AblationTensor.from_ablation_run(run)

            # Main effects from Phase 0 data in the tensor (if any)
            effects = tensor.main_effects()
            if effects:
                print(f"\nMain effects (mean |delta| per block, FDR-corrected):")
                for block_id, effect in sorted(effects.items(), key=lambda x: -x[1])[:10]:
                    marker = " ***" if effect > 0.3 else " *" if effect > 0.1 else ""
                    print(f"  {block_id:50s} {effect:.3f}{marker}")

            # Pairwise interactions — the Phase 1 data
            # Separate baseline and Phase 1 results for the interaction computation
            baseline_config_ids = {c.id for c in run.configs if c.phase == "baseline"}
            baseline_results = [r for r in run.results if r.config_id in baseline_config_ids]

            phase1_config_ids = {c.id for c in run.configs if c.phase == "phase1"}
            phase1_results = [r for r in run.results if r.config_id in phase1_config_ids]

            if phase1_results and baseline_results:
                interactions = tensor.pairwise_interactions(
                    phase1_results=phase1_results,
                    baseline_results=baseline_results,
                    free_block_ids=FREE_BLOCKS,
                    covering_array=covering_array,
                )
                if interactions:
                    print(f"\nPairwise interactions (top 10 by |interaction effect|):")
                    sorted_pairs = sorted(interactions.items(), key=lambda x: -abs(x[1]))
                    for (a, b), effect in sorted_pairs[:10]:
                        a_short = a.split("/")[-1]
                        b_short = b.split("/")[-1]
                        sign = "synergy" if effect > 0 else "antagonism"
                        print(f"  {a_short:30s} × {b_short:30s} {effect:+.3f} ({sign})")
                    print(f"\n  NOTE: Interaction effects may be confounded with higher-order")
                    print(f"  interactions from other blocks absent in the same covering array row.")
                    print(f"  Large effects should be confirmed with targeted 2-block-only ablation.")

            # Suppression detection (Phase 0 tensor entries only)
            suppressions = detect_suppression(tensor)
            if suppressions:
                print(f"\nSuppression patterns (from single-block data): {len(suppressions)}")
                for s in suppressions[:5]:
                    print(f"  {s}")

        except Exception as e:
            print(f"\nCould not compute tensor: {e}")
            import traceback
            traceback.print_exc()
            print("Run analysis manually on the saved results.")


if __name__ == "__main__":
    main()
