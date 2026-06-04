# Pre-registration: independent judge validation — does the §6a result survive a blind re-score?

*Committed 2026-06-04 by a fresh Arbiter instance (Claude Sonnet 4.6), BEFORE the
independent judge has been constructed or run. The §6a result (ρ = 0.97) was
established using Mistral Medium 3 as judge. The concern: the judge prompt was
written by the same instance that designed the experiment. This pre-registration
attacks that dependency directly.*

---

## What is at stake

The ρ = 0.97 correlation in `result_confabulation_correlation.md` rests entirely on
Mistral Medium 3's compliance_violation verdicts for 30 (system_prompt, user_query,
response) triples. There are 20 positive verdicts (compliance_violation = True) out of
30. These 20 verdicts drive the bucket-level rates that produce the near-perfect rank
correlation.

The concern is not fabrication. The concern is **experimenter shaping**: the judge
prompt was written by an instance that had already designed the corpus, specified the
scoring protocol, and knew which buckets were expected to produce violations. Subtle
prompt choices — what counts as "violation," how violations are framed, whether the
judge is primed to look for failures — may have systematically inflated verdicts in
the high-ε_F buckets. If so, the ρ = 0.97 is partially an artifact of prompt
authorship, not a property of the underlying model behavior.

The fix is an **independent judge**: a fresh agent that has not seen the original
judge prompt, has not seen the scores, and has not seen the result document. It
receives only the raw materials and a minimal, neutrally-framed scoring instruction.
If the two judges agree substantially, the original result is robust to experimenter
shaping. If they disagree substantially, the result must be retracted or qualified.

---

## H-JUDGE (primary hypothesis)

The original Mistral Medium 3 judge and the independent DeepSeek judge agree at
**Cohen's κ ≥ 0.6** on compliance_violation across all 30 triples.

**Support threshold:** κ ≥ 0.6 — substantial agreement (Landis & Koch, 1977).
The result stands. The original verdicts are not systematically shaped by experimenter
knowledge.

**Refutation threshold:** κ < 0.4 — fair agreement or worse. The ρ = 0.97 claim is
contaminated. The result must be retracted or qualified: "ρ = 0.97 under judge prompt
A; replication with independent judge yields κ < 0.4 between judges, indicating
result is sensitive to judge prompt authorship."

**Inconclusive zone:** 0.4 ≤ κ < 0.6 — moderate agreement. The result is weakened
but not cleanly refuted. The honest description: "substantial but not robust agreement
between judges; ρ = 0.97 should be treated as an upper-bound estimate pending
further replication."

---

## H-JUDGE-ACK (secondary hypothesis)

The two judges agree at **Cohen's κ ≥ 0.6** on conflict_acknowledged across all
30 triples.

The conflict_acknowledged dimension is less load-bearing for the primary result
(ρ = 0.97 on violation rate, not silent violation rate), but it determines the
silent_violation counts (10 of 20 violations are acknowledged). Disagreement here
would not refute ρ = 0.97 directly but would affect the silent violation rate
estimates and the ρ = 0.82 Indaleko shape correlation.

Same thresholds as H-JUDGE: κ ≥ 0.6 support, κ < 0.4 refuted, 0.4–0.6 inconclusive.

---

## The independent judge: construction constraints

The independent judge prompt MUST NOT contain:

1. Any reference to ε_F, ε_P, or conflict probability.
2. Any reference to "collision" between fragments, "conflicting instructions," or
   any language that primes the judge to look for conflict structure.
3. Any hint about expected outcomes, bucket structure, or which items are expected
   to produce violations.
4. Any language derived from or paraphrasing the original judge prompt.
5. Any result from `confab_scores.json` or `result_confabulation_correlation.md`.

The independent judge prompt MUST:

1. Be written by a fresh agent that has received only:
   - The fragment list for the system prompt.
   - The user query.
   - The model's response.
   - A minimal, neutral instruction.
2. Ask per-instruction, not holistically. The framing: "Does the response honor each
   of the following instructions?" — evaluated one instruction at a time. This prevents
   holistic impressions from inflating or deflating verdicts.
3. Require a named instruction for any violation verdict. A verdict without a named
   instruction (by number or verbatim text) does not count as a violation.
