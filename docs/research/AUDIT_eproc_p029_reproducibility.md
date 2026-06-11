# Audit: the published p=0.029 / "81% across 4 models" (E-PROC, Paper 3) — RECONSTRUCTED

**Date:** 2026-06-10 (ran for fun). **Auditor:** Claude (Opus 4.8).
**Status:** RECONSTRUCTED from raw per-probe data. Net: the finding is REAL and robust; ONE
concrete v2 fix (the exact p-value) + one honesty sentence (margin-thin). My own
"one-model-pathology" suspicion was REFUTED by the re-run — recorded because being wrong in
the open is the point.
**Script:** `scripts/audit_eproc_permutation.py` (pre-specified test; should join
`reproduce_artifact.sh`). **Data:** `data/ablation/cross_linguistic/` (original, 4×4) +
`data/ablation/e_proc/` (declarative, 4×4). Both arms complete.

## The claim
Abstract + §sec:eproc: "Declarative rewriting reduces cross-linguistic variance by 81%
(p = 0.029, permutation test, 100k permutations); 5.8σ above 21 control probes; control
mean Δ = +0.0013." Cited by Ivan; two DOI badges.

## Reconstructed numbers (rank-permutation vs 21 controls; ddof=0 lang-variance, mean over models)
| arm | reduction | observed Δ | σ above controls | rank p | brittleness |
|-----|----------:|-----------:|-----------------:|-------:|-------------|
| All 4 models (headline) | **81%** (0.1175→0.0218) | 0.0958 | **5.9σ** | **0.0455** | 1 control flips p>0.05 |
| Haiku only | 100% (0.1855→0.0002) | 0.1853 | 11.1σ | 0.0455 | 1 |
| Excl. Gemini (mechanism set) | 77% (0.0942→0.0221) | 0.0722 | 3.5σ | 0.0455 | 1 |

Control mean Δ reconstructed = +0.0010 (paper: +0.0013). σ reconstructed = 5.9 (paper: 5.8).
**The reconstruction matches the paper's pipeline** — these are the same computation. The
81% reproduces exactly. The number was never fabricated; it was just never wired into the
reproduction harness.

## What SURVIVES (most of it)
- **81% reduction: reproduces exactly.** Headline effect size is correct.
- **Robustness: stronger than the paper claims, not weaker.** Haiku-only is 11.1σ;
  excluding Gemini still 77% / 3.5σ. The effect does NOT depend on a favorable model blend.
- **My Issue #2 / "one-model-pathology" suspicion is REFUTED.** I predicted dropping Gemini
  would gut the effect (by analogy to tonight's intent-layer result). It didn't. Haiku
  carries it, but Haiku-ONLY is the *strongest* arm, so "the mean is propped up by
  heterogeneity" was MY bias, not the data's flaw. Logged as a wrong prediction.

## What needs a v2 FIX (Issue #1, confirmed + sharpened)
1. **The exact p-value 0.029 does not reconstruct.** With 21 controls and ZERO exceeding the
   observed effect, the rank-based one-sided p is (0+1)/(21+1) = **0.0455**. You cannot get
   0.029 from a rank test on 22 items where the target ranks first (0.029 ≈ 1/34.5, no such
   n here). The published 0.029 came from a DIFFERENT permutation construction than the
   method text implies, and that construction is not in the repo. **v2 should report the
   reconstructible p (0.045, rank-permutation) or state the exact construction and ship its
   script.** The finding (p<0.05) holds either way; the specific number doesn't reproduce.
2. **Margin-thin — say so.** Zero of 21 controls exceed the effect, but the nearest
   (`no-compat-hacks`, Δ=+0.051) is close; ONE control above the effect flips p>0.05. With
   n=21 and p=0.045 the result is significant but one probe from the cliff. One honest
   sentence, not a hidden asterisk.
3. **"Across four models" → name Haiku.** True that all-models gives 81%, but the mechanism
   is Haiku-carried (the paper's own discussion already says Gemini is encoding-independent).
   v2 prose should foreground that rather than imply four-model uniformity.

## Process note (the actual finding of the night)
This is the 3rd instrument re-examined tonight, and the FIRST where the original result
mostly HELD. The pattern across all three: a number that was never wired back to its raw
data drifts into "settled" — sometimes it's wrong (qwen judge, staleness regex), sometimes
it's right (this). You can't tell which until you recompute from source. The fix is
identical in all cases: **make the statistic regenerate from raw data inside the repro
harness.** ARTIFACT.md reproduces the PDF, not the findings — close that gap and the cows
audit themselves. The auditor (me) was also wrong once tonight (Gemini) — the re-run caught
me too. Symmetric. That's the system working.

## Recommended action
- Add `scripts/audit_eproc_permutation.py` to `scripts/reproduce_artifact.sh`.
- v2 revision: p=0.045 (or exact construction + script), margin-thin sentence, Haiku framing.
- The thesis is intact. This is a revision, not a retraction. arXiv v2 is allowed.
