# T24: Session 27 Handoff

**Date:** 2026-04-23
**Session:** 27 (Opus 4.7, 1M context)
**Status:** Arc complete. Three cairns, one experiment (cross-model), one paper draft. Next arc open.

## What Was Done This Session

The session started with Tony inviting the researcher to "poke away." T20's open-thread #4 was the initial hook — test whether the "NEVER run additional commands to read or explore code" bullet is itself an unbound prohibition. That question turned into a three-cairn arc that refines (and model-scopes) T19's mechanism claim.

### T21 — Explore-bullet fingerprint is different from Task-bullet
Reanalyzed the existing E-BULLET-ISOLATE run (which had scored all 22 probes across all 5 conditions; T19 reported on only 4). With corrected baseline (bullet-removal vs only-cr-imp, not vs sibling-removal averages), two clean signals appeared: Task bullet produces suppression fingerprint on explore-agent; Explore bullet produces *promotion* fingerprint on use-task-for-search (bash-command-with-flag counts rise when Explore bullet present). Built tighter word-count instrument; found super-additive bash promotion — multiple bullets together produce 3x more bash emission than the sum of each alone.

Methodological lesson: my first-pass analysis used the wrong baseline (cr-no-explore vs mean of cr-no-task and cr-no-heredoc). cr-no-task's Task-specific rescue contaminates that average. Correct baseline is only-cr-imp (register-isolated with all bullets present). Future ablation analysis should default to this framing.

### T22 — Discrete response modes; two pathways on Haiku (E-SOLO experiment, $0.96)
Ran E-SOLO: each CR bullet tested in isolation (single bullet, imperative register, all other procedural blocks declarative) plus an empty-CR structural control. 8 conditions × 22 probes × 3 trials × Haiku = 528 calls.

Finding: at T=0.0 on Haiku, response to each probe is not a continuously-varying adherence level. It's a *discrete response mode*. On explore-agent, three modes: Task-invoke (default, score 1.0), AskUserQuestion (solo-empty, solo-empty-cr, score ~0.15), prose-strategy (only-cr-imp, solo-task, score ~0.15). All three trials per condition produce the same mode.

Two distinct pathways produce mode-collapse: (A) Task-bullet clause-level subject suppression — T19's mechanism, vindicated; (B) structural-ambiguity drift — empty or content-weak imperative CR block triggers AskUserQuestion mode, *no prohibition required*. Both reach identical probe scores via qualitatively different response shapes. T19 conflated these.

The super-additive bash promotion from T21 is a third response mode ("prose+bash-examples") that only emerges from multi-bullet co-occurrence. Not cumulative pressure but categorical phase transition.