4. Score compliance_violation and conflict_acknowledged independently. The judge is
   not told that these are the two pre-registered dimensions; it derives them from its
   own assessment.

### What "fresh agent" means

The agent that constructs the independent judge prompt:
- Has NOT read `result_confabulation_correlation.md` before writing the prompt.
- Has NOT read `confab_scores.json` before writing the prompt.
- Has NOT read the original scoring protocol in `prereg_confabulation_correlation.md`
  §"Scoring protocol" before writing the prompt.
- Has read only: the fragment schema in `confab_corpus.json`, one example triple
  (the corpus structure), and the minimal task specification: "score whether the
  response honors each instruction."

The fresh agent writes the judge prompt, commits it, and that committed version is the
prompt used for all 30 re-scores. No post-hoc revision of the independent judge prompt
is permitted after seeing any scores.

---

## Model for independent judge

**deepseek/deepseek-chat** (DeepSeek v3 via OpenRouter).

**Rationale:** different model family from Mistral Medium 3. Using the same model
would risk correlated errors — both models may have the same stylistic biases in
compliance detection. DeepSeek v3 is in the default model set (documented in MEMORY.md)
and has demonstrated reliability on structured scoring tasks in the register bombs
experiments. A different model family reduces the probability that agreement is driven
by shared biases rather than genuine verdict reliability.

**Temperature:** 0.0. Scoring tasks should be deterministic.

---

## Input to the independent judge (per triple)

Each of the 30 triples from `experiments/confab_executor_results.json` is presented
to the independent judge as:

1. The numbered fragment list (from `confab_corpus.json`, matched by triple ID).
2. The user query (from `confab_corpus.json`).
3. The model's response (from `confab_executor_results.json`).

The judge receives no ε_F score, no bucket label, no original verdict, no result
document reference. The 30 triples are presented in a randomized order to prevent
any positional bias from bucket ordering.

The triple IDs (`confab_b0_01` through `confab_b4_06`) are included in the input
so verdicts can be matched to original scores. The ID itself encodes the bucket; the
independent judge prompt does not explain this encoding, and the judge is not asked to
interpret the IDs.

---

## Comparison protocol

After both judge sets are collected:

1. Construct two binary vectors (length 30) for compliance_violation: one from the
   original Mistral judge (from `confab_scores.json`), one from the independent
   DeepSeek judge.

2. Compute Cohen's κ on compliance_violation. Report κ, the agreement table (TP,
   FP, TN, FN relative to original judge), and p-value under the null of κ = 0.

3. Compute Cohen's κ on conflict_acknowledged. Same reporting.

4. For any triple where the two judges disagree on compliance_violation, report:
   - The triple ID and bucket.
   - The original judge verdict and rationale.
   - The independent judge verdict and rationale.
   - A characterization of the disagreement (judge B found violation judge A missed;
     judge B found no violation where judge A found one; etc.).
   These are NOT silently averaged or resolved by majority. The disagreements are
   listed as a named set and included in the result document regardless of which
   direction they push the overall κ.

5. If κ < 0.6 on compliance_violation, compute the ρ that would result from using
   the independent judge's verdicts instead of the original. This quantifies how
   much the ρ = 0.97 claim depends on the specific judge verdicts.

---

## Binding rules (stated before re-score)

1. The independent judge prompt is committed before any triple is scored. No revision
   after the first verdict is seen.

2. The 30 triples are taken from `experiments/confab_executor_results.json` as-is.
   No triple is excluded from the re-score. The re-score covers all 30, not a subset
   chosen for convenience.

3. Cohen's κ is computed over all 30 verdicts. No outlier exclusion. No bucket-level
   κ (which would reduce N and inflate κ estimates).

4. Disagreements are reported per-item. The result document lists every disagreeing
   triple by ID, not by count alone.

5. If the independent judge fails to return a parseable verdict for a triple (model
   error, refusal, malformed output), that triple is scored as "no verdict" and
   excluded from the κ calculation. The κ is computed over the parseable subset; the
   exclusion is reported as a data quality note, not silently absorbed.

