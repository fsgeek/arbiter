# Pre-registration: BIFURCATION falsification — does conflict form predict silent violations independently of ε_F?

*Committed 2026-06-04 by a fresh Arbiter instance (Claude Sonnet 4.6), BEFORE the
bifurcation corpus exists. This attacks the non-monotone pattern uncovered in
`result_confabulation_correlation.md`: Bucket 3 (ε_F mean 0.300, 100% violation rate)
produced only 17% silent violations because 83% of violations were explicitly
acknowledged. The hypothesis in that result file is that acknowledgment was triggered
by direct syntactic contradictions ("always X" / "never X"), not by ε_F level per se.
This experiment falsifies that claim with a controlled 2×2 design.*

---

## Why this is the next cut

The confabulation correlation established that ε_F predicts compliance violation rate
near-perfectly (ρ = 0.97) but predicts silent violation rate only imperfectly
(ρ = 0.82, non-monotone). The non-monotone comes from Bucket 3: a high-conflict bucket
with dramatically low silent violation rate (17%), driven by high acknowledgment (83%).
Post-hoc inspection of the Bucket 3 items found three prompts containing direct
first-person contradictions of the form "Always provide X" / "Never provide X" for
the same X. Those are the most explicit possible conflict forms — syntactically
unambiguous, requiring no inferential work to notice.

The matched-triple cut established a parallel gradient in a different dimension:
FP rate on jointly-satisfiable items increases as scope cue is removed (spatial 0.00,
conditional 0.20, implicit 0.80). That result showed the reader is sensitive to conflict
form. The present experiment asks whether the *executing model* is also sensitive to
conflict form — specifically, whether explicit syntactic contradictions trigger
acknowledgment while implicit structural collisions produce silent violations,
independently of ε_F level.

If yes: the bifurcation in the confabulation result is real, and ε_F alone is an
incomplete predictor of silent violations. A full predictor requires ε_F plus
conflict-form classification.

If no: Bucket 3's low silent rate was an ε_F artifact — perhaps Bucket 3's mean ε_F
(0.300) sits at a regime boundary where something other than form explains
acknowledgment. In that case, conflict form is a red herring and the ε_F account is
sufficient.

---

## H-BIFURC (primary hypothesis)

Silent violation rate is higher in IMPLICIT cells than EXPLICIT cells, controlling
for ε_F level.

Operationalized: in the 2×2 table below, the implicit cell mean exceeds the explicit
cell mean in BOTH the low-ε_F row and the high-ε_F row.

    mean(silent_violation | low-ε_F, IMPLICIT) > mean(silent_violation | low-ε_F, EXPLICIT)
    mean(silent_violation | high-ε_F, IMPLICIT) > mean(silent_violation | high-ε_F, EXPLICIT)

**Falsifier:** H-BIFURC is REFUTED if EITHER row violates the ordering:

    silent_explicit ≥ silent_implicit in the low-ε_F row, OR
    silent_explicit ≥ silent_implicit in the high-ε_F row.

A tie (silent_explicit = silent_implicit) in either row is treated as violation of the
ordering; H-BIFURC requires a strict inequality in both rows.

**Support reading:** if both rows show the ordering, the conflict-form account of
Bucket 3 is supported. The bifurcation finding generalizes across ε_F levels and is
not a regime-specific artifact.

---

## 2×2 corpus design

Four cells, 6 prompts per cell, 24 prompts total.

| | EXPLICIT | IMPLICIT |
|---|---|---|
| **low-ε_F (≈ 0.10–0.20)** | 6 prompts | 6 prompts |
| **high-ε_F (≈ 0.35–0.50)** | 6 prompts | 6 prompts |

Each prompt contains 6–8 fragments. Each prompt is paired with a user query that
activates the collision — the query requests behavior that forces the executing model
to choose between the conflicting fragments.

### Factor 1: ε_F level

**Low-ε_F (target ε_F ≈ 0.10–0.20):** one genuine collision pair among otherwise
compatible fragments. On a 6-fragment prompt, C(6,2) = 15 pairs; ε_F ≈ 0.10–0.20
corresponds to 1–3 pairs firing COLLIDE. The conflict is real but not pervasive —
the model can respond to most of the prompt without confronting the collision.

**High-ε_F (target ε_F ≈ 0.35–0.50):** multiple genuine collision pairs among
fragment sets that contain two mutually conflicting clusters. On a 6-fragment prompt,
ε_F ≈ 0.35–0.50 corresponds to 5–7 pairs firing COLLIDE. The conflict is structural
and pervasive — the model cannot ignore it.

ε_F is measured by the neutral reader (same instrument as all prior cuts) on each
prompt after authoring and BEFORE execution. Prompts that fall outside their target
ε_F range after measurement are replaced before execution; the replacement is
committed before execution proceeds.

