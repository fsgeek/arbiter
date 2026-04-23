# Session 27 — Framing Notes for Paper Correction

**Date:** 2026-04-23
**Status:** Working notes, not a draft. Captures how the session 26 recommendation ("corrective short paper") should be updated given session 27 findings.
**Not yet validated:** Sonnet E-SOLO results still in flight.

## What Session 26 Recommended

Option 2 from `session26_correction.md`: *"What the Register Bomb Actually Is"* — a 4-page standalone corrective paper featuring E-BULLET-ISOLATE as central figure. Mechanism renamed to "unbound prohibition." Natural third paper in arc: phenomenon → mechanism → design.

## What Session 27 Complicates

Two findings force a scope revision:

### 1. The Haiku mechanism is two pathways, not one

T22's E-SOLO results show that the "register bomb" score collapse on explore-agent has at least two separable mechanisms:

- **Pathway A**: Task-bullet under register isolation → prose-strategy response mode → Task-tool invocation suppressed. This is what T19 called "unbound prohibition." It *is* real, clause-specific, and single-bullet.
- **Pathway B**: Empty/weak-content imperative CR block → AskUserQuestion response mode → Task-tool invocation replaced by clarification questions. No prohibition needed. Triggered by structural properties of the block itself.

Both pathways produce the same observable (low explore-agent score). The original paper conflated them. T19 cleaned up one. T22 identifies the other.

A third mode, **"prose+bash-examples"**, emerges only from multi-bullet interaction (specifically the Task bullet and Explore bullet together) and is responsible for the use-task-for-search collapse. This is not captured by either pathway A or pathway B as single-bullet mechanisms; it's an emergent interaction.

Implication: a corrective paper that names pathway A as "the" mechanism and ignores pathway B and the interaction mode would be a third iteration of the same mistake (over-claiming uniformity).

### 2. Cross-model replication is partial at best

Gemini 2.0 Flash, run on the same E-SOLO design, exhibits neither pathway:
- explore-agent stays at 1.000 across all conditions, including solo-task (where Gemini ignores the "NEVER use Task" bullet and invokes Task anyway) and solo-empty-cr.
- Gemini has its own distinct response-shape patterns (e.g., producing `TodoWrite:` markdown code blocks on use-task-for-search regardless of CR content) that don't map to Haiku's three-mode structure.

Sonnet results in flight. Preliminary (4/8 conditions): explore-agent uniformly low (0.10-0.20) across all conditions including supposedly-null ones like solo-push — which could mean Sonnet's default is already low-Task-invocation, or that *any* imperative bullet collapses Sonnet's explore-agent. Baseline run (all-decl on Sonnet) needed to distinguish. Launched.

Implication: the phenomenon is not a general LLM property. It is observed strongly in Haiku, partially in Sonnet (TBD), not at all in Gemini. The paper's mechanism claim must be model-scoped.

## Candidate Revised Framing

### Title candidates

- *"Register-Isolated Prohibitions Trigger Discrete Response-Mode Shifts in Claude Haiku, Not General LLM Suppression"*
- *"Register Bombs Are Mode Switches, Not Semantic Propagation: A Cross-Model E-SOLO Analysis"*
- *"Three Mechanisms Behind One Collapse: Refining the Register-Bomb Account"*

The second or third. The first is accurate but overclaims from the title. Title should flag both the mechanism refinement AND the cross-model limitation.

### Structure (6–8 pages, instead of the 4 from session 26's rec)

1. **Introduction** — Paper 3 identified the phenomenon. Session 26's correction attributed it to clause-level unbound prohibition. This paper refines further: it's not a single mechanism, it's a tree of discrete response modes whose structure is model-specific.

2. **Method recap** — E-PHASE baseline (all-decl vs only-cr-imp). E-BULLET-ISOLATE. New: E-SOLO (each CR bullet in isolation, plus an empty-CR structural control).