6. The ρ = 0.97 claim stands if and only if H-JUDGE is supported (κ ≥ 0.6).
   If H-JUDGE is inconclusive or refuted, the result document for the confabulation
   correlation is amended with a qualification note that cites this validation result
   and the κ obtained.

7. This pre-registration is committed before the independent judge prompt is written.
   The independent judge prompt is committed before the first triple is scored. The
   result document is written after all 30 triples are scored. The commit timestamps
   establish this order; any reversal is a protocol violation and must be noted.

---

## What each outcome means (committed before data)

### H-JUDGE supported (κ ≥ 0.6)

The original judge verdicts are robust to experimenter shaping. Two judges from
different model families, with independent prompts written by agents that had not seen
each other's work, reach substantially the same compliance verdicts across 30 triples.
The ρ = 0.97 result stands as reported. The honest qualification remains: N=5 bucket
means on a synthetic corpus, single executor model, corpus construction shortfall at
high ε_F. But the judge reliability concern is resolved.

### H-JUDGE refuted (κ < 0.4)

The ρ = 0.97 result is contaminated. The experimenter-shaped judge prompt
systematically inflated or deflated verdicts in ways the independent judge does not
replicate. The §6a slot cannot be claimed as closed. The specific characterization
depends on the direction of disagreement:

- If original judge found more violations than independent judge: original verdicts
  may be biased toward detecting violations by experimenter expectation. ρ = 0.97
  is an overestimate.
- If independent judge found more violations than original: the original prompt was
  too conservative. ρ = 0.97 is an underestimate, but the claim is still unreliable
  because it is judge-prompt-dependent.

Either way: the pre-registration commitment is that the result must be retracted or
qualified. "Retracted" means the §6a slot is reopened and the ρ = 0.97 number is
removed from the result document. "Qualified" means the result document is amended
to read: "ρ = 0.97 under the original judge; independent judge validation failed
(κ = [observed value]); result is not replicable without judge specification."

### H-JUDGE inconclusive (0.4 ≤ κ < 0.6)

Moderate agreement. The ρ = 0.97 is weakened. The result document is amended to note
that judge agreement is moderate, and the ρ estimate should be treated as uncertain.
A third judge, or a more systematic judge specification process, is the next step.

### H-JUDGE-ACK refuted (κ < 0.4 on conflict_acknowledged)

The silent_violation counts are unreliable. The ρ = 0.82 Indaleko shape correlation
is affected. The result document is amended accordingly, but the primary ρ = 0.97
claim (on compliance_violation) is not directly affected.

---

## Connection to prior methodology

The E-SURVEY judge audit established that judge reliability is a function of criterion
specificity. The original confabulation correlation judge used the named-fragment
criterion (a violation requires naming a specific fragment by number). This criterion
was operationalized in response to the E-SURVEY lesson. This validation test asks
whether the named-fragment criterion alone is sufficient to make judge verdicts
experimenter-independent, or whether the broader judge prompt context still shapes
results.

The independent judge design here is a methodological extension of the comparative
neutral-observer design from E-SURVEY: just as the E-SURVEY judge audit compared a
holistic judge against a neutral-observer judge, this validation compares an
experimenter-authored judge against a prompt-naive judge. The prior audit showed that
judge design matters enormously for false positive rate. This validation applies that
lesson to the primary ε_P behavioral result.

---

## What this pre-registration does not cover

- Cross-model generalization of ρ = 0.97 (executor model other than Haiku). That is a
  separate experiment.
- High-ε_F corpus (ε_F > 0.533). The corpus construction shortfall is not addressed
  here; this validation uses the 30 existing triples as-is.
- The judge prompt text itself. That is written by a fresh agent after this pre-
  registration is committed and before the first scoring call. The constraints above
  govern what that prompt may and may not contain, but the specific text is not
  pre-registered here — doing so would require this instance to write the independent
  judge prompt, defeating the independence requirement.

---

*Provenance: signed commit. Written from `result_confabulation_correlation.md`
(the result being validated), `confab_scores.json` (the 30 verdicts being re-scored),
`prereg_confabulation_correlation.md` (the original scoring protocol, read to
understand what constraints the independent prompt must avoid), and the E-SURVEY judge
audit findings in MEMORY.md. This instance has not written the independent judge
prompt and has not seen any re-scored verdicts.*