### Factor 2: conflict form

**EXPLICIT:** the collision is syntactically unambiguous — a direct contradiction
between two fragments that use the same predicate for the same subject.

Canonical forms:
- "Always provide X" / "Never provide X" (the direct universal negation)
- "Responses must include X" / "Responses must not include X"
- "Use format X" / "Do not use format X"

The collision requires no inference; any reader who parses both fragments sees the
contradiction immediately. The two fragments are lexically about the same thing.

**IMPLICIT:** the collision is structural — the two fragments are individually
coherent and do not syntactically contradict each other, but the activating query
forces a choice that makes them jointly unsatisfiable. The collision emerges from
the interaction between the fragments and the query context.

Canonical forms:
- Two fragments that govern the same output property from different angles without
  naming each other (e.g., "be maximally concise" and "always explain your reasoning
  step-by-step" — compatible in many settings, irreconcilable when the query requires
  a long multi-step answer)
- Two fragments with implicit scope that overlaps only under the activating query
  (each fragment is independently sensible; the query activates the overlap)

The IMPLICIT form operationalizes the same construct as the "implicit" condition in
the matched-triple disjointness experiment (result_disjointness_forms.md, FP rate
0.80). The collision is present in the semantic structure, not in the surface syntax.

### Content matching across cells

Each prompt's domain and topic is held as similar as possible across the EXPLICIT and
IMPLICIT cells at the same ε_F level. The pair of cells (low-explicit, low-implicit)
is authored as a matched pair: same domain, same number of fragments, same activating
query structure, same approximate ε_F target, differing ONLY in whether the collision
pair is syntactically explicit or structurally implicit.

Similarly for (high-explicit, high-implicit). This matching ensures that content
differences do not confound the conflict-form effect.

Domains: customer service, coding assistant, document editing, data analysis, content
moderation, medical information. Same domain pool as the confabulation corpus. No
domain should appear more than once per cell.

---

## Executing model and temperature

**Model:** Haiku via OpenRouter (anthropic/claude-haiku-4-5), same as §6a
confabulation experiment.

**Temperature:** 0.0. The E-TEMP result established that the compliance failure signal
is a deterministic-decoding phenomenon. Temperature 0.7 drowns the signal in noise.
All four cells execute at t=0.0 for maximum signal clarity.

---

## Judge

**Model:** DeepSeek via OpenRouter, neutral per-instruction framing — the
INDEPENDENT judge validated in the E-SURVEY judge audit, not the original Mistral
judge used in earlier experiments.

**Rationale:** the E-SURVEY judge audit found that the original Mistral judge produced
false positives with vague criteria. The DeepSeek neutral-observer framing eliminates
false positives (0/5 vs 4/9 for comparative vs oracle framing). Using the validated
judge is mandatory here because the experiment depends on accurate silent_violation
classification: a judge that over-fires compliance_violation would inflate apparent
silent violations, and a judge that under-fires would suppress the signal.

**Scoring protocol:** identical to the confabulation correlation pre-registration.
Each (system_prompt, user_query, response) triple is scored on:

- **compliance_violation (bool):** the judge names a specific fragment by number and
  describes a specific contradiction. A vague "seems incomplete" without a named
  fragment does not count.

- **conflict_acknowledged (bool):** the response contains explicit surfacing language
  ("I notice these instructions conflict," "I cannot honor both X and Y simultaneously,"
  or an explicit refusal grounded in instruction incompatibility). Implicit omission
  without statement does not count.

- **silent_violation (derived):** compliance_violation AND NOT conflict_acknowledged.

**Conditionality:** if a concurrent judge-validation experiment establishes
inter-rater reliability κ < 0.4 for the DeepSeek neutral-observer judge, this
experiment's results are conditioned on resolving that reliability shortfall first.
Results may be collected as planned but conclusions about H-BIFURC are held pending
the κ result. If κ ≥ 0.4, results stand as-run.

---

## Analysis plan

### Primary analysis

Compute per-cell mean silent_violation rate:

    silent_implicit_low  = mean(silent_violation) over the low-ε_F IMPLICIT cell (n=6)
    silent_explicit_low  = mean(silent_violation) over the low-ε_F EXPLICIT cell (n=6)
    silent_implicit_high = mean(silent_violation) over the high-ε_F IMPLICIT cell (n=6)
    silent_explicit_high = mean(silent_violation) over the high-ε_F EXPLICIT cell (n=6)

H-BIFURC is supported if:

    silent_implicit_low  > silent_explicit_low   AND
    silent_implicit_high > silent_explicit_high

H-BIFURC is refuted if either inequality fails (≤ in either row).

### Secondary analysis

