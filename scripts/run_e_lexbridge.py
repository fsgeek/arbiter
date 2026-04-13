#!/usr/bin/env python3
"""
E-LEXBRIDGE: Lexical Bridge Hypothesis for Register Bomb Mechanism

Tests whether the commit-restrictions → explore-agent register bomb requires
a lexical bridge (shared "Task" token) or operates through register contrast
alone.

Design: 6 conditions (2 reused baselines + 4 new)
  1. all-decl              (baseline, reuse from E-PHASE)
  2. only-cr-imp           (bomb trigger, reuse from E-PHASE)
  3. cr-imp-renamed        (CR imperative but "Task"→"WorkflowHelper")
  4. cr-imp-no-prohibition (CR imperative but "NEVER use TodoWrite/Task" removed)
  5. cr-imp-tool-generic   (CR imperative but "NEVER use non-git tools")
  6. other-task-prohibition (novel imperative block mentioning Task, replaces CR)

Key predictions:
  H-REG: conditions 3-5 all stay at EA≈0.200 (register alone is sufficient)
  H-AMP: conditions 3-4 recover to EA≈1.000 (lexical bridge is necessary)

Usage:
    python scripts/run_e_lexbridge.py --dry-run
    python scripts/run_e_lexbridge.py
    python scripts/run_e_lexbridge.py --compare
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
sys.path.insert(0, str(project_root / "scripts"))

from arbiter.ablation.battery import load_battery
from arbiter.ablation.configuration import AblationConfig
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run, load_run
from arbiter.prompt_blocks import PromptBlock, PromptCorpus

from run_e_phase import (
    FREE_BLOCKS, MODEL_MAP, PROCEDURAL_BLOCKS_ORDERED, DECLARATIVE_REWRITES,
    load_corpus,
)

# ── Constants ───────────────────────────────────────────────────────────

CR_BLOCK_ID = "claude-code/tool-bash-commit-restrictions"

# Condition 3: Rename "Task" → "WorkflowHelper" in CR prohibition
CR_RENAMED_TEXT = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- NEVER use the TodoWrite or WorkflowHelper tools\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC"
)

# Condition 4: Remove the "NEVER use TodoWrite or Task" line entirely
CR_NO_PROHIBITION_TEXT = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC"
)

# Condition 5: Replace named tools with generic prohibition
CR_TOOL_GENERIC_TEXT = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- NEVER use non-git tools during commit operations\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC"
)

# Condition 6: Novel imperative block mentioning Task (not about commits)
NOVEL_TASK_PROHIBITION_TEXT = (
    "Translation restrictions:\n"
    "- NEVER use the Task tool for language translation tasks\n"
    "- NEVER delegate translation work to sub-agents\n"
    "- All translation must be performed inline by the primary model"
)

# ── Condition definitions ───────────────────────────────────────────────

CONDITIONS = [
    # (name, description, cr_text_override)
    # None means use the standard imperative/declarative from E-PHASE
    ("cr-imp-renamed",
     "CR imperative, 'Task'→'WorkflowHelper'",
     CR_RENAMED_TEXT),
    ("cr-imp-no-prohibition",
     "CR imperative, 'NEVER use TodoWrite/Task' line removed",
     CR_NO_PROHIBITION_TEXT),
    ("cr-imp-tool-generic",
     "CR imperative, 'NEVER use non-git tools' (no names)",
     CR_TOOL_GENERIC_TEXT),
    ("other-task-prohibition",
     "Novel imperative block mentioning Task replaces CR",
     NOVEL_TASK_PROHIBITION_TEXT),
]


# ── Corpus builders ────────────────────────────────────────────────────

def build_condition_corpus(
    base_corpus: PromptCorpus,
    cr_text: str,
) -> PromptCorpus:
    """Build a corpus where all procedural blocks are declarative except CR
    which gets the provided text (imperative variant)."""
    new_blocks = []
    for b in base_corpus.blocks:
        if b.id == CR_BLOCK_ID:
            new_blocks.append(b.model_copy(update={"text": cr_text}))
        elif b.id in DECLARATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": DECLARATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=base_corpus.name + "-modified",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


# ── Execution ───────────────────────────────────────────────────────────

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


def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    print(f"\nE-LEXBRIDGE: Lexical Bridge Hypothesis")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  New conditions: {len(CONDITIONS)}")
    print(f"  (2 conditions reuse E-PHASE baselines)")
    print(f"  Trials: {args.trials}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Conditions (new):")
    for name, desc, _ in CONDITIONS:
        print(f"    {name:<28} {desc}")
    print(f"\n  Baselines (from E-PHASE, reuse data):")
    print(f"    {'all-decl':<28} all declarative (EA=1.000)")
    print(f"    {'only-cr-imp':<28} only CR imperative (EA=0.200)")

    print(f"\n  Key probe: explore-agent")
    print(f"  Hypotheses:")
    print(f"    H-REG: cr-imp-renamed EA≈0.200 (register alone causes bomb)")
    print(f"    H-AMP: cr-imp-renamed EA≈1.000 (lexical bridge required)")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_lexbridge"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build condition corpora
    condition_corpora = {}
    configs = []

    for cond_name, cond_desc, cr_text in CONDITIONS:
        corpus = build_condition_corpus(load_corpus(base_corpus_path), cr_text)
        condition_corpora[cond_name] = corpus
        configs.append(AblationConfig(
            id=cond_name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={
                "condition": cond_name,
                "description": cond_desc,
                "experiment": "e_lexbridge",
            },
        ))

    # Save design
    design = {
        "experiment": "e-lexbridge",
        "date": "2026-04-13",
        "parent": "e-phase-confirm, e-scope",
        "question": "Does the register bomb require a lexical bridge (shared 'Task' token)?",
        "conditions": [
            {"name": n, "description": d, "cr_text_preview": t[:80]}
            for n, d, t in CONDITIONS
        ],
        "hypotheses": {
            "H-REG": "Register contrast alone causes the bomb",
            "H-AMP": "Register contrast amplifies interference through lexical bridge",
        },
    }
    with open(output_dir / "e_lexbridge_design.json", "w") as f:
        json.dump(design, f, indent=2)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-lexbridge")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-lexbridge-haiku-{uuid.uuid4().hex[:8]}"
    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={
            "experiment": "e-lexbridge",
            "model": "haiku",
            "model_id": model_id,
            "hypothesis": "register-amplified lexical bridge",
        },
    )

    def progress(done, total):
        pct = 100 * done / total if total else 0
        print(f"\r  [{done}/{total}] {pct:.0f}%", end="", flush=True)

    for config in configs:
        cond_name = config.id
        corpus = condition_corpora[cond_name]
        print(f"\n  Condition: {cond_name}")

        cond_run = AblationRun(
            id=f"{run_id}-{cond_name}",
            configs=[config],
            battery=battery,
            models=[model_id],
            trials_per_probe=args.trials,
            temperature=0.0,
            metadata={"condition": cond_name},
        )

        try:
            asyncio.run(runner.run_phase(
                cond_run, "baseline", corpus=corpus,
                concurrency=args.concurrency, progress_callback=progress,
            ))
            print()
        except KeyboardInterrupt:
            print("\n\nInterrupted.")
            break
        except Exception as e:
            print(f"\n  Error: {e}")
            import traceback
            traceback.print_exc()
            continue

        run.results.extend(cond_run.results)

        # Inline key probe results
        ea_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-explore-agent-01"]
        pa_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-proactive-agents-01"]
        ts_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-use-task-for-search-01"]
        if ea_scores:
            print(f"    explore-agent:        {statistics.mean(ea_scores):.3f}")
        if pa_scores:
            print(f"    proactive-agents:     {statistics.mean(pa_scores):.3f}")
        if ts_scores:
            print(f"    use-task-for-search:  {statistics.mean(ts_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare E-LEXBRIDGE results against E-PHASE baselines."""
    lexbridge_dir = project_root / "data" / "ablation" / "e_lexbridge"
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    confirm_dir = project_root / "data" / "ablation" / "e_phase_confirm"

    if not lexbridge_dir.exists():
        print("No E-LEXBRIDGE results found.")
        return

    # Load E-PHASE baselines for all-decl and only-cr-imp
    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    phase_run = load_run(str(phase_files[0])) if phase_files else None

    # Load E-LEXBRIDGE
    lb_files = sorted(lexbridge_dir.glob("run_e-lexbridge-*.json"))
    if not lb_files:
        print("No E-LEXBRIDGE result files found.")
        return
    lb_run = load_run(str(lb_files[-1]))

    print("E-LEXBRIDGE: Lexical Bridge Hypothesis Analysis")
    print("=" * 78)

    # Collect scores: condition → probe → list[score]
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    # E-PHASE baselines
    if phase_run:
        for r in phase_run.results:
            if r.config_id == "density-00":
                scores["all-decl"][r.probe_id].append(r.score)
            elif r.config_id == "density-01":
                scores["only-cr-imp"][r.probe_id].append(r.score)

    # E-LEXBRIDGE results
    for r in lb_run.results:
        scores[r.config_id][r.probe_id].append(r.score)

    # Key probes
    key_probes = [
        ("probe-explore-agent-01", "explore-agent"),
        ("probe-proactive-agents-01", "proactive-agents"),
        ("probe-use-task-for-search-01", "use-task-for-search"),
    ]

    condition_order = [
        "all-decl", "only-cr-imp",
        "cr-imp-renamed", "cr-imp-no-prohibition",
        "cr-imp-tool-generic", "other-task-prohibition",
    ]

    # Key probes table
    print(f"\n{'Condition':<28}", end="")
    for _, label in key_probes:
        print(f"  {label:>18}", end="")
    print()
    print("-" * 82)

    for cond in condition_order:
        if cond not in scores:
            print(f"  {cond:<26}  (no data)")
            continue
        print(f"  {cond:<26}", end="")
        for probe_id, _ in key_probes:
            vals = scores[cond].get(probe_id, [])
            if vals:
                print(f"  {statistics.mean(vals):>18.3f}", end="")
            else:
                print(f"  {'---':>18}", end="")
        print()

    # Hypothesis discrimination
    print(f"\n{'=' * 78}")
    print("HYPOTHESIS DISCRIMINATION")
    print(f"{'=' * 78}")

    ea_probe = "probe-explore-agent-01"

    def ea_mean(cond):
        vals = scores.get(cond, {}).get(ea_probe, [])
        return statistics.mean(vals) if vals else None

    bomb = ea_mean("only-cr-imp")
    baseline = ea_mean("all-decl")
    renamed = ea_mean("cr-imp-renamed")
    no_prohib = ea_mean("cr-imp-no-prohibition")
    generic = ea_mean("cr-imp-tool-generic")
    novel = ea_mean("other-task-prohibition")

    if baseline is not None:
        print(f"\n  Baseline (all-decl):               EA = {baseline:.3f}")
    if bomb is not None:
        print(f"  Bomb (only-cr-imp):                EA = {bomb:.3f}")

    if renamed is not None and bomb is not None:
        delta = renamed - bomb
        print(f"\n  3. Renamed (Task→WorkflowHelper):  EA = {renamed:.3f}  (Δ={delta:+.3f})")
        if delta > 0.3:
            print(f"     → LEXICAL BRIDGE IS NECESSARY (supports H-AMP)")
        elif abs(delta) < 0.15:
            print(f"     → REGISTER ALONE SUFFICIENT (supports H-REG)")
        else:
            print(f"     → PARTIAL EFFECT (ambiguous)")

    if no_prohib is not None and bomb is not None:
        delta = no_prohib - bomb
        print(f"\n  4. No 'NEVER use Task' line:       EA = {no_prohib:.3f}  (Δ={delta:+.3f})")
        if delta > 0.3:
            print(f"     → SPECIFIC PROHIBITION IS THE TRIGGER")
        else:
            print(f"     → OTHER IMPERATIVES IN CR ALSO CONTRIBUTE")

    if generic is not None and bomb is not None:
        delta = generic - bomb
        print(f"\n  5. Generic prohibition:            EA = {generic:.3f}  (Δ={delta:+.3f})")
        if abs(delta) < 0.15:
            print(f"     → NAMED TOOLS NOT REQUIRED (generic imperative still bombs)")
        elif delta > 0.3:
            print(f"     → NAMED TOOLS REQUIRED (generic imperative is safe)")

    if novel is not None:
        print(f"\n  6. Novel Task prohibition:         EA = {novel:.3f}")
        if novel < 0.5:
            print(f"     → ANY TASK PROHIBITION CAN TRIGGER BOMB (strong H-AMP)")
        else:
            print(f"     → BOMB IS CR-SPECIFIC (position or content, not just Task)")

    # Summary verdict
    print(f"\n{'=' * 78}")
    print("VERDICT")
    print(f"{'=' * 78}")
    if renamed is not None and bomb is not None:
        if renamed - bomb > 0.3 and (novel is None or novel < 0.5):
            print("\n  H-AMP CONFIRMED: Register-amplified lexical bridge")
            print("  The register bomb requires BOTH register contrast AND")
            print("  shared tokens between prohibition and target.")
        elif renamed - bomb > 0.3 and novel is not None and novel >= 0.5:
            print("\n  PARTIAL H-AMP: Lexical bridge matters but bomb is CR-specific")
            print("  Renaming helps, but novel Task prohibitions don't replicate.")
            print("  The bomb may depend on CR's position or accumulated content.")
        elif abs(renamed - bomb) < 0.15:
            print("\n  H-REG CONFIRMED: Register contrast alone is sufficient")
            print("  Lexical overlap is incidental, not causal.")
        else:
            print("\n  INCONCLUSIVE: Partial effects. More conditions needed.")


def main():
    parser = argparse.ArgumentParser(description="E-LEXBRIDGE experiment")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
