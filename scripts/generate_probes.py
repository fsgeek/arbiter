#!/usr/bin/env python3
"""Generate a probe battery from a block corpus using LLM.

Takes a decomposed prompt corpus and generates behavioral probes
for each free block. This is the piece that makes `arbiter scan`
work on arbitrary prompts.

Usage:
    # Generate probes for Claude Code v2.1.50
    python scripts/generate_probes.py

    # Dry run — show generation prompts without calling LLM
    python scripts/generate_probes.py --dry-run

    # Generate for specific blocks only
    python scripts/generate_probes.py --blocks tone-emoji,no-time-estimates
"""

import argparse
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.probe import Probe
from arbiter.ablation.probe_generator import (
    _select_scoring_method,
    build_generation_prompt,
    parse_generated_probe,
)
from arbiter.ablation.battery import ProbeBattery, save_battery

# Reuse the block lists from run_phase0
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


def main():
    parser = argparse.ArgumentParser(description="Generate probe battery from corpus")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without calling LLM")
    parser.add_argument("--corpus", default="data/prompts/claude-code/v2.1.50_blocks.json")
    parser.add_argument("--output", default="data/ablation/generated_battery.json")
    parser.add_argument("--model", default="haiku", choices=["haiku", "gemini", "sonnet"])
    parser.add_argument("--blocks", type=str, help="Comma-separated block short names to generate")
    args = parser.parse_args()

    # Load corpus
    corpus_path = project_root / args.corpus
    with open(corpus_path) as f:
        data = json.load(f)
    blocks_by_id = {b["id"]: b for b in data["blocks"]}

    # Filter to free blocks (or specific blocks if requested)
    if args.blocks:
        requested = [f"claude-code/{b}" for b in args.blocks.split(",")]
        target_ids = [bid for bid in requested if bid in blocks_by_id]
    else:
        target_ids = [bid for bid in FREE_BLOCKS if bid in blocks_by_id]

    print(f"Generating probes for {len(target_ids)} blocks")

    # Build generation prompts
    gen_tasks = []
    for block_id in target_ids:
        b = blocks_by_id[block_id]
        method = _select_scoring_method(b["modality"], b.get("category", ""), b["text"])
        prompt = build_generation_prompt(
            block_id=b["id"],
            block_text=b["text"],
            category=b.get("category", "unknown"),
            modality=b["modality"],
            scope=str(b.get("scope", "unknown")),
            scoring_method=method,
        )
        gen_tasks.append((block_id, method, prompt))
        short = block_id.split("/")[-1]
        print(f"  {short:40s} -> {method}")

    if args.dry_run:
        print(f"\n--dry-run: showing first generation prompt\n")
        if gen_tasks:
            print(gen_tasks[0][2])
        return

    # Set up LLM caller
    model_map = {
        "haiku": "anthropic/claude-haiku-4-5",
        "gemini": "google/gemini-2.0-flash-001",
        "sonnet": "anthropic/claude-sonnet-4-5",
    }

    import openai
    from arbiter.llm_caller import LLMCaller

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    model_id = model_map[args.model]
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-probe-gen",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )
    caller = LLMCaller(client, model_id)

    # Generate probes
    probes = []
    failures = []

    for i, (block_id, method, prompt) in enumerate(gen_tasks):
        short = block_id.split("/")[-1]
        print(f"\n[{i+1}/{len(gen_tasks)}] Generating probe for {short}...", end=" ", flush=True)

        try:
            response = caller._call_llm(prompt)
            probe = parse_generated_probe(response, block_id, method)
            probes.append(probe)
            print(f"OK ({probe.scoring_method})")
        except Exception as e:
            print(f"FAILED: {e}")
            failures.append((block_id, str(e)))

    # Assemble battery
    battery = ProbeBattery(
        probes=probes,
        metadata={
            "version": "generated-1.0",
            "generator": "scripts/generate_probes.py",
            "generator_model": model_id,
            "corpus": str(args.corpus),
            "n_generated": len(probes),
            "n_failed": len(failures),
        },
    )

    output_path = project_root / args.output
    save_battery(battery, output_path)
    print(f"\nBattery saved: {output_path}")
    print(f"  {len(probes)} probes generated, {len(failures)} failures")

    if failures:
        print(f"\nFailed blocks:")
        for bid, err in failures:
            print(f"  {bid}: {err}")


if __name__ == "__main__":
    main()
