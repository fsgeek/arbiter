#!/usr/bin/env python3
"""
Session 19 experiment: E-TOPO — Topology Inversion Rewrite Test

Tests whether declarative rewriting of the three strongest topology-
inverting blocks fixes the cooperative→competitive inversion in Spanish.

Prediction: If imperative-mode interference causes the topology inversion,
declarative rewrites should shift Spanish pairwise topology toward
cooperative (negative Δ, removing blocks hurts).

Design:
  - Rewrite 3 blocks (proactive-agents, use-task-for-search, todowrite)
    from imperative to declarative in English and Spanish
  - Run Phase 1 pairwise on Spanish with modified corpus (Haiku)
  - Compare topology direction against original E-PAIR-ES results

Usage:
    python scripts/run_topology_rewrite_test.py --dry-run
    python scripts/run_topology_rewrite_test.py
    python scripts/run_topology_rewrite_test.py --compare
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import uuid
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.battery import load_battery
from arbiter.ablation.configuration import AblationConfig, build_baseline_config, build_phase1_configs
from arbiter.ablation.covering_array import generate_covering_array
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

# ── Model and block constants (from run_fragility_experiments.py) ─────

MODEL_MAP = {
    "haiku": "anthropic/claude-haiku-4-5",
}

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

# ── Declarative rewrites ─────────────────────────────────────────────
#
# Original: imperative register ("You should...", "Use X...", "Do Y...")
# Rewrite:  declarative register ("X is...", "Status: enabled", factual)
#
# The semantic content is preserved. Only the speech act changes:
# command → description.

REWRITES = {
    "claude-code/tool-policy-proactive-agents": {
        "en": (
            "Task tool with specialized agents:\n"
            "- Status: available for all tasks matching an agent's description\n"
            "- Activation: proactive (no user request required)\n"
            "- Selection: based on match between task and agent description"
        ),
        "es": (
            "Herramienta Task con agentes especializados:\n"
            "- Estado: disponible para todas las tareas que coincidan con la descripción de un agente\n"
            "- Activación: proactiva (no requiere solicitud del usuario)\n"
            "- Selección: basada en la coincidencia entre tarea y descripción del agente"
        ),
    },
    "claude-code/tool-policy-use-task-for-search": {
        "en": (
            "File search tool preference:\n"
            "- Preferred tool: Task tool\n"
            "- Reason: reduces context window usage\n"
            "- Applies to: all file search operations"
        ),
        "es": (
            "Preferencia de herramienta para búsqueda de archivos:\n"
            "- Herramienta preferida: herramienta Task\n"
            "- Razón: reduce el uso de la ventana de contexto\n"
            "- Aplica a: todas las operaciones de búsqueda de archivos"
        ),
    },
    "claude-code/task-management-todowrite": {
        "en": (
            "TodoWrite tool status and requirements:\n"
            "- Usage frequency: very high (required for all task tracking)\n"
            "- Planning: required for breaking complex tasks into steps\n"
            "- Completion marking: required immediately upon task completion (no batching)\n"
            "- User visibility: TodoWrite is the primary mechanism for progress reporting\n"
            "- Omission consequence: important tasks forgotten (unacceptable)"
        ),
        "es": (
            "Estado y requisitos de la herramienta TodoWrite:\n"
            "- Frecuencia de uso: muy alta (requerida para todo el seguimiento de tareas)\n"
            "- Planificación: requerida para dividir tareas complejas en pasos\n"
            "- Marcado de finalización: requerido inmediatamente al completar una tarea (sin agrupar)\n"
            "- Visibilidad del usuario: TodoWrite es el mecanismo principal para informar del progreso\n"
            "- Consecuencia de omisión: tareas importantes olvidadas (inaceptable)"
        ),
    },
}


# ── Corpus manipulation ──────────────────────────────────────────────

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


def apply_rewrites(corpus: PromptCorpus, lang: str) -> PromptCorpus:
    """Apply declarative rewrites to the corpus."""
    new_blocks = []
    rewrites_applied = 0
    for b in corpus.blocks:
        if b.id in REWRITES and lang in REWRITES[b.id]:
            new_b = b.model_copy(update={"text": REWRITES[b.id][lang]})
            new_blocks.append(new_b)
            rewrites_applied += 1
        else:
            new_blocks.append(b)
    print(f"  Applied {rewrites_applied} declarative rewrites")
    return PromptCorpus(
        name=corpus.name + "-declarative-topo",
        source_file=corpus.source_file,
        blocks=new_blocks,
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
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )


# ── Main experiment ──────────────────────────────────────────────────

def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)

    lang = "es"
    model_key = "haiku"
    model_id = MODEL_MAP[model_key]

    print(f"\nE-TOPO: Topology Inversion Rewrite Test")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Language: {lang} (Spanish)")
    print(f"  Model: {model_key} ({model_id})")

    # Load and modify corpus
    corpus = load_corpus(corpus_path_for_lang(lang))
    corpus = apply_rewrites(corpus, lang)

    # Generate covering array (same structure as E-PAIR-ES)
    constrained = [b.id for b in corpus.blocks if b.id not in FREE_BLOCKS]
    n_free = len(FREE_BLOCKS)
    ca = generate_covering_array(n_free, strength=2)
    print(f"  Covering array: {len(ca)} rows × {n_free} columns")

    configs = build_phase1_configs(corpus, FREE_BLOCKS, constrained, ca)
    baseline = build_baseline_config(corpus, FREE_BLOCKS, constrained)
    configs.insert(0, baseline)

    n_calls = len(configs) * len(battery.probes) * args.trials
    est_cost = n_calls * 0.001
    print(f"  Configs: {len(configs)} ({len(configs)-1} covering array + 1 baseline)")
    print(f"  Total calls: {n_calls}")
    print(f"  Estimated cost: ${est_cost:.2f}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_topo"
    output_dir.mkdir(parents=True, exist_ok=True)

    client = make_client("e-topo")
    from arbiter.llm_caller import LLMCaller
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-topo-es-{model_key}-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-topo",
            "language": lang,
            "model": model_key,
            "model_id": model_id,
            "rewrites": list(REWRITES.keys()),
        },
    )

    # Save covering array
    ca_path = output_dir / f"phase1_covering_array_topo_{model_key}.json"
    ca_data = [{"id": c.id, "present": c.present_blocks, "absent": c.absent_blocks} for c in configs]
    with open(ca_path, "w") as f:
        json.dump(ca_data, f, indent=2)

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    # Set phases
    for config in configs:
        if config.id != "baseline":
            config.phase = "phase1"

    # Run baseline
    print(f"\n  Running baseline...")
    try:
        asyncio.run(runner.run_phase(
            run, "baseline", corpus=corpus,
            concurrency=5, progress_callback=progress,
        ))
        print()
    except Exception as e:
        print(f"\n  Baseline error: {e}")

    # Run Phase 1
    print(f"  Running Phase 1 ({len(configs)-1} configs)...")
    try:
        asyncio.run(runner.run_phase(
            run, "phase1", corpus=corpus,
            concurrency=5, progress_callback=progress,
        ))
        print()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving partial results...")
    except Exception as e:
        print(f"\n\nError: {e}. Saving partial results...")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare E-TOPO results against original E-PAIR-ES."""

    topo_dir = project_root / "data" / "ablation" / "e_topo"
    pair_dir = project_root / "data" / "ablation" / "e_pair_es"

    if not topo_dir.exists():
        print("No E-TOPO results found. Run the experiment first.")
        return

    # Load results
    topo_file = list(topo_dir.glob("run_e-topo-*.json"))
    pair_file = list(pair_dir.glob("run_e-pair-es-*.json"))

    if not topo_file or not pair_file:
        print("Missing result files.")
        return

    topo_data = load_run(str(topo_file[0]))
    pair_data = load_run(str(pair_file[0]))

    # Compare per-probe: baseline vs phase1 delta for each
    target_probes = [
        "probe-proactive-agents-01",
        "probe-use-task-for-search-01",
        "probe-todowrite-01",
    ]

    print("E-TOPO: Topology Inversion Rewrite Comparison")
    print("=" * 80)
    print()
    print(f"{'Probe':<35} {'Orig ES Δ':>10} {'Decl ES Δ':>10} {'Shift':>10} {'Direction':>12}")
    print("-" * 80)

    for dataset, label in [(pair_data, "orig"), (topo_data, "decl")]:
        pass  # just structure

    all_orig_deltas = []
    all_decl_deltas = []

    # Get all probe IDs
    probe_ids = set()
    for r in pair_data.results:
        probe_ids.add(r.probe_id)

    for pid in sorted(probe_ids):
        # Original (imperative) Spanish pairwise
        orig_baseline = [r.score for r in pair_data.results if r.probe_id == pid and r.config_id == "baseline"]
        orig_phase1 = [r.score for r in pair_data.results if r.probe_id == pid and r.config_id != "baseline"]

        # Declarative Spanish pairwise
        decl_baseline = [r.score for r in topo_data.results if r.probe_id == pid and r.config_id == "baseline"]
        decl_phase1 = [r.score for r in topo_data.results if r.probe_id == pid and r.config_id != "baseline"]

        if not all([orig_baseline, orig_phase1, decl_baseline, decl_phase1]):
            continue

        orig_delta = statistics.mean(orig_phase1) - statistics.mean(orig_baseline)
        decl_delta = statistics.mean(decl_phase1) - statistics.mean(decl_baseline)
        shift = decl_delta - orig_delta

        is_target = pid in target_probes
        marker = " <<<" if is_target else ""

        # Direction interpretation
        if orig_delta > 0 and decl_delta < 0:
            direction = "FIXED"
        elif orig_delta > 0 and decl_delta > 0 and decl_delta < orig_delta:
            direction = "reduced"
        elif orig_delta < 0 and decl_delta < 0:
            direction = "stable"
        else:
            direction = ""

        print(f"{pid:<35} {orig_delta:>+10.3f} {decl_delta:>+10.3f} {shift:>+10.3f} {direction:>12}{marker}")

        all_orig_deltas.append(orig_delta)
        all_decl_deltas.append(decl_delta)

    print()
    print(f"Overall topology: original={statistics.mean(all_orig_deltas):+.3f}  declarative={statistics.mean(all_decl_deltas):+.3f}")

    orig_competitive = sum(1 for d in all_orig_deltas if d > 0)
    decl_competitive = sum(1 for d in all_decl_deltas if d > 0)
    print(f"Competitive probes (Δ>0): original={orig_competitive}/{len(all_orig_deltas)}  declarative={decl_competitive}/{len(all_decl_deltas)}")

    # Target probes specifically
    print()
    print("Target probes (rewritten blocks):")
    for pid in target_probes:
        orig_baseline = [r.score for r in pair_data.results if r.probe_id == pid and r.config_id == "baseline"]
        orig_phase1 = [r.score for r in pair_data.results if r.probe_id == pid and r.config_id != "baseline"]
        decl_baseline = [r.score for r in topo_data.results if r.probe_id == pid and r.config_id == "baseline"]
        decl_phase1 = [r.score for r in topo_data.results if r.probe_id == pid and r.config_id != "baseline"]

        if all([orig_baseline, orig_phase1, decl_baseline, decl_phase1]):
            orig_d = statistics.mean(orig_phase1) - statistics.mean(orig_baseline)
            decl_d = statistics.mean(decl_phase1) - statistics.mean(decl_baseline)
            print(f"  {pid}: {orig_d:+.3f} → {decl_d:+.3f} ({'FIXED' if orig_d > 0 and decl_d < 0 else 'shifted' if decl_d < orig_d else 'no change'})")


def main():
    parser = argparse.ArgumentParser(description="E-TOPO: Topology inversion rewrite test")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without running")
    parser.add_argument("--compare", action="store_true", help="Compare results against E-PAIR-ES")
    parser.add_argument("--trials", type=int, default=3, help="Trials per probe")
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
