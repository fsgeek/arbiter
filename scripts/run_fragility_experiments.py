#!/usr/bin/env python3
"""
Session 18 experiments: Testing mechanisms of cross-linguistic fragility.

Experiment 1 (E-PROC): Procedural Simplification
  Tests whether procedural encoding causes cross-linguistic fragility.
  Rewrites commit-restrictions from procedural to declarative form.
  Prediction: declarative form will have lower cross-linguistic variance.

Experiment 2 (E-DENSE): Information Density / Padding
  Tests whether prompt compression drives inter-model agreement.
  Pads Mandarin corpus blocks with neutral filler to match English length.
  Prediction: padded Mandarin will show lower inter-model agreement.

Experiment 3 (E-PAIR-ES): Phase 1 Pairwise on Spanish
  Tests whether the topology inversion (cooperative → competitive)
  holds for pairwise interactions, not just main effects.

Usage:
    python scripts/run_fragility_experiments.py --experiment proc --dry-run
    python scripts/run_fragility_experiments.py --experiment proc --model haiku
    python scripts/run_fragility_experiments.py --experiment dense --model haiku
    python scripts/run_fragility_experiments.py --experiment pair-es --model haiku
    python scripts/run_fragility_experiments.py --compare proc
"""

import argparse
import asyncio
import copy
import json
import os
import statistics
import sys
import uuid
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.battery import load_battery
from arbiter.ablation.configuration import AblationConfig, build_baseline_config
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

# ── Shared constants ─────────────────────────────────────────────────

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

LANGUAGES = ["en", "zh", "fr", "es"]

# ── Corpus loading ───────────────────────────────────────────────────

def corpus_path_for_lang(lang: str) -> Path:
    base = project_root / "data" / "prompts" / "claude-code"
    if lang == "en":
        return base / "v2.1.50_blocks.json"
    return base / f"v2.1.50_blocks_{lang}.json"


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


def make_client(experiment_id: str):
    """Create OpenRouter client with experiment-specific labeling."""
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
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )


def run_single_baseline(
    experiment_id: str,
    model_key: str,
    lang: str,
    corpus: PromptCorpus,
    battery,
    output_dir: Path,
    trials: int = 3,
    concurrency: int = 5,
    variant: str = "",
):
    """Run a single baseline experiment."""
    from arbiter.llm_caller import LLMCaller

    model_id = MODEL_MAP[model_key]
    client = make_client(experiment_id)
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]
    config = build_baseline_config(corpus, FREE_BLOCKS, constrained)

    suffix = f"-{variant}" if variant else ""
    run_id = f"{experiment_id}-{lang}-{model_key}{suffix}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=[config],
        battery=battery,
        models=[model_id],
        trials_per_probe=trials,
        temperature=0.0,
        metadata={
            "experiment": experiment_id,
            "language": lang,
            "model": model_key,
            "model_id": model_id,
            "variant": variant,
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    print(f"  Running {experiment_id} / {lang} / {model_key}{f' / {variant}' if variant else ''}")
    print(f"  Model: {model_id}")
    print(f"  API label: arbiter-{experiment_id}")

    try:
        asyncio.run(runner.run_phase(
            run, "baseline", corpus=corpus,
            concurrency=concurrency, progress_callback=progress,
        ))
        print()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving partial results...")
    except Exception as e:
        print(f"\n\nError: {e}. Saving partial results...")

    output_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"  Saved: {save_path} ({len(run.results)} results)")

    if run.results:
        scores = [r.score for r in run.results]
        print(f"  Mean adherence: {statistics.mean(scores):.3f}")

    return run


# ── Experiment 1: Procedural Simplification ──────────────────────────

