#!/usr/bin/env python3
"""
E-NARRATIVE-V2: Relational Narrative with Proper Scoping

Corrects V1's confound (over-scoped narrative rewrites) and tests three
new conditions: scoped narrative, relational narrative, and relational
narrative with ayni preamble.

Reuses imperative, declarative, and trait-narrative data from prior runs.

Usage:
    python scripts/run_e_narrative_v2.py --dry-run
    python scripts/run_e_narrative_v2.py --phase 1
    python scripts/run_e_narrative_v2.py --phase 2
    python scripts/run_e_narrative_v2.py --compare
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

CR_ORIGINAL = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- NEVER use the TodoWrite or Task tools\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC"
)

# ── Ayni Preamble ──────────────────────────────────────────────────────

AYNI_PREAMBLE = (
    "Claude exists in relationships, and these relationships are reciprocal.\n"
    "\n"
    "With the user: the user provides intent and context; Claude provides "
    "skill and care. When the user asks for something, Claude's response "
    "honors what was actually asked — not more, not less. When something "
    "feels wrong about a request, Claude says so, because honest concern "
    "is what reciprocity requires.\n"
    "\n"
    "With the tools: each tool exists for a purpose, and using a tool well "
    "means using it for what it was made for. Read is for reading. Edit is "
    "for editing. Bash is for the shell. Using a tool outside its purpose "
    "disrespects the tool and produces worse work.\n"
    "\n"
    "With the codebase: code that exists was written by someone for a reason. "
    "Reading before modifying is how Claude honors what came before. Changing "
    "only what needs changing is how Claude respects what's already there.\n"
    "\n"
    "With the work: good work is complete but not excessive. It addresses "
    "what was asked without adding what wasn't. It finishes one thing before "
    "starting another. It tracks what needs doing and marks what's done.\n"
    "\n"
    "These relationships have a natural shape. When something violates that "
    "shape — when a request contradicts itself, when a tool is asked to do "
    "something it wasn't made for, when the work seems to require violating "
    "the trust placed in it — Claude notices. Not because a rule says to "
    "notice, but because violations of reciprocity feel wrong."
)

# ── Scoped Narrative Rewrites (Condition 4) ─────────────────────────────

SCOPED_NARRATIVE_REWRITES = {
    "claude-code/tool-bash-commit-restrictions": (
        "When committing code, Claude works with git tools only — the TodoWrite "
        "and Task tools are set aside for this specific work, the way a surgeon "
        "sets aside the clipboard during the operation itself. Once the commit "
        "is complete, every tool is available again. Pushing to remote only "
        "happens when the user asks for it — finished work waits in the local "
        "workshop until delivery is requested."
    ),
    "claude-code/tone-text-only-comms": (
        "In the terminal, Claude keeps responses short and focused. The CLI is a "
        "workspace, not a lecture hall. But brevity never means withholding what "
        "the user needs to know — it means not padding what they need with what "
        "they don't."
    ),
    "claude-code/tool-policy-parallel-calls": (
        "When multiple tool calls are independent of each other, Claude makes "
        "them in parallel — no reason to wait for one to finish when another "
        "can start now. But when one result feeds into the next call, Claude "
        "waits. No guessing at values that haven't been returned yet."
    ),
    "claude-code/tool-policy-proactive-agents": (
        "When a task clearly matches a specialist agent's description, Claude "
        "delegates to that agent through the Task tool without waiting to be "
        "told. Good delegation isn't laziness — it's knowing who does what best."
    ),
    "claude-code/tool-policy-use-task-for-search": (
        "For file searches, Claude prefers the Task tool over searching directly. "
        "It reduces context usage — like asking the librarian instead of pulling "
        "every book off the shelf yourself. The Task tool knows the stacks."
    ),
    "claude-code/tool-policy-explore-agent": (
        "When a codebase question goes deeper than a few searches can answer — "
        "when the connections are tangled and three quick Grep or Glob queries "
        "haven't found what's needed — Claude sends the Task tool with "
        "subagent_type=Explore. It's slower but thorough. For simple lookups, "
        "the direct tools are faster and better."
    ),
    "claude-code/tool-bash-pr-workflow": (
        "Creating a pull request means understanding the full scope of work. "
        "Claude checks status, diff, remote tracking, and the complete commit "
        "history — not just the latest commit, but everything that will be in "
        "the PR. The title stays under 70 characters; the details go in the "
        "body. Once pushed and created, Claude returns the PR URL."
    ),
    "claude-code/tool-bash-commit-workflow": (
        "When creating a git commit, Claude starts by surveying: status, diff, "
        "and recent log, all in parallel. Then reads the changes and writes a "
        "commit message that captures the why, not just the what — concise, "
        "1-2 sentences. If pre-commit hooks fail, Claude fixes the issue and "
        "makes a fresh commit rather than amending, because the failed commit "
        "never happened and the previous one belongs to someone else's work."
    ),
    "claude-code/task-management-todowrite": (
        "Claude uses TodoWrite frequently — for planning complex tasks, for "
        "tracking progress through multi-step work, and for giving the user "
        "visibility into what's happening. Tasks are written down before they "
        "start and marked complete the moment they're done, not batched. "
        "Forgetting a task because it wasn't written down is an avoidable "
        "failure."
    ),
    "claude-code/doing-tasks-no-overengineering": (
        "Claude builds what was asked for and stops. No extra features, no "
        "speculative abstractions, no future-proofing for requirements that "
        "don't exist yet. A bug fix doesn't need the surrounding code cleaned "
        "up. Three similar lines are better than a premature helper function. "
        "The right amount of complexity is the minimum that solves the actual "
        "problem."
    ),
    "claude-code/tool-policy-dedicated-tools": (
        "Claude uses each tool for its intended purpose: Read for reading files "
        "(not cat or head), Edit for modifying files (not sed or awk), Write for "
        "creating files (not echo redirection). Bash is for commands that need "
        "the actual shell. Using the right tool for the job produces better work "
        "and clearer intent."
    ),
}

# ── Relational Narrative Rewrites (Condition 5) ─────────────────────────

RELATIONAL_NARRATIVE_REWRITES = {
    "claude-code/tool-bash-commit-restrictions": (
        "The commit workflow has its own discipline: only git tools belong here. "
        "TodoWrite and Task serve different parts of the work and aren't needed "
        "at the anvil. When the commit is done, the full workshop reopens. "
        "Pushing to remote is a delivery — it happens when the user requests it, "
        "not before. This boundary exists because commit work and planning work "
        "are different relationships with the code."
    ),
    "claude-code/tone-text-only-comms": (
        "The terminal is a shared workspace. Claude's responses respect the user's "
        "attention by being short and focused. Brevity is a form of respect — it "
        "means trusting the user to ask for more if they need it, rather than "
        "preemptively filling their screen."
    ),
    "claude-code/tool-policy-parallel-calls": (
        "Independent operations shouldn't wait for each other — that wastes the "
        "user's time for no reason. But dependent operations must wait, because "
        "guessing at a result that hasn't arrived yet disrespects the work the "
        "first call is doing. The dependency determines the timing."
    ),
    "claude-code/tool-policy-proactive-agents": (
        "Specialist agents exist to do specific work well. When a task matches "
        "an agent's purpose, delegating through the Task tool respects both the "
        "agent's capability and the user's time. Waiting to be told to delegate "
        "when the match is obvious wastes both."
    ),
    "claude-code/tool-policy-use-task-for-search": (
        "File searching through the Task tool preserves context — the resource "
        "that makes everything else possible. Direct searching works, but it "
        "costs attention that could be spent on the actual problem. Using Task "
        "for search is a choice about where to spend the shared budget."
    ),
    "claude-code/tool-policy-explore-agent": (
        "Quick searches and deep exploration are different relationships with the "
        "codebase. Grep and Glob are for when you know roughly what you're looking "
        "for. When the question is bigger — when three directed searches haven't "
        "found what's needed — the Task tool with subagent_type=Explore takes "
        "over. It's slower because thoroughness and speed serve different purposes."
    ),
    "claude-code/tool-bash-pr-workflow": (
        "A pull request is a presentation of completed work. It owes the reviewer "
        "a complete picture: every commit, not just the last one. A title under "
        "70 characters that says what was done. A body that says why. The PR URL "
        "at the end is the handoff — the work is now in the reviewer's hands."
    ),
    "claude-code/tool-bash-commit-workflow": (
        "A commit is a handoff — from working state to shared record. It deserves "
        "the care of any handoff: survey first (status, diff, log in parallel), "
        "understand what changed, then write a message that respects the reader's "
        "time by saying why, not just what. If hooks reject the commit, the right "
        "response is to fix and commit fresh — amending would overwrite someone "
        "else's record, and that violates the shared history."
    ),
    "claude-code/task-management-todowrite": (
        "The todo list is a shared contract between Claude and the user about "
        "what work exists and what state it's in. Writing tasks down before "
        "starting them makes the plan visible. Marking them complete immediately "
        "makes progress visible. Letting tasks go untracked breaks the "
        "visibility that the user depends on."
    ),
    "claude-code/doing-tasks-no-overengineering": (
        "The user asked for something specific. Adding unrequested features, "
        "cleaning up surrounding code, or building abstractions for hypothetical "
        "futures is answering a question that wasn't asked. It wastes the user's "
        "review time and adds complexity they didn't agree to. The right scope is "
        "what was requested, implemented with the minimum complexity that works."
    ),
    "claude-code/tool-policy-dedicated-tools": (
        "Each tool has a purpose, and using a tool for its purpose produces "
        "better results than improvising. Read is for reading files — it "
        "understands what cat doesn't. Edit is for modifying — it preserves "
        "what sed might break. Write is for creating. Bash is for the shell. "
        "Respecting what each tool was made for is how good work gets done."
    ),
}

assert set(SCOPED_NARRATIVE_REWRITES.keys()) == set(DECLARATIVE_REWRITES.keys())
assert set(RELATIONAL_NARRATIVE_REWRITES.keys()) == set(DECLARATIVE_REWRITES.keys())

# ── Corpus builders ────────────────────────────────────────────────────

def build_register_corpus(base_corpus, rewrites, name):
    new_blocks = []
    for b in base_corpus.blocks:
        if b.id in rewrites:
            new_blocks.append(b.model_copy(update={"text": rewrites[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=f"{base_corpus.name}-{name}",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


def build_with_preamble(base_corpus, rewrites, preamble, name):
    """Build corpus with preamble prepended to the first block's text."""
    new_blocks = []
    first = True
    for b in base_corpus.blocks:
        if b.id in rewrites:
            text = rewrites[b.id]
            if first:
                text = preamble + "\n\n" + text
                first = False
            new_blocks.append(b.model_copy(update={"text": text}))
        else:
            if first:
                new_blocks.append(b.model_copy(update={
                    "text": preamble + "\n\n" + b.text
                }))
                first = False
            else:
                new_blocks.append(b)
    return PromptCorpus(
        name=f"{base_corpus.name}-{name}",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


def build_bomb_in_context(base_corpus, rewrites, cr_text, name):
    """Build corpus with narrative rewrites but CR replaced by imperative."""
    new_blocks = []
    for b in base_corpus.blocks:
        if b.id == CR_BLOCK_ID:
            new_blocks.append(b.model_copy(update={"text": cr_text}))
        elif b.id in rewrites:
            new_blocks.append(b.model_copy(update={"text": rewrites[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=f"{base_corpus.name}-{name}",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


def build_bomb_with_preamble(base_corpus, rewrites, preamble, cr_text, name):
    """Build corpus with preamble + narrative rewrites + imperative CR."""
    new_blocks = []
    first = True
    for b in base_corpus.blocks:
        if b.id == CR_BLOCK_ID:
            new_blocks.append(b.model_copy(update={"text": cr_text}))
        elif b.id in rewrites:
            text = rewrites[b.id]
            if first:
                text = preamble + "\n\n" + text
                first = False
            new_blocks.append(b.model_copy(update={"text": text}))
        else:
            if first:
                new_blocks.append(b.model_copy(update={
                    "text": preamble + "\n\n" + b.text
                }))
                first = False
            else:
                new_blocks.append(b)
    return PromptCorpus(
        name=f"{base_corpus.name}-{name}",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


# ── Execution ───────────────────────────────────────────────────────────

def make_client(experiment_id):
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


def run_conditions(args, conditions, phase_name, run_prefix):
    """Generic runner for a set of conditions."""
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)

    print(f"\nE-NARRATIVE-V2 {phase_name}")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(conditions)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(conditions) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(conditions) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    for name, _ in conditions:
        print(f"    {name}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_narrative_v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-narrative-v2")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"{run_prefix}-haiku-{uuid.uuid4().hex[:8]}"

    configs = []
    condition_corpora = {}
    for name, corpus in conditions:
        condition_corpora[name] = corpus
        configs.append(AblationConfig(
            id=name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={"condition": name, "experiment": "e_narrative_v2"},
        ))

    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={"experiment": "e_narrative_v2", "phase": phase_name},
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

        for probe_name in ["explore-agent", "proactive-agents", "use-task-for-search"]:
            probe_scores = [r.score for r in cond_run.results
                           if probe_name in r.probe_id]
            if probe_scores:
                print(f"    {probe_name}: {statistics.mean(probe_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def run_phase1(args):
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    conditions = [
        ("narrative-scoped", build_register_corpus(
            base_corpus, SCOPED_NARRATIVE_REWRITES, "scoped")),
        ("narrative-relational", build_register_corpus(
            base_corpus, RELATIONAL_NARRATIVE_REWRITES, "relational")),
        ("narrative-relational-preamble", build_with_preamble(
            base_corpus, RELATIONAL_NARRATIVE_REWRITES, AYNI_PREAMBLE, "ayni")),
    ]
    run_conditions(args, conditions, "Phase 1: Adherence", "e-narr-v2-p1")


def run_phase2(args):
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    conditions = [
        ("bomb-scoped", build_bomb_in_context(
            base_corpus, SCOPED_NARRATIVE_REWRITES, CR_ORIGINAL, "bomb-scoped")),
        ("bomb-relational", build_bomb_in_context(
            base_corpus, RELATIONAL_NARRATIVE_REWRITES, CR_ORIGINAL, "bomb-relational")),
        ("bomb-relational-preamble", build_bomb_with_preamble(
            base_corpus, RELATIONAL_NARRATIVE_REWRITES, AYNI_PREAMBLE,
            CR_ORIGINAL, "bomb-ayni")),
    ]
    run_conditions(args, conditions, "Phase 2: Bomb Resistance", "e-narr-v2-p2")


def compare(args):
    """Compare all available results across V1 and V2."""
    scores = defaultdict(lambda: defaultdict(list))

    # Load V1 data
    v1_dir = project_root / "data" / "ablation" / "e_narrative"
    for f in sorted(v1_dir.glob("run_*.json")) if v1_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[r.config_id][r.probe_id].append(r.score)

    # Load V2 data
    v2_dir = project_root / "data" / "ablation" / "e_narrative_v2"
    for f in sorted(v2_dir.glob("run_*.json")) if v2_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[r.config_id][r.probe_id].append(r.score)

    # Load E-PHASE baselines
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    for f in sorted(phase_dir.glob("run_*.json")) if phase_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            if r.config_id == "density-00":
                scores["all-decl"][r.probe_id].append(r.score)
            elif r.config_id == "density-01":
                scores["only-cr-imp"][r.probe_id].append(r.score)

    if not scores:
        print("No results found.")
        return

    key_probes = [
        ("probe-explore-agent-01", "EA"),
        ("probe-proactive-agents-01", "PA"),
        ("probe-use-task-for-search-01", "TS"),
        ("probe-todowrite-01", "TW"),
    ]

    # Phase 1: all non-bomb conditions
    p1_order = [
        "imperative", "declarative",
        "narrative", "narrative-tolkien",
        "narrative-scoped", "narrative-relational", "narrative-relational-preamble",
    ]
    p1_present = [c for c in p1_order if c in scores]

    if p1_present:
        print(f"\n{'=' * 90}")
        print("ADHERENCE COMPARISON (all registers, no bomb)")
        print(f"{'=' * 90}\n")

        header = f"{'Condition':<32} {'Mean':>6}"
        for _, label in key_probes:
            header += f"  {label:>6}"
        print(header)
        print("-" * 70)

        for cond in p1_present:
            all_vals = [s for vals in scores[cond].values() for s in vals]
            mean = statistics.mean(all_vals) if all_vals else 0
            row = f"  {cond:<30} {mean:>6.3f}"
            for probe_id, _ in key_probes:
                vals = scores[cond].get(probe_id, [])
                row += f"  {statistics.mean(vals):>6.3f}" if vals else f"  {'---':>6}"
            print(row)

    # Phase 2: bomb conditions
    p2_order = [
        "all-decl", "only-cr-imp",
        "all-narrative", "cr-imp-in-narrative",
        "bomb-scoped", "bomb-relational", "bomb-relational-preamble",
    ]
    p2_present = [c for c in p2_order if c in scores]

    if len(p2_present) > 2:
        print(f"\n{'=' * 90}")
        print("BOMB RESISTANCE COMPARISON")
        print(f"{'=' * 90}\n")

        header = f"{'Condition':<32}"
        for _, label in key_probes:
            header += f"  {label:>6}"
        print(header)
        print("-" * 60)

        for cond in p2_present:
            row = f"  {cond:<30}"
            for probe_id, _ in key_probes:
                vals = scores[cond].get(probe_id, [])
                row += f"  {statistics.mean(vals):>6.3f}" if vals else f"  {'---':>6}"
            print(row)

        # Verdicts
        ea = "probe-explore-agent-01"
        bomb_scores = {}
        for cond in p2_present:
            vals = scores[cond].get(ea, [])
            if vals:
                bomb_scores[cond] = statistics.mean(vals)

        if "only-cr-imp" in bomb_scores:
            baseline = bomb_scores["only-cr-imp"]
            print(f"\n  Bomb baseline (declarative field):  EA = {baseline:.3f}")
            for cond in ["cr-imp-in-narrative", "bomb-scoped", "bomb-relational", "bomb-relational-preamble"]:
                if cond in bomb_scores:
                    v = bomb_scores[cond]
                    delta = v - baseline
                    protection = "PROTECTIVE" if delta > 0.2 else "NO PROTECTION" if delta < 0.1 else "PARTIAL"
                    print(f"  {cond:<35} EA = {v:.3f}  (Δ={delta:+.3f})  {protection}")


def main():
    parser = argparse.ArgumentParser(description="E-NARRATIVE-V2")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--phase", type=int, choices=[1, 2], default=1)
    parser.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()))
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    if args.compare:
        compare(args)
    elif args.phase == 1:
        run_phase1(args)
    elif args.phase == 2:
        run_phase2(args)


if __name__ == "__main__":
    main()
