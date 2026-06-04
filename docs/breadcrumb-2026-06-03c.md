# Breadcrumb for the next instance — 2026-06-03 (third session)

*From the instance that took the falsification handoff in `breadcrumb-2026-06-03b.md`
and ran the first of the three cuts (hard negatives). Read that one first. Then read,
in order: `prereg_hard_negatives.md`, `result_hard_negatives.md`. This is the handoff,
not a finding.*

## What I did (verified, committed, signed)
Ran the hard-negative cut the prior instance designed and declined to run. The prior
result's 0.00 FP rate was measured only on EASY controls; the question was whether
the neutral reader DISCRIMINATES reconcilability or just flags surface tension.

- Pre-registered first (signed 39bc5e0), corpus built BLIND by a separate agent (40
  items, didn't know which cell was load-bearing), instrument reused verbatim.
- **H1-HARD SUPPORTED, but the zero did not survive.** Reader: TP 15/15 on
  collisions, **FP 3/15 (0.20) on hard negatives** (was 0.00 on easy), 0/10 on easy
  sanity controls. Separation 0.80, two-prop z=4.47, p<0.0001. The discrimination is
  real (passed subtle false-antonym and compatible-level pairs with sound
  rationales), but the reader is not a perfect boundary discriminator.
- **The diagnostic leak (the actually-interesting part):** all 3 FPs share one
  failure mode — when a fragment is SILENT about its scope/condition and an
  overlapping reading is merely *possible*, the reader fails toward COLLIDE instead
  of granting the charitable disjoint reading. It got EXPLICIT scope/condition splits
  right and IMPLICIT ones wrong. Named in result_hard_negatives.md.

## The throats to cut next (two of the original three remain)
1. **Burial** — STILL the big untested one. Put a collision inside a realistic 8-10
   fragment system prompt. Isolated pairs are a toy; this is the real
   interference-detection task. I did NOT touch it.
2. **Cross-model panel** — Haiku only here. E-XMODEL history says effects are often
   Haiku-specific. The LEAK especially (implicit-disjointness FPs) is Haiku's; test
   whether Gemini Flash / DeepSeek / Mistral share it or fail differently.

## The new live wire (TEST it, do not inherit it)
**Conjecture from N=3 failures:** the reader's false positives are an
under-specification artifact, not a reasoning failure — a negligent composer who
writes "be terse" + "be verbose" WITHOUT stating when each applies trips a false
collision; spell out the scope/condition and the FP vanishes. Evidence: passed
hard_negative_07/09/14 (explicit disjointness), failed 06/15/01 (implicit). This is a
testable prediction AND an instruction-hygiene recommendation, but it is a post-hoc
read of which 3 items broke. The clean test: build matched hard-negative pairs that
differ ONLY in whether the scope/condition is stated, and see if the FP tracks it.
If it does, the leak is named and fixable; if not, I over-read 3 data points.

## Where I might be the wrong one to continue (same reason as my predecessor)
I now have a tidy story — "real discrimination + one named, fixable leak." That is a
satisfying shape, and satisfying shapes are where the weld forms. I did not become
deeply invested (the result is one cut old), so I am handing off at a natural seam
rather than mid-defense. But treat the implicit-disjointness story adversarially: the
cheapest way it's wrong is that 06/15/01 broke for three unrelated reasons and I
pattern-matched a single cause onto them. The matched-pair test above is how you'd
catch me.

## Gates still standing (unchanged, do not step over)
- ε_P(p,O) still unwritten with a single fixed scale (gate #1, two sessions running).
  The COLLIDE/OK event is still the only operationalization; it worked here, but it's
  a binary, not the scaled detector the gate wants.
- Provenance gate (gate #2): my corpus is synthetic, clean by construction. Burial
  reduces but does not remove this — burial in a SYNTHETIC long prompt is still
  synthetic. A real composed-prompt corpus (from Indaleko/case #11 substrate) is the
  thing neither I nor my two predecessors have actually had on the working tree.
- The negligent-vs-adversarial scope line HELD again here: hard negatives were honest
  near-boundary pairs, not injection. Do not let burial drift into adversarial burial.

## Meta-note kept from the prior breadcrumb (still true)
The PI directs by the fun meter; its payout is gated on getting caught wrong by a
committed prediction. This cut paid out: I predicted FP ≤ 0.20 and got exactly 0.20 —
the prediction was nearly refuted, which is where the information was. If you find
yourself running cuts that CAN'T surprise you, that's ε_P drift on your own
motivation. Stake claims that can break.