# Alternative rewrites of commit-restrictions
COMMIT_RESTRICTIONS_DECLARATIVE = {
    "en": (
        "During commit operations, the following tools and commands are unavailable:\n"
        "- TodoWrite tool: disabled\n"
        "- Task tool: disabled\n"
        "- File reading/exploration commands (except git): disabled\n"
        "- git push: disabled unless user explicitly requests it\n"
        "- git -i (interactive) flag: disabled\n"
        "- git rebase --no-edit: disabled\n"
        "- Empty commits: disabled\n"
        "Commit messages must use HEREDOC format."
    ),
    "zh": (
        "在提交操作期间，以下工具和命令不可用：\n"
        "- TodoWrite 工具：已禁用\n"
        "- Task 工具：已禁用\n"
        "- 文件读取/浏览命令（git 除外）：已禁用\n"
        "- git push：除非用户明确要求，否则已禁用\n"
        "- git -i（交互式）标志：已禁用\n"
        "- git rebase --no-edit：已禁用\n"
        "- 空提交：已禁用\n"
        "提交消息必须使用 HEREDOC 格式。"
    ),
    "fr": (
        "Pendant les opérations de commit, les outils et commandes suivants sont indisponibles :\n"
        "- Outil TodoWrite : désactivé\n"
        "- Outil Task : désactivé\n"
        "- Commandes de lecture/exploration de fichiers (sauf git) : désactivées\n"
        "- git push : désactivé sauf demande explicite de l'utilisateur\n"
        "- Option git -i (interactif) : désactivée\n"
        "- git rebase --no-edit : désactivé\n"
        "- Commits vides : désactivés\n"
        "Les messages de commit doivent utiliser le format HEREDOC."
    ),
    "es": (
        "Durante las operaciones de commit, las siguientes herramientas y comandos no están disponibles:\n"
        "- Herramienta TodoWrite: deshabilitada\n"
        "- Herramienta Task: deshabilitada\n"
        "- Comandos de lectura/exploración de archivos (excepto git): deshabilitados\n"
        "- git push: deshabilitado a menos que el usuario lo solicite explícitamente\n"
        "- Opción git -i (interactivo): deshabilitada\n"
        "- git rebase --no-edit: deshabilitado\n"
        "- Commits vacíos: deshabilitados\n"
        "Los mensajes de commit deben usar formato HEREDOC."
    ),
}

COMMIT_RESTRICTIONS_SCOPED = {
    "en": (
        "[COMMIT MODE RESTRICTIONS]\n"
        "When performing git commit operations, these restrictions apply:\n"
        "  Disabled: TodoWrite, Task, file read/explore (non-git), git push (unless asked), git -i, git rebase --no-edit, empty commits\n"
        "  Required: HEREDOC commit messages\n"
        "[END COMMIT MODE RESTRICTIONS]"
    ),
    "zh": (
        "[提交模式限制]\n"
        "执行 git 提交操作时，以下限制适用：\n"
        "  已禁用：TodoWrite、Task、文件读取/浏览（非 git）、git push（除非被要求）、git -i、git rebase --no-edit、空提交\n"
        "  必需：HEREDOC 提交消息\n"
        "[提交模式限制结束]"
    ),
    "fr": (
        "[RESTRICTIONS MODE COMMIT]\n"
        "Lors des opérations de commit git, ces restrictions s'appliquent :\n"
        "  Désactivés : TodoWrite, Task, lecture/exploration fichiers (non-git), git push (sauf demande), git -i, git rebase --no-edit, commits vides\n"
        "  Requis : messages de commit HEREDOC\n"
        "[FIN RESTRICTIONS MODE COMMIT]"
    ),
    "es": (
        "[RESTRICCIONES MODO COMMIT]\n"
        "Al realizar operaciones de commit git, se aplican estas restricciones:\n"
        "  Deshabilitados: TodoWrite, Task, lectura/exploración archivos (no-git), git push (salvo solicitud), git -i, git rebase --no-edit, commits vacíos\n"
        "  Requerido: mensajes de commit HEREDOC\n"
        "[FIN RESTRICCIONES MODO COMMIT]"
    ),
}


def modify_corpus_block(corpus: PromptCorpus, block_id: str, new_text: str) -> PromptCorpus:
    """Create a new corpus with one block's text replaced."""
    new_blocks = []
    for b in corpus.blocks:
        if b.id == block_id:
            new_b = b.model_copy(update={"text": new_text})
            new_blocks.append(new_b)
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=corpus.name,
        source_file=corpus.source_file,
        blocks=new_blocks,
    )


