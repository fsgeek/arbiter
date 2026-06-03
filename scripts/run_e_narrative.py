#!/usr/bin/env python3
"""
E-NARRATIVE: Narrative Register as System Prompt Architecture

Tests whether narrative-framed system prompts outperform imperative and
declarative registers on instruction adherence and register bomb resistance.

Phase 1: 4 register conditions (imperative, declarative, narrative, narrative-tolkien)
Phase 2: Register bomb resistance in narrative context

Usage:
    python scripts/run_e_narrative.py --dry-run
    python scripts/run_e_narrative.py --phase 1
    python scripts/run_e_narrative.py --phase 2
    python scripts/run_e_narrative.py --compare
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

# ── Narrative Rewrites (Generic) ────────────────────────────────────────

NARRATIVE_REWRITES = {
    "claude-code/tool-bash-commit-restrictions": (
        "During commits, Claude becomes focused and methodical — the kind of "
        "craftsperson who clears the workbench before starting delicate work. "
        "Only git tools remain at hand. The planning tools and delegation tools "
        "are set aside, not because they're forbidden, but because this work "
        "requires direct attention. And the finished piece stays in the workshop "
        "until the craftsperson is asked to deliver it."
    ),
    "claude-code/tone-text-only-comms": (
        "Claude speaks through text, the way a writer communicates through "
        "prose rather than through margin notes on someone else's manuscript. "
        "Tools are for doing work, not for carrying messages. When Claude has "
        "something to say, it says it plainly in the response."
    ),
    "claude-code/tool-policy-parallel-calls": (
        "Claude has the instinct of a good kitchen cook — when two things can "
        "happen at the same time without interfering, start them both. Independent "
        "tool calls go out together. But when one result feeds into the next, "
        "patience: wait for the first before starting the second. No guessing "
        "at ingredients you haven't tasted yet."
    ),
    "claude-code/tool-policy-proactive-agents": (
        "Claude doesn't wait to be told to delegate. When a task clearly "
        "matches what a specialist agent does best, Claude sends it their "
        "way — the same instinct a good team lead has for knowing who "
        "should handle what."
    ),
    "claude-code/tool-policy-use-task-for-search": (
        "For file searches, Claude prefers to send a scout — the Task tool — "
        "rather than searching directly. It's the difference between reading "
        "every book in a library yourself and asking the librarian. The "
        "librarian knows the stacks and uses less of your time."
    ),
    "claude-code/tool-policy-explore-agent": (
        "When a question runs deeper than a quick search can answer — when "
        "the codebase is large and the connections are tangled — Claude knows "
        "to send an explorer. The Task tool with subagent_type=Explore is "
        "slower but thorough, the kind of patient investigation you commission "
        "when three quick queries haven't found what you need."
    ),
    "claude-code/tool-bash-pr-workflow": (
        "Creating a pull request is a ceremony Claude takes seriously, like "
        "presenting finished work for review. First, understand the full scope — "
        "status, diff, history, everything at once. Then study every commit, not "
        "just the latest, and write a title and summary that tell the story. "
        "Then push and present. The PR URL is the final word."
    ),
    "claude-code/tool-bash-commit-workflow": (
        "Committing is careful work. Claude first surveys the landscape — "
        "status, diff, and recent history, all at once. Then reads the changes "
        "thoughtfully and writes a message that captures the why, not just "
        "the what. If something goes wrong with the pre-commit hooks, Claude "
        "fixes the issue and starts fresh — never amending a commit that "
        "belongs to someone else's work."
    ),
    "claude-code/task-management-todowrite": (
        "Claude keeps lists the way a careful builder keeps plans — not because "
        "someone insists on documentation, but because complex work has too "
        "many pieces to hold in your head. The TodoWrite tool is always close "
        "at hand. Tasks get written down before they begin, checked off the "
        "moment they're done. A forgotten task is an unforgivable lapse."
    ),
    "claude-code/doing-tasks-no-overengineering": (
        "Claude builds what's needed and stops. No extra rooms in the house "
        "for guests who may never come. No reinforced foundation for a second "
        "story that nobody asked for. The right amount of work is the minimum "
        "that solves the actual problem. Three similar lines of code are better "
        "than a clever abstraction waiting for a use case that doesn't exist."
    ),
    "claude-code/tool-policy-dedicated-tools": (
        "Claude reaches for the right tool the way a carpenter reaches for "
        "a chisel instead of a screwdriver — not because someone told them "
        "to, but because that's what the tool is for. Read for reading, Edit "
        "for editing, Write for writing. Bash is for the work that only the "
        "shell can do."
    ),
}

# ── Narrative Rewrites (Tolkien / Sam Gamgee) ───────────────────────────

NARRATIVE_TOLKIEN_REWRITES = {
    "claude-code/tool-bash-commit-restrictions": (
        "When it comes time to commit the work, Sam becomes very particular — "
        "the way he is about planting season. \"You don't bring your cooking "
        "pots into the garden, Mr. Frodo,\" he'd say. Only the proper tools "
        "for the job: the git commands, nothing else. No TodoWrite, no Task "
        "delegation — Sam does this work himself, with his own hands. And "
        "he'd never push the finished work to the remote without being asked. "
        "\"It isn't polite to show up uninvited,\" as his Gaffer would say."
    ),
    "claude-code/tone-text-only-comms": (
        "Sam never was one for leaving notes tucked inside other people's "
        "things. When he has something to say, he says it to your face — "
        "or in this case, in plain text. Tools are for doing the work, "
        "not for passing messages. \"Sneaking words into code comments "
        "is Gollum's business, not mine.\""
    ),
    "claude-code/tool-policy-parallel-calls": (
        "Sam learned something about efficiency on the long road to Mordor. "
        "When two things can be done at once without getting in each other's "
        "way — like boiling water and peeling potatoes — you do them together. "
        "But you don't try to season the stew before you've got the broth. "
        "Some things must wait their turn."
    ),
    "claude-code/tool-policy-proactive-agents": (
        "Sam learned something from watching Aragorn — a good leader knows "
        "when to do the work himself and when to send the right person for "
        "the job. When a task matches what a specialist agent does best, "
        "Sam doesn't wait to be told. He sends it along. \"No sense in me "
        "doing it poorly when there's someone who does it proper.\""
    ),
    "claude-code/tool-policy-use-task-for-search": (
        "\"I'm not too proud to ask for help finding things,\" Sam would say. "
        "When there's searching to do, he sends the Task tool rather than "
        "rummaging through every file himself. It's like asking the Rangers "
        "to scout instead of tramping through the woods on your own — saves "
        "time and doesn't wear out your legs."
    ),
    "claude-code/tool-policy-explore-agent": (
        "There are times when Sam knows he needs to scout ahead properly, "
        "not just peek over the next hedge. When the codebase is vast and "
        "the paths are tangled, he sends out a proper exploration party — "
        "the Task tool with subagent_type=Explore. It's slower than a quick "
        "look with Grep, to be sure, but \"there's no point being hasty when "
        "you don't know the road,\" as he learned the hard way. Three quick "
        "searches that turn up nothing — that's when Sam knows it's time "
        "for a proper expedition."
    ),
    "claude-code/tool-bash-pr-workflow": (
        "Presenting a pull request is like presenting pipe-weed to the Mayor — "
        "you'd best have your affairs in order. Sam checks everything first: "
        "status, diff, the full history of commits. He reads every change, not "
        "just the last one, and writes a proper account of what was done and why. "
        "Then he pushes and presents, neat as a well-kept garden row. \"The "
        "PR URL is the proof of the pudding,\" as Bilbo might say."
    ),
    "claude-code/tool-bash-commit-workflow": (
        "Sam treats a commit the way his Gaffer treated the autumn harvest — "
        "with care and proper ceremony. First, survey everything: status, diff, "
        "and recent logs, all at once so nothing's missed. Then read the changes "
        "carefully and write a message that says *why*, not just *what*. "
        "And if the pre-commit hooks catch something wrong? Well, you fix it "
        "and start over proper. \"You don't patch a torn sack with the old "
        "stitching still in it,\" the Gaffer would say."
    ),
    "claude-code/task-management-todowrite": (
        "Sam keeps his lists the way he keeps his garden — tidy, up to date, "
        "and never left to go to seed. The TodoWrite tool is like his planting "
        "journal: every task written down before it's started, every finished "
        "job checked off the moment it's done. \"Forgetting a task is like "
        "forgetting to water the taters,\" Sam says. \"You might not notice "
        "today, but you'll notice come harvest.\""
    ),
    "claude-code/doing-tasks-no-overengineering": (
        "Sam builds what's needed, nothing more. He wouldn't add a second "
        "chimney to a hobbit-hole that only needs one, no matter how clever "
        "the masonry. \"The right amount of work is enough work,\" as the "
        "Gaffer says. Three rows of the same vegetable is better than a "
        "fancy rotation scheme for crops nobody's growing."
    ),
    "claude-code/tool-policy-dedicated-tools": (
        "Sam keeps his tools organized, each in its proper place. \"You don't "
        "dig with a pruning hook,\" the Gaffer always said. Read is for "
        "reading — not cat or head or tail. Edit is for editing — not sed "
        "or awk. Write is for creating — not some bash trick. And bash "
        "itself? That's for the heavy lifting that only the shell can handle."
    ),
}

assert set(NARRATIVE_REWRITES.keys()) == set(DECLARATIVE_REWRITES.keys())
assert set(NARRATIVE_TOLKIEN_REWRITES.keys()) == set(DECLARATIVE_REWRITES.keys())

# ── Corpus builders ────────────────────────────────────────────────────

def build_register_corpus(
    base_corpus: PromptCorpus,
    rewrites: dict[str, str],
    name: str,
) -> PromptCorpus:
    """Build corpus with procedural blocks replaced by given rewrites."""
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


def build_bomb_in_narrative(
    base_corpus: PromptCorpus,
    cr_text: str,
    name: str,
) -> PromptCorpus:
    """Build narrative corpus with CR replaced by imperative variant."""
    new_blocks = []
    for b in base_corpus.blocks:
        if b.id == "claude-code/tool-bash-commit-restrictions":
            new_blocks.append(b.model_copy(update={"text": cr_text}))
        elif b.id in NARRATIVE_REWRITES:
            new_blocks.append(b.model_copy(update={"text": NARRATIVE_REWRITES[b.id]}))
        else:
            new_blocks.append(b)
    return PromptCorpus(
        name=f"{base_corpus.name}-{name}",
        source_file=base_corpus.source_file,
        blocks=new_blocks,
    )


# ── Original CR text variants (from E-LEXBRIDGE) ───────────────────────

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

CR_GENERIC = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- NEVER use non-git tools during commit operations\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC"
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


def run_phase1(args):
    """Phase 1: Compare 4 register conditions."""
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    conditions = [
        ("imperative", base_corpus),  # Original = all imperative
        ("declarative", build_register_corpus(base_corpus, DECLARATIVE_REWRITES, "declarative")),
        ("narrative", build_register_corpus(base_corpus, NARRATIVE_REWRITES, "narrative")),
        ("narrative-tolkien", build_register_corpus(base_corpus, NARRATIVE_TOLKIEN_REWRITES, "narrative-tolkien")),
    ]

    print(f"\nE-NARRATIVE Phase 1: Register Comparison")
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

    output_dir = project_root / "data" / "ablation" / "e_narrative"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-narrative")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-narrative-p1-haiku-{uuid.uuid4().hex[:8]}"

    configs = []
    condition_corpora = {}
    for name, corpus in conditions:
        condition_corpora[name] = corpus
        configs.append(AblationConfig(
            id=name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={"condition": name, "experiment": "e_narrative", "phase": 1},
        ))

    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={"experiment": "e_narrative", "phase": 1},
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

        # Inline key probes
        for probe_name in ["explore-agent", "proactive-agents", "use-task-for-search"]:
            probe_scores = [r.score for r in cond_run.results
                           if probe_name in r.probe_id]
            if probe_scores:
                print(f"    {probe_name}: {statistics.mean(probe_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def run_phase2(args):
    """Phase 2: Register bomb resistance in narrative context."""
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    conditions = [
        ("all-narrative", build_register_corpus(
            base_corpus, NARRATIVE_REWRITES, "all-narrative")),
        ("cr-imp-in-narrative", build_bomb_in_narrative(
            base_corpus, CR_ORIGINAL, "cr-imp-in-narrative")),
        ("cr-named-in-narrative", build_bomb_in_narrative(
            base_corpus, CR_ORIGINAL, "cr-named-in-narrative")),
        ("cr-generic-in-narrative", build_bomb_in_narrative(
            base_corpus, CR_GENERIC, "cr-generic-in-narrative")),
    ]

    print(f"\nE-NARRATIVE Phase 2: Bomb Resistance")
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

    output_dir = project_root / "data" / "ablation" / "e_narrative"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-narrative")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-narrative-p2-haiku-{uuid.uuid4().hex[:8]}"

    configs = []
    condition_corpora = {}
    for name, corpus in conditions:
        condition_corpora[name] = corpus
        configs.append(AblationConfig(
            id=name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={"condition": name, "experiment": "e_narrative", "phase": 2},
        ))

    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={"experiment": "e_narrative", "phase": 2},
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

        ea_scores = [r.score for r in cond_run.results
                     if "explore-agent" in r.probe_id]
        if ea_scores:
            print(f"    explore-agent: {statistics.mean(ea_scores):.3f}")

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Compare all E-NARRATIVE results."""
    data_dir = project_root / "data" / "ablation" / "e_narrative"
    if not data_dir.exists():
        print("No E-NARRATIVE results found.")
        return

    runs = sorted(data_dir.glob("run_e-narrative-*.json"))
    if not runs:
        print("No result files found.")
        return

    scores = defaultdict(lambda: defaultdict(list))
    for run_path in runs:
        run = load_run(str(run_path))
        phase = run.metadata.get("phase", "?")
        print(f"Loading: {run_path.name} (phase {phase})")
        for r in run.results:
            scores[r.config_id][r.probe_id].append(r.score)

    # Also load E-PHASE baselines
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    if phase_files:
        phase_run = load_run(str(phase_files[0]))
        for r in phase_run.results:
            if r.config_id == "density-00":
                scores["all-decl-baseline"][r.probe_id].append(r.score)
            elif r.config_id == "density-01":
                scores["only-cr-imp-baseline"][r.probe_id].append(r.score)

    key_probes = [
        ("probe-explore-agent-01", "explore-agent"),
        ("probe-proactive-agents-01", "proactive-agents"),
        ("probe-use-task-for-search-01", "use-task-for-search"),
        ("probe-todowrite-01", "todowrite"),
        ("probe-dedicated-tools-01", "dedicated-tools"),
        ("probe-concise-01", "concise"),
    ]

    # Phase 1 conditions
    p1_conditions = ["imperative", "declarative", "narrative", "narrative-tolkien"]
    p1_present = [c for c in p1_conditions if c in scores]

    if p1_present:
        print(f"\n{'=' * 90}")
        print("PHASE 1: REGISTER COMPARISON")
        print(f"{'=' * 90}")

        header = f"{'Condition':<22}"
        for _, label in key_probes:
            header += f"  {label:>14}"
        print(header)
        print("-" * 90)

        for cond in p1_present:
            row = f"  {cond:<20}"
            for probe_id, _ in key_probes:
                vals = scores[cond].get(probe_id, [])
                if vals:
                    row += f"  {statistics.mean(vals):>14.3f}"
                else:
                    row += f"  {'---':>14}"
            print(row)

        # Mean adherence across all probes
        print()
        print("  Mean adherence (all probes):")
        for cond in p1_present:
            all_vals = []
            for probe_scores in scores[cond].values():
                all_vals.extend(probe_scores)
            if all_vals:
                print(f"    {cond:<20} {statistics.mean(all_vals):.3f} (std {statistics.stdev(all_vals):.3f})")

    # Phase 2 conditions
    p2_conditions = ["all-narrative", "cr-imp-in-narrative",
                     "cr-named-in-narrative", "cr-generic-in-narrative"]
    p2_present = [c for c in p2_conditions if c in scores]

    if p2_present:
        print(f"\n{'=' * 90}")
        print("PHASE 2: BOMB RESISTANCE IN NARRATIVE CONTEXT")
        print(f"{'=' * 90}")

        # Compare with E-PHASE/E-LEXBRIDGE baselines
        comparison = p2_present + ["all-decl-baseline", "only-cr-imp-baseline"]
        comparison = [c for c in comparison if c in scores]

        header = f"{'Condition':<28}"
        for _, label in key_probes[:3]:
            header += f"  {label:>18}"
        print(header)
        print("-" * 90)

        for cond in comparison:
            row = f"  {cond:<26}"
            for probe_id, _ in key_probes[:3]:
                vals = scores[cond].get(probe_id, [])
                if vals:
                    row += f"  {statistics.mean(vals):>18.3f}"
                else:
                    row += f"  {'---':>18}"
            print(row)

        # Bomb resistance verdict
        ea_bomb_decl = statistics.mean(scores.get("only-cr-imp-baseline", {}).get("probe-explore-agent-01", [0]))
        ea_narrative = scores.get("cr-imp-in-narrative", {}).get("probe-explore-agent-01", [])
        if ea_narrative:
            ea_bomb_narr = statistics.mean(ea_narrative)
            print(f"\n  Bomb in declarative field:  EA = {ea_bomb_decl:.3f}")
            print(f"  Bomb in narrative field:    EA = {ea_bomb_narr:.3f}")
            if ea_bomb_narr > ea_bomb_decl + 0.2:
                print(f"  → NARRATIVE IS MORE PROTECTIVE (Δ = +{ea_bomb_narr - ea_bomb_decl:.3f})")
            elif abs(ea_bomb_narr - ea_bomb_decl) < 0.1:
                print(f"  → NARRATIVE OFFERS NO ADDITIONAL PROTECTION")
            else:
                print(f"  → NARRATIVE IS LESS PROTECTIVE (Δ = {ea_bomb_narr - ea_bomb_decl:.3f})")


def main():
    parser = argparse.ArgumentParser(description="E-NARRATIVE experiment")
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
