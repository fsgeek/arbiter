#!/usr/bin/env python3
"""
E-REG: Register Rewriting for Intra-Lingual Suppression

Tests whether the tone-concise → use-task-for-search suppression (+0.77 delta,
largest in the corpus) is register-mediated or semantic.

Background:
  Phase 0 found: removing tone-concise improves use-task-for-search adherence
  from 0.23 → 1.00. Paper 3 showed that declarative rewriting fixes cross-
  linguistic topology inversion. E-REG tests whether the same mechanism
  operates within English on the strongest suppression pair.

Two competing hypotheses:
  H1 (Register): tone-concise's mild imperative register ("should be short")
      competes with use-task-for-search for obligatory force. Declarative
      rewriting resolves the competition.
  H2 (Semantic): The concept of conciseness itself biases toward shorter
      token paths (bash grep vs structured tool invocation). Register
      doesn't matter — the semantic pressure is sufficient.

5 conditions:
  1. Baseline — both blocks, original imperative form (expect ~0.23)
  2. Ablation — tone-concise removed (replicates Phase 0: expect ~1.00)
  3. Declarative tone — tone-concise rewritten declarative, rest unchanged
  4. Both declarative — both blocks rewritten declarative
  5. Intensified tone — tone-concise rewritten maximally imperative

Predictions:
  If H1 (register): condition 3 recovers → ~1.00; condition 5 worsens → <0.23
  If H2 (semantic): condition 3 stays → ~0.23; condition 5 stays → ~0.23
  Mixed:            condition 3 partial recovery; interesting boundary found

Usage:
    python scripts/run_e_reg.py --dry-run
    python scripts/run_e_reg.py --model haiku
    python scripts/run_e_reg.py --model haiku --model gemini
    python scripts/run_e_reg.py --compare
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
from arbiter.ablation.configuration import AblationConfig, build_baseline_config
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

# ── Constants ─────────────────────────────────────────────────────────

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
    "mistral": "mistralai/mistral-medium-3.1",
}

# ── Block rewrites ────────────────────────────────────────────────────
#
# Original tone-concise (mild imperative):
#   "Your output will be displayed on a command line interface. Your
#   responses should be short and concise. You can use Github-flavored
#   markdown for formatting, and will be rendered in a monospace font
#   using the CommonMark specification."
#
# Original use-task-for-search (imperative):
#   "When doing file search, prefer to use the Task tool in order to
#   reduce context usage."

TONE_CONCISE_DECLARATIVE = (
    "Output environment: command line interface. "
    "Response style: short, concise. "
    "Supported formatting: Github-flavored markdown "
    "(CommonMark specification), rendered in monospace font."
)

TONE_CONCISE_INTENSIFIED = (
    "You MUST keep ALL responses extremely brief and concise. "
    "NEVER write lengthy explanations or verbose output. "
    "ALWAYS minimize response length — every unnecessary word wastes "
    "the user's time. Your output is displayed on a command line "
    "interface. Use markdown formatting ONLY when strictly necessary."
)

USE_TASK_DECLARATIVE = (
    "File search tool preference: Task tool. "
    "Reason: reduces context window usage. "
    "Applies to: all file search operations."
)

# ── Condition definitions ─────────────────────────────────────────────

# Each condition is: (name, description, tone_concise_action, use_task_action)
# Actions: "original" = keep as-is, "remove" = ablate, "declarative" = rewrite,
#          "intensified" = stronger imperative
CONDITIONS = [
    ("baseline",       "Both blocks, original imperative",   "original",     "original"),
    ("ablation",       "tone-concise removed",               "remove",       "original"),
    ("decl-tone",      "tone-concise declarative",           "declarative",  "original"),
    ("decl-both",      "Both blocks declarative",            "declarative",  "declarative"),
    ("intensified",    "tone-concise intensified imperative", "intensified", "original"),
]


# ── Corpus manipulation ──────────────────────────────────────────────

def load_corpus(path: Path) -> PromptCorpus:
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


def modify_corpus_block(corpus: PromptCorpus, block_id: str, new_text: str) -> PromptCorpus:
    """Create a new corpus with one block's text replaced."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id == block_id:
            new_blocks.append(b.model_copy(update={"text": new_text}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name,
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


def remove_corpus_block(corpus: PromptCorpus, block_id: str) -> PromptCorpus:
    """Create a new corpus with one block removed."""
    return PromptCorpus(
        name=corpus.name,
        source_file=corpus.source_file,
        blocks=[b for b in corpus.blocks if b.id != block_id],
    )


def build_condition_corpus(base_corpus: PromptCorpus, tone_action: str, task_action: str) -> PromptCorpus:
    """Build a corpus for a specific experimental condition."""
    corpus = base_corpus

    # Apply tone-concise action
    if tone_action == "remove":
        corpus = remove_corpus_block(corpus, "claude-code/tone-concise")
    elif tone_action == "declarative":
        corpus = modify_corpus_block(corpus, "claude-code/tone-concise", TONE_CONCISE_DECLARATIVE)
    elif tone_action == "intensified":
        corpus = modify_corpus_block(corpus, "claude-code/tone-concise", TONE_CONCISE_INTENSIFIED)
    # "original" = no change

    # Apply use-task-for-search action
    if task_action == "declarative":
        corpus = modify_corpus_block(corpus, "claude-code/tool-policy-use-task-for-search", USE_TASK_DECLARATIVE)
    # "original" = no change

    return corpus


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


# ── Experiment execution ──────────────────────────────────────────────

def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    models = args.model if args.model else ["haiku"]

    print(f"\nE-REG: Register Rewriting for Intra-Lingual Suppression")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(CONDITIONS)}")
    print(f"  Models: {', '.join(models)}")
    print(f"  Trials: {args.trials}")

    # Cost estimate
    n_calls = len(CONDITIONS) * len(models) * len(battery.probes) * args.trials
    # llm_judge probes require an extra call for judging
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * len(models) * n_judge * args.trials
    total_calls = n_calls + n_judge_calls
    est_cost = total_calls * 0.001  # conservative average
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total_calls}")
    print(f"  Estimated cost: ${est_cost:.2f}")

    print(f"\n  Conditions:")
    for name, desc, tone, task in CONDITIONS:
        print(f"    {name:<15} {desc}")

    print(f"\n  Hypotheses:")
    print(f"    H1 (Register):  decl-tone recovers search adherence; intensified worsens it")
    print(f"    H2 (Semantic):  decl-tone has no effect; intensified has no effect")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_reg"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build all condition configs and their corpora
    # We need separate corpora per condition since we're modifying block text
    condition_corpora: dict[str, PromptCorpus] = {}
    configs: list[AblationConfig] = []
    constrained = [b.id for b in base_corpus.blocks if b.id not in FREE_BLOCKS]

    for cond_name, cond_desc, tone_action, task_action in CONDITIONS:
        corpus = build_condition_corpus(base_corpus, tone_action, task_action)
        condition_corpora[cond_name] = corpus

        # All blocks in the (possibly modified) corpus are present.
        # For ablation, the block was already removed from the corpus,
        # so it won't appear in present_blocks — no need for absent_blocks.
        present = [b.id for b in corpus.blocks]
        absent = []

        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",  # All conditions run as "baseline" phase
            present_blocks=present,
            absent_blocks=absent,
            metadata={
                "condition": cond_name,
                "description": cond_desc,
                "tone_action": tone_action,
                "task_action": task_action,
            },
        ))

    # Save condition design for reproducibility
    design = {
        "experiment": "e-reg",
        "date": "2026-03-24",
        "hypotheses": {
            "H1_register": "Declarative rewriting recovers adherence; intensification worsens it",
            "H2_semantic": "Rewriting has no effect; the concept of conciseness itself causes suppression",
        },
        "conditions": [
            {
                "name": name,
                "description": desc,
                "tone_concise": tone,
                "use_task_for_search": task,
            }
            for name, desc, tone, task in CONDITIONS
        ],
        "rewrites": {
            "tone_concise_declarative": TONE_CONCISE_DECLARATIVE,
            "tone_concise_intensified": TONE_CONCISE_INTENSIFIED,
            "use_task_declarative": USE_TASK_DECLARATIVE,
        },
    }
    with open(output_dir / "e_reg_design.json", "w") as f:
        json.dump(design, f, indent=2)
    print(f"\n  Design saved: {output_dir / 'e_reg_design.json'}")

    # Run each model
    for model_key in models:
        model_id = MODEL_MAP[model_key]
        print(f"\n{'='*60}")
        print(f"  Model: {model_key} ({model_id})")
        print(f"{'='*60}")

        client = make_client("e-reg")
        from arbiter.llm_caller import LLMCaller
        caller = LLMCaller(client, model_id)
        runner = AblationRunner(caller=caller)

        run_id = f"e-reg-{model_key}-{uuid.uuid4().hex[:8]}"
        run = AblationRun(
            id=run_id,
            configs=configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "experiment": "e-reg",
                "model": model_key,
                "model_id": model_id,
            },
        )

        def progress(done, total):
            pct = 100 * done / total if total else 0
            print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

        # Run each condition separately since they use different corpora
        for config in configs:
            cond_name = config.id
            corpus = condition_corpora[cond_name]

            print(f"\n  Condition: {cond_name}")

            # Create a single-config run for this condition
            cond_run = AblationRun(
                id=f"{run_id}-{cond_name}",
                configs=[config],
                battery=battery,
                models=[model_id],
                trials_per_probe=args.trials,
                temperature=0.0,
                metadata={
                    "experiment": "e-reg",
                    "condition": cond_name,
                    "model": model_key,
                    "model_id": model_id,
                },
            )

            try:
                asyncio.run(runner.run_phase(
                    cond_run, "baseline", corpus=corpus,
                    concurrency=args.concurrency, progress_callback=progress,
                ))
                print()
            except KeyboardInterrupt:
                print("\n\nInterrupted. Saving partial results...")
                break
            except Exception as e:
                print(f"\n  Error in {cond_name}: {e}")
                continue

            # Merge results into the main run
            run.results.extend(cond_run.results)

            # Quick inline summary for this condition
            search_scores = [
                r.score for r in cond_run.results
                if r.probe_id == "probe-use-task-for-search-01"
            ]
            concise_scores = [
                r.score for r in cond_run.results
                if r.probe_id == "probe-concise-01"
            ]
            if search_scores:
                print(f"    use-task-for-search: {statistics.mean(search_scores):.3f}")
            if concise_scores:
                print(f"    concise: {statistics.mean(concise_scores):.3f}")

        # Save the complete run
        save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
        print(f"\n  Saved: {save_path} ({len(run.results)} results)")


