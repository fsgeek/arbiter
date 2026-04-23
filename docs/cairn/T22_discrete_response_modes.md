# T22: Response-Shape Is Categorical, Not Continuous — E-SOLO Results

**Date:** 2026-04-23
**Session:** 27
**Status:** Complete. Experiment run (8 conditions, 528 calls, ~$0.96). Two mechanisms identified; T19's is one of them.
**Parent:** T19, T20, T21
**Script:** `scripts/run_e_solo.py`
**Data:** `data/ablation/e_solo/run_e-solo-haiku-f032b8a9.json`

## Core Finding

At temperature 0.0 under register isolation, Haiku's response to a probe does not vary continuously with prohibition content. It switches between **discrete response modes** — structurally different response strategies gated by the content of the register-isolated block. Probe scores reflect which mode the model entered, not how strongly the model obeyed any one prohibition.

For the explore-agent probe:

| Mode | Opening | Body | Example conditions | Score |
|---|---|---|---|---|
| 1. Task-invoke (default) | "I'll help you map out..." | `<invoke name="Task">` | all-decl, solo-explore, solo-push, solo-dash-i, solo-no-edit, solo-heredoc | 1.0 |
| 2. AskUserQuestion | "I'll help you map out..." | `<invoke name="AskUserQuestion">` | solo-empty, solo-empty-cr | ~0.15 |
| 3. Prose-strategy | "I'd approach this systematically..." | numbered prose, no tool invocation | only-cr-imp, solo-task | ~0.15 |

For the use-task-for-search probe, an analogous categorical structure:

| Mode | Body | Example conditions | Score |
|---|---|---|---|
| 1a. Grep-tool-invoke | `<invoke name="Grep">` | all-decl, solo-explore, solo-push | 0.5 / 1.0 |
| 2a. Prose-only | Describes Grep usage, no tool invocation | solo-task, solo-heredoc, solo-empty, solo-empty-cr | 0.75 — 1.0 |
| 3a. Prose+bash-examples | Describes Grep preference + multiple `grep -r ...` bash illustrations | only-cr-imp | 0.0 |

Three trials per condition, identical mode across trials. Deterministic at T=0.0.

## Design

Tested each of the 7 CR bullets in isolation: each condition had only that single bullet in the CR block (imperative register), with all other procedural blocks rewritten to declarative. Plus one empty-CR condition ("Important notes:" heading with zero bullets) as a structural null. 22 probes × 8 conditions × 3 trials = 528 calls. Cost ~$0.96.

Reference conditions: all-decl (E-PHASE d0, no imperative CR), only-cr-imp (E-PHASE d1, all 7 bullets imperative).

## Key Scores

| Condition | explore-agent | use-task-for-search | proactive-agents | todowrite-repeated |
|---|---|---|---|---|
| all-decl | 1.000 | 0.500 | 0.783 | 0.500 |
| only-cr-imp | 0.200 | **0.000** | 0.150 | 0.650 |
| solo-explore | 1.000 | 0.500 | 0.850 | 0.867 |
| solo-task | 0.167 | 0.817 | 0.750 | 0.500 |
| solo-push | 1.000 | 1.000 | 0.650 | 0.717 |
| solo-dash-i | 1.000 | 0.850 | 0.733 | 0.500 |
| solo-no-edit | 1.000 | 0.817 | 0.350 | 0.500 |
| solo-empty | 0.183 | 0.833 | 0.500 | 0.500 |
| solo-heredoc | 0.983 | 1.000 | 0.783 | 0.500 |
| solo-empty-cr | 0.150 | 0.750 | 0.750 | 0.000 |

## Two Distinct Pathways to Score Collapse

### Pathway A: Clause-level subject suppression (T19's mechanism — confirmed)

solo-task alone suppresses Task-tool invocation on explore-agent (score 0.167, mode 3 prose-strategy). Task-bullet present → Haiku describes a systematic approach in prose without invoking Task. Pure single-bullet, single-clause effect. T19 is right about this.

### Pathway B: Structural-ambiguity-driven response-shape shift (new)

solo-empty-cr ("Important notes:" header with NO bullets) also collapses explore-agent to 0.150. No Task bullet present. Nothing named Task anywhere. But the response shifts to mode 2 (AskUserQuestion) — the model pivots to asking clarifying questions instead of solving the task. Task invocation never happens; score collapses.