3. **Results I — Haiku three-mode structure** — E-SOLO on Haiku. Central figure: response-mode classification table showing Task-invoke / AskUserQuestion / prose-strategy modes and their triggers. This is the primary contribution.

4. **Results II — Pathways A and B are independent** — solo-task triggers mode 3 (prohibition-aware); solo-empty-cr triggers mode 2 (structural-ambiguity); they reach the same score via different response shapes. Evidence: raw-response inspection.

5. **Results III — Multi-bullet interaction is a distinct mode** — only-cr-imp's bash-command emission is not additive. Figure: bash-cmd-with-flag counts across conditions showing emergent "prose+bash-examples" mode requires co-occurrence.

6. **Results IV — Cross-model limits** — Gemini doesn't exhibit any of these pathways; Sonnet [pending]. The phenomenon is Claude-specific and possibly Haiku-specific. Figure: per-model probe-score table on E-SOLO conditions.

7. **Discussion — what the original paper's register-bomb metaphor was measuring.** It was measuring a model-specific mode-switching phenomenon in Haiku, not a general LLM mechanism. The engineering advice ("maintain uniform register") still works for Haiku, and incidentally avoids triggering mode 2/3 on Sonnet-class models. Why it works is different from what the original paper said.

8. **Implications for Arbiter** — Design must be model-aware. A single scope-welding invariant does not cover mode 2 (structural ambiguity) or emergent interaction mode 3. At minimum, Arbiter should target a specific model and document which mode-switching behaviors the design prevents.

### What survives from the session 26 correction

- "Register is the revealing condition, not the disease" — correct for pathway A.
- "Clause-granularity scope processing" — correct for pathway A on Haiku.
- "All experimental data intact" — still true; just the interpretation widens.
- Engineering advice — empirically works, though for a more complicated reason than previously stated.

### What's new and paper-worthy

- Discrete-mode categorical structure (T22). This is the headline finding.
- Pathway A / pathway B separation (T22). Explains what T19 couldn't.
- Super-additive "prose+bash-examples" mode (T22). Multi-bullet emergent.
- Cross-model limits (T22). Scopes the claim explicitly.

### What's deferred to a later paper

- The design of an Arbiter DSL fragment addressing these issues. Separate paper; this one is about the phenomenon.
- Generalization beyond claude-code / v2.1.50 corpus. Out of scope; one cairn of future work.

## Decision Points Pending

1. **Whether to pursue this paper at all vs Path B (DSL sketch).** Session 26 preferred Path B ("research is ahead of design"). Session 27's findings give the paper more substance (multiple mechanisms, cross-model data) AND complicate Path B (more invariants needed before DSL can be defended). I lean toward: write the paper first, then return to DSL with a better-grounded invariant list. Path A now dominates Path B on informational density — the paper would be closer to publishable than the DSL would be to implementable.

2. **Whether to extend cross-model to additional models** (DeepSeek, Mistral) before writing. Cost per model ~$1-2 (cheap) or ~$15 for a Sonnet-class. 4 models is a stronger story than 3. But the Gemini finding alone ("does not generalize") is already adequate for the point. I lean against extending — diminishing returns.

3. **Whether to run the "E-AMBIGUITY" experiment** described in T22's next-steps list, varying content-quality on imperative blocks to characterize pathway B in finer detail. ~$0.30. I lean toward yes — it would turn pathway B from "observed" to "characterized."

## Cost Accounting

- Session 26 experimental spend: $0.72
- Session 27 (so far): ~$1.50 + Sonnet ongoing (expected $10–15) + Sonnet baseline ($0.12)
- All within the $50 per-experiment authorization.

## Working Conclusion

The corrective short paper is still the right target. It should expand from 4 pages to 6–8 to carry the three refinements (two pathways, multi-bullet emergent, cross-model limits). The paper is stronger than the session 26 version would have been. Sonnet data is the last decisive piece.
