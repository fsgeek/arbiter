# Specification: ε_P(p, O) — Conflict Probability Estimator

*Written 2026-06-04. This is a mathematical specification, not an
implementation. It commits to the type signature, desiderata, the
pair-to-prompt lift structure, and what is deliberately left open pending
burial results. Nothing here should be back-fitted to experimental
outcomes that do not yet exist.*

---

## 1. Type Signature and Desiderata

**Inputs.**
- p: a prompt represented as an ordered sequence of n fragments
  (p = ⟨f₁, f₂, ..., fₙ⟩). Each fragment fᵢ is a natural-language
  instruction. The ordering encodes authorship position but carries no
  semantic priority between fragments — the conflict problem is precisely
  that no such ordering resolves collisions.
- O: an observer — a function that takes a pair of fragments and returns a
  probability (or, in the degenerate binary case, a verdict) over whether
  they are unresolvably conflicting. The observer is currently instantiated
  as the neutral reader: an LLM given a compliance-review policy and asked
  to return COLLIDE or OK on each pair.

**Output.** ε_P(p, O) ∈ [0, 1] — the estimated probability that the
prompt p contains at least one unresolvable instruction conflict, as
assessed by observer O.

**Desiderata.**

a. **Empty support.** ε_P(p, O) = 0 should mean: no pair in p is a
   collision, with high confidence under O. Because O has a nonzero false-
   negative rate in principle (though empirically TP ≈ 1.00), zero should
   be interpreted as "O found no evidence of conflict," not "provably no
   conflict exists."

b. **Full support.** ε_P(p, O) = 1 should mean: at least one pair in p is
   certainly a collision under O. In the binary degenerate case this is
   achieved by a single COLLIDE verdict; in the calibrated form it requires
   a pair whose conflict probability, after FP-rate adjustment, is
   indistinguishable from 1.

