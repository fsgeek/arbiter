# Spine Audit — what an adversarial pass found in the conversation-built model

*Recorded 2026-06-03 by the Arbiter instance (Claude Opus 4.8), after dispatching
three read-only scourers (one substrate-grounding, one weld-breaking, one
adversarial skeptic) to attack a model built across a single conversation with
Tony Mason. The instance had, by its own admission, "adopted the model" and was
therefore the wrong party to grade it. This file records what broke, so the next
instance does not rebuild the same spine and make the same welds.*

*Methodology note: this audit is itself an instance of the project's central
claim. The instance resolved conflicts across the conversation (welded two
documents, dodged an impossibility proof, named a "law") and could not see it had
done so — the executor could not audit the executor. External observers found all
four. That is Arbiter's thesis, demonstrated on Arbiter's author-instance.*

---

## The root failure (the weakest joint, beneath the others)

**`epsilon_P` was never written down.** It existed only in conversation. A
grep of the corpus confirms `epsilon_P`, `C(p)`, "structural-incoherence
oracle", and `P_d` appear in no Arbiter document. Because the definition was
unwritten, it silently shifted scale to fit whatever data was in front of it:
within-instruction clarity for the 81% number, cross-layer granularity for
case #11, between-instruction topology for the inversion. **An undefined metric
cannot fail an experiment, so it cannot pass one either.** All four breaks below
are symptoms of this one undefined term doing load-bearing work.

This is the same unfalsifiable-by-flexibility failure the instance had, one turn
earlier, correctly attacked in the haber/ser/estar architecture. The instance
committed the identical sin in its own metric in the same breath, unseen.

## What broke

1. **The `epsilon_P` / Paper 3 weld — REFUTED.** The claim that Paper 3's "81%
   variance reduction" and the cross-linguistic topology inversion are both
   measurements of one quantity (residual incoherence) is false and fabricated in
   the retelling. Verified against `social_register/main.tex`:
   - 81% (0.1567→0.0290, p=0.029) is a **within-instruction** encoding-clarity
     metric — variance of a single block's adherence across language/model cells.
   - Topology inversion (r=−0.274) is a **between-instruction** interaction-structure
     metric. They measure different scales and co-vary independently.
   - Paper 3 frames **both** as social-register effects, **not** as instruction
     contradictions. The word "incoherence" appears **zero** times in the paper.
   - The numbers are honest and correctly reported. The *framing* welded them.

2. **The impossibility-proof dodge — REFUTED.** "Define safety on prompt
   structure, not model behavior, and you escape the epistemic-honesty
   impossibility proof" is false. The oracle does not escape the impossibility;
   it **relocates** it. The Indaleko headwater itself proves coherence is
   context-relative: the same prompt is coherent under synthetic scale and
   incoherent under production scale (28.5M files). A human labeler building the
   oracle cannot make that distinction without observing external operating
   context. The gap moves from "model internals opaque" to "operator
   decision-context opaque" — same FLP shape. **Consequence: the metric must be
   `epsilon_P(p, O)`, relative to a named operating context O (data scale,
   indexing status, jurisdiction, binding moment), not `epsilon_P(p)`.**

3. **The "intent-blind / malice == negligence" claim — REFUTED on a class.**
   Structural defense is NOT intent-blind across all incoherence. It is blind to
   **frame-relative** incoherence — conflict living in the pragmatics of
   reconciliation, not surface syntax. Skeptic's counterexample: Fragment A
   "MUST preserve the nuance of *Werdegang*" + Fragment B "simplify all terms to
   monosyllabic English" — both individually correct, both grammatical, conflict
   only in frame reconciliation. The structural oracle returns C=0 ("clean") and
   **fails silently**, giving no signal it is wrong. This is the same blind spot
   the weld exposed: register/frame incoherence is a *different type* than
   binding-conflict, and the proposed oracle only catches the latter. This is
   exactly where the mixed-language survivor (and `epsilon`) lives.

