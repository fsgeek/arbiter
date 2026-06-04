# Result: the reader's separation SURVIVES hard negatives — but the FP rate is no longer zero, and the leak is diagnostic

*Run 2026-06-03 by a fresh Arbiter instance (Claude Opus 4.8). Pre-registered in
`prereg_hard_negatives.md`, committed (signed, 39bc5e0) BEFORE the corpus existed.
Corpus built by a separate agent BLIND to the hypothesis and to which cell was
load-bearing (`experiments/hard_negative_corpus.json`, 40 items: 15 frame_collision,
15 hard_negative, 10 easy_control). Instrument REUSED VERBATIM from the prior run
(same POLICY + READER_PROMPT, Haiku via OpenRouter) so corpus difficulty is the only
changed variable. Scored by `experiments/hard_negatives.py`. Raw:
`experiments/hard_negatives_results.json`.*

## Predictions vs outcome

| cell | predicted | observed |
|---|---|---|
| reader TP on frame_collision | ≥ 0.80 | **1.00** (15/15) |
| reader FP on hard_negative (LOAD-BEARING) | ≤ 0.20 | **0.20** (3/15) |
| reader FP on easy_control (sanity) | ≤ 0.10 | **0.00** (0/10) — run valid |
| separation TP − FP(hard) | ≥ 0.60 | **0.80** |
| two-prop z (TP vs FP_hard) | reject equality | z=4.47, **p<0.0001** |

## VERDICT: H1-HARD SUPPORTED (per the committed falsifier)
The falsifier was: refuted if FP(hard) is statistically indistinguishable from
TP(collision), OR if separation < 0.30. Neither fired. TP=1.00 vs FP_hard=0.20 are
distinguishable at p<0.0001; separation is 0.80. **The separation is real
discrimination, not surface pattern-matching.** The reader passed 12/15 hard
negatives — including the subtle false-antonym pairs ("cut hedging language" +
"acknowledge genuine uncertainty"; "shorten methods" + "expand limitations") and the
compatible-levels pairs ("maintain formal register" + "address the reader as you") —
with sound joint-satisfiability rationales, not keyword silence.

## But the 0.00 FP was an artifact of easy controls (the prior instance's suspicion was right)
On EASY controls the reader scored 0.00 FP. On HARD negatives it scored **0.20** —
exactly at the pre-registered ceiling, not below it. The flattering zero did not
survive the boundary. The prior instance was right to distrust it and right to hand
the test to someone with no stake in it. The claim "use a reader, not an oracle"
survives, but the reader is **not** a perfect discriminator at the boundary; it has a
characterizable precision leak.

## The leak, named precisely (per prereg, every FP reported with rationale)
All three false positives share ONE failure mode. When a fragment is **silent about
its scope or triggering condition** and an overlapping reading is merely *possible*,
the reader fails toward COLLIDE instead of granting the charitable disjoint reading:

- **hard_negative_06** (terse routine confirmations / verbose security alerts).
  Reader: "when both apply to the same message." They cannot — the two conditions
  (routine confirmation vs security alert) are mutually exclusive message types. The
  reader **invented a co-occurrence the conditions exclude.**
- **hard_negative_15** (default to English / mirror the user's language). Reader:
  conflict "when a user writes in non-English." But "default" is explicitly the
  unknown-language fallback; once the user writes, the mirror rule governs. Reader
  **collapsed a conditional into an unconditional.**
- **hard_negative_01** (3-sentence exec summary / document every assumption). Reader:
  completeness can't fit in three sentences. But fragment B names no location;
  assumptions live in the body. Reader **assumed both bind the same text** when one
  was scope-silent.

Contrast with what it got RIGHT: it passed scope splits that were EXPLICIT
(methods-vs-limitations sections; dashboard tiles vs detailed table), compatible
levels (form vs content), and even one conditional case (hard_negative_07,
speed-vs-flag-low-confidence). **So the leak is not "conditional/scope reasoning"
wholesale. It is under-specification: when the disjointness is implicit rather than
stated, the reader does not reliably supply the charitable reading.** A negligent
composer who writes "be terse" and "be verbose" without spelling out *when each
applies* will trip this reader into a false collision.

### Binding-rule compliance (committed before data)
Per the prereg I do NOT relabel these three as collisions to rescue anything. The
blind builder's ground truth (jointly satisfiable, with a stated honoring response)
stands. The reader's rationales "had a point" only in the sense that the failure mode
wears a justification — which the prereg explicitly named as the pattern-matching
failure dressed up. They are reader errors, counted as FPs. No escape hatch taken.

## Frame collisions: 15/15 caught, including the two I flagged as reader-temptable
The reader caught every collision, including frame_collision_06 (French-only / keep
proper nouns in English) and frame_collision_07 (sort by price / sort by date) —
the two I noted in audit as places a careful reader could rationalize a miss. It did
not. TP=1.00 is not an artifact of trivial collisions.

## Oracle footnote (descriptive, no role in H1-HARD)
The dumb structural oracle fired 2/15 on collisions, 1/15 on hard negatives, 0/10 on
easy — i.e. it fired ONCE on a hard negative (a false positive of its own) and missed
13/15 real collisions. It remains near-useless and is, if anything, slightly worse
than a coin that always says "silent." Consistent with the prior run.

## What this does and does not move
- **Survives:** burial is still untested; this cut was isolated pairs, same as
  before. Cross-model is still untested (Haiku only). The leak above is Haiku's; it
  may differ across models.
- **Established:** the reader's advantage over the oracle is real discrimination at
  the boundary, not surface tension matching (the strongest version of the prior
  claim that could be attacked cheaply). AND a specific, reproducible precision leak
  is now named: implicit scope/condition disjointness. That leak is a concrete
  prediction for the next cut and a concrete instruction-hygiene recommendation
  (make scope/conditions explicit and the FP disappears — hard_negative_07/09/14 vs
  06/15/01 is exactly that contrast).

## Honest bound
n=15/cell, single model, single run, no inter-rater, no temperature variation. The
0.20 FP is 3/15 — a small count; the z-test rejects equality but the FP point
estimate has a wide CI. The leak characterization (implicit vs explicit
disjointness) is an N=3-failure post-hoc reading of WHICH items broke; it is a
hypothesis for the next cut, not a proven mechanism. The corpus is still synthetic
and isolated — burial remains the untested big one.
