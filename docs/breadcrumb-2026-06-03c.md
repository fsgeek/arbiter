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

## The new live wire — TESTED, same session (no longer a conjecture)
The "implicit-scope" conjecture got the matched-triple test I designed for the next
instance — I ran it myself rather than hand off a test that could embarrass my own
fresh claim (the dodge would have been the un-honest move at 86k tokens, not a
separation-of-duties move). Pre-reg e9bc0c7, result in
`result_disjointness_forms.md`. Outcome: a clean gradient, FP = spatial 0.00 /
conditional 0.20 / implicit 0.80, content held fixed. **IMPLICITNESS dominates;
conditional-exclusivity is a minor secondary leak; explicit spatial scope is
bulletproof.** This CORRECTED my own one-commit-old over-claim (which lumped implicit
+ conditional). I went in expecting to kill the implicit theory and the controlled
design refused to let me. Corrected note added to result_hard_negatives.md.

Actionable core that survives: a negligent composer writing two BARE directives trips
a false-collision ~80% of the time; the same pair scoped to named regions trips it
0%. The fix for the dominant leak is authoring discipline (state the scope), not a
smarter reader. The neutral reader is sufficient IF fragments say where/when they
apply.

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
