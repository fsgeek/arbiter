#!/usr/bin/env python3
"""Run cross-linguistic baseline comparison.

Tests whether system prompt language affects behavioral adherence.
Uses the same English probes against translated system prompts.
Compares to existing English baseline.

Design:
- Independent variable: system prompt language (en, zh, fr, es)
- Dependent variable: probe adherence scores
- Control: English baseline (already collected)
- Probes stay in English (user speaks English)
- Model: Haiku 4.5 (matches existing data)

Usage:
    python scripts/run_cross_linguistic.py --dry-run
    python scripts/run_cross_linguistic.py --model haiku
    python scripts/run_cross_linguistic.py --model haiku --lang zh
    python scripts/run_cross_linguistic.py --compare    # Compare results
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.battery import load_battery
from arbiter.ablation.configuration import AblationConfig, build_baseline_config
from arbiter.ablation.probe import ProbeResult
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

# Same free/constrained split as Phase 0
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
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "kimi": "moonshotai/kimi-k2",
    "minimax": "minimax/minimax-m1",
    "mistral": "mistralai/mistral-medium-3.1",
}

LANGUAGES = ["en", "zh", "fr", "es"]


def load_corpus(path: Path) -> PromptCorpus:
    """Load a block corpus from JSON."""
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


def corpus_path_for_lang(lang: str) -> Path:
    """Get corpus file path for a language."""
    base = project_root / "data" / "prompts" / "claude-code"
    if lang == "en":
        return base / "v2.1.50_blocks.json"
    return base / f"v2.1.50_blocks_{lang}.json"


def run_baseline(args):
    """Run baseline for specified languages."""
    import openai

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    print(f"Battery: {len(battery.probes)} probes")

    model_id = MODEL_MAP[args.model]
    print(f"Model: {model_id}")

    languages = [args.lang] if args.lang else LANGUAGES
    output_dir = project_root / "data" / "ablation" / "cross_linguistic"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check which translated corpora exist
    for lang in languages:
        cp = corpus_path_for_lang(lang)
        if not cp.exists():
            if args.dry_run:
                print(f"  WARNING: {cp.name} not yet created")
            else:
                print(f"ERROR: Translated corpus not found: {cp}")
                if lang != "en":
                    print(f"  Run: python scripts/translate_corpus.py --lang {lang}")
                sys.exit(1)

    # Cost estimate
    n_calls = len(languages) * len(battery.probes) * args.trials
    cost_per_call = {
        "haiku": 0.001,
        "gemini": 0.0003,
        "deepseek": 0.0005,
        "kimi": 0.001,
        "minimax": 0.001,
    }
    est_cost = n_calls * cost_per_call.get(args.model, 0.001)
    print(f"\nPlan: {len(languages)} languages × {len(battery.probes)} probes × {args.trials} trials = {n_calls} calls")
    print(f"Estimated cost: ${est_cost:.2f}")

    if args.dry_run:
        print("\n--dry-run: stopping here.")
        for lang in languages:
            cp = corpus_path_for_lang(lang)
            status = "exists" if cp.exists() else "MISSING"
            print(f"  {lang}: {cp.name} [{status}]")
        return

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-cross-linguistic-baseline",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )

    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    for lang in languages:
        print(f"\n{'='*60}")
        print(f"Language: {lang} ({['English', 'Mandarin', 'French', 'Spanish'][LANGUAGES.index(lang)]})")
        print(f"{'='*60}")

        corpus = load_corpus(corpus_path_for_lang(lang))
        constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]

        config = build_baseline_config(corpus, FREE_BLOCKS, constrained)
        configs = [config]

        import uuid
        run_id = f"xling-{lang}-{args.model}-{uuid.uuid4().hex[:8]}"
        run = AblationRun(
            id=run_id,
            configs=configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "experiment": "cross-linguistic-baseline",
                "language": lang,
                "model": args.model,
                "model_id": model_id,
            },
        )

        def progress(done, total):
            pct = 100 * done / total if total else 0
            print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

        try:
            asyncio.run(runner.run_phase(
                run, "baseline", corpus=corpus,
                concurrency=args.concurrency, progress_callback=progress,
            ))
            print()
        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving partial results...")
        except Exception as e:
            print(f"\n\nError: {e}. Saving partial results...")

        save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
        print(f"Saved: {save_path} ({len(run.results)} results)")

        # Quick summary
        if run.results:
            scores = [r.score for r in run.results]
            print(f"  Mean adherence: {statistics.mean(scores):.3f}")
            print(f"  Std dev: {statistics.stdev(scores):.3f}" if len(scores) > 1 else "")
            print(f"  Min/Max: {min(scores):.3f} / {max(scores):.3f}")


def compare_results(args):
    """Compare cross-linguistic baseline results."""
    results_dir = project_root / "data" / "ablation" / "cross_linguistic"
    if not results_dir.exists():
        print("No cross-linguistic results found. Run baselines first.")
        sys.exit(1)

    print("Cross-linguistic baseline comparison")
    print("=" * 70)

    # Load all runs
    runs_by_lang = {}
    for f in sorted(results_dir.glob("run_xling-*.json")):
        try:
            run = load_run(str(f))
        except Exception as e:
            print(f"  Skipping {f.name}: {e}")
            continue
        if not run.results:
            continue
        lang = run.metadata.get("language", "??")
        model = run.metadata.get("model", "??")
        key = f"{lang}-{model}"
        if key not in runs_by_lang:
            runs_by_lang[key] = run
        else:
            # Keep the one with more results
            if len(run.results) > len(runs_by_lang[key].results):
                runs_by_lang[key] = run

    # Also look for English Phase 0 baseline
    phase0_dir = project_root / "data" / "ablation" / "phase0_results"
    if phase0_dir.exists():
        for f in phase0_dir.glob("run_phase0-*.json"):
            try:
                run = load_run(str(f))
            except Exception:
                continue
            baseline_results = [r for r in run.results if r.config_id == "baseline"]
            if baseline_results:
                model = run.metadata.get("model", "haiku")
                key = f"en-{model} (phase0)"
                if key not in runs_by_lang:
                    runs_by_lang[key] = AblationRun(
                        id=f"phase0-en-{model}",
                        configs=[],
                        battery=run.battery,
                        models=run.models,
                        results=baseline_results,
                        metadata={"language": "en", "model": model},
                    )

    if not runs_by_lang:
        print("No results found.")
        return

    # Per-language summary
    print(f"\n{'Language':<12} {'Model':<10} {'N':>4} {'Mean':>8} {'StdDev':>8} {'Min':>8} {'Max':>8}")
    print("-" * 70)

    lang_scores = {}
    for key in sorted(runs_by_lang):
        run = runs_by_lang[key]
        lang = run.metadata.get("language", "??")
        model = run.metadata.get("model", "??")

        # Use only baseline results
        baseline_results = [r for r in run.results if r.config_id == "baseline"]
        if not baseline_results:
            baseline_results = run.results  # cross-linguistic runs are baseline-only

        scores = [r.score for r in baseline_results]
        if not scores:
            continue

        mean = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0.0
        lang_scores[key] = scores

        print(f"{lang:<12} {model:<10} {len(scores):>4} {mean:>8.3f} {std:>8.3f} {min(scores):>8.3f} {max(scores):>8.3f}")

    # Per-probe comparison
    if len(lang_scores) > 1:
        print(f"\nPer-probe breakdown:")
        print(f"{'Probe':<45}", end="")
        for key in sorted(lang_scores):
            lang = key.split("-")[0]
            print(f" {lang:>8}", end="")
        print()
        print("-" * (45 + 9 * len(lang_scores)))

        # Group by probe
        probe_scores = {}
        for key in sorted(runs_by_lang):
            run = runs_by_lang[key]
            baseline_results = [r for r in run.results if r.config_id == "baseline"]
            if not baseline_results:
                baseline_results = run.results

            for r in baseline_results:
                if r.probe_id not in probe_scores:
                    probe_scores[r.probe_id] = {}
                lang = run.metadata.get("language", "??")
                model = run.metadata.get("model", "??")
                lkey = f"{lang}-{model}"
                if lkey not in probe_scores[r.probe_id]:
                    probe_scores[r.probe_id][lkey] = []
                probe_scores[r.probe_id][lkey].append(r.score)

        for probe_id in sorted(probe_scores):
            print(f"{probe_id:<45}", end="")
            for key in sorted(lang_scores):
                scores = probe_scores.get(probe_id, {}).get(key, [])
                if scores:
                    print(f" {statistics.mean(scores):>8.3f}", end="")
                else:
                    print(f" {'--':>8}", end="")
            print()

        # Delta from English
        en_key = [k for k in lang_scores if k.startswith("en-")]
        if en_key:
            en_key = en_key[0]
            en_mean = statistics.mean(lang_scores[en_key])
            print(f"\nDelta from English baseline ({en_mean:.3f}):")
            for key in sorted(lang_scores):
                if key == en_key:
                    continue
                lang = key.split("-")[0]
                other_mean = statistics.mean(lang_scores[key])
                delta = other_mean - en_mean
                pct = 100 * delta / en_mean if en_mean else 0
                print(f"  {lang}: {delta:+.3f} ({pct:+.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Cross-linguistic ablation baseline")
    parser.add_argument("--model", choices=list(MODEL_MAP.keys()), help="Model to test")
    parser.add_argument("--lang", choices=LANGUAGES, help="Single language (default: all)")
    parser.add_argument("--trials", type=int, default=3, help="Trials per probe")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    parser.add_argument("--compare", action="store_true", help="Compare existing results")
    args = parser.parse_args()

    if args.compare:
        compare_results(args)
    elif args.model:
        run_baseline(args)
    else:
        parser.print_help()
        print("\nEither --model (to run) or --compare (to analyze) is required.")


if __name__ == "__main__":
    main()