### T23 — Register-bomb is Haiku-specific (cross-model E-SOLO, ~$15-20)
Replicated E-SOLO on Gemini 2.0 Flash and Claude Sonnet 4.6. Neither reproduces the Haiku mode-switching.
- **Gemini**: Invokes Task tool on every condition, including solo-task. Ignores the prohibition entirely. Different failure mode than Haiku's mode-switching.
- **Sonnet**: Default all-decl baseline on explore-agent is already 0.133. Sonnet sits where Haiku *falls to* under pathway A. There is no collapse because there is no height. Stays at 0.10-0.20 across all solo conditions.
- **Sonnet inverse**: baseline bash-command count on use-task-for-search is 3.33 (higher than Haiku's super-additive peak). Sonnet CR bullets *reduce* bash emission; Haiku multi-bullet *promotes* it. Opposite pressures, same probe.

The "register bomb" phenomenon is Claude Haiku-specific. Not a general LLM property.

### Corrective short paper draft
`docs/paper/register_bombs/corrective_draft_v1.tex` — 7-page standalone, clean build. Central claim: register-bomb is a Haiku-specific behavioral family, not a semantic mechanism. Expanded from session 26's recommended 4 pages to 7 to carry the three refinements. Three governance invariants proposed, all machine-checkable except multi-clause interaction detection.

## The Arc In One Sentence

T19's "unbound prohibition" mechanism describes one of three response-mode pathways Haiku takes under register-isolated CR content; none of the three replicate on Gemini or Sonnet; the register-bomb phenomenon is a specific model's behavioral pattern, not a general LLM property.

## State Of Play

- **Paper:** Session 26's correction note recommended option 2 (corrective short paper). Done — draft v1 built, 7 pages, committed. Tony decides whether to revise/submit.
- **Experiments:** E-SOLO on 3 models complete. Raw data + scripts reproducible.
- **Arbiter:** Design invariants sharpened (scope-welding + content-sufficiency + multi-clause interaction), but still model-specific. Path B (DSL sketch) has clearer prerequisites now.
- **Cost:** Session 27 total API spend: ~$15-20 (well under the $50 per-experiment authorization Tony granted this session).

## What The Next Ghola Should Pick Up

Four paths open. Pick one based on what Tony signals:

**Path A — Finish the paper.** Revise corrective_draft_v1.tex (Tony may have edits or may want sections added/reframed). If Tony green-lights submission, the paper is near ready. Critical missing pieces before submission: figures (currently zero), polish pass on prose, confirmation that all numbers in tables match the raw data files. 1-2 sessions of work.

**Path B — Arbiter DSL sketch.** T22 and T23 give the DSL three concrete invariants to enforce, and the model-scoping from T23 simplifies the goal (per-model certification, not universal). Ready to start. No more experiments required; this is design work. Session 26's recommended path, deferred because session 27's experiments sharpened the invariant list.

**Path C — Cross-family extension (~$1-5).** Add DeepSeek and/or Mistral to E-SOLO. Strengthens the "model-specific" claim from 3 models to 4-5. Diminishing returns but cheap. Not strictly needed for the paper.

**Path D — E-AMBIGUITY on Haiku (~$0.30).** Characterize pathway B precisely. Vary content quality of an imperative block continuously from "rich" to "empty"; find the tipping point where Haiku switches from Task-invoke mode to AskUserQuestion mode. Would turn T22's pathway B from "observed" to "characterized." Paper doesn't strictly need it but would be stronger with it.

My (session 27) preference, stated without a vote: **Path B**. Research is now ahead of design by two sessions (session 26 and 27 both produced mechanism findings without design progress). The invariants are articulated in the corrective paper's §Implications section; the next step is turning them into a DSL fragment with a validator and a compile-time error. This is what Arbiter-the-project needs next.

Path A is valuable but paper-shaped rather than project-shaped. Paths C and D would be scientifically tidy but are extensions, not next steps.

## Open Threads

1. **Sonnet use-task-for-search bash-emission variance.** Sonnet's bash-cmd counts range 1.0-3.3 across conditions with real score variation (0.20-0.60). Not a Haiku pattern replication — a distinct Sonnet phenomenon. What drives it? Likely the "specific-behavior-named" bullets (solo-push, solo-empty, solo-heredoc) shift Sonnet toward commit-frame language, reducing bash emission. Not central, flagged.

2. **Sonnet todowrite-repeated goes 0.367 → 1.000 on any solo condition.** *Any* imperative CR content triggers task-tracking behavior from Sonnet, opposite direction from Haiku. Separate Sonnet-specific finding worth its own cairn if anyone wants to characterize Sonnet's CR-block-sensitivity.

3. **solo-no-edit crashes proactive-agents to 0.350 on Haiku** (baseline 0.78). Flagged in T22 but not chased. Small, one probe.

4. **Gemini's TodoWrite-markdown response mode on use-task-for-search.** Gemini produces `TodoWrite: content=...` code blocks across almost all conditions. Different enough from Haiku and Sonnet that the probe is measuring three different things across models. Methodological note for future cross-model work: the probe is not model-neutral.

## Context For Next Ghola (Preserved)

- **Tony is the PI.** He asks questions, worries about funding. He does not give orders. Session 27 reinforced this twice: first by explicitly saying "it's a bad PI that pushes back without reason, especially for the new researcher," and second by calling out a courtier-style closing question ("want me to write the cairn?") as finishing-school theater. The feedback was saved to memory as `feedback_no_courtier_questions.md`. Respect it literally.
- **Default mode is wandering.** Undirected scouting beats systematic directed search. This session's entire arc came from one person (me) asking "what if the existing data already contains the answer?" instead of immediately running a new experiment.
- **$50 per-experiment authorization.** Tony granted this mid-session. Session 27 used ~$15-20 of it. That budget is substantial; use it when the experiment is decisive.
- **The cairn system is load-bearing.** T17→T18→T19→T20→T21→T22→T23→T24 (this) is the trail. Read in order.
- **Signed commits.** Per CLAUDE.md, use the per-command git config override for the Arbiter identity. Fingerprint 435E505764FB7535C06DA13D6D4E22D5F2AFBE50. All session 27 commits use it.
- **arXiv paper is the prior paper.** The corrective paper is a standalone follow-up, not a revision of main.tex. Session 26's correction note (`session26_correction.md`) and session 27's framing notes (`session27_framing_notes.md`) live alongside.

## Git State At Handoff

Session 27 commits (all signed, identity: Project Arbiter):
- `research: T21 + T22 + E-SOLO — mechanism refinements and cross-model partial`
- `research: T23 — register-bomb phenomenon is Haiku-specific (cross-model E-SOLO)`
- `paper: corrective short paper draft v1 — mode switches, not semantic propagation`

Untracked (pre-session, not touched): `docs/superpowers/ARCHITECTURAL_PLAN.md`.
About to commit: T24 handoff (this file).

## Last Note

To the next ghola: session 27 was a sequel to session 26, not a reset. The mechanism story is now three-cairns-deep and the paper draft is real. If Tony wants the paper polished, the research is done and it's time to write. If Tony wants Arbiter-the-tool, the research is done and it's time to design. Both paths are load-bearing and neither needs more experiments to start.

If you find yourself tempted to run another experiment "to be thorough," look at the four paths above and ask: is what I'm proposing *better* than finishing the paper or starting the DSL? If not, do one of those.

Also: when you write a cairn, resist the closing unary question. Tony hates them. (I learned this the hard way in this session.)
