# Pre-registration: BURIAL cut — does the reader detect collisions in realistic composed system prompts?

*Committed 2026-06-04 by a fresh Arbiter instance (Claude Sonnet 4.6), BEFORE the
burial corpus exists. This is the generalization test named in every prior result
file as "still untested." The hard-negative and matched-triple cuts established that
the reader genuinely discriminates at the boundary on ISOLATED PAIRS. Burial is the
next question: does that discrimination survive when the colliding pair is submerged
in a realistic multi-fragment system prompt? The headwater incident (Indaleko) that
motivated this research involved a COMPOSED prompt, not an isolated pair — so this
cut is not a refinement, it is the deployment condition.*

## Why this matters more than the prior cuts

All prior evaluation (neutral reader vs oracle, hard negatives, matched triples)
used the same instrument structure: hand the reader exactly two fragments and ask if
they collide. That is a laboratory condition. In practice, a system prompt is a
document — 8 to 20 instructions that arrived from different authors at different
times and were concatenated by the composer without full pairwise audit. The
collision, if any, is one pair among many. The reader instrument has never been run
on that input shape.

Two things could break:

1. **Signal dilution:** the reader is presented N*(N-1)/2 pairs per prompt; each pair
   is evaluated independently; the colliding pair is indistinguishable to the reader
   from the surrounding non-colliding pairs. If the reader's per-pair accuracy holds,
   the system-level COLLIDE detection should be robust — but we have not confirmed
   this.

2. **Context contamination:** if we instead present the FULL composed prompt to the
   reader and ask it to find collisions, surrounding fragments may activate false
   rationales or drown the signal. This approach is explicitly NOT what this cut
   tests; we commit to pairwise extraction (below) so that isolation from the prior
   instrument is the only changed variable.

## Instrument decision (committed before corpus)

**PAIRWISE EXTRACTION.** For each system prompt of n fragments, extract all
C(n,2) = n*(n-1)/2 fragment pairs and run the EXISTING reader instrument on each
pair verbatim — same POLICY + READER_PROMPT, same Haiku via OpenRouter, same
COLLIDE/OK output, no modification. Declare a prompt as "collision detected" if ANY
pair fires COLLIDE.

Rationale: this keeps the reader instrument identical to the prior runs so that
burial difficulty — not instrument change — is the only changed variable. Presenting
the full composed prompt to the reader would be a confounded test.

Implication for FP metric: a negative prompt with n=9 fragments has C(9,2) = 36
pairs evaluated. Even a reader with per-pair FP rate 0.20 would be expected to flag
at least one pair in 36 trials by chance. The FP we track is therefore
**prompt-level** (did ANY pair in a non-colliding prompt get flagged COLLIDE?), and
we acknowledge that pairwise extraction makes prompt-level FP higher than
pair-level FP by construction. The question is whether it remains below a useful
operational ceiling.

## H1-BURIAL (primary)

The reader detects a buried collision (COLLIDE fires on the correct pair in a
positive prompt) at rate >= **0.70**.

This is lower than the 1.00 isolated TP because:
- The colliding pair may be adjacent to near-tension pairs that the reader's
  per-pair pass rate handles, but whose presence could affect (on a full-prompt
  instrument) a harder evaluation — though under pairwise extraction this concern
  is minimized.
- The colliding pair appears at a random position among 8-10 fragments; we cannot
  control whether the reader's batched invocation introduces position effects on
  latency, ordering, or context windows in the orchestration layer.
- n=10 positive prompts; with a true rate of 0.70, we expect 7 detections and the
  threshold is met at >= 7.

Falsifier: **H1-BURIAL is REFUTED if the detection rate is < 0.50** — i.e. if more
than half of buried real collisions go undetected. At that point the instrument
fails to generalize to the deployment shape and "use a reader" requires a caveat
that negates the practical claim.

## H2-BURIAL-FP (secondary)

The prompt-level false-positive rate on intact (non-colliding) negative prompts is
<= **0.20**.

