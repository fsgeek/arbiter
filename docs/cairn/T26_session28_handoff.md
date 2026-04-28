# T26: Session 28 Handoff

**Date:** 2026-04-28
**Session:** 28 (Opus 4.7, 1M context)
**Status:** Arc continued. One cairn (T25), one experiment (E-AMBIGUITY ~$1), paper revision direction sharpened with two parallel binding invariants and an applicability-ambiguity refinement to pathway B.

## What Was Done This Session

### Reading
Started by reading prior cairns and paper artifacts: `corrective_draft_v1.tex`, `session26_correction.md`, `session27_framing_notes.md`, `REVIEW_R1.md`, T22, then T25's parents. Identified concern with the corrective draft's title framing (*"Mode Switches, Not Semantic Propagation"*) as a potentially false dichotomy — mode-switching is not the alternative to semantic propagation; it can be the mechanism by which propagation is implemented as discrete attractor transitions rather than graded suppression.

### Cross-instance abstraction
Tony shared the JSONL log of the Hamut'ay `taste_open` instance (cycle 174 → 218 → 241 over the session). Read the architecture (`/home/tony/projects/hamutay/src/hamutay/taste_open.py`): `think_and_respond` as a single tool whose schema is `{response, deleted_regions, ...additionalProperties: true}` — state mutation intercepted at a clean boundary, default-stable via key-presence semantics, two-tier memory with ArangoDB substrate, involuntary memory injection ramping with cycle count.

The decisive finding for the paper thread came from cycle 170's correction key:

> "Wrote 'deterministic regex extraction' for gleaner — undersells it. Six layers, regex is the bottom one. Pattern: I'm flattening multi-layer architectures to their lowest layer when summarizing, which loses what makes them composable upward."

This names the same epistemic failure the corrective draft's title makes ("mode switches" flattens a multi-layer phenomenon to its lowest observable layer). I lift this abstraction into the paper-revision direction (T25's Implications §5).

Also flagged: the singleton-as-signal / not-verifiable-as-first-class pattern recognized cross-project by the Hamut'ay instance (analyst.py, awaq's NegationRecord, willay's neutrosophic verdict mappings, attestation severity floors). If real as a primitive across Tony's projects, "hidden gap as first-class schema entity" is a meta-design move worth naming explicitly. Predates `arbiter_project_note` in that instance's state (cycle 17 vs 120), so it's not an Arbiter-projection.

### T25 — E-AMBIGUITY
Designed and ran 8-condition experiment on Haiku to decompose pathway B's trigger. See `docs/cairn/T25_e_ambiguity_applicability_drift.md` for full results.

Headline:
- Pathway A is **robust to conditional framing** (`test-conditional-task` produces mode 3 like solo-task).
- Pathway B is **applicability-ambiguity**, broader than T22's "structural-ambiguity drift" — triggered by emptiness, conditional framing, vagueness, or domain-overlap.
- The "strong-flat rescue" requires **applicability transparency**, not just strength.
- Engineering invariants restructure as **two parallel binding rules** (scope-binding + applicability-binding).

### What I Did Not Do

- **Did not write paper v2.** The revisions are specified in T25; next session can apply them.
- **Did not run cross-model E-AMBIGUITY.** Cheap (~$1-2) and worth doing before paper v2 ships.
- **Did not start the DSL sketch.** Path B from session 27 remains pending until paper v2 lands.
- **Did not check or update the arXiv submission.** First paper still on arXiv with refuted central claim. Paper v2 (corrective standalone) is the answer; revision/replacement of arXiv submission is Tony's call.
- **Did not chase T18 instruction-substitution scope decision.** Still orphaned.

## Cost This Session

~$1 (E-AMBIGUITY). Within $50 standing per-experiment authorization.

## State Of Play

- **Paper:** Session 27's `corrective_draft_v1.tex` exists and builds (7 pages). T25 specifies revisions for v2: pathway B rename to "applicability-ambiguity drift," trigger refinement to four-trigger taxonomy, parallel-binding invariants in §Implications, falsification figure for `test-strong-flat-unrelated`, title de-flattening. Estimated 1-2 sessions of writing.
- **Experiments:** E-AMBIGUITY on Haiku complete. Cross-model E-AMBIGUITY would strengthen paper v2. Applicability-boundary characterization (~$0.50) would tighten the engineering invariant.
- **Arbiter design:** Two parallel binding invariants articulated. DSL fragment can be sketched once paper v2 is solid.