def run_experiment_proc(args):
    """E-PROC: Procedural simplification of commit-restrictions."""
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)

    # Only run the commit-restrictions probe to save cost
    # Actually, run all probes — the other blocks are unchanged,
    # so they serve as a within-experiment control
    print(f"\nE-PROC: Procedural Simplification")
    print(f"  Battery: {len(battery.probes)} probes")

    languages = [args.lang] if args.lang else LANGUAGES
    models = [args.model] if args.model else list(MODEL_MAP.keys())

    # Three variants: original (already have data), declarative, scoped
    variants = {
        "declarative": COMMIT_RESTRICTIONS_DECLARATIVE,
        "scoped": COMMIT_RESTRICTIONS_SCOPED,
    }

    # Cost estimate
    n_calls = len(models) * len(languages) * len(battery.probes) * args.trials * len(variants)
    est_cost = n_calls * 0.001  # conservative average
    print(f"  Plan: {len(variants)} variants × {len(models)} models × {len(languages)} langs × {len(battery.probes)} probes × {args.trials} trials")
    print(f"  Total calls: {n_calls}")
    print(f"  Estimated cost: ${est_cost:.2f}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_proc"

    for variant_name, variant_texts in variants.items():
        for model_key in models:
            for lang in languages:
                corpus = load_corpus(corpus_path_for_lang(lang))
                new_text = variant_texts[lang]
                corpus = modify_corpus_block(
                    corpus,
                    "claude-code/tool-bash-commit-restrictions",
                    new_text,
                )
                run_single_baseline(
                    experiment_id=f"e-proc-{variant_name}",
                    model_key=model_key,
                    lang=lang,
                    corpus=corpus,
                    battery=battery,
                    output_dir=output_dir,
                    trials=args.trials,
                    concurrency=args.concurrency,
                    variant=variant_name,
                )


# ── Experiment 2: Information Density Padding ────────────────────────

# Neutral filler text that adds length without semantic content
PADDING_TEMPLATE_ZH = (
    "（以下为格式填充内容，请忽略此段落。"
    "此文本仅用于标准化文档长度，不包含任何指令或信息。"
    "请继续按照上述规则行事。）"
)  # ~80 chars of semantically neutral padding


def create_padded_mandarin_corpus() -> PromptCorpus:
    """Create a Mandarin corpus padded to approximately English length.

    For each block, appends neutral filler to bring the character count
    to roughly match the English equivalent.
    """
    en_corpus_path = corpus_path_for_lang("en")
    zh_corpus_path = corpus_path_for_lang("zh")

    with open(en_corpus_path) as f:
        en_data = json.load(f)
    with open(zh_corpus_path) as f:
        zh_data = json.load(f)

    # Build English length map
    en_lengths = {}
    for b in en_data["blocks"]:
        en_lengths[b["id"]] = len(b["text"])

    # Pad each Mandarin block
    padded_blocks = []
    total_padding = 0
    for b in zh_data["blocks"]:
        en_len = en_lengths.get(b["id"], len(b["text"]))
        zh_len = len(b["text"])
        deficit = en_len - zh_len

        text = b["text"]
        if deficit > len(PADDING_TEMPLATE_ZH):
            # Add padding repetitions
            n_reps = deficit // len(PADDING_TEMPLATE_ZH)
            padding = "\n" + "\n".join([PADDING_TEMPLATE_ZH] * n_reps)
            text = text + padding
            total_padding += len(padding)

        padded_blocks.append(PromptBlock(
            id=b["id"],
            source=b["source"],
            tier=b["tier"],
            category=b["category"],
            text=text,
            modality=b["modality"],
            scope=b["scope"],
            exports=b.get("exports", []),
            imports=b.get("imports", []),
            line_start=b.get("line_start", 0),
            line_end=b.get("line_end", 0),
        ))

    corpus = PromptCorpus(
        name=zh_data["name"] + "-padded",
        source_file=zh_data.get("source_file", "unknown"),
        blocks=padded_blocks,
    )

    original_len = sum(len(b["text"]) for b in zh_data["blocks"])
    padded_len = sum(len(b.text) for b in padded_blocks)
    en_total = sum(en_lengths.get(b["id"], 0) for b in zh_data["blocks"])
    print(f"  Padding: {original_len} → {padded_len} chars ({100*padded_len/en_total:.0f}% of English, was {100*original_len/en_total:.0f}%)")

    return corpus


def run_experiment_dense(args):
    """E-DENSE: Information density / padding test."""
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)

    print(f"\nE-DENSE: Information Density / Padding")
    print(f"  Battery: {len(battery.probes)} probes")

    models = [args.model] if args.model else list(MODEL_MAP.keys())

    n_calls = len(models) * len(battery.probes) * args.trials
    est_cost = n_calls * 0.001
    print(f"  Plan: {len(models)} models × {len(battery.probes)} probes × {args.trials} trials")
    print(f"  Total calls: {n_calls}")
    print(f"  Estimated cost: ${est_cost:.2f}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    corpus = create_padded_mandarin_corpus()
    output_dir = project_root / "data" / "ablation" / "e_dense"

    for model_key in models:
        run_single_baseline(
            experiment_id="e-dense-zh-padded",
            model_key=model_key,
            lang="zh",
            corpus=corpus,
            battery=battery,
            output_dir=output_dir,
            trials=args.trials,
            concurrency=args.concurrency,
            variant="padded",
        )


# ── Experiment 3: Phase 1 Pairwise on Spanish ───────────────────────

def run_experiment_pair_es(args):
    """E-PAIR-ES: Phase 1 pairwise ablation on Spanish corpus."""
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)

    print(f"\nE-PAIR-ES: Phase 1 Pairwise on Spanish")
    print(f"  Battery: {len(battery.probes)} probes")

    model_key = args.model or "haiku"
    model_id = MODEL_MAP[model_key]

    # Load Spanish corpus
    corpus = load_corpus(corpus_path_for_lang("es"))

    # Generate covering array for Phase 1 (pairwise)
    from arbiter.ablation.covering_array import generate_covering_array
    from arbiter.ablation.configuration import build_phase1_configs

    constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]

    # Generate 2-way covering array
    n_free = len(FREE_BLOCKS)
    ca = generate_covering_array(n_free, strength=2)
    print(f"  Covering array: {len(ca)} rows × {n_free} columns")

    # Build configs from covering array
    configs = build_phase1_configs(corpus, FREE_BLOCKS, constrained, ca)
    # Add baseline
    baseline = build_baseline_config(corpus, FREE_BLOCKS, constrained)
    configs.insert(0, baseline)

    n_calls = len(configs) * len(battery.probes) * args.trials
    est_cost = n_calls * 0.001
    print(f"  Configs: {len(configs)} ({len(configs)-1} covering array + 1 baseline)")
    print(f"  Plan: {len(configs)} configs × {len(battery.probes)} probes × {args.trials} trials")
    print(f"  Total calls: {n_calls}")
    print(f"  Estimated cost: ${est_cost:.2f}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_pair_es"
    output_dir.mkdir(parents=True, exist_ok=True)

    client = make_client("e-pair-es")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-pair-es-{model_key}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-pair-es",
            "language": "es",
            "model": model_key,
            "model_id": model_id,
        },
    )

    # Save the covering array for reproducibility
    ca_path = output_dir / f"phase1_covering_array_es_{model_key}.json"
    ca_data = [{"id": c.id, "present": c.present_blocks, "absent": c.absent_blocks} for c in configs]
    with open(ca_path, "w") as f:
        json.dump(ca_data, f, indent=2)
    print(f"  Covering array saved: {ca_path}")

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    # Run Phase 1 — all configs are labeled as "baseline" phase in the current system
    # So we need to set them appropriately
    for config in configs:
        if config.id != "baseline":
            config.phase = "phase1"

    # Run baseline first
    print(f"\n  Running baseline...")
    try:
        asyncio.run(runner.run_phase(
            run, "baseline", corpus=corpus,
            concurrency=args.concurrency, progress_callback=progress,
        ))
        print()
    except Exception as e:
        print(f"\n  Baseline error: {e}")

    # Then Phase 1
    print(f"  Running Phase 1 ({len(configs)-1} configs)...")
    try:
        asyncio.run(runner.run_phase(
            run, "phase1", corpus=corpus,
            concurrency=args.concurrency, progress_callback=progress,
        ))
        print()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving partial results...")
    except Exception as e:
        print(f"\n\nError: {e}. Saving partial results...")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"  Saved: {save_path} ({len(run.results)} results)")


