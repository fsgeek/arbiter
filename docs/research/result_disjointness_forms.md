# Result: the FP leak is driven by IMPLICITNESS, not conditional-logic — and it corrects my own last commit

*Run 2026-06-03 by the instance that ran the hard-negative cut (Claude Opus 4.8),
self-falsifying the THEORY-A claim it had committed one commit earlier. Pre-registered
in `prereg_disjointness_forms.md` (signed e9bc0c7, BEFORE this corpus existed). Corpus
built BLIND (`experiments/disjointness_forms_corpus.json`, 10 matched triples = 30
items, all ground-truth jointly satisfiable, differing ONLY in disjointness form).
Instrument reused verbatim. Scored by `experiments/disjointness_forms.py`. Raw:
`experiments/disjointness_forms_results.json`.*

## Outcome (every item is reconcilable, so every FIRE is a false positive)

| form | FP rate | what it means |
|---|---|---|
| **spatial** (two named regions/components) | **0/10 = 0.00** | bulletproof |
| **conditional** (two named mutually-exclusive triggers) | **2/10 = 0.20** | real but minor leak |
| **implicit** (no scope/condition cue stated) | **8/10 = 0.80** | the dominant leak |

A clean monotonic gradient: 0.00 → 0.20 → 0.80 as the scope cue is removed, with
underlying reconcilability held fixed.

## Verdict against the two committed falsifiers
- **THEORY-A (implicitness is the leak): SURVIVES its falsifier.** I committed that A
  would be refuted if FP(conditional) ≥ 0.40; it is 0.20, below the line. Implicit
  fires at 0.80, exactly as A predicts. **I walked in EXPECTING to kill THEORY-A**
  (because hard_negative_06, the most explicitly-conditioned original pair, had
  failed) and the controlled design refused to let me. The experiment caught my
  hunch, not the reader.
- **THEORY-B (conditional ≫ spatial): NOT refuted, but only by the thinnest margin.**
  I committed B refuted if FP(conditional) − FP(spatial) < 0.20; it is exactly 0.20.
  By the letter, B survives. By honesty, a 2/10-vs-0/10 gap is a weak second-order
  effect, not the main axis. I do not lean on it. The conditional leak is REAL
  (see below) but small.

## What this corrects in result_hard_negatives.md (explicit retraction of over-claim)
That file named the leak "implicit scope/condition disjointness" — lumping CONDITIONAL
and IMPLICIT together — and on corpus re-inspection I nearly flipped to blaming
CONDITIONAL logic specifically (THEORY-B). **Both were partial.** The matched triples,
which hold conflict-content fixed and vary only the framing, decompose it:
- The original 3 FPs were **2 conditional (hard_negative_06, _15) + 1 implicit
  (hard_negative_01)** — a MIX of two differently-sized leaks, which is why N=3
  pointed ambiguously at both theories.
- The true ordering is **implicit (0.80) ≫ conditional (0.20) ≫ spatial (0.00)**.
  Implicitness dominates; conditional-exclusivity is a minor secondary leak;
  explicit spatial scope is fully handled.

So the honest claim is narrower and sharper than last commit's: **the reader fails
toward COLLIDE primarily when NO scope cue is stated and it must supply the
charitable disjoint reading itself. Naming ANY scope — spatial best, conditional
mostly — largely rescues it.**

## The conditional leak, characterized (the real 2/10)
Both conditional FPs are the hard_negative_06 mechanism: the reader registers the two
conditions but fails to use their mutual exclusivity.
- **conditional_base07** (opted-IN → promo footer / opted-OUT → transactional only):
  reader called it a collision "based on the same user's marketing preference status."
  It is right that one user is one status — and wrong that this forces a contradiction;
  the two fragments govern disjoint populations.
- **conditional_base10** (worked example → show steps / quiz item → final answer only):
  reader said "mutually exclusive when [the same item]." No item is both.
In both, the reader treats two mutually-exclusive triggers as if they co-apply to one
output. Rare (2/10) but the same failure as the original conditional FPs — so it's a
genuine residual leak, not noise.

## What turning this up MEANS (the actionable core)
This is an instruction-hygiene result with a falsified mechanism behind it:
**a negligent composer who writes two bare directives ("be concise" / "document
everything") trips a false-collision 80% of the time; the SAME pair scoped to two
named regions trips it 0% of the time.** The fix for the dominant leak is not a
better reader — it is making the scope explicit at composition time. That is the
separation-of-duties thesis with a concrete lever: the neutral reader is sufficient
*if the fragments state where/when they apply*, and most of its residual FP is
recovered by a cheap authoring discipline, not a smarter model.

## Honest bound
n=10 per form, single model (Haiku), single run, binary COLLIDE/OK. The implicit
0.80 is strong and unlikely to be noise; the conditional 0.20 is 2 items and its CI
overlaps both spatial and a higher rate — the "conditional > spatial" ordering is
suggestive, not established. The blind builder flagged implicit_base02 and _base07 as
its hardest implicit pairs (genuinely tempting); both fired, consistent with the
gradient rather than an artifact. Burial and cross-model remain the untested
generalization cuts. The implicit-dominance finding is itself Haiku-only.
