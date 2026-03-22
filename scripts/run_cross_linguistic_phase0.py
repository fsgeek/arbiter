#!/usr/bin/env python3
"""Run Phase 0 ablation on translated corpora.

Tests whether the hub topology (no-time-estimates dominance) survives
translation. Runs single-block removal for each translated corpus
and compares main effects across languages.

Usage:
    python scripts/run_cross_linguistic_phase0.py --dry-run
    python scripts/run_cross_linguistic_phase0.py --model haiku
    python scripts/run_cross_linguistic_phase0.py --model haiku --lang zh
    python scripts/run_cross_linguistic_phase0.py --compare
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
from arbiter.ablation.configuration import build_phase0_configs
from arbiter.ablation.probe import ProbeResult
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

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
}

LANGUAGES = ["zh", "fr", "es"]  # en already has Phase 0 data


def load_corpus(path: Path) -> PromptCorpus:
    with open(path) as f:
        data = json.load(f)
    blocks = []
    for b in data["blocks"]:
        blocks.append(PromptBlock(
            id=b["id"], source=b["source"], tier=b["tier"],
            category=b["category"], text=b["text"], modality=b["modality"],
            scope=b["scope"], exports=b.get("exports", []),
            imports=b.get("imports", []),
            line_start=b.get("line_start", 0), line_end=b.get("line_end", 0),
        ))
    return PromptCorpus(
        name=data["name"],
        source_file=data.get("source_file", "unknown"),
        blocks=blocks,
    )


def corpus_path_for_lang(lang: str) -> Path:
    base = project_root / "data" / "prompts" / "claude-code"
    if lang == "en":
        return base / "v2.1.50_blocks.json"
    return base / f"v2.1.50_blocks_{lang}.json"


def run_phase0(args):
    import openai

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)

    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    model_id = MODEL_MAP[args.model]

    languages = [args.lang] if args.lang else LANGUAGES
    output_dir = project_root / "data" / "ablation" / "cross_linguistic_phase0"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cost estimate
    n_configs = len(FREE_BLOCKS) + 1  # baseline + one per block
    n_calls_per_lang = n_configs * len(battery.probes) * args.trials
    n_calls = len(languages) * n_calls_per_lang
    est_cost = n_calls * 0.001
    print(f"Plan: {len(languages)} langs × {n_configs} configs × {len(battery.probes)} probes × {args.trials} trials = {n_calls} calls")
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
            "X-Title": "arbiter-cross-linguistic-phase0",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )

    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    for lang in languages:
        print(f"\n{'='*60}")
        print(f"Phase 0: {lang}")
        print(f"{'='*60}")

        corpus = load_corpus(corpus_path_for_lang(lang))
        constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]
        configs = build_phase0_configs(corpus, FREE_BLOCKS, constrained)

        import uuid
        run_id = f"xling-p0-{lang}-{args.model}-{uuid.uuid4().hex[:8]}"
        run = AblationRun(
            id=run_id,
            configs=configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "experiment": "cross-linguistic-phase0",
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
            asyncio.run(runner.run_phase(
                run, "phase0", corpus=corpus,
                concurrency=args.concurrency, progress_callback=progress,
            ))
            print()
        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving partial results...")
        except Exception as e:
            print(f"\n\nError: {e}. Saving partial results...")

        save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
        print(f"Saved: {save_path} ({len(run.results)} results)")


def compare_results(args):
    """Compare main effects across languages."""
    results_dir = project_root / "data" / "ablation" / "cross_linguistic_phase0"

    # Load cross-linguistic Phase 0 runs
    runs_by_lang = {}
    if results_dir.exists():
        for f in sorted(results_dir.glob("run_xling-p0-*.json")):
            try:
                run = load_run(str(f))
            except Exception:
                continue
            if not run.results:
                continue
            lang = run.metadata.get("language", "??")
            runs_by_lang[lang] = run

    # Load English Phase 0
    phase0_dir = project_root / "data" / "ablation" / "phase0_results"
    if phase0_dir.exists():
        for f in phase0_dir.glob("run_phase0-*.json"):
            try:
                run = load_run(str(f))
            except Exception:
                continue
            if run.results:
                runs_by_lang["en"] = run
                break

    if not runs_by_lang:
        print("No results found.")
        return

    print(f"Languages with Phase 0 data: {sorted(runs_by_lang.keys())}")

    # Compute main effects per language
    effects_by_lang = {}
    for lang, run in sorted(runs_by_lang.items()):
        # Baseline scores
        baseline_scores = {}
        for r in run.results:
            if r.config_id == "baseline":
                if r.probe_id not in baseline_scores:
                    baseline_scores[r.probe_id] = []
                baseline_scores[r.probe_id].append(r.score)

        baseline_means = {pid: statistics.mean(s) for pid, s in baseline_scores.items()}

        # Per-block effects
        effects = {}
        for config in run.configs:
            if config.phase != "phase0":
                continue
            removed = config.absent_blocks[0]
            results = [r for r in run.results if r.config_id == config.id]
            probe_scores = {}
            for r in results:
                if r.probe_id not in probe_scores:
                    probe_scores[r.probe_id] = []
                probe_scores[r.probe_id].append(r.score)

            deltas = []
            for pid, scores in probe_scores.items():
                if pid in baseline_means:
                    deltas.append(statistics.mean(scores) - baseline_means[pid])
            if deltas:
                effects[removed] = statistics.mean(deltas)

        effects_by_lang[lang] = effects
        bm = statistics.mean(baseline_means.values()) if baseline_means else 0
        print(f"\n{lang}: baseline={bm:.3f}, {len(effects)} block effects computed")

    # Cross-linguistic comparison table
    all_blocks = set()
    for effects in effects_by_lang.values():
        all_blocks.update(effects.keys())

    langs = sorted(effects_by_lang.keys())
    print(f"\n{'Block':<45}", end="")
    for lang in langs:
        print(f" {lang:>8}", end="")
    print()
    print("-" * (45 + 9 * len(langs)))

    rows = []
    for block in sorted(all_blocks):
        short = block.split("/")[-1]
        row = [short]
        for lang in langs:
            eff = effects_by_lang[lang].get(block)
            row.append(eff)
        rows.append(row)

    # Sort by English effect magnitude
    en_idx = langs.index("en") if "en" in langs else 0
    rows.sort(key=lambda r: abs(r[1 + en_idx]) if r[1 + en_idx] is not None else 0, reverse=True)

    for row in rows:
        print(f"{row[0]:<45}", end="")
        for val in row[1:]:
            if val is not None:
                print(f" {val:>+8.4f}", end="")
            else:
                print(f" {'--':>8}", end="")
        print()

    # Hub analysis per language
    print(f"\nHub analysis (blocks with largest |main effect|):")
    for lang in langs:
        effects = effects_by_lang[lang]
        top5 = sorted(effects.items(), key=lambda x: -abs(x[1]))[:5]
        print(f"\n  {lang}:")
        for block, eff in top5:
            print(f"    {block.split('/')[-1]:40s} {eff:+.4f}")

    # Correlation between languages
    if len(langs) >= 2:
        print(f"\nEffect correlation between languages:")
        common_blocks = set.intersection(*[set(e.keys()) for e in effects_by_lang.values()])
        for i, l1 in enumerate(langs):
            for l2 in langs[i+1:]:
                vals1 = [effects_by_lang[l1][b] for b in common_blocks]
                vals2 = [effects_by_lang[l2][b] for b in common_blocks]
                if len(vals1) >= 3:
                    # Pearson correlation
                    mean1 = statistics.mean(vals1)
                    mean2 = statistics.mean(vals2)
                    num = sum((a - mean1) * (b - mean2) for a, b in zip(vals1, vals2))
                    den1 = sum((a - mean1) ** 2 for a in vals1) ** 0.5
                    den2 = (sum((b - mean2) ** 2 for b in vals2)) ** 0.5
                    if den1 > 0 and den2 > 0:
                        r = num / (den1 * den2)
                        print(f"  {l1} vs {l2}: r = {r:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Cross-linguistic Phase 0 ablation")
    parser.add_argument("--model", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--lang", choices=LANGUAGES)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    if args.compare:
        compare_results(args)
    elif args.model:
        run_phase0(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