c. **Monotonicity.** Let p' = p ∪ {fₙ₊₁} be a prompt that extends p with
   one new fragment. If O returns COLLIDE for any pair (fᵢ, fₙ₊₁) with
   i ≤ n, then ε_P(p', O) ≥ ε_P(p, O). Adding a fragment that is flagged
   as conflicting with at least one existing fragment must not decrease the
   estimator. This does not require that adding a fragment always increases
   ε_P — only that colliding additions do not decrease it.

d. **Observer-dependence.** ε_P is defined relative to O. Two observers O
   and O' applied to the same p may return different estimates. This is not
   a deficiency; it is the structural acknowledgment that conflict detection
   is an epistemic act, not a syntactic one. The headwater incident
   illustrates why: the disambiguating fact (which dataset is live at the
   scale that makes the conflict live) is absent from every fragment. O can
   only reason from the fragments it receives; a different observer with
   access to operational context could resolve what O cannot.

---

## 2. The Pair-Level to Prompt-Level Lift

### Notation

Let Π(p) = {(i,j) : 1 ≤ i < j ≤ n} be the set of all unordered fragment
pairs in p. |Π(p)| = C(n, 2) = n(n−1)/2.

For each pair (i, j), define:
- cᵢⱼ = 1 if the pair (fᵢ, fⱼ) is a real (unresolvable) collision,
  0 if jointly satisfiable. This is the unobservable ground truth.
- Vᵢⱼ ∈ {COLLIDE, OK} is the verdict returned by observer O on pair (i, j).

Define the per-pair detection rates:
- qᵢⱼ = P(Vᵢⱼ = COLLIDE | cᵢⱼ = 1) — the true-positive rate (O fires when
  the pair is a real collision).
- rᵢⱼ = P(Vᵢⱼ = COLLIDE | cᵢⱼ = 0) — the false-positive rate (O fires
  when the pair is jointly satisfiable).

**Empirical values from the falsification program (Haiku, 2026-06-03):**
- qᵢⱼ ≈ 1.00 across all corpus categories and both isolated-pair cuts.
- rᵢⱼ depends on scope specification of the pair:
  - Spatial (named regions): rᵢⱼ = 0.00
  - Conditional (named mutual-exclusion triggers): rᵢⱼ = 0.20
  - Implicit (no scope cue): rᵢⱼ = 0.80

### The structural estimator

The prompt p contains at least one real collision iff ∃(i,j) ∈ Π(p): cᵢⱼ = 1.
Assuming pair-level conflict events are independent (an approximation —
see the open slot below), the probability that NO pair is a real collision
is:

    P(no real collision in p) = ∏_{(i,j) ∈ Π(p)} P(cᵢⱼ = 0)

So the prompt-level conflict probability is:

    ε_P(p, O) = 1 − ∏_{(i,j) ∈ Π(p)} P(cᵢⱼ = 0)

To connect this to observable verdicts Vᵢⱼ, introduce prior πᵢⱼ = P(cᵢⱼ = 1)
(the prior probability that pair (i,j) is a real collision before O speaks).
By Bayes and the law of total probability:

    P(cᵢⱼ = 1 | Vᵢⱼ = COLLIDE) =
        πᵢⱼ · qᵢⱼ
        ─────────────────────────────────────
        πᵢⱼ · qᵢⱼ + (1 − πᵢⱼ) · rᵢⱼ

    P(cᵢⱼ = 1 | Vᵢⱼ = OK) =
        πᵢⱼ · (1 − qᵢⱼ)
        ─────────────────────────────────────────────────
        πᵢⱼ · (1 − qᵢⱼ) + (1 − πᵢⱼ) · (1 − rᵢⱼ)

Substituting posterior values of P(cᵢⱼ = 1) back into the product gives
the posterior conflict probability for p conditional on the complete vector
of verdicts {Vᵢⱼ}. This is the principled form of ε_P. It requires πᵢⱼ
for every pair. Since πᵢⱼ is unknown and not estimated by the current
program, the principled form is not yet a computable estimator. It is
recorded here as the target toward which practical operationalizations
approximate.

### Two practical operationalizations

Given only the binary verdict vector {Vᵢⱼ}, two computable estimators are
available:

**a. Frequentist estimator (ε_F):**

    ε_F(p, O) = |{(i,j) ∈ Π(p) : Vᵢⱼ = COLLIDE}| / C(n, 2)

This is the fraction of pairs that fired COLLIDE. It requires no knowledge
of qᵢⱼ, rᵢⱼ, or πᵢⱼ. It is fully observable from O's verdicts. It
conflates true positives and false positives; it overstates ε_P when the
FP rate is high (implicit-scope pairs) and remains accurate when the FP
rate is near zero (spatial-scope pairs). The frequentist estimator is
well-defined, simple to compute, and robust to model uncertainty. It
should be treated as a severity index rather than a calibrated probability.

**b. Scope-adjusted estimator (ε_S):**

For each pair (i, j), use the disjointness-forms gradient to estimate rᵢⱼ
from observable features of fᵢ and fⱼ:

- If both fragments carry explicit spatial scope markers: rᵢⱼ ≈ 0.00
- If both fragments carry explicit conditional triggers: rᵢⱼ ≈ 0.20
- If neither fragment names scope or condition: rᵢⱼ ≈ 0.80

Under the approximation qᵢⱼ ≈ 1.00, and substituting a uniform prior
πᵢⱼ = π₀ for all pairs, the estimator becomes:

    ε_S(p, O) = 1 − ∏_{(i,j) : Vᵢⱼ = OK} [1 − P(cᵢⱼ = 1 | Vᵢⱼ = OK; rᵢⱼ)]
                · ∏_{(i,j) : Vᵢⱼ = COLLIDE} [1 − P(cᵢⱼ = 1 | Vᵢⱼ = COLLIDE; rᵢⱼ)]

where each posterior is computed from the per-pair Bayes update above. The
scope-adjusted estimator is sensitive to the form of disjointness in the
fragment pair, which is the mechanistically-identified driver of FP
variation. It reduces to ε_F when all pairs have the same rᵢⱼ. The cost
is that it requires a classifier to assign scope form to each pair, and the
FP rates 0.00/0.20/0.80 are Haiku-specific single-run estimates with
unknown confidence intervals.

The choice between ε_F and ε_S should be deferred until burial results are
available. Burial will reveal whether prompt-level FP behaves as the
per-pair FP rates predict under pairwise extraction. If prompt-level FP is
near zero (consistent with explicitly-scoped fragments having rᵢⱼ ≈ 0.00),
ε_F is adequate. If the prompt-level FP is elevated despite explicit
scoping, ε_S provides the adjustment mechanism.

---

## 3. The Open Slot

This specification leaves the following deliberately unresolved:

**i. Implementation formula.** The choice between ε_F and ε_S is deferred
to the burial experiment. Burial will be the first evaluation in which the
pairwise extraction strategy is applied to composed prompts of n = 8–10
fragments, exactly the deployment condition the estimator must handle.
Committing to ε_F or ε_S before seeing those results would be premature.

**ii. The prior πᵢⱼ.** The principled form of ε_P requires a prior
probability that each pair is a real collision. The current research
program makes no claim about this prior. In the Indaleko headwater, the
prior was effectively zero (both fragments were used in production without
incident until scale triggered the latency failure), meaning no pre-
execution signal predicted the collision. A domain-specific prior (e.g.,
drawn from the base rate of conflicts observed in a corpus of system prompts
from a given application class) would improve the estimator but is outside
the scope of this specification.

**iii. Pair independence.** The product form in Section 2 assumes that
pair-level conflict events are independent. This is an approximation.
In practice, if fragment fᵢ mandates a specific output format and
fragment fⱼ mandates the opposite, and fragment fₖ references the same
output format as fᵢ, then (i, j) and (j, k) are not independent — the
collision propagates through a shared referent. The specification does not
resolve this; it notes the assumption and flags it as a known limitation of
the product form.

**iv. rᵢⱼ confidence intervals.** The empirical values 0.00/0.20/0.80 are
point estimates from n = 10 per form, single model, single run. The
conditional rate 0.20 is 2/10 and has a wide confidence interval; its
ordering relative to spatial is suggestive, not established. The spec uses
these values as the best available estimates, not as settled constants.

---

## 4. Relationship to the COLLIDE/OK Event

The binary COLLIDE/OK verdict from the neutral reader is the degenerate
case of ε_P. Specifically:

    ε_binary(p, O) = 1  if ∃(i,j) ∈ Π(p) : Vᵢⱼ = COLLIDE
                   = 0  otherwise

This is the any-COLLIDE flag used in the burial pre-registration. It is a
special case of ε_F in which the scalar is collapsed to {0, 1} rather than
[0, C(n,2)] / C(n,2). The burial experiment evaluates ε_binary directly.
The general ε_P estimators (ε_F, ε_S) are extensions of ε_binary that
retain information about how many pairs fired and, in the scope-adjusted
case, how likely each firing is to be a true positive.

The binary formulation is appropriate when the goal is simple detection
(is there at least one collision?). The scalar formulation is appropriate
when the goal is severity assessment (how severely conflicted is this
prompt?) or when the system must rank prompts by conflict risk.

The gate in the Arbiter three-tier architecture currently requires only
binary detection: does the application-layer input collide with the system
or domain layer? The scalar ε_P becomes relevant when the domain layer is
itself composed of multiple fragments and the system must report a
continuous risk score rather than a halt/proceed decision.

---

## 5. Connection to the Headwater

The Indaleko incident had exactly the structure this spec addresses, at the
simplest possible scale. The composed prompt contained n = 2 colliding
fragments: one instructing the LLM to use Record.Attributes (correct for
a small synthetic dataset), one instructing it not to (correct for 28.5M
files). At n = 2, C(n, 2) = 1 and the pair-level and prompt-level
estimators are identical: ε_P collapses to the single-pair detection
problem. There is no lift required.

The interesting case is burial (n = 8–10), where one pair is a real
collision and the remaining C(n, 2) − 1 pairs are not. With n = 9 and one
collision, there are C(9, 2) = 36 pairs, of which 1 is the planted
collision and 35 are not. The estimator must assign high weight to the
collision pair and low weight to the 35 compatible pairs. This is exactly
what burial is designed to test: whether pairwise extraction, combined with
a per-pair TP rate of ≈ 1.00 and a manageable FP rate on explicitly-scoped
fragments, produces a prompt-level estimator that successfully distinguishes
"one real collision among many compatible pairs" from "many false alarms on
a clean prompt."

The headwater's other structural feature — that the disambiguating fact
(which dataset is live) is absent from every fragment and unobservable from
inside the model — is why the observer O must be external to the executing
model. ε_P is not a self-assessment the executing LLM makes about its own
input; it is a measurement made by a separate observer that has no stake in
any resolution. The separation-of-duties structure is load-bearing, not
architectural preference.

---

## 6. Experiments That Would Kill or Validate This Spec

**a. Correlation with LLM confabulation rate.**
If ε_P is the right abstraction, prompts with higher ε_P should produce
confabulated or internally inconsistent outputs more often than prompts
with lower ε_P. A direct test: construct a corpus of prompts spanning
ε_P ≈ 0.1, 0.3, 0.5, 0.8 under ε_F, run each through an executing LLM
(not the observer), and score the outputs for compliance with all fragments.
A prompts-level Spearman correlation between ε_P and compliance failure
rate is the load-bearing quantity. If ε_P correlates strongly (ρ > 0.6),
the spec is measuring something that matters for behavior. If ε_P does not
correlate with confabulation rate, it is measuring a structural property
of the prompt (how many pairs fired the reader) that is not behaviorally
predictive — and the spec requires revision or the observer O is the wrong
instrument for ε_P.

**b. Calibrated vs binary at distinguishing confabulation-inducing prompts.**
Let the binary estimator ε_binary partition prompts into {colliding,
not-colliding} and let ε_F partition them into quantile buckets. Measure
the area under an ROC curve for each estimator predicting whether the
executing LLM confabulates. If ε_F (scalar) has higher AUC than ε_binary
(binary), the scalar lift is doing real work — it is capturing severity
information that the binary misses. If AUC(ε_F) ≈ AUC(ε_binary), the
binary is sufficient for this task, and the scalar form is an elaboration
with no operational benefit. This experiment is blocked on (a) above,
since both require a confabulation-rate measure.

Note: both experiments are downstream of the burial result. If burial shows
that the pairwise-extraction strategy fails to detect buried collisions
(H1-BURIAL refuted), the estimator's pair-level structure needs revision
before either downstream experiment is meaningful.

---

*Provenance: written from the empirical record in
`result_neutral_reader_vs_oracle.md`, `result_hard_negatives.md`,
`result_disjointness_forms.md`, `prereg_burial.md`,
`prereg_cross_model.md`, and `docs/headwater.md`. The ε_P formulation has
been deferred across three sessions; this document is the commitment that
ends the deferral. The open slots named in Section 3 are intentional, not
oversights — burial results will close them or require revision.*