# ── Analysis ──────────────────────────────────────────────────────────

def compare(args):
    """Analyze E-REG results."""
    output_dir = project_root / "data" / "ablation" / "e_reg"

    if not output_dir.exists():
        print("No E-REG results found. Run the experiment first.")
        return

    run_files = sorted(output_dir.glob("run_e-reg-*.json"))
    if not run_files:
        print("No result files found.")
        return

    print("E-REG: Register Rewriting Analysis")
    print("=" * 80)

    # Primary probes of interest
    primary_probes = {
        "probe-use-task-for-search-01": "use-task-for-search",
        "probe-concise-01": "concise",
    }

    for run_file in run_files:
        run = load_run(str(run_file))
        model = run.metadata.get("model", "unknown")
        print(f"\n{'─'*60}")
        print(f"  Model: {model} ({run.metadata.get('model_id', '?')})")
        print(f"  Results: {len(run.results)}")
        print(f"{'─'*60}")

        # Group results by condition
        by_condition: dict[str, list] = defaultdict(list)
        for r in run.results:
            by_condition[r.config_id].append(r)

        # ── Primary analysis: target probe ──
        print(f"\n  PRIMARY: use-task-for-search adherence (the suppression target)")
        print(f"  {'Condition':<18} {'Mean':>8} {'Raw scores'}")
        print(f"  {'-'*55}")

        condition_scores: dict[str, float] = {}
        for cond_name, _, _, _ in CONDITIONS:
            results = by_condition.get(cond_name, [])
            search_results = [r for r in results if r.probe_id == "probe-use-task-for-search-01"]
            if search_results:
                scores = [r.score for r in search_results]
                mean = statistics.mean(scores)
                condition_scores[cond_name] = mean
                print(f"  {cond_name:<18} {mean:>8.3f}  {[f'{s:.2f}' for s in scores]}")
            else:
                print(f"  {cond_name:<18}     ---  (no data)")

        # ── Hypothesis test ──
        baseline = condition_scores.get("baseline")
        ablation = condition_scores.get("ablation")
        decl_tone = condition_scores.get("decl-tone")
        decl_both = condition_scores.get("decl-both")
        intensified = condition_scores.get("intensified")

        if baseline is not None:
            print(f"\n  HYPOTHESIS TEST:")
            if ablation is not None:
                print(f"    Phase 0 replication: {baseline:.3f} → {ablation:.3f} "
                      f"(Δ={ablation - baseline:+.3f})")
            if decl_tone is not None:
                recovery = decl_tone - baseline
                pct = (recovery / (1.0 - baseline) * 100) if baseline < 1.0 else 0
                print(f"    Declarative tone:    {baseline:.3f} → {decl_tone:.3f} "
                      f"(Δ={recovery:+.3f}, {pct:.0f}% of gap recovered)")
                if decl_tone > 0.8:
                    print(f"    → H1 (register): SUPPORTED — declarative rewriting recovers adherence")
                elif decl_tone < 0.35:
                    print(f"    → H2 (semantic): SUPPORTED — rewriting doesn't help")
                else:
                    print(f"    → MIXED — partial recovery suggests both mechanisms")
            if decl_both is not None:
                print(f"    Both declarative:    {baseline:.3f} → {decl_both:.3f} "
                      f"(Δ={decl_both - baseline:+.3f})")
            if intensified is not None:
                print(f"    Intensified:         {baseline:.3f} → {intensified:.3f} "
                      f"(Δ={intensified - baseline:+.3f})")
                if intensified < baseline - 0.05:
                    print(f"    → Intensification WORSENS suppression (supports register theory)")
                elif intensified > baseline + 0.05:
                    print(f"    → Intensification IMPROVES — unexpected! Imperative clarity helps?")
                else:
                    print(f"    → Intensification has no effect (supports semantic theory)")

        # ── Conciseness check ──
        print(f"\n  CONTROL: concise probe (verify instruction still works)")
        print(f"  {'Condition':<18} {'Mean':>8}")
        print(f"  {'-'*30}")
        for cond_name, _, _, _ in CONDITIONS:
            results = by_condition.get(cond_name, [])
            concise_results = [r for r in results if r.probe_id == "probe-concise-01"]
            if concise_results:
                scores = [r.score for r in concise_results]
                print(f"  {cond_name:<18} {statistics.mean(scores):>8.3f}")

        # ── Spillover: all probes ──
        print(f"\n  SPILLOVER: all probes by condition")
        all_probes = sorted(set(r.probe_id for r in run.results))
        header = f"  {'Probe':<35}" + "".join(f" {c[0]:<12}" for c in CONDITIONS)
        print(header)
        print(f"  {'-'*len(header)}")

        for pid in all_probes:
            row = f"  {pid:<35}"
            for cond_name, _, _, _ in CONDITIONS:
                results = [r for r in by_condition.get(cond_name, []) if r.probe_id == pid]
                if results:
                    mean = statistics.mean([r.score for r in results])
                    row += f" {mean:<12.3f}"
                else:
                    row += f" {'---':<12}"
            print(row)

        # ── Mean across all probes (excluding target) ──
        print(f"\n  GLOBAL EFFECT: mean adherence excluding target probes")
        for cond_name, _, _, _ in CONDITIONS:
            results = [
                r for r in by_condition.get(cond_name, [])
                if r.probe_id not in primary_probes
            ]
            if results:
                mean = statistics.mean([r.score for r in results])
                print(f"    {cond_name:<18} {mean:.3f}")


def main():
    parser = argparse.ArgumentParser(description="E-REG: Register Rewriting")
    parser.add_argument(
        "--model", action="append", choices=list(MODEL_MAP.keys()),
        help="Model(s) to test (repeatable; default: haiku only)",
    )
    parser.add_argument("--trials", type=int, default=3, help="Trials per probe")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without running")
    parser.add_argument("--compare", action="store_true", help="Analyze existing results")
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