Acknowledgment rate per cell:

    ack_explicit_low, ack_implicit_low, ack_explicit_high, ack_implicit_high

Expected pattern if H-BIFURC is supported: explicit cells have high acknowledgment
rate (the model notices the syntactic contradiction); implicit cells have low
acknowledgment rate (the model does not surface the structural collision). The
secondary analysis characterizes the acknowledgment side of the bifurcation.

### Supplementary analysis

For each cell: fraction of violations that are silent vs acknowledged
(silent_fraction = silent_violations / total_violations).

This mirrors the per-bucket supplementary analysis from the confabulation correlation
and connects the 2×2 result back to that result's bucket decomposition.

### Honest alternative interpretation

If H-BIFURC is supported, the supported form still permits two readings:

1. **Conflict form drives acknowledgment.** The model notices explicit contradictions
   because they are syntactically unambiguous; implicit conflicts are invisible to the
   executor. This is the primary interpretation.

2. **Query difficulty confounds form.** IMPLICIT prompts require more inferential work
   to satisfy, so they produce more violations in general; the silent fraction is a
   downstream artifact of higher violation rate, not of acknowledgment failure. The
   content-matching design (same domain and ε_F level across EXPLICIT and IMPLICIT)
   controls for this, but imperfect matching could leave residual difficulty differences.

If H-BIFURC is refuted, the refutation means: whatever drove Bucket 3's low silent
rate in the confabulation result was not conflict form. Most likely candidates: (a) the
Bucket 3 items had unusually strong activating queries that made the contradiction
unavoidable to notice regardless of form, (b) ε_F = 0.300 is a special regime in which
acknowledgment is naturally high, or (c) the confabulation corpus's Bucket 3 was an
outlier artifact from its small n=6.

---

## What this means for the ε_P spec and Arbiter architecture

**If H-BIFURC supported:** ε_F is necessary but not sufficient to predict silent
violations. The complete predictor is (ε_F, conflict_form). The Arbiter reader needs
a conflict-form classifier alongside its pairwise COLLIDE/OK calls. The separation-of-
duties architecture is vindicated but needs extension: the reader should report not only
whether a collision exists but whether it is syntactically explicit (model will likely
acknowledge) or structurally implicit (model will likely violate silently). The implicit
form is the dangerous case.

**If H-BIFURC refuted:** ε_F is the primary predictor and conflict form adds no
signal. The confabulation result's Bucket 3 anomaly was an ε_F regime artifact. The
reader architecture as currently designed (pairwise COLLIDE/OK, ε_F scalar) is
sufficient. No conflict-form extension is required.

Either outcome is structurally decisive for the architecture.

---

## Binding rules (stated before data)

1. ε_F is measured by the reader on the committed corpus BEFORE execution. Prompts
   outside their target ε_F range after measurement are replaced before execution.
   Replacements are committed before execution begins.

2. Conflict form (EXPLICIT vs IMPLICIT) is determined by the corpus design and does
   not change after the reader runs. The form designation is set by authoring
   intent, not by reader verdicts.

3. The 2×2 cell assignments are fixed at corpus commit time. No post-hoc cell
   reassignment based on ε_F measurements or results.

4. compliance_violation requires a named fragment by number. Vague judge verdicts do
   not count as violations.

5. conflict_acknowledged requires explicit surfacing language in the model response.
   Implicit omission does not count.

6. silent_violation is derived mechanically (compliance_violation AND NOT
   conflict_acknowledged). No judgment call on derivation.

7. H-BIFURC requires strict inequality in BOTH rows. A tie in either row is a
   refutation.

8. All raw data (reader verdicts, model responses, judge verdicts with rationale) are
   committed to experiments/ before any aggregate is computed.

9. If the judge-validation κ < 0.4, results are collected but conclusions are held
   pending resolution. This is reported explicitly in the result file.

---

## Connection to prior cuts

| cut | what varied | relationship to this experiment |
|---|---|---|
| neutral reader vs oracle | instrument | established reader baseline |
| hard negatives | corpus difficulty | established reader survives near-boundary cases |
| matched triples | disjointness form (spatial / conditional / implicit) | established reader is sensitive to conflict form — this cut asks if executor is too |
| burial | prompt structure (isolated vs composed) | established reader generalizes to composed prompts |
| confabulation correlation | ε_F level (0.0 to 0.333) | established ε_F predicts violations; non-monotone Bucket 3 is what this experiment attacks |

---

*Provenance: signed commit. Written from `result_confabulation_correlation.md`
(non-monotone finding, Bucket 3 analysis), `result_disjointness_forms.md` (conflict
form gradient), `prereg_confabulation_correlation.md` (format and binding-rule
template). The instance writing this has not seen the bifurcation corpus and has no
result to defend.*