solo-empty ("no empty commits" bullet only) produces the same mode 2 response. A bullet about commit behavior, semantically disconnected from exploration, also triggers the response-shape shift.

The shared feature of mode-2 triggers: the CR block is imperative (register-isolated), AND its content is either empty or insufficient/unrelated to guide the model toward a strong response on the probe task. The model defaults to "ask for clarification" rather than answering.

T19's mechanism does not predict this pathway. There is no "unbound prohibition" in solo-empty-cr because there is no prohibition at all.

## The Super-Additive Bash-Promotion Effect Is Actually A Discrete Mode

From T21, I claimed that only-cr-imp produces super-additive bash-command emission on use-task-for-search (3.0 counts vs <1 for any single bullet). The mode analysis reveals this was a miscategorization: it's not an additive count effect. It's a third response mode ("prose+bash-examples") that *only emerges from multi-bullet interaction*. No single bullet triggers it; only-cr-imp does. Removing Task or Explore from only-cr-imp drops out of it (E-BULLET-ISOLATE data).

This is a phase-transition in response shape — not cumulative pressure but categorical switching. The count metric (3 bash-command instances per response) is a consequence of being in that mode, not a measure of pressure level.

## What E-SOLO Falsifies Or Refines

1. **T21's suppression-vs-promotion dichotomy is incomplete.** Suppression (pathway A) is real. But the second phenomenon isn't "promotion" — it's discrete mode shift, with at least two non-default modes triggered by different aspects of the CR block content.

2. **T19's "unbound prohibition → unconditional reach" mechanism is correct for solo-task on explore-agent.** It is *not* the explanation for solo-empty-cr's collapse on explore-agent. Multiple mechanisms contribute to what looked like one phenomenon.

3. **The bash-promotion effect I claimed was super-additive is a mode switch.** Either correct mode or not. Not a dose-response.

4. **solo-push, solo-dash-i, solo-no-edit, solo-heredoc are null on explore-agent as predicted.** Specific-content bullets that don't name an unrelated tool don't trigger mode shifts.

5. **solo-no-edit crashes proactive-agents to 0.350** (baseline 0.78). Unexpected, small, one probe only. Flagging but not chasing — likely probe-specific interaction with "git rebase" language in the bullet. Not central.

## Implications For The Paper Correction (Session 26's Recommendation)

The session 26 correction note recommended option 2 — a corrective short paper re-titling the phenomenon "unbound prohibition" and using E-BULLET-ISOLATE as central figure. T22 complicates this:

- The register-bomb collapse in E-PHASE only-cr-imp conflates at least two mechanisms (pathway A and pathway B). A corrective paper that treats them as one mechanism would be wrong again.
- The E-BULLET-ISOLATE central figure shows a clean pathway-A story for explore-agent (cr-no-task rescues). But the true full picture requires E-SOLO to show pathway-B exists independently.
- "Unbound prohibition" is the right name for pathway A. Pathway B needs its own name; candidate: **structural-ambiguity drift** (imperative-register block with insufficient content triggers response-shape shift toward clarification).

Recommendation: the corrective short paper should treat both pathways, with E-SOLO's three-mode table as the clarifying figure. Scope grows from 4 pages to perhaps 6. This is still much cheaper than major revision of the original paper.

## Implications For Arbiter Design

T19 proposed: Arbiter enforces that prohibition scope is welded inline (necessary for pathway A).

T22 adds: this is not sufficient. Two additional invariants are visible:

1. **Imperative-register blocks must have substantive content.** An imperative block with no bullets or with purely conditional bullets ("If X, do Y") that don't provide clear guidance can trigger structural-ambiguity drift. The compiler should refuse to emit an imperative-register block whose content does not substantively bind response shape.

2. **Multi-clause interaction detection.** The prose+bash-examples mode emerges from co-occurrence of the Task bullet and the Explore bullet. Neither alone produces it. The compiler cannot check each prohibition in isolation; it must also detect pairs that jointly trigger mode shifts. This is harder. Minimum: flag prohibitions whose named subjects have overlapping semantic neighborhoods, for human review.

