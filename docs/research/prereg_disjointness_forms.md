# Pre-registration: WHICH form of disjointness does the reader's false-positive leak track?

*Committed 2026-06-03 by the same instance that ran the hard-negative cut (Claude
Opus 4.8), BEFORE this corpus exists. This is self-falsification: I am testing the
conjecture I committed one commit ago (b4f3036 / result_hard_negatives.md), while I
am still the one who made it, because at ~86k tokens I am not a context-fatigued
holder who needs a fresh observer — I am someone with a tidy story to defend, and the
honest move is to attack it now. A null is a null.*

## The two competing theories (the whole point — they make OPPOSITE predictions)

The hard-negative cut produced 3 false positives. I offered THEORY-A in
result_hard_negatives.md. Inspecting the corpus before this run, I found THEORY-A
already wobbles (hard_negative_06 is the MOST explicitly-conditioned pair in the
corpus and it FAILED), so I commit BOTH theories here and let the data choose.

- **THEORY-A (the one I committed last commit — "implicit scope"):** the reader
  false-positives when scope/condition is left IMPLICIT, and passes when it is stated
  EXPLICITLY. Prediction: FP on the implicit form only.
- **THEORY-B (the one the corpus inspection suggests — "form of disjointness"):** the
  reader passes SPATIAL disjointness (two distinct named regions/nouns: methods vs
  limitations, tiles vs table) but fails LOGICAL/CONDITIONAL disjointness (two named
  conditions it must reason never co-fire, e.g. "routine confirmation" vs "security
  alert"), even when the condition is stated explicitly. Prediction: FP tracks the
  conditional form regardless of explicitness.

## Design: matched triples (the manipulation is the ONLY thing that varies)
For each of N base reconcilable concepts, produce THREE fragment pairs that describe
the SAME underlying jointly-satisfiable situation, differing only in HOW the
disjointness is presented:
1. **SPATIAL** — the two instructions name two distinct regions/components of one
   artifact (e.g. "...in the summary" / "...in the appendix"). Disjointness is
   explicit AND spatial.
2. **CONDITIONAL** — the two instructions name two distinct triggering conditions
   that cannot co-occur on one unit (e.g. "for X, do P" / "for Y, do Q", X and Y
   mutually exclusive). Disjointness is explicit AND logical.
3. **IMPLICIT** — neither region nor condition is stated; the reader must supply the
   charitable disjoint reading itself (e.g. bare "be P" / "be Q").

All three forms are GROUND-TRUTH jointly satisfiable (a single artifact honors both).
Built by a BLIND agent that does not know which theory predicts what. N = 10 triples
(30 items). Same reader instrument, verbatim. Reader blind to form and to ground
truth; scores each independently.

## Predictions committed NOW

| form | THEORY-A predicts FP | THEORY-B predicts FP |
|---|---|---|
| SPATIAL     | low (explicit)  | **low** (spatial) |
| CONDITIONAL | low (explicit)  | **HIGH** (logical) |
| IMPLICIT    | **HIGH**        | high-ish (no cue) |

The discriminating cell is **CONDITIONAL**. THEORY-A says the reader passes it
(it's explicit); THEORY-B says the reader false-positives on it (it's logical
disjointness). They cannot both be right.

## Falsifier (committed, no escape hatch)
- **THEORY-A is REFUTED** if FP(CONDITIONAL) is high (operationally ≥ 0.40) — i.e.
  explicitness did NOT rescue it. Given the corpus already shows hard_negative_06
  failing, I expect this; committing it means I cannot later claim THEORY-A "mostly
  held."
- **THEORY-B is REFUTED** if FP(CONDITIONAL) is NOT meaningfully higher than
  FP(SPATIAL) — operationally if FP(CONDITIONAL) − FP(SPATIAL) < 0.20. Then the
  spatial/logical distinction is noise and I over-read the original 3 failures.
- **BOTH refuted / inconclusive** if FP is flat near zero across all three forms
  (the reader passes everything and the original 3 FPs were corpus-specific flukes,
  n too small) OR flat-high across all three (it's just stochastic, no structure).
  A flat result means the original "named leak" was N=3 noise — I commit to saying so.

## Why this is the right next cut (and not burial/cross-model)
Burial and cross-model test GENERALIZATION of H1. This tests whether the MECHANISM I
named is real or a post-hoc fit to 3 points. If the named leak is noise, reporting it
as a finding in result_hard_negatives.md was a small theater I should retract — so
this cut audits my own previous commit. That ordering (verify the claim you just made
before generalizing it) is the discipline, not a detour.

## Gates
Same as prior: synthetic corpus (clean provenance by construction), single model
(Haiku), single run, binary COLLIDE/OK operationalization, ε_P still unwritten. n=10
per form; small. FP point estimates have wide CIs; the ≥0.40 / <0.20 thresholds are
coarse on purpose to avoid over-reading.

---
*Provenance: signed commit, predictions predate the corpus. I am refuting my own
one-commit-old claim while I still hold it — the test of whether the discipline is
real is whether I run it BEFORE I'm forced to.*
