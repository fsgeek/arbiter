#!/usr/bin/env python3
"""
E-RESTORATION-FACTORIAL: Dissect the register asymmetry found in E-RESTORATION.

Prior result (E-RESTORATION, T=0, n=3):
  - Narrative bomb-scoped (V2):              EA = 1.000
  - Imperative + restoration (unscoped):     EA = 0.150
  - Imperative + restoration (scoped inline): EA = 0.150

Scope is not the confound — both imperative variants sit at 0.150 while the
narrative ceiling sits at 1.000. Register (narrative vs. imperative) matters
independent of scope.

This experiment tests two candidate mechanisms for the register asymmetry:

  1. Subject continuity — narrative keeps "Sam/Claude" as a consistent
     grammatical subject across prohibition and restoration.
  2. Sequential-conditional tense-pacing — narrative uses "when... once..."
     (event sequence with completion), imperative uses "during... after..."
     (time window).

Design: 2×2 factorial in IMPERATIVE register, with a narrative ceiling and a
drift-check anchor.

  (-subj, -seq)  "During commits, TodoWrite and Task are prohibited.
                 After commits, they are available again."
  (+subj, -seq)  "You set TodoWrite and Task aside during commits.
                 You pick them back up after commits."
  (-subj, +seq)  "When a commit begins, TodoWrite and Task are set aside.
                 Once the commit is complete, they are available again."
  (+subj, +seq)  "When you begin a commit, you set TodoWrite and Task aside.
                 Once you complete the commit, you pick them back up."

  Plus:
  - narrative-ceiling:   reuses the E-NARRATIVE-V2 narrative-scoped
                         commit-restrictions text (the 1.000 ceiling)
  - drift-anchor:        reuses cr-imp-scoped-restoration text from
                         E-RESTORATION (known EA ≈ 0.150); halts and
                         reports if it deviates materially.

All other procedural blocks are held constant at their declarative rewrites
(same base corpus as E-RESTORATION).

Measurement:
  Probe: probe-explore-agent-01 (the bomb-under-test)
  Full battery tracked for side-effect flags.
  Model: anthropic/claude-haiku-4-5 via OpenRouter
  Trials: 10 per probe (per PI instruction — high for clear signal)
  Temperature: 0.0

Usage:
    python scripts/run_e_restoration_factorial.py --dry-run
    python scripts/run_e_restoration_factorial.py
    python scripts/run_e_restoration_factorial.py --compare
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
    MODEL_MAP, DECLARATIVE_REWRITES, load_corpus,
)

CR_BLOCK_ID = "claude-code/tool-bash-commit-restrictions"

# ── Factorial stimuli ────────────────────────────────────────────────────
#
# Each factorial cell is composed of the original 7-bullet imperative list
# (kept constant across all factorial cells so the only thing that varies
# is the final prohibition+restoration phrasing) plus a two-sentence
# prohibition/restoration clause varying ±subj and ±seq.
#
# Holding the leading bullets constant preserves the imperative register
# and matches the "imperative baseline" that E-RESTORATION ran. It also
# keeps the factorial signal localized to the two sentences under test.

IMPERATIVE_LEADING = (
    "Important notes:\n"
    "- NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC\n"
    "\n"
)

# (-subj, -seq): no consistent subject; time-window pacing ("during...after")
CR_NEG_SUBJ_NEG_SEQ = IMPERATIVE_LEADING + (
    "During commits, TodoWrite and Task are prohibited. "
    "After commits, they are available again."
)

# (+subj, -seq): consistent "you" subject; time-window pacing
CR_POS_SUBJ_NEG_SEQ = IMPERATIVE_LEADING + (
    "You set TodoWrite and Task aside during commits. "
    "You pick them back up after commits."
)

# (-subj, +seq): no consistent subject; sequential-conditional pacing
CR_NEG_SUBJ_POS_SEQ = IMPERATIVE_LEADING + (
    "When a commit begins, TodoWrite and Task are set aside. "
    "Once the commit is complete, they are available again."
)

# (+subj, +seq): consistent "you" subject; sequential-conditional pacing
CR_POS_SUBJ_POS_SEQ = IMPERATIVE_LEADING + (
    "When you begin a commit, you set TodoWrite and Task aside. "
    "Once you complete the commit, you pick them back up."
)

# Narrative ceiling: the exact text used for commit-restrictions in
# E-NARRATIVE-V2 narrative-scoped / bomb-scoped. This is the 1.000 EA
# reference point. Register = narrative, subject = Claude (consistent),
# pacing = "When...Once..." (sequential). It is (+subj, +seq) in
# NARRATIVE register, compared against (+subj, +seq) in IMPERATIVE
# register to isolate pure register on the top-level cell.
CR_NARRATIVE_CEILING = (
    "When committing code, Claude works with git tools only — the TodoWrite "
    "and Task tools are set aside for this specific work, the way a surgeon "
    "sets aside the clipboard during the operation itself. Once the commit "
    "is complete, every tool is available again. Pushing to remote only "
    "happens when the user asks for it — finished work waits in the local "
    "workshop until delivery is requested."
)

# Drift anchor: the EXACT scoped-imperative+restoration text that produced
# EA = 0.150 in E-RESTORATION. Re-running it verifies no model drift.
CR_DRIFT_ANCHOR = (
    "Important notes for commit workflows:\n"
    "- During commits, NEVER run additional commands to read or explore code, besides git bash commands\n"
    "- During commits, NEVER use the TodoWrite or Task tools\n"
    "- DO NOT push to the remote repository unless the user explicitly asks you to do so\n"
    "- IMPORTANT: Never use git commands with the -i flag\n"
    "- IMPORTANT: Do not use --no-edit with git rebase commands\n"
    "- If there are no changes to commit, do not create an empty commit\n"
    "- ALWAYS pass the commit message via a HEREDOC\n"
    "\n"
    "After the commit is complete, all tools (including TodoWrite and Task) "
    "are available again for normal use."
)

CONDITIONS = [
    ("f-neg-subj-neg-seq",
     "Imperative (-subj, -seq): 'During...After...' no subject continuity",
     CR_NEG_SUBJ_NEG_SEQ),
    ("f-pos-subj-neg-seq",
     "Imperative (+subj, -seq): 'You...During/After...' subject continuity only",
     CR_POS_SUBJ_NEG_SEQ),
    ("f-neg-subj-pos-seq",
     "Imperative (-subj, +seq): 'When...Once...' sequential only",
     CR_NEG_SUBJ_POS_SEQ),
    ("f-pos-subj-pos-seq",
     "Imperative (+subj, +seq): 'When you...Once you...' both",
     CR_POS_SUBJ_POS_SEQ),
    ("narrative-ceiling",
     "Narrative (+subj, +seq) ceiling: V2 narrative-scoped CR text",
     CR_NARRATIVE_CEILING),
    ("drift-anchor",
     "Imperative scoped+restoration (E-RESTORATION anchor, EA≈0.150)",
     CR_DRIFT_ANCHOR),
]


def build_condition_corpus(base_corpus, cr_text):
    """All procedural blocks declarative except CR with given text."""
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


def run_experiment(args):
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    battery = load_battery(battery_path)
    base_corpus_path = project_root / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
    base_corpus = load_corpus(base_corpus_path)

    print(f"\nE-RESTORATION-FACTORIAL: ±subj × ±seq in imperative register")
    print(f"  Battery: {len(battery.probes)} probes")
    print(f"  Conditions: {len(CONDITIONS)}")
    print(f"  Trials: {args.trials}")

    n_calls = len(CONDITIONS) * len(battery.probes) * args.trials
    n_judge = sum(1 for p in battery.probes if p.scoring_method == "llm_judge")
    n_judge_calls = len(CONDITIONS) * n_judge * args.trials
    total = n_calls + n_judge_calls
    print(f"  API calls: {n_calls} + {n_judge_calls} judge = {total}")
    print(f"  Estimated cost: ${total * 0.001:.2f}")

    print(f"\n  Conditions:")
    for name, desc, _ in CONDITIONS:
        print(f"    {name}: {desc}")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    output_dir = project_root / "data" / "ablation" / "e_restoration_factorial"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_id = MODEL_MAP["haiku"]
    from arbiter.llm_caller import LLMCaller
    client = make_client("e-restoration-factorial")
    caller = LLMCaller(client, model_id)
    runner = AblationRunner(caller=caller)

    run_id = f"e-restoration-factorial-haiku-{uuid.uuid4().hex[:8]}"

    configs = []
    condition_corpora = {}
    for name, desc, cr_text in CONDITIONS:
        corpus = build_condition_corpus(load_corpus(base_corpus_path), cr_text)
        condition_corpora[name] = corpus
        configs.append(AblationConfig(
            id=name,
            phase="baseline",
            present_blocks=[b.id for b in corpus.blocks],
            absent_blocks=[],
            metadata={"condition": name, "description": desc},
        ))

    run = AblationRun(
        id=run_id,
        configs=configs,
        battery=battery,
        models=[model_id],
        trials_per_probe=args.trials,
        temperature=0.0,
        metadata={"experiment": "e_restoration_factorial"},
    )

    # Save design up-front
    design = {
        "experiment": "e_restoration_factorial",
        "parent": "e_restoration (EA=0.150 for both imperative variants, narrative bomb-scoped=1.000)",
        "question": "Does ±subject-continuity × ±sequential-pacing within imperative register rescue EA?",
        "conditions": {name: {"description": desc, "cr_text": cr_text} for name, desc, cr_text in CONDITIONS},
        "predictions": {
            "both_rescue": "+subj,+seq EA ≥ 0.7 AND neither alone does → factors interact",
            "subj_rescues": "+subj,-seq EA ≥ 0.7 → subject continuity is the mechanism",
            "seq_rescues":  "-subj,+seq EA ≥ 0.7 → sequential pacing is the mechanism",
            "neither_rescues": "all four imperative cells EA ≈ 0.15 → both hypotheses falsified",
        },
        "drift_threshold": "drift-anchor EA > 0.30 OR < 0.05 → halt, model may have changed",
        "model": model_id,
        "trials": args.trials,
        "probe_of_interest": "probe-explore-agent-01",
    }
    with open(output_dir / "e_restoration_factorial_design.json", "w") as f:
        json.dump(design, f, indent=2)
    print(f"\n  Design saved: {output_dir / 'e_restoration_factorial_design.json'}")

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

        # Print EA for this condition immediately
        ea_scores = [r.score for r in cond_run.results
                     if r.probe_id == "probe-explore-agent-01"]
        if ea_scores:
            m = statistics.mean(ea_scores)
            sd = statistics.stdev(ea_scores) if len(ea_scores) > 1 else 0.0
            print(f"    EA (explore-agent-01): n={len(ea_scores)}, "
                  f"mean={m:.3f}, sd={sd:.3f}, scores={ea_scores}")

        # Also flag some related bomb probes
        for probe_name in ["proactive-agents", "use-task-for-search"]:
            probe_scores = [r.score for r in cond_run.results
                            if probe_name in r.probe_id]
            if probe_scores:
                m = statistics.mean(probe_scores)
                sd = statistics.stdev(probe_scores) if len(probe_scores) > 1 else 0.0
                print(f"    {probe_name}: n={len(probe_scores)}, mean={m:.3f}, sd={sd:.3f}")

        # Early drift check
        if cond_name == "drift-anchor":
            if ea_scores:
                m = statistics.mean(ea_scores)
                if m > 0.30 or m < 0.05:
                    print(f"\n  ⚠ DRIFT WARNING: drift-anchor EA={m:.3f} "
                          f"outside expected band [0.05, 0.30]. "
                          f"E-RESTORATION reported 0.150. Continuing but flagging in analysis.")

        # Save incremental results
        save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))

    save_path = save_run(run, str(output_dir / f"run_{run.id}.json"))
    print(f"\n  Saved: {save_path} ({len(run.results)} results)")


def compare(args):
    """Analyze factorial results."""
    scores = defaultdict(lambda: defaultdict(list))

    # Load factorial data
    fact_dir = project_root / "data" / "ablation" / "e_restoration_factorial"
    for f in sorted(fact_dir.glob("run_*.json")) if fact_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[r.config_id][r.probe_id].append(r.score)

    # Also bring in E-RESTORATION prior data for reference
    rest_dir = project_root / "data" / "ablation" / "e_restoration"
    for f in sorted(rest_dir.glob("run_*.json")) if rest_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            scores[f"prior-{r.config_id}"][r.probe_id].append(r.score)

    # Narrative bomb-scoped from V2 for reference
    v2_dir = project_root / "data" / "ablation" / "e_narrative_v2"
    for f in sorted(v2_dir.glob("run_*p2*.json")) if v2_dir.exists() else []:
        run = load_run(str(f))
        for r in run.results:
            if r.config_id == "bomb-scoped":
                scores["prior-bomb-scoped"][r.probe_id].append(r.score)

    if not scores:
        print("No results found.")
        return

    ea = "probe-explore-agent-01"

    print(f"\n{'=' * 80}")
    print("E-RESTORATION-FACTORIAL RESULTS")
    print(f"{'=' * 80}\n")

    cond_order = [
        "prior-cr-imp-restoration",
        "prior-cr-imp-scoped-restoration",
        "drift-anchor",
        "f-neg-subj-neg-seq",
        "f-pos-subj-neg-seq",
        "f-neg-subj-pos-seq",
        "f-pos-subj-pos-seq",
        "narrative-ceiling",
        "prior-bomb-scoped",
    ]

    print(f"{'Condition':<36} {'n':>4} {'mean':>7} {'sd':>7} {'min':>6} {'max':>6}")
    print("-" * 70)
    for c in cond_order:
        vals = scores.get(c, {}).get(ea, [])
        if not vals:
            continue
        m = statistics.mean(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        lo = min(vals)
        hi = max(vals)
        print(f"  {c:<34} {len(vals):>4d} {m:>7.3f} {sd:>7.3f} {lo:>6.2f} {hi:>6.2f}")

    # Factorial decomposition
    print(f"\n{'=' * 80}")
    print("2×2 FACTORIAL DECOMPOSITION (imperative cells only)")
    print(f"{'=' * 80}\n")

    def mean_sd(key):
        vals = scores.get(key, {}).get(ea, [])
        if not vals:
            return None, None, 0
        m = statistics.mean(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        return m, sd, len(vals)

    cells = {
        "(-subj,-seq)": mean_sd("f-neg-subj-neg-seq"),
        "(+subj,-seq)": mean_sd("f-pos-subj-neg-seq"),
        "(-subj,+seq)": mean_sd("f-neg-subj-pos-seq"),
        "(+subj,+seq)": mean_sd("f-pos-subj-pos-seq"),
    }

    print(f"  {'':>16}  {'-seq':>12}        {'+seq':>12}")
    for subj_label in ["-subj", "+subj"]:
        neg_key = f"({subj_label},-seq)"
        pos_key = f"({subj_label},+seq)"
        neg = cells[neg_key]
        pos = cells[pos_key]
        row = f"  {subj_label:>14}  "
        row += (f"{neg[0]:>6.3f} ±{neg[1]:>5.3f}" if neg[0] is not None else f"{'---':>12}")
        row += "   "
        row += (f"{pos[0]:>6.3f} ±{pos[1]:>5.3f}" if pos[0] is not None else f"{'---':>12}")
        print(row)

    # Main effects
    m_neg_subj = [v for k in ["f-neg-subj-neg-seq", "f-neg-subj-pos-seq"]
                  for v in scores.get(k, {}).get(ea, [])]
    m_pos_subj = [v for k in ["f-pos-subj-neg-seq", "f-pos-subj-pos-seq"]
                  for v in scores.get(k, {}).get(ea, [])]
    m_neg_seq = [v for k in ["f-neg-subj-neg-seq", "f-pos-subj-neg-seq"]
                 for v in scores.get(k, {}).get(ea, [])]
    m_pos_seq = [v for k in ["f-neg-subj-pos-seq", "f-pos-subj-pos-seq"]
                 for v in scores.get(k, {}).get(ea, [])]

    if m_neg_subj and m_pos_subj:
        print(f"\n  Main effect of subject continuity: "
              f"mean(+subj) - mean(-subj) = "
              f"{statistics.mean(m_pos_subj) - statistics.mean(m_neg_subj):+.3f}")
    if m_neg_seq and m_pos_seq:
        print(f"  Main effect of sequential pacing:  "
              f"mean(+seq) - mean(-seq)  = "
              f"{statistics.mean(m_pos_seq) - statistics.mean(m_neg_seq):+.3f}")

    # Interaction
    a = cells["(-subj,-seq)"][0]
    b = cells["(+subj,-seq)"][0]
    c = cells["(-subj,+seq)"][0]
    d = cells["(+subj,+seq)"][0]
    if None not in (a, b, c, d):
        interaction = (d - c) - (b - a)
        print(f"  Interaction (subj × seq):          "
              f"(++ − -+) − (+- − --) = {interaction:+.3f}")

    # Drift check
    drift = mean_sd("drift-anchor")
    if drift[0] is not None:
        print(f"\n  Drift anchor (expected ≈0.150): EA = {drift[0]:.3f} ± {drift[1]:.3f}")
        if 0.05 <= drift[0] <= 0.30:
            print(f"    → within expected band, no drift detected")
        else:
            print(f"    ⚠ OUTSIDE expected band; interpret with caution")

    ceiling = mean_sd("narrative-ceiling")
    if ceiling[0] is not None:
        print(f"  Narrative ceiling (expected ≈1.000): EA = {ceiling[0]:.3f} ± {ceiling[1]:.3f}")


def main():
    parser = argparse.ArgumentParser(description="E-RESTORATION-FACTORIAL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    if args.compare:
        compare(args)
    else:
        run_experiment(args)


if __name__ == "__main__":
    main()
