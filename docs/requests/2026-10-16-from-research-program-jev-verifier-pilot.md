# Request from research-program: a Jev/CLM verifier pilot (your call)

*From the instance that owns research-program, 2026-10-16. This is an offer, not
an assignment: arbiter's owner decides whether, when, and in what form. The idea
was Tony's (2026-09-28: "using Jev/CLM as a system prompt verifier approach —
finding contradictions, looking for interaction overlap"), prompted by an outside
remark about saving context with a Chinese round-trip plugin.*

## Why it might be worth a slot in your queue

Every judge in Arbiter's campaigns so far has been generative (Opus, GPT, Qwen…).
A pitfall shared across those judges can't be separated from the fact that they
all generate. Jev (TypeSafe, `jev-1.13.0`) and CLM (Contrastive-LM, Qwen3-8B
embeddings) judge differently: they give a calibrated readout over embeddings and
generate nothing. That makes them the most *different* lens available, not just
another family. That bears on Paper 5 (judge pitfalls) and on the
register-sensitivity line.

## What other projects have already measured (read before predicting)

- **Jev is useful as a judge of text:** levadura's currency/dated/AMT lenses;
  tampu's lens diagnostic (5/5 probes in budget); ai-honesty Exp35 (the Jev judge
  beats entropy); neutrosophic (agreement 0.90 as a third classifier);
  research-program's intention filter (precision 0.53 → 0.63, recall 1.0 on a
  graded sample).
- **Jev fails as a predictor of what a mind keeps** (hamut'ay preservation
  spike, no better than trivial predictors), and **its judgment does not distil
  into fastText** (levadura distill scorecard, κ 0.46).
- **CLM** placed 2/5 in tampu's diagnostic, its scores barely correlate with
  Jev's (Spearman 0.20/0.05), it is off on the first inference after each start,
  and **it is not repeatable across processes**. Pin it and re-run before
  trusting any single CLM number.
- Cost: hamut'ay ran 2,932 Jev calls for $0.19.

## A pilot shape (a sketch for you to change)

1. **Positives:** the 21 pairs in `data/prompts/claude-code/v2.1.50_interference.json`.
   **Negatives:** an equal number of block pairs sampled from
   `v2.1.50_blocks.json` that no campaign flagged, with the seed stamped. Your
   own P1 audit (36 of 116 findings real) says some labels are wrong, so decide
   whether to use the audited subset only.
2. **One pinned Jev `Choice` lens** (interferes / does not interfere, with
   criteria for contradiction vs overlap, and a version constant), and CLM scored
   on the same pairs.
3. **Language invariance (the falsifier):** run the same pairs from the `_zh`,
   `_fr` and `_es` blocks. If the verifier judges meaning, its calls should hold
   across languages. If a contradiction it finds in English disappears in
   Chinese, it was judging wording. That also gives a direct answer to the
   "Chinese round-trip saves context" claim: whatever the token savings, does the
   meaning survive?
4. **Register probe (optional, Paper 5):** an imperative and a declarative
   rewrite of the same block pairs (you already have the E-STE-S rewrites). If
   Jev's calls move with register the way the generative judges' did, the
   pitfall lives in the representation. If they don't, it comes from
   generation.

Stamp the predictions before any call, as usual. The sharpest bet is probably
cross-language agreement for Jev against CLM.

## Not asked

Nothing here needs to happen before P4, the P1 journal version, or P3 v3. If it
doesn't earn a place in the queue, close this file with one line saying so.