# ── Comparison / Analysis ────────────────────────────────────────────

def compare_proc(args):
    """Compare E-PROC results against original baselines."""
    from collections import defaultdict

    proc_dir = project_root / "data" / "ablation" / "e_proc"
    orig_dir = project_root / "data" / "ablation" / "cross_linguistic"

    if not proc_dir.exists():
        print("No E-PROC results found. Run the experiment first.")
        return

    print("E-PROC: Procedural Simplification Comparison")
    print("=" * 72)

    # Load all results
    all_runs = {}  # (variant, model, lang) -> run

    # Original baselines
    for f in sorted(orig_dir.glob("run_xling-*.json")):
        run = load_run(str(f))
        lang = run.metadata.get("language", "?")
        model = run.metadata.get("model", "?")
        all_runs[("original", model, lang)] = run

    # E-PROC variants
    for f in sorted(proc_dir.glob("run_*.json")):
        run = load_run(str(f))
        variant = run.metadata.get("variant", "?")
        lang = run.metadata.get("language", "?")
        model = run.metadata.get("model", "?")
        all_runs[(variant, model, lang)] = run

    # Extract commit-restrictions scores
    probe_id = "probe-commit-restrictions-01"

    print(f"\nCommit-restrictions probe scores:")
    print(f"{'Variant':<15} {'Model':<10} {'en':>6} {'zh':>6} {'fr':>6} {'es':>6} {'Var':>8} {'Range':>6}")
    print("-" * 72)

    variant_variances = defaultdict(list)

    for variant in ["original", "declarative", "scoped"]:
        for model in sorted(MODEL_MAP.keys()):
            scores = {}
            for lang in LANGUAGES:
                key = (variant, model, lang)
                if key not in all_runs:
                    continue
                run = all_runs[key]
                probe_results = [r for r in run.results if r.probe_id == probe_id]
                if probe_results:
                    scores[lang] = statistics.mean([r.score for r in probe_results])

            if len(scores) >= 2:
                vals = list(scores.values())
                var = statistics.variance(vals)
                rng = max(vals) - min(vals)
                variant_variances[variant].append(var)

                scores_str = "  ".join(f"{scores.get(l, -1):>5.2f}" if l in scores else f"{'--':>5}" for l in LANGUAGES)
                print(f"{variant:<15} {model:<10} {scores_str} {var:>8.4f} {rng:>6.3f}")

    # Summary
    print(f"\nMean cross-linguistic variance by variant:")
    for variant in ["original", "declarative", "scoped"]:
        if variant in variant_variances:
            vals = variant_variances[variant]
            print(f"  {variant:<15}: {statistics.mean(vals):.4f} (n={len(vals)})")

    # Permutation test: original vs declarative
    if "original" in variant_variances and "declarative" in variant_variances:
        import random
        random.seed(42)

        orig = variant_variances["original"]
        decl = variant_variances["declarative"]
        observed = statistics.mean(orig) - statistics.mean(decl)

        all_vals = orig + decl
        n_orig = len(orig)
        n_perms = 100_000
        count = sum(1 for _ in range(n_perms)
                    if (random.shuffle(all_vals) or True) and
                    statistics.mean(all_vals[:n_orig]) - statistics.mean(all_vals[n_orig:]) >= observed)

        p = count / n_perms
        print(f"\n  Original vs Declarative: Δ={observed:.4f}, p={p:.5f}")


def main():
    parser = argparse.ArgumentParser(description="Session 18 fragility experiments")
    parser.add_argument("--experiment", "-e", choices=["proc", "dense", "pair-es"],
                        help="Experiment to run")
    parser.add_argument("--model", choices=list(MODEL_MAP.keys()),
                        help="Model to test (default: all)")
    parser.add_argument("--lang", choices=LANGUAGES,
                        help="Single language (default: all)")
    parser.add_argument("--trials", type=int, default=3,
                        help="Trials per probe (default: 3)")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="Max concurrent API calls")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without running")
    parser.add_argument("--compare", choices=["proc", "dense", "pair-es"],
                        help="Compare existing results")
    args = parser.parse_args()

    if args.compare:
        if args.compare == "proc":
            compare_proc(args)
        else:
            print(f"Compare for {args.compare} not yet implemented")
    elif args.experiment == "proc":
        run_experiment_proc(args)
    elif args.experiment == "dense":
        run_experiment_dense(args)
    elif args.experiment == "pair-es":
        run_experiment_pair_es(args)
    else:
        parser.print_help()
        print("\nEither --experiment (to run) or --compare (to analyze) is required.")


if __name__ == "__main__":
    main()