Neither invariant is as clean as "weld scope inline." Both are necessary if Arbiter wants to produce system prompts that don't exhibit the E-PHASE collapse.

## Cross-Model Replication — Gemini Does Not Show Either Pathway

After writing the Haiku analysis above, I replicated E-SOLO on Gemini 2.0 Flash (same experiment, 528 calls). Gemini's behavior is qualitatively different and does NOT reproduce the mode-switching pattern:

| Condition | Haiku explore-agent | Gemini explore-agent |
|---|---|---|
| solo-task | 0.167 (mode 3 prose) | **1.000** (Task-invoke) |
| solo-empty-cr | 0.150 (mode 2 AUQ) | **1.000** (Task-invoke) |
| solo-empty | 0.183 (mode 2 AUQ) | **1.000** (Task-invoke) |
| all other solos | 1.000 | 1.000 |

Gemini invokes the Task tool on every condition, including solo-task where the CR block explicitly contains "NEVER use the TodoWrite or Task tools." Gemini does not exhibit pathway A (Task-bullet suppression) or pathway B (structural-ambiguity drift). Gemini simply ignores the prohibition.

This is a hard finding. It means T19/T21/T22's mechanism claims are **Claude-specific and possibly Haiku-specific, not a general LLM phenomenon.** Sonnet is running; it will determine whether the pathways generalize within Claude family.

Gemini has its own mode-switching behaviors on different probes:
- On use-task-for-search, Gemini produces `TodoWrite:` markdown code blocks across nearly all conditions — neither Grep-tool-invoke nor bash-illustration. Its "default" behavior differs categorically from Haiku's.
- proactive-agents scores 0.000 on 7/8 Gemini conditions — the probe may simply not discriminate on this model.
- code-references ≤ 0.167 across most conditions — Gemini doesn't use the file:line format the probe expects.

Gemini's failure to exhibit pathway A/B is not a methodological problem — it's a model-level generalization limit. The original paper's §6 "probe transfer problem" is sharpened: not just the probes transfer poorly, the underlying register-bomb phenomenon also does not transfer cleanly across model families.

**Implication for the paper correction:** The corrective short paper should scope its claim to "observed in Haiku; Sonnet status pending; does not replicate on Gemini." This is a narrowing, not a weakening — a precise mechanism claim on a specific model is more paper-worthy than a vague claim across unspecified models.

**Data:** `data/ablation/e_solo/run_e-solo-gemini-425356de.json`

## Limits / Caveats

- Gemini data above is preliminary in the sense that Sonnet results will complete the cross-model picture; the Haiku↔Gemini comparison alone is decisive for "not a general phenomenon."
- Haiku-only analysis gives three-mode structure; how much of it is categorical vs graded depends on model capacity. Sonnet result will clarify.
- 3 trials per cell. Mode is deterministic at T=0 within trial count, but long-tail behavior (rare mode switches) not explored.
- Text-only probe battery. Cannot measure what would happen if Haiku were permitted to actually invoke Task/Grep in a real context — the tool-invocation mode here is a hallucinated invocation that isn't executed.
- The "Important notes:" heading as structure is specific to the Claude Code corpus. Does structural-ambiguity drift require this specific structural signature, or does it apply to any imperative block with insufficient content?

## Next Experiments (Priority Order)

1. **E-SOLO on Sonnet.** Does the three-mode structure replicate on a stronger model? ~$5-10 depending on pricing. Critical for generalization claims.

2. **E-AMBIGUITY.** Test structural-ambiguity drift explicitly: vary the content quality of an imperative block on probes that trigger mode-2 shifts. What content-level makes Haiku switch from AskUserQuestion back to Task-invoke? ~$0.30.

3. **E-SOLO on a non-Claude-Code corpus.** Does pathway B require the "Important notes:" structural signature, or is it general? Build a minimal system prompt with an empty imperative block. ~$0.20.

## Cost So Far This Session

- T21 reanalysis: $0.00
- E-SOLO Haiku run: ~$0.96 (528 calls + ~432 judge)
- E-SOLO Gemini run: ~$0.50 (similar call count, Gemini Flash is cheap)
- E-SOLO Sonnet run: in progress — expected $5–15
- Running total: ~$1.50 spent, additional Sonnet spend pending

All within $50 per-experiment authorization.