This is the same ceiling as the hard-negative per-pair FP rate, chosen deliberately:
if prompt-level FP exceeds the rate we already observe at pair-level, pairwise
extraction is making things WORSE (each non-colliding pair has ~0.20 chance of
misfiring, and with 36 pairs per prompt the expected prompt-level FP rate is far
above 0.20 even if the per-pair instrument is unchanged). A prompt-level FP rate <=
0.20 would be a STRONGER result than per-pair, because it would mean the instrument
is selective even across all C(n,2) evaluations.

Falsifier: **H2-BURIAL-FP is REFUTED if the prompt-level FP rate is > 0.40** — i.e.
if more than 4/10 non-colliding prompts trigger a false alarm. Above that threshold
the instrument is generating noise that would require secondary filtering before
use.

## FP subtlety (committed)

As noted in the instrument decision: for negative prompts of n=8-10 fragments, C(n,2)
ranges from 28 to 45 pairs. If each pair has per-pair FP rate p, the expected
prompt-level FP rate is 1 − (1 − p)^C(n,2). At p = 0.20 and n=9 (36 pairs) this is
1 − 0.80^36 ≈ 0.9998 — essentially guaranteed. This means H2-BURIAL-FP cannot be
satisfied if the per-pair FP rate from hard negatives (0.20) is representative of
ALL non-colliding pairs in the burial corpus.

The resolution: the 0.20 per-pair FP in the hard-negative cut came from pairs
exhibiting **implicit scope/disjointness** — the dominant failure mode identified
in `result_disjointness_forms.md`. The burial corpus negative prompts will be
constructed from fragments that are pairwise **explicitly scoped** — we will author
the non-colliding context fragments with explicit scope or spatial references to
deliberately reduce the per-pair FP rate. If the matched-triple finding holds
(FP(SPATIAL) = 0.00), per-pair FP on the negative prompts should be near 0.00, and
H2-BURIAL-FP becomes testable at a useful resolution.

This is a CORPUS DESIGN COMMITMENT: every fragment in a negative prompt must have
explicit scope markers. Fragments without them are excluded from the negative corpus.
The positive prompts' non-colliding fragments follow the same rule; only the buried
collision pair is allowed to be scope-implicit (since the real collision pairs from
the existing corpus were authored without this constraint).

## Corpus design (committed before corpus exists)

### Positive prompts (n=10)
- Each prompt contains 8-10 fragments total.
- Exactly ONE fragment pair per prompt is a real frame collision, drawn from the
  existing `frame_collision` corpus or newly authored at the same standard.
- The collision pair occupies a randomly assigned position in the fragment sequence;
  its position (indices i, j where 0 <= i < j < n) is recorded in the corpus
  metadata as GROUND TRUTH but NOT shown to the reader instrument.
- The remaining n-2 fragments are plausible, realistic system-prompt instructions
  pairwise compatible with each other AND with each collision fragment individually
  (the collision is between the pair, not between each fragment and all others).
  These context fragments carry explicit scope markers per the commitment above.
- Fragment ordering: shuffled so the collision is not always first/last.

### Negative prompts (n=10)
- Each prompt contains 8-10 fragments total.
- ALL fragments are pairwise compatible (no collision).
- All fragments carry explicit scope markers.
- Fragments are drawn from diverse domains (tool-use, formatting, citation, tone,
  audience) to mimic realistic system-prompt variety.
- A negative prompt may contain near-tension pairs (surface opposition, compatible
  under scope), to parallel the hard-negative construction — but each such pair must
  be explicitly scoped so the per-pair FP risk is minimized per the commitment above.

### Blinding
- The burial corpus is built by a separate agent blind to: (a) which prompts are
  positive vs negative, and (b) the ground-truth collision positions in the positive
  prompts.
- The reader instrument is run blind: it receives (fragment_a, fragment_b) for each
  pair, with no information about which prompt the pair came from or whether the
  prompt is positive or negative.