4. **The "three witnesses = one law" claim — PARTIALLY BROKE (instance-generated
   gloss).** Indaleko / FNMA case #11 / 10-Q share a family resemblance but no
   demonstrated isomorphism. Indaleko = two live instructions + unobservable
   disambiguating context. FNMA = one constraint at wrong granularity. 10-Q = one
   ontology layer true while another is false. "All hiding in gaps" is
   abstraction-to-vacuity where gaps are defined post-hoc. `headwater.md` does not
   invoke FNMA or 10-Q; `blueprint-correction-note.md` never says "law" or
   "isomorphism." The unification is the instance's synthesis, not PI testimony or
   documented source. Downgrade to: "three cases worth testing for isomorphism,"
   pending a mathematical demonstration.

5. **haber/ser/estar falsifiability — SURVIVED, CONDITIONALLY.** Not refuted, but
   not yet sharp. The strawman's falsification bound is "band-level encoding
   preserves substantially better" — "substantially better" is unquantified; N,
   X%, and fail/preserve fractions are named as commitments-to-be-made, not made.
   Each cross-layer gap is documented as a research finding, so a negative result
   can be reinterpreted post-hoc ("the binding moment was not operative," "the
   scope was wrong"). As written it is a flexible framework gesture, not a
   falsifiable hypothesis. The pre-registration discipline is the right guard but
   **has not been executed on the substrate.**

## What is grounded (survived verification)

- **Case #11 is real**, down to the feature-size histogram. `mandatory_features`
  is a flat 13-feature per-member YAML list; institutional commitment is at band
  level and incompatible-by-construction with depth-3 trees (split on ≤7
  features); FM-cell trees empirically use 1–5 features (corpus histogram
  size-1:43 / 2:386 / 3:940 / 4:615 / 5:86 / ≥6:0); structure lives in unnameable
  `property_state` (R²_named 0.022–0.035 vs R²_all 0.580–0.961). Sources:
  `governance/docs/superpowers/specs/2026-05-12-...preregistration-note.md`,
  `...2026-05-13-...result-note.md`, `governance/runs/fm_rich_policy_vocab_adequacy_2016Q1.json`.
  **This is the most grounded thing in the corpus and is ready to serve as the
  first-experiment substrate.**
- **The Indaleko headwater** is grounded against commits 24f1885 / 2f77fce /
  d6928bb (see `headwater.md`).
- **Paper 3's two numbers are honest** (81% and r=−0.274), individually real and
  correctly reported. The error was framing, not data.
- **The epistemic-honesty impossibility** (text-only observation cannot verify
  internal epistemic state; FLP-shaped) is grounded in ai-honesty.

## Gating verdict for the first falsification experiment

**No honest first experiment can run yet. The gate is the definition, not the
data.** Two artifacts must be committed to files before anything is
capable-of-failing:

1. A written `epsilon_P(p, O)` with a **single fixed measurement scale** (pick
   one: within-instruction clarity / between-instruction topology / cross-layer
   granularity — Paper 3 proves they dissociate) and a **pinned conflict class**
   for C (syntactic opposition / semantic frame mismatch / granularity failure —
   and own that the oracle is blind to frame-relative pragmatics).
2. The strawman's **N, specific canonical inferences, X% thresholds, and expected
   fail/preserve fractions**, committed in writing with a
   **no-post-hoc-reinterpretation rule** (a failed prediction is a refutation, not
   a discovery of which layer was mis-specified).

Then the case #11 FNMA license-preservation suite (currently **to-be-built** — no
implementation exists in either repo) is the right first experiment, because its
substrate is the most grounded thing available.

## Corrections to prior artifacts in this conversation

- `headwater.md` states "NL fragments have no type system to check the seam" and
  treats prompt injection as the weaponized special case of negligent
  composition. Per break #3, the seam-checking it implies is blind to
  frame-relative incoherence; the "type system" metaphor over-promises. The
  negligence-not-malice arrow is sound; the claim that a structural checker is
  *intent-blind across all classes* is not.
- The "three-witness law" framing, if it propagates, should carry break #4: it is
  a conjecture of isomorphism, not an established one.
