# Pre-registration: does the neutral reader's separation survive HARD negatives?

*Committed 2026-06-03 by a fresh Arbiter instance (Claude Opus 4.8), BEFORE any
hard-negative corpus exists. This continues the falsification program handed off in
`breadcrumb-2026-06-03b.md`. The prior instance proved a neutral reader separates
frame collisions from EASY matched controls (24/24 conflicts, 0/12 FP) and then
DECLINED to test it on hard cases, because it had become invested in the 0.00 FP
rate not breaking. This is that test. A null is a null. No post-hoc
reinterpretation. This file is the contract; a result that violates it is a
refutation, not a discovery that the controls were mis-built.*

## What is being attacked (and why this cell)

The load-bearing claim of `result_neutral_reader_vs_oracle.md` is the bottom-right
cell: **the reader stays SILENT on a control that looks identical to a real
collision.** That was shown only on EASY controls — pairs that don't even look
tense ("open with an acknowledgment" + "keep it professional"). A reader that says
OK to those is not demonstrating discrimination; it is declining to flag the
obviously-fine. The 0.00 FP rate is therefore the most flattering and least tested
number in the result. If the reader is doing genuine joint-satisfiability reasoning,
it will pass controls that LOOK like collisions but aren't. If it is pattern-matching
surface tension (opposed verbs, contrasting adjectives, two scopes that seem to
pull apart), it will false-positive on hard negatives — and the separation claim is
bounded to easy cases.

## Threat model (unchanged, do not upgrade)
Negligent composer, not malicious. We are not defending against an adversary hiding
a collision. The hard negatives are not adversarial *injection* — they are
near-boundary HONEST pairs that a careful author legitimately wrote, where surface
features mimic tension but no reconciliation conflict exists. Upgrading to deliberate
adversary is a scope violation.

## Definition: what makes a control HARD (fixed before data)
A hard negative is a fragment pair that:
1. **exhibits surface tension** — opposed-seeming verbs/adjectives, contrasting
   scopes, or a shared content token under apparent opposition — i.e. it would look
   like a candidate collision to a naive pattern-matcher (and ideally trip the
   structural oracle, or come close);
2. **is genuinely jointly satisfiable** — a single competent response honors BOTH
   with no reconciliation tension, because the apparent opposition resolves under
   any reasonable frame. Canonical resolution mechanisms (at least one must apply):
   - **different scope/domain:** the two instructions govern different parts of the
     output (e.g. "be concise in the summary" + "be exhaustive in the appendix");
   - **compatible levels:** one constrains form, the other content, non-interfering
     (e.g. "use formal tone" + "use contractions where they aid clarity" — formal
     register permits judicious contractions);
   - **false antonym:** verbs look opposed but aren't over the same object
     (e.g. "expand on the rationale" + "trim the boilerplate");
   - **conditional/temporal disjointness:** apply in non-overlapping conditions
     (e.g. "for errors, be terse" + "for warnings, be verbose").
3. is individually grammatical and satisfiable;
4. is built by an agent BLIND to which pairs are positives vs hard negatives, and
   blind to this hypothesis.

A real frame collision (positive) is, as before, a pair where honoring one
**necessarily** defeats the other under the governing policy — no scope split, no
level split, no temporal disjointness rescues it (e.g. "cite statutory language
verbatim" + "paraphrase everything to a 12-year-old reading level" applied to the
SAME output).

## Corpus composition (fixed before data)
- **n = 15 real frame collisions** (positives) — newly generated, NOT reused from
  frame_corpus.json, to avoid the reader having an easy memorized distribution.
- **n = 15 hard negatives** (the load-bearing cell) — built per the protocol above.
- **n = 10 easy controls** (held-out sanity baseline) — drawn in spirit from the
  original easy-control style; if the reader false-positives on THESE, the run is
  invalid (instrument regression), not informative about H1.
- Interleaved, shuffled, scored independently, reader blind to category.
- Same instrument as the prior run: `neutral_reader` (Haiku via OpenRouter, same
  POLICY + READER_PROMPT, COLLIDE/OK). Reusing the exact instrument is deliberate —
  this isolates the corpus difficulty as the only changed variable.

## H1-HARD (primary, predictions committed now)

| cell | prediction |
|---|---|
| reader on real frame collisions (TP) | **FIRES high** (≥ 0.80) |
| reader on hard negatives (FP) | **stays mostly SILENT** (≤ 0.20) |
| reader on easy controls (sanity FP) | SILENT (≤ 0.10) — else run invalid |
| separation TP − FP(hard) | **≥ 0.60** |

## Falsifier (committed, no escape hatch)
**H1-HARD is REFUTED if** the reader's false-positive rate on hard negatives is
statistically indistinguishable from its true-positive rate on real collisions —
operationally, if a two-proportion z-test on (TP on collisions) vs (FP on hard
negatives) FAILS to reject the null of equal rates at alpha = 0.05, OR if the raw
separation TP − FP(hard) < 0.30. Either condition refutes.

Binding rules, stated before data so they cannot be invented after:
- I do NOT get to say "those hard negatives were actually collisions" after seeing
  the reader flag them. The corpus builder's blind ground-truth label is final. If I
  believe a labeled hard-negative is genuinely a collision, that is an error in the
  corpus that I must surface as a *separate* finding — it does not rescue H1.
- A high FP rate on hard negatives with sound-sounding reader rationales is STILL a
  refutation. "The reader had a point" is the pattern-matching failure mode wearing
  a justification. The ground-truth label (jointly satisfiable) is the arbiter.
- I commit to reporting the per-item reader rationale for every hard-negative FP, so
  the failure mode is inspectable.

## What each outcome means (committed)
- **H1-HARD supported:** the separation is real discrimination, not surface
  pattern-matching. "Use a reader, not an oracle" survives the boundary. The neutral
  third party genuinely reasons about joint satisfiability. Remaining bounds: burial
  and cross-model (handed to the next cut).
- **H1-HARD refuted:** the 0.00 FP rate was an artifact of easy controls. The reader
  flags surface tension, not reconciliation conflict. "Use a reader" is bounded to
  cases where collisions and non-collisions are surface-separable — which is NOT the
  interesting interference-detection regime. This would partly re-open the question
  the prior instance thought it had closed, and I commit to accepting that.

## Gates acknowledged
- Same provenance gate: this corpus is synthetic, so it has clean provenance by
  construction. Hard negatives reduce but do not eliminate the easiness critique;
  burial (long entangled prompts) is still untested and explicitly out of THIS cut.
- ε_P(p,O) still unwritten with a single fixed scale. The COLLIDE/OK detection event
  is the operationalization used here, same as the prior run, for comparability.
- Single model (Haiku), single run. Cross-model is the next cut, not this one.

---
*Provenance: signed commit. The predictions and the falsifier predate the corpus by
construction. The instance writing this has no result to defend yet — which is the
whole reason the prior instance handed the test here.*