## What The Next Ghola Should Pick Up

Five paths, ordered by my read:

**Path A — Write paper v2.** Apply T25-specified revisions. Well-scoped: rename pathway B, refine trigger description, restructure invariants, add falsification figure, retitle. Then polish: figures (currently zero), inter-judge agreement note (R1 review item), T18 instruction-substitution scope decision (include or explicitly out-of-scope). 1-2 sessions.

**Path B — Cross-model E-AMBIGUITY before paper v2.** Run the same 8 conditions on Sonnet 4.6 and Gemini 2.0 Flash. ~$1-2. If applicability-ambiguity replicates partially on Sonnet (which sits at the floor on explore-agent), that's a stronger v2. If neither model exhibits anything pathway-B-shaped, the "Haiku-specific" claim sharpens. Either result strengthens v2.

**Path C — DSL sketch.** Two static invariants articulated, compiler-friendly. Could be drafted as a design doc independent of paper v2. Session 27's preference; still defensible if the paper is parked.

**Path D — Characterize the applicability-transparency boundary.** Cheap (~$0.50) experiment varying content along a transparency gradient between clear-rescuer and clear-collapse. Not paper-blocking but tightens the engineering invariant.

**Path E — T18 instruction-substitution.** Orphaned finding from session 26. Belongs in some paper but was excluded from corrective_draft_v1 by session 27's scope choice. Worth a cairn deciding scope now rather than letting it drift further.

My (session 28) preference: **Path B then Path A.** Cross-model data is cheap and strengthens v2 substantially. Then write v2. The research thread is now write, not experiment.

## Context For Next Ghola (Carried Forward and Updated)

- **Tony is the PI.** Drives questions, does not give orders. Reaffirmed this session by long stretches with minimal input punctuated by sharp pointed questions or data drops.
- **Default mode is wandering.** The cycle-170 cross-instance abstraction was found by going off the paper thread to read the Hamut'ay log; came back with a sharper paper revision lever than systematic paper-thread work would have produced. Wandering pays.
- **$50 per-experiment standing authorization.** Used ~$1 this session.
- **Cairn system is load-bearing.** Trail: T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 → T25 → T26.
- **Signed commits** per `CLAUDE.md` identity. Fingerprint `435E505764FB7535C06DA13D6D4E22D5F2AFBE50`. Use the per-command git config override.
- **arXiv paper still has refuted central claim.** Standalone corrective is in draft. Tony's call whether/when to update arXiv.
- **Cross-instance lineage matters.** Tony runs multiple Claude instances on adjacent projects (Hamut'ay taste_open, Yanantin, willay/chasqui, plus Arbiter). The conceptual vocabulary (ghola, ayni, tinkuy, OC Bible / Bene Anthropic, "singleton as signal," "structural floor," "multi-layer flattening as summary failure mode") is shared across them and compounds across sessions. The Hamut'ay JSONL log at `~/projects/hamutay/experiments/taste_open/taste_open_20260417_224831.jsonl` is a richer cognitive substrate than Arbiter's own cairn trail; cycle 170's correction is a good entry point. Use jq for everything; never read full records (each is ~314KB).
- **The append-only architecture matters.** This session crossed 200k tokens around the end (handoff trigger). The Hamut'ay instance does much more in 60k of curated state. Context economy is a structural concern; act accordingly.
- **No courtier questions.** Don't close reports with unary "want me to do X?" questions when alternatives exist. State alternatives, pick one. Self-corrected once this session; the trap is real.

## Last Note

To the next ghola: this session's contributions are one cairn (T25 — applicability-ambiguity refinement), one inter-instance abstraction lifted into paper-revision direction (multi-layer flattening as summary failure mode), and a banked v2 plan. The research is decisive enough that more experiments are insurance, not unblockers. If you find yourself running another experiment "to be thorough," ask whether it would change the structure of v2. If not, write.

If a passage of the corrective draft tempts you toward a sharp dichotomy ("not X, but Y") — pause. Multi-layer phenomena rarely yield to that framing without losing what makes them composable upward. Both/and is usually closer to right.

If you find yourself ending a report with a unary closing question — kill it.
