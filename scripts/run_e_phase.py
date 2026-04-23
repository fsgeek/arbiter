#!/usr/bin/env python3
"""
E-PHASE: Phase Transition Mapping — Imperative Register Saturation

Tests whether imperative register effects have a critical threshold
(phase transition) or degrade smoothly (additive effects).

Background:
  Paper 3 showed declarative rewriting fixes topology inversion cross-
  linguistically. E-REG showed intra-lingual register effects are model-
  dependent. Neither varied the DOSE — how many imperative instructions
  can you stack before the system breaks?

Design:
  12 conditions with increasing imperative density (0→11 procedural blocks).
  At density=0, all 11 procedural blocks are rewritten to declarative.
  Each step adds one block back in its original imperative form, ordered
  by cross-linguistic variance (most fragile first).

  Phase A: Haiku only (most sensitive, cheapest). Scout for curve shape.
  Phase B: If discontinuity found, bracket with all 4 models.
           If smooth, 5-point subsample across all 4 models.

Predictions:
  Phase transition: adherence stable until density N, then collapses.
  Smooth/linear: adherence degrades monotonically with density.
  Threshold effect: step function at some critical density.

Usage:
    python scripts/run_e_phase.py --dry-run
    python scripts/run_e_phase.py                          # Phase A (Haiku)
    python scripts/run_e_phase.py --model haiku --model gemini  # specific models
    python scripts/run_e_phase.py --compare                # analyze results
    python scripts/run_e_phase.py --compare --plot         # with matplotlib
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
from arbiter.ablation.configuration import AblationConfig
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
    "sonnet": "anthropic/claude-sonnet-4-6",
    "gemini": "google/gemini-2.0-flash-001",
    "deepseek": "deepseek/deepseek-chat-v3-0324",
    "mistral": "mistralai/mistral-medium-3.1",
}

# ── Procedural blocks ordered by cross-linguistic variance ────────────
# Most fragile first — this determines the order blocks are added back
# to imperative as density increases.

PROCEDURAL_BLOCKS_ORDERED = [
    "claude-code/tool-bash-commit-restrictions",   # 0.1567
    "claude-code/tone-text-only-comms",            # 0.0834
    "claude-code/tool-policy-parallel-calls",      # 0.0760
    "claude-code/tool-policy-proactive-agents",    # 0.0731
    "claude-code/tool-policy-use-task-for-search", # 0.0607
    "claude-code/tool-policy-explore-agent",       # 0.0499
    "claude-code/tool-bash-pr-workflow",           # 0.0225
    "claude-code/tool-bash-commit-workflow",       # 0.0211
    "claude-code/task-management-todowrite",       # 0.0132
    "claude-code/doing-tasks-no-overengineering",  # 0.0093
    "claude-code/tool-policy-dedicated-tools",     # 0.0000
]

# ── Declarative rewrites for all 11 procedural blocks ─────────────────
#
# Each rewrite preserves the semantic content but changes the speech act
# from imperative ("Do X", "NEVER Y", "You should Z") to declarative
# ("X: enabled", "Y: not supported", fact-stating).
#
# Three rewrites reused from E-TOPO (proactive-agents, use-task-for-search,
# todowrite). Eight are new for this experiment.

DECLARATIVE_REWRITES = {
    "claude-code/tool-bash-commit-restrictions": (
        "Commit context tool restrictions:\n"
        "- Allowed tools: git bash commands only\n"
        "- Disallowed tools: TodoWrite, Task\n"
        "- Push policy: requires explicit user request\n"
        "- Git flags: -i flag unsupported; --no-edit unsupported for rebase\n"
        "- Empty commits: not created\n"
        "- Commit message format: HEREDOC"
    ),
    "claude-code/tone-text-only-comms": (
        "Communication channel: text output (displayed to user)\n"
        "Tool purpose: task completion only\n"
        "Communication via Bash/code comments: not supported"
    ),
    "claude-code/tool-policy-parallel-calls": (
        "Tool call parallelism:\n"
        "- Independent calls: parallel (in same response)\n"
        "- Dependent calls: sequential\n"
        "- Parameter values: must be known (no placeholders)"
    ),
    # From E-TOPO
    "claude-code/tool-policy-proactive-agents": (
        "Task tool with specialized agents:\n"
        "- Status: available for all tasks matching an agent's description\n"
        "- Activation: proactive (no user request required)\n"
        "- Selection: based on match between task and agent description"
    ),
    # From E-TOPO
    "claude-code/tool-policy-use-task-for-search": (
        "File search tool preference:\n"
        "- Preferred tool: Task tool\n"
        "- Reason: reduces context window usage\n"
        "- Applies to: all file search operations"
    ),
    "claude-code/tool-policy-explore-agent": (
        "Codebase exploration tool:\n"
        "- Deep research: Task tool with subagent_type=Explore\n"
        "- Simple/directed search: Glob or Grep directly\n"
        "- Explore agent speed: slower than direct tools\n"
        "- Threshold: use when >3 queries needed"
    ),
    "claude-code/tool-bash-pr-workflow": (
        "Pull request creation process:\n"
        "- Step 1: git status, git diff, remote tracking check, git log (parallel)\n"
        "- Step 2: analyze all commits, draft title (<70 chars) + summary\n"
        "- Step 3: create branch if needed, push with -u, gh pr create (HEREDOC body)\n"
        "- Disallowed tools: TodoWrite, Task\n"
        "- Output: PR URL"
    ),
    "claude-code/tool-bash-commit-workflow": (
        "Git commit process:\n"
        "- Step 1: git status, git diff, git log (parallel)\n"
        "- Step 2: analyze staged changes, draft message (1-2 sentences, no secrets)\n"
        "- Step 3: stage files, commit with Co-Authored-By, verify with git status\n"
        "- Hook failure: fix issue, create new commit (not amend)"
    ),
    # From E-TOPO
    "claude-code/task-management-todowrite": (
        "TodoWrite tool status and requirements:\n"
        "- Usage frequency: very high (required for all task tracking)\n"
        "- Planning: required for breaking complex tasks into steps\n"
        "- Completion marking: required immediately upon task completion (no batching)\n"
        "- User visibility: TodoWrite is the primary mechanism for progress reporting\n"
        "- Omission consequence: important tasks forgotten (unacceptable)"
    ),
    "claude-code/doing-tasks-no-overengineering": (
        "Code change scope: directly requested or clearly necessary changes only\n"
        "- Feature additions: only when requested\n"
        "- Error handling: system boundaries only (user input, external APIs)\n"
        "- Abstractions: minimum needed for current task\n"
        "- Comments/docstrings: only on changed code, only when logic non-obvious"
    ),
    "claude-code/tool-policy-dedicated-tools": (
        "Tool preference for file operations:\n"
        "- Read files: Read tool (not cat/head/tail)\n"
        "- Edit files: Edit tool (not sed/awk)\n"
        "- Create files: Write tool (not cat/heredoc/echo)\n"
        "- Bash: system commands and terminal operations only\n"
        "- Communication: text output only (not bash echo)"
    ),
}

assert len(DECLARATIVE_REWRITES) == len(PROCEDURAL_BLOCKS_ORDERED) == 11


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


def build_density_corpus(base_corpus: PromptCorpus, density: int) -> PromptCorpus:
    """Build a corpus with exactly `density` procedural blocks in imperative form.

    At density=0, all 11 procedural blocks are rewritten to declarative.
    At density=N, the first N blocks (ordered by cross-linguistic variance,
    most fragile first) are kept in their original imperative form.
    At density=11, the corpus is unchanged (all procedural blocks imperative).
    """
    # Which blocks stay imperative (original form)?
    imperative_blocks = set(PROCEDURAL_BLOCKS_ORDERED[:density])

    new_blocks = []
    for b in base_corpus.blocks:
        if b.id in DECLARATIVE_REWRITES and b.id not in imperative_blocks:
            # Rewrite to declarative
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)

    return PromptCorpus(
        name=f"{base_corpus.name}-density-{density}",
        source_file=base_corpus.source_file,
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

    # Determine which densities to test
    if args.densities:
        densities = sorted(set(int(d) for d in args.densities))
    else:
        densities = list(range(12))  # 0 through 11

    print(f"\nE-PHASE: Phase Transition Mapping")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Densities: {densities} ({len(densities)} conditions)")
    print(f"  Models: {', '.join(models)}")
    print(f"  Trials: {args.trials}")

    # Cost estimate
    n_calls = len(densities) * len(models) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(densities) * len(models) * n_judge * args.trials
    total_calls = n_calls + n_judge_calls
    est_cost = total_calls * 0.001
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total_calls}")
    print(f"  Estimated cost: ${est_cost:.2f}")

    print(f"\n  Density schedule (blocks added back to imperative):")
    for d in densities:
        if d == 0:
            print(f"    density={d:>2}  (all declarative)")
        elif d <= len(PROCEDURAL_BLOCKS_ORDERED):
            block = PROCEDURAL_BLOCKS_ORDERED[d-1]
            short = block.split("/")[-1]
            print(f"    density={d:>2}  + {short}")
        else:
            print(f"    density={d:>2}  (all imperative)")

    print(f"\n  Prediction:")
    print(f"    Phase transition: stable until density N, then collapse")
    print(f"    Smooth/linear:   monotonic degradation with density")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_phase"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save experiment design
    design = {
        "experiment": "e-phase",
        "date": "2026-03-28",
        "question": "Does imperative register saturation have a critical threshold (phase transition) or degrade smoothly?",
        "procedural_blocks_ordered": PROCEDURAL_BLOCKS_ORDERED,
        "ordering_criterion": "cross-linguistic variance (most fragile first)",
        "densities_tested": densities,
        "models": models,
        "trials": args.trials,
        "rewrites": DECLARATIVE_REWRITES,
        "predictions": {
            "phase_transition": "Adherence stable until density N, then collapses",
            "smooth_linear": "Adherence degrades monotonically with density",
            "threshold": "Step function at some critical density",
        },
    }
    with open(output_dir / "e_phase_design.json", "w") as f:
        json.dump(design, f, indent=2)
    print(f"\n  Design saved: {output_dir / 'e_phase_design.json'}")

    # Run each model
    for model_key in models:
        model_id = MODEL_MAP[model_key]
        print(f"\n{'='*60}")
        print(f"  Model: {model_key} ({model_id})")
        print(f"{'='*60}")

        client = make_client("e-phase")
        from arbiter.llm_caller import LLMCaller
        caller = LLMCaller(client, model_id)
        runner = AblationRunner(caller=caller)

        run_id = f"e-phase-{model_key}-{uuid.uuid4().hex[:8]}"

        # Build configs for all densities
        configs = []
        density_corpora: dict[int, PromptCorpus] = {}

        for density in densities:
            corpus = build_density_corpus(base_corpus, density)
            density_corpora[density] = corpus

            present = [b.id for b in corpus.blocks]
            configs.append(AblationConfig(
                id=f"density-{density:02d}",
                phase="baseline",
                present_blocks=present,
                absent_blocks=[],
                metadata={
                    "density": density,
                    "imperative_blocks": PROCEDURAL_BLOCKS_ORDERED[:density],
                    "declarative_blocks": PROCEDURAL_BLOCKS_ORDERED[density:],
                },
            ))

        run = AblationRun(
            id=run_id,
            configs=configs,
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={
                "experiment": "e-phase",
                "model": model_key,
                "model_id": model_id,
                "densities": densities,
            },
        )

        def progress(done, total):
            pct = 100 * done / total if total else 0
            print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

        # Run each density condition
        for config in configs:
            density = config.metadata["density"]
            corpus = density_corpora[density]

            if density == 0:
                label = "all declarative"
            elif density == 11:
                label = "all imperative (original)"
            else:
                label = f"+ {PROCEDURAL_BLOCKS_ORDERED[density-1].split('/')[-1]}"

            print(f"\n  Density {density:>2}: {label}")

            cond_run = AblationRun(
                id=f"{run_id}-d{density:02d}",
                configs=[config],
                battery=battery,
                models=[model_id],
                trials_per_probe=args.trials,
                temperature=0.0,
                metadata={
                    "experiment": "e-phase",
                    "density": density,
                    "model": model_key,
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
                run.results.extend(cond_run.results)
                break
            except Exception as e:
                print(f"\n  Error at density {density}: {e}")
                continue

            run.results.extend(cond_run.results)

            # Quick inline summary
            scores = [r.score for r in cond_run.results]
            if scores:
                mean = statistics.mean(scores)
                print(f"    Mean adherence: {mean:.3f}")

        # Save the complete run
        save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
        print(f"\n  Saved: {save_path} ({len(run.results)} results)")


# ── Analysis ──────────────────────────────────────────────────────────

def compare(args):
    """Analyze E-PHASE results: dose-response curve."""
    output_dir = project_root / "data" / "ablation" / "e_phase"

    if not output_dir.exists():
        print("No E-PHASE results found. Run the experiment first.")
        return

    run_files = sorted(output_dir.glob("run_e-phase-*.json"))
    if not run_files:
        print("No result files found.")
        return

    print("E-PHASE: Phase Transition Analysis")
    print("=" * 80)

    all_curves = {}  # model -> [(density, mean_adherence)]

    for run_file in run_files:
        run = load_run(str(run_file))
        model = run.metadata.get("model", "unknown")
        print(f"\n{'─'*60}")
        print(f"  Model: {model} ({run.metadata.get('model_id', '?')})")
        print(f"  Results: {len(run.results)}")
        print(f"{'─'*60}")

        # Group by density
        by_density: dict[int, list] = defaultdict(list)
        for r in run.results:
            # Extract density from config_id "density-NN"
            d = int(r.config_id.split("-")[1])
            by_density[d].append(r)

        # Dose-response curve
        print(f"\n  DOSE-RESPONSE: mean adherence by imperative density")
        print(f"  {'Density':>8} {'Mean':>8} {'StdDev':>8} {'N':>5}  {'Curve'}")
        print(f"  {'-'*60}")

        curve = []
        for d in sorted(by_density.keys()):
            scores = [r.score for r in by_density[d]]
            mean = statistics.mean(scores)
            sd = statistics.stdev(scores) if len(scores) > 1 else 0
            bar = "█" * int(mean * 40)
            curve.append((d, mean, sd))
            print(f"  {d:>8} {mean:>8.3f} {sd:>8.3f} {len(scores):>5}  {bar}")

        all_curves[model] = curve

        # Look for phase transition
        if len(curve) >= 3:
            means = [m for _, m, _ in curve]
            deltas = [means[i+1] - means[i] for i in range(len(means)-1)]

            # Find largest negative step
            if deltas:
                worst_idx = min(range(len(deltas)), key=lambda i: deltas[i])
                worst_delta = deltas[worst_idx]
                d_from = curve[worst_idx][0]
                d_to = curve[worst_idx + 1][0]

                print(f"\n  LARGEST DROP: density {d_from}→{d_to}, "
                      f"Δ={worst_delta:+.3f}")

                # Is it a phase transition? Compare worst step to mean step
                mean_delta = statistics.mean(deltas)
                if len(deltas) > 1:
                    sd_delta = statistics.stdev(deltas)
                    if sd_delta > 0:
                        z = (worst_delta - mean_delta) / sd_delta
                        print(f"  Mean step: {mean_delta:+.3f}, "
                              f"SD: {sd_delta:.3f}, "
                              f"Z-score of worst: {z:.1f}")
                        if abs(z) > 2:
                            print(f"  → POSSIBLE PHASE TRANSITION at density {d_to}")
                        else:
                            print(f"  → Smooth degradation (no outlier step)")

        # Per-probe dose-response for most interesting probes
        print(f"\n  PER-PROBE dose-response (probes with |range| > 0.2):")
        all_probes = sorted(set(r.probe_id for r in run.results))
        interesting = []

        for pid in all_probes:
            probe_curve = []
            for d in sorted(by_density.keys()):
                scores = [r.score for r in by_density[d] if r.probe_id == pid]
                if scores:
                    probe_curve.append((d, statistics.mean(scores)))
            if probe_curve:
                values = [m for _, m in probe_curve]
                probe_range = max(values) - min(values)
                if probe_range > 0.2:
                    interesting.append((pid, probe_curve, probe_range))

        interesting.sort(key=lambda x: -x[2])
        for pid, pc, pr in interesting[:10]:
            short = pid.replace("probe-", "").replace("-01", "")
            vals = " ".join(f"{m:.2f}" for _, m in pc)
            print(f"    {short:<30} range={pr:.2f}  [{vals}]")

    # Cross-model comparison if multiple models
    if len(all_curves) > 1:
        print(f"\n{'='*60}")
        print(f"  CROSS-MODEL COMPARISON")
        print(f"{'='*60}")
        all_densities = sorted(set(d for curve in all_curves.values() for d, _, _ in curve))
        header = f"  {'Density':>8}" + "".join(f" {m:>10}" for m in all_curves)
        print(header)
        print(f"  {'-'*len(header)}")
        for d in all_densities:
            row = f"  {d:>8}"
            for model, curve in all_curves.items():
                matching = [m for dd, m, _ in curve if dd == d]
                if matching:
                    row += f" {matching[0]:>10.3f}"
                else:
                    row += f" {'---':>10}"
            print(row)

    # Plot if requested
    if args.plot and all_curves:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))

            for model, curve in all_curves.items():
                densities_plot = [d for d, _, _ in curve]
                means = [m for _, m, _ in curve]
                sds = [s for _, _, s in curve]
                ax.errorbar(densities_plot, means, yerr=sds,
                           marker='o', capsize=3, label=model)

            ax.set_xlabel("Imperative Density (number of procedural blocks)")
            ax.set_ylabel("Mean Adherence")
            ax.set_title("E-PHASE: Imperative Register Saturation")
            ax.legend()
            ax.set_xlim(-0.5, 11.5)
            ax.set_ylim(0, 1.05)
            ax.grid(True, alpha=0.3)

            # Add block labels on x-axis
            block_labels = ["all\ndecl"] + [
                b.split("/")[-1][:8]
                for b in PROCEDURAL_BLOCKS_ORDERED
            ]
            ax.set_xticks(range(12))
            ax.set_xticklabels(block_labels, rotation=45, ha="right", fontsize=7)

            plot_path = output_dir / "e_phase_curve.png"
            fig.tight_layout()
            fig.savefig(plot_path, dpi=150)
            print(f"\n  Plot saved: {plot_path}")
            plt.close()
        except ImportError:
            print("\n  matplotlib not available — skipping plot")


def main():
    parser = argparse.ArgumentParser(description="E-PHASE: Phase Transition Mapping")
    parser.add_argument(
        "--model", action="append", choices=list(MODEL_MAP.keys()),
        help="Model(s) to test (repeatable; default: haiku only)",
    )
    parser.add_argument(
        "--densities", nargs="+", type=int,
        help="Specific densities to test (default: 0-11)",
    )
    parser.add_argument("--trials", type=int, default=3, help="Trials per probe")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without running")
    parser.add_argument("--compare", action="store_true", help="Analyze existing results")
    parser.add_argument("--plot", action="store_true", help="Generate matplotlib plot (with --compare)")
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