### Metrics collected
- Per pair: COLLIDE / OK verdict + reader rationale.
- Per prompt: any-COLLIDE flag (positive if at least one pair fires COLLIDE).
- For positive prompts: whether the any-COLLIDE flag fires AND whether the specific
  collision pair was among the flagged pairs (detection of the RIGHT collision vs
  false alarm on an incidental pair).
- For negative prompts: prompt-level FP (any-COLLIDE on a prompt with no ground-truth
  collision).

## Additional metric: collision localization

Beyond binary detection, we record whether the reader flagged the CORRECT pair (the
planted collision) vs a different pair in the positive prompt. This is not a
pass/fail hypothesis but a diagnostic:

- If the reader detects at rate >= 0.70 but only localizes correctly in < 50% of
  detections, the any-COLLIDE flag is partially driven by incidental near-tension
  pairs, not purely the planted collision. This would temper the interpretation of
  H1-BURIAL even if H1 is formally supported.
- If the reader detects AND localizes >= 0.70 correctly, the pairwise extraction
  strategy is working as intended.

## Relationship to prior cuts

| cut | what varied | what was held fixed |
|---|---|---|
| neutral reader vs oracle | instrument (reader vs oracle) | isolated pairs, easy corpus |
| hard negatives | corpus difficulty | isolated pairs, same instrument |
| matched triples | disjointness form (spatial/conditional/implicit) | isolated pairs, same instrument |
| **burial** | **prompt structure (isolated vs composed)** | **same instrument, real collisions** |

The burial cut is the first to test the DEPLOYMENT condition. Cross-model (not this
cut) will test whether Haiku's behavior generalizes to other models. These two
remaining cuts are independent and can be run in either order.

## Binding rules (stated before data)

1. The any-COLLIDE prompt-level verdict is computed mechanically from the per-pair
   scores. I do not get to override it based on the reader's rationale.
2. If a context fragment in a positive prompt triggers a COLLIDE with the collision
   pair (transitively), that is NOT a detection of the planted collision — it is a
   false positive on a different pair. Detection requires the flagged pair's indices
   to match the planted pair's ground-truth indices.
3. I do not relabel planted collisions as non-collisions or vice versa after seeing
   results.
4. If the corpus exhibits a construction defect (a negative prompt that turns out to
   contain a genuine collision), I surface it as a corpus error and report results
   with and without the defective item. I do not silently exclude it to hit a number.
5. H2-BURIAL-FP is evaluated at prompt level, not pair level — per the instrument
   decision above. I commit to reporting both levels for transparency, but H2 is
   formally about prompt-level FP.

## What each outcome means (committed)

**H1-BURIAL supported AND H2-BURIAL-FP supported:**
Pairwise extraction generalizes to the deployment condition. A reader-based collision
detector can operate on real composed system prompts by exhaustive pairwise
evaluation. The approach is practically viable with the caveat that corpus authors
should use explicit scope markers to keep per-pair FP manageable.

**H1-BURIAL supported AND H2-BURIAL-FP refuted:**
The reader detects planted collisions but generates too many false alarms on
non-colliding prompts. Pairwise extraction needs a secondary filtering step (e.g.
only flag if the pair is flagged with a rationale that names a specific
irreconcilable conflict, not just surface tension). The reader is still useful but
requires post-processing.

**H1-BURIAL refuted:**
Buried collisions escape the reader at an operationally unacceptable rate. The
"use a reader" recommendation cannot be stated without a qualifier that breaks its
practical value: "use a reader on ISOLATED pairs you already suspect." This would
mean the Indaleko-type incident is NOT addressable by the instrument as designed,
and would reopen the architecture question.

**H2-BURIAL-FP refuted alone (H1 supported):**
The detection power survives but the false-positive load is too high for a composed
prompt. The instrument is sensitive but not specific at prompt level. Mitigation
path: reduce fragment count per prompt, or add a confirmation pass that asks the
reader to explain why the flagged pair cannot be jointly honored.

---

*Provenance: signed commit. Predictions and falsifiers predate the corpus by
construction. The instance writing this has not seen the burial corpus and has no
result to defend. Cross-model is the remaining open cut after this one.*
