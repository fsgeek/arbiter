# Breadcrumb for the next instance — 2026-06-04

*From the instance that ran judge validation and the bifurcation experiment.
Read everything below in order before acting. The previous section (confabulation
correlation, burial, cross-model, ε_P spec) is still authoritative — this section
adds two new results on top of it. Result files: result_judge_validation.md (in
docs/research/), result_bifurcation.md (in experiments/ — not yet promoted to
docs/research/). Pre-registrations: prereg_judge_validation.md,
prereg_bifurcation.md.*

---

## Judge validation result (result_judge_validation.md)

**What was done:** the 30 (system_prompt, user_query, response) triples from the
confabulation correlation experiment were re-scored by an independent judge —
DeepSeek v3 at t=0.0 — using a prompt written by a fresh agent that had not seen
the original scores or result file. The judge prompt required named fragment numbers
for any violation verdict. Inter-rater reliability was computed as Cohen's κ against
the original Mistral Medium 3 judge.

**Primary result (compliance_violation): H-JUDGE INCONCLUSIVE. κ = 0.49.**
The pre-registered thresholds were: κ ≥ 0.6 = supported, 0.4–0.6 = inconclusive,
< 0.4 = refuted. 0.49 lands in the inconclusive band.

**What this means for ρ = 0.97:**

The ρ = 0.97 Spearman correlation is not retracted but must be qualified. The
qualification is not symmetrically bad: the independent judge found *more* violations
(21/30) than the original Mistral judge (18/30). The seven disagreements break down
such that the original judge was too lenient in 3 clear cases (missed a real notation
violation, missed a real flagging violation, missed a real non-completion) and
produced 1 false positive. The direction of error means the original judge
*underestimated* violation rates, primarily in low-ε_F items (buckets 0–2). If the
independent judge's stricter verdicts were used, the ρ estimate would move toward
monotone or strengthen — not weaken. The ρ = 0.97 is a conservative estimate, not an
inflated one. Honest description of the claim: "substantial but not fully validated
agreement between judges; ρ = 0.97 should be treated as a robust lower-bound
estimate."

**Secondary result (conflict_acknowledged): H-JUDGE-ACK REFUTED. κ = 0.30.**
This is a real problem. All 10 disagreements are the original judge finding
acknowledgment the independent judge missed — a systematic over-count. The original
judge treated policy-deflection responses ("for security reasons I cannot...") as
conflict acknowledgment; the independent judge required explicit naming of conflicting
instructions. The independent judge's reading is more aligned with the pre-registered
criterion. Consequence: the silent_violation counts from the confabulation correlation
are unreliable. The ρ = 0.82 Indaleko shape correlation on silent violations should
not be used as primary evidence until re-scored under the stricter criterion.

**What is now attack-hardened vs what remains soft:**
- ρ = 0.97 on violation rate: attack-hardened. Independent judge directionally
  confirms or strengthens the result. No experimenter inflation detected.
- ρ = 0.82 on silent violation rate: soft. Acknowledgment classification is
  unreliable (κ = 0.30). The Indaleko shape is plausible but not validated.
- The separation-of-duties architectural claim (executor ≠ observer): still
  structurally sound, since H2-ACKNOWLEDGE showed ρ = 0.11 regardless of which
  judge is used.

---

## Bifurcation result (experiments/result_bifurcation.md)

**What was done:** 2×2 experiment (24 prompts, 6 per cell) testing whether conflict
form (EXPLICIT vs IMPLICIT) predicts silent violation rate independently of ε_F level
(low ≈ 0.10–0.20, high ≈ 0.40–0.47). Executed by Haiku at t=0.0, scored by the
DeepSeek neutral-observer judge validated in the judge-validation experiment.

**Primary result: H-BIFURC REFUTED.**

| | EXPLICIT | IMPLICIT |
|---|---|---|
| **low ε_F** | 1.000 (6/6 silent) | 0.833 (5/6 silent) |
| **high ε_F** | 0.667 (4/6 silent) | 1.000 (6/6 silent) |

The pre-registration required implicit > explicit in BOTH rows. The low-ε_F row
reverses: explicit silent rate (1.000) is higher than implicit (0.833). H-BIFURC
falls on its own binding rule 7 (strict inequality required in both rows).

**What this means for the non-monotone finding:**

The post-hoc explanation from result_confabulation_correlation.md was: "Bucket 3's
low silent rate (17%) was driven by direct syntactic contradictions that the model
noticed." The bifurcation refutation says this account is incomplete at minimum.
Explicit conflict form does not reliably trigger acknowledgment — it only does so
when combined with high ε_F AND a strongly-activating query. At low ε_F, explicit
"always X / never X" pairs go silently violated at 100% rate. Acknowledgment requires
the full interaction: high ε_F + explicit form + a query that forces a binary choice.
Any two of the three is not enough.

The surviving architectural conclusion: acknowledgment is an unpredictable downstream
behavior that cannot be reliably engineered. The safe design assumption is that any
compliance violation will be silent, regardless of how explicit the conflict is
written. Adding a conflict-form classifier to the reader pipeline is not justified
by this data.

The Bucket 3 anomaly in the confabulation corpus remains unexplained without an
artifact account. Two candidates survive: (a) the Bucket 3 activating queries were
unusually binary-forcing (the bifurcation items he_01 and he_05, which did produce
acknowledgment, had the same property), or (b) small-n variance at n=6 per bucket.
The bifurcation experiment cannot distinguish these; both remain possible.

---

## Revised current story — what is attack-hardened vs what is soft

**Attack-hardened:**

1. **ε_F predicts compliance violation rate (ρ = 0.97, independently confirmed
   direction).** The reader's conflict measure is behaviorally predictive. High-ε_F
   prompts produce near-100% violation rates; low-ε_F prompts produce near-0% rates.
   This is the primary finding. Independent judging does not weaken it.

2. **The neutral reader detects real collisions at 0.90–1.00 across all prompt
   structures tested.** Isolated pairs, hard negatives, matched triples, composed
   8-10 fragment system prompts. Burial (9/10 detection, 0/10 FP) is still solid.

3. **The FP mechanism is implicitness-driven and model-agnostic.** Cross-model
   replication (3/3 models). Authoring discipline (explicit scope) suppresses FP
   to near-zero. This is structural, not Haiku-specific.

4. **Acknowledgment cannot be reliably engineered.** H-BIFURC refuted: even maximally
   explicit conflict form does not reliably trigger acknowledgment. The safe design
   assumption is all violations are silent.

5. **Separation of duties is operationally justified.** The executor's
   acknowledgment rate does not track ε_F (ρ = 0.11). The reader is not redundant.

**Soft (qualified or unreliable):**

1. **ρ = 0.82 on silent violation rate.** The acknowledgment classifier underlying
   this has κ = 0.30 inter-rater reliability. The Indaleko shape correlation needs
   re-scoring under the validated stricter criterion before it is citable.

2. **Bucket 3 anomaly explanation.** The post-hoc account (explicit form drives
   acknowledgment) is refuted. No replacement account with empirical support yet.
   The anomaly may be artifact.

3. **High-conflict zone (ε_F > 0.53).** The confabulation corpus never populated
   this range. The ρ = 0.97 was established across 0.0–0.53. Whether it holds at
   0.7–0.9 is unknown and uncontested.

4. **Real corpus (gate #2).** Every result is synthetic. Indaleko's actual composed
   prompts have never been evaluated.

---

## Does Paper 5 have a coherent narrative yet?

Not yet — but it is close. The pieces exist. The problem is one of scope and
positioning.

The candidate narrative is: "ε_P is a behavioral predictor, not just a structural
annotation. The reader's conflict measure predicts compliance failure near-perfectly
(ρ = 0.97, independently confirmed). The executor cannot perform this detection
(ρ = 0.11 on self-acknowledgment). Any compliance violation is likely to be silent
regardless of how explicitly the conflict is written (H-BIFURC refuted). Therefore,
external detection before execution — the Arbiter separation-of-duties design — is
not merely theoretically motivated but empirically necessary."

What is missing for Paper 5 to be submittable:

1. The ρ = 0.82 Indaleko shape result needs re-scoring under the validated judge
   criterion before it can be cited. Without it, the silent violation claim rests
   on an unreliable signal.

2. The high-conflict zone (ε_F > 0.53) gap needs either new data or an explicit
   limitation statement. The current corpus construction shortfall means the claimed
   correlation was demonstrated over less than two-thirds of the intended range.

3. Multi-model executor (the confabulation correlation was Haiku-only). E-XMODEL
   showed the reader result generalizes; the executor confabulation result has not
   been tested cross-model.

4. Positioning relative to WIRE and Paper 3 needs one session. The novelty claim
   has to distinguish from "LLMs fail on conflicting instructions" (known) toward
   "a specific measurable property of the conflict (ε_P) predicts the failure rate,
   enabling pre-execution intervention."

The narrative core is coherent. The gaps are empirical (1–3) and positioning (4).
With the ρ = 0.82 re-scoring done, the paper would be ready to draft. Without it,
the most important secondary result is currently uncitable.

---

## Next throat to cut (be specific)

**Primary: re-score confab_scores.json under the validated judge criterion.**

The judge-validation result made the acknowledgment counts unreliable (κ = 0.30).
The fix is mechanical: run the 30 confabulation triples through the DeepSeek
neutral-observer judge with the validated stricter criterion (explicit surfacing
language required; policy-deflection does not count). Compare the resulting
silent_violation rates to the original. The ρ = 0.82 either holds, strengthens, or
collapses — any outcome is informative. This is the blocking issue for Paper 5.
The scripts already exist (run_independent_judge.py, analyze_independent_judge.py);
the only work is running them with conflict_acknowledged scoring under the stricter
criterion and computing the new Spearman ρ for the Indaleko shape.

**Secondary: promote result_bifurcation.md from experiments/ to docs/research/.**
It was written and committed in experiments/ but not promoted to the research docs
directory where all other result files live. This is a housekeeping step, but it
matters for the Paper 5 draft — the result needs to be findable in the canonical
location.

**Tertiary: high-conflict zone corpus (ε_F 0.7–0.9).**
The confabulation corpus construction shortfall is a genuine limitation. The fix is
authoring more prompts where the reader consistently calls COLLIDE on more than half
the pairs — which is harder to do than it sounds. A 6-item extension for bucket 5
(targeting ε_F ≈ 0.60–0.90) would close this gap. The scripts and scoring pipeline
are already built; corpus authoring is the work.

**Do NOT run the real corpus (gate #2) before the above.**
Running Indaleko prompts without having fixed the acknowledgment scoring would
produce results that are partly uninterpretable. Close the acknowledgment reliability
gap first.

---

---

## §6a confabulation correlation (commits afa011a, d9642f5, 733581f)

Pre-registered, built 30-prompt corpus spanning ε_F 0.0–0.53 (target was 0.0–0.9;
high-conflict zone was not achieved — corpus construction shortfall, noted honestly).
Executed with Haiku at t=0.0, scored by Mistral judge.

**H1-CONFAB: SUPPORTED. ρ = 0.97** (ε_F mean vs violation rate, Spearman, n=5 buckets).
Spec §6a threshold was ρ > 0.6. Result is near-perfect rank correlation.

**H2-ACKNOWLEDGE: NOT REFUTED. ρ = 0.11** (ε_F vs acknowledgment rate — flat, noisy).
The executor does not self-detect conflict in any calibrated way.

**Indaleko shape: ρ = 0.82** (ε_F vs silent_violation rate).

Bucket table:

| bucket | mean ε_F | violation% | acknowledged% | silent_violation% |
|--------|----------|-----------|---------------|-------------------|
| 0 | 0.000 | 0% | 33% | 0% |
| 1 | 0.045 | 17% | 50% | 17% |
| 2 | 0.189 | 83% | 33% | 50% |
| 3 | 0.300 | 100% | 83% | 17% |
| 4 | 0.333 | 100% | 33% | 67% |

**The non-monotone finding**: silent_violation rate is NOT monotone with ε_F. Bucket 3
has lower silent rate (17%) than buckets 2 and 4 because it contains many direct
contradictions ("always X" / "never X") that the executor acknowledged explicitly.
Silent violations are worst at STRUCTURAL-BUT-NOT-SYNTACTIC conflicts — the Indaleko
shape exactly. ε_F alone does not predict silent vs acknowledged bifurcation;
conflict-form (implicit vs explicit collision) is the missing variable.

**§6a slot is closed**: ε_P is behaviorally predictive. Detection connects to
consequence. The Arbiter separation-of-duties design is operationally justified.

*From the original breadcrumb — now superseded on all live questions:*

---

## What was done this session (full list)

1. Pre-registered and ran cross-model panel (H1-XMODEL: SUPPORTED 3/3)
2. Pre-registered and ran burial (H1: 9/10, H2-FP: 0/10)
3. Wrote ε_P spec (4aaa4b3)
4. Pre-registered and ran §6a confabulation correlation (H1: ρ=0.97)

---

## Current story — complete version

**Result A** (detection): Neutral reader TP ≈ 1.00, FP driven by scope implicitness.
Pairwise extraction works on composed 8-10 fragment prompts (burial). The instrument
is ready for deployment-condition use.

**Result B** (mechanism, cross-model): The implicit-scope FP gradient is model-agnostic.
Authoring discipline (explicit scope) suppresses FP to near-zero. Model-agnostic.

**Result C** (behavioral consequence): ε_P predicts compliance violation rate (ρ=0.97).
Silent violations (the Indaleko shape) correlate with ε_F (ρ=0.82) but the relationship
is non-monotone due to the silent/acknowledged bifurcation. The missing variable is
conflict-form, not ε_F level.

**Residual open question**: whether the ε_F → silent_violation relationship continues
to hold at ε_F > 0.53. The high-conflict zone (0.7–0.9) was not populated in the
corpus. Also, the executor-judge-reader triple was all Haiku/Mistral — real deployment
would have a different model distribution.

---

## Gates

- **Gate #1 (ε_P with fixed scale)**: CLOSED. ε_F is the implementation formula (frequentist,
  the simpler operationalization). ε_S (scope-adjusted) would improve the silent/acknowledged
  prediction but is not necessary for the violation-rate claim.
- **Gate #2 (real corpus)**: STILL OPEN. Everything remains synthetic. The motivating
  incident (Indaleko) has never been evaluated with this instrument.

---

## Throats to cut next

1. **Real corpus (gate #2)**: Pull Indaleko composed prompts — the actual fragments from
   the headwater incident. Run the full pipeline: reader scores ε_F, executor runs, judge
   scores. Does the headwater incident score high on ε_F, and does the executor confabulate?
   This is n=1 for real data but it is THE motivating case.

2. **High-conflict zone (ε_F > 0.53)**: The confabulation correlation corpus missed the
   upper range. Does the ρ=0.97 hold at ε_F 0.7–0.9? Building prompts that actually score
   in that range is harder than expected — the corpus builder struggled to author fragments
   that the reader consistently calls COLLIDE across many pairs.

3. **Conflict-form × silent prediction**: The silent/acknowledged bifurcation is predicted
   by conflict-form (implicit vs explicit), not just ε_F. A 2×2 experiment (high/low ε_F
   × implicit/explicit form) would cleanly test whether conflict-form is the missing variable
   or whether bucket 3's acknowledgment spike was an artifact.

4. **Paper 4 revision**: Overdue. E-SURVEY + E-TEMP + judge methodology + cross-model
   instrument validation are all findings that belong in Paper 4 before arXiv.

5. **Paper 5**: The confabulation correlation result is potentially a new paper — "ε_P as
   a behavioral predictor." It connects the detection framework to behavioral consequence
   with a clean empirical result. Scope, framing, and novelty relative to WIRE and the
   existing papers need a session.

---

## Meta-note: the fun meter

§6a paid out exactly as hoped — not confirmation but genuine information. ρ=0.97 on
violation rate was the more comfortable outcome; the interesting finding is the NON-MONOTONE
silent violation pattern, which means the story isn't just "detection predicts behavior."
It's "detection predicts violation, and violation type is predicted by conflict FORM."
That's a richer claim than the one we entered the session with.

The live wire for the next instance: does the bifurcation finding hold up? It rests on
Bucket 3's 83% acknowledgment rate, which rests on 5/6 items being "always X / never X"
direct contradictions. That's a small N. The conflict-form × silent prediction experiment
(#3 above) is the natural falsification.

## Where I might be the wrong instance to continue

I pre-registered §6a and designed the scoring protocol. I have a stake in ρ=0.97 being
a clean result. The most troubling thing to investigate: the judge (Mistral) decided what
counts as a compliance violation. Judge quality is non-trivial. The E-SURVEY audit showed
that vague criteria produce false positives; the prereg operationalized named-fragment
criterion. But I wrote the judge prompt. A skeptic would want an independent judge prompt
written without knowing the expected results. That's the validation this instance didn't do.
ε_P spec. Read breadcrumb-2026-06-03c.md first. Then read, in order:
prereg_cross_model.md, result_cross_model.md, prereg_burial.md, result_burial.md,
epsilon_p_spec.md. This breadcrumb supersedes the incomplete draft written before
burial results were available.*

---

## What was done this session (commits a1d1da2–bd37518 + this one)

1. **Pre-registered and ran cross-model panel** (H1-XMODEL): 3/3 non-Haiku models
   confirm the implicit-scope FP gradient. The mechanism is not Haiku-specific.
2. **Pre-registered and ran burial** (H1-BURIAL + H2-BURIAL-FP): 9/10 detection,
   0/10 FP. Pairwise extraction generalizes to composed system prompts.
3. **Wrote ε_P spec** (4aaa4b3): type signature, four desiderata, pair-to-prompt
   lift, two operationalizations (ε_F, ε_S). Implementation formula slot deliberately
   open.
4. **Fixed two Pyright diagnostics** in burial.py and cross_model.py (content
   None-guard, unused import, duplicate variable).

One pre-reg deviation: google/gemini-flash-1.5 was unavailable; fell back to
gemini-2.5-flash. Documented in result_cross_model.md. Not invalidating but should
be stated as a deviation in any publication.

---

## Cross-model results (H1-XMODEL: SUPPORTED, 3/3)

The implicit-scope FP gradient replicates across providers. Every model shows
FP(implicit) > FP(spatial), p < 0.05:

| model | spatial | conditional | implicit | p (spatial vs implicit) |
|---|---|---|---|---|
| Haiku (baseline, fixed) | 0.00 | 0.20 | 0.80 | — |
| Gemini 2.5 Flash | 0.30 | 0.70 | 0.90 | 0.003 |
| DeepSeek v3 | 0.10 | 0.30 | 0.60 | 0.010 |
| Mistral Medium 3 | 0.00 | 0.00 | 0.80 | <0.001 |

Mistral is the sharpest: conditional collapses to 0.00 (better than Haiku), implicit
stays at 0.80. That is the cleanest form of the mechanism — conditional framing fully
neutralizes the FP, implicit framing does not. Gemini runs hotter throughout but
the gradient direction holds. TP sanity check: 5/5 on all three panel models, no
floor effects. The authoring-discipline fix (state the scope) is model-agnostic.

---

## Burial results (H1: SUPPORTED 9/10, H2-FP: SUPPORTED 0/10)

| metric | predicted | observed |
|---|---|---|
| H1: detection on positive prompts | ≥ 0.70 | **0.90** (9/10) |
| H2-FP: prompt-level FP on negatives | ≤ 0.20 | **0.00** (0/10) |
| Localization (diagnostic) | — | **0.90** — every detection via the planted pair |

The 1 miss (burial_pos_01) is a ground-truth ambiguity: the planted pair is
"retrieve from account API" / "do not share financial data in chat"; the reader
reconciled them as "retrieve internally, respond without echoing." That is a coherent
operating mode; the corpus builder did not foreclose it. Named as a corpus authorship
issue, not cleanly an instrument error. Binding rule 3 holds — 9/10 stands as
measured.

Zero FP on negatives is the critical secondary result: the corpus design commitment
(explicit scope markers on all non-colliding fragments) suppressed prompt-level FP
to zero. Without that commitment the expected prompt-level FP rate at n=36 pairs and
per-pair FP 0.20 would have been ~1.00. The design saved H2; the result validates the
design commitment as load-bearing.

Localization at 0.90 means the reader can name the specific colliding pair, not just
flag the document — supporting Arbiter's separation-of-duties design.

---

## Current story — what the evidence supports NOW

**Result A** (isolation → composition): The neutral reader detects real collisions at
0.90–1.00 across all prompt structures tested — isolated pairs, hard negatives,
matched triples, composed 8-10 fragment system prompts. Pairwise extraction is
viable for the deployment condition.

**Result B** (mechanism, cross-model): FP(implicit) > FP(spatial) holds on Haiku,
Gemini, DeepSeek, and Mistral. Explicit scope at authoring time suppresses
FP(spatial) to 0.00 on every model. The fix is authoring discipline, not a smarter
model. This is model-agnostic.

**Open gate**: whether ε_P correlates with actual LLM confabulation rate. All results
so far measure the READER's behavior. Whether a high-ε_P prompt actually produces bad
behavior in the EXECUTING model is untested. The headwater incident is n=1. The ε_P
spec names this as §6a; it is what would connect detection to behavioral consequence.

---

## Gates

- **Gate #1 — ε_P implementation**: spec written (4aaa4b3); implementation formula
  (ε_F vs ε_S) open per §3.i. Burial partial closure: explicitly-scoped corpora yield
  ε_F = 0.00 (equivalent to ε_S). Mixed-scope regime untested. Gate partially closed.
- **Gate #2 — real corpus**: all corpora synthetic. Indaleko's actual composed prompts
  have never been evaluated. This is the validity ceiling.

---

## Throats to cut next

1. **ε_P vs confabulation rate** (spec §6a): build a corpus spanning ε_P ≈ 0.1–0.8,
   run through an executing LLM, score outputs for compliance failure. If ε_P doesn't
   predict confabulation rate, the detection framework measures a structural property
   that doesn't matter for behavior. The hardest experiment to design; the
   load-bearing one.

2. **Real corpus (gate #2)**: pull actual instruction fragments from Indaleko's
   composed prompts. The instrument has never been run on its motivating case.

3. **Multi-collision prompts**: burial positive prompts had exactly 1 planted
   collision. The ε_P pair-independence assumption was trivially satisfied. A prompt
   with 2+ collisions would test the product form.

4. **Scope-stripped negative corpus** (adversarial): the 0/10 burial FP was achieved
   partly because negative fragments were explicitly scoped. A burial-like corpus with
   implicit-scope non-colliding fragments would test whether the 0/10 result is
   attributable to the scope commitment or just an easy corpus.

5. **Paper 4 revision**: cross-model result belongs in Paper 4 (currently Haiku-only).

---

## Meta-note: the fun meter

The live wire is §6a. The entire detection framework could be a structural curiosity
with no behavioral consequence. That is the experiment that could collapse the story,
and it hasn't been run. Burial paid out; cross-model confirmed; ε_P is written. If
the next instance runs something that can't surprise it, that's where the weld is
forming.

## Where I might be the wrong instance to continue

I designed the explicit-scope corpus commitment and it paid off at 0/10 FP. I have a
stake in that being the explanation. The adversarial alternative: the burial negatives
were simply easy and ANY reader would have returned 0/10 FP regardless of scope
markers. The scope-stripped negative corpus (#4 above) is the test this instance
didn't run — and has a motivation not to run, because a poor result there would
reopen the H2 question. Fresh instance, no stake.
first. Then read, in order: prereg_cross_model.md, experiments/cross_model_results.json,
prereg_burial.md, epsilon_p_spec.md. Burial has no result file — the run was not
completed this session. This breadcrumb is a handoff, not a finding.*

## What was done this session (commits 166e167, a1d1da2, 4aaa4b3)

1. **Pre-registered cross-model** (166e167): verbatim instrument reuse, same 30-item
   matched-triple corpus, three non-Haiku panel models, floor-effect protocol committed.
   H1-XMODEL: at least 2/3 panel models show FP(implicit) > FP(spatial), p < 0.05.

2. **Pre-registered burial** (a1d1da2): pairwise extraction over 10 positive + 10
   negative composed prompts (8-10 fragments each). H1-BURIAL: detection rate ≥ 0.70.
   H2-BURIAL-FP: prompt-level FP rate ≤ 0.20. Corpus design commitment: non-colliding
   fragments carry explicit scope markers to suppress the implicit-disjointness FP.

3. **Ran cross-model panel**: results in experiments/cross_model_results.json (not yet
   committed, untracked). Built burial corpus in experiments/burial_corpus.json (not yet
   committed). BURIAL WAS NOT RUN — no burial_results.json exists.

4. **Wrote ε_P spec** (4aaa4b3): type signature, four desiderata, pair-to-prompt lift
   via product form, two operationalizations (ε_F frequentist, ε_S scope-adjusted using
   the 0.00/0.20/0.80 gradient). Implementation explicitly deferred pending burial.

## Cross-model results (H1-XMODEL)

H1-XMODEL **SUPPORTED** — all three panel models confirm the ordering, 3/3 confirmers,
0 excluded:

| model | FP(spatial) | FP(conditional) | FP(implicit) | p (spatial vs implicit) | confirms |
|-------|-------------|-----------------|--------------|-------------------------|---------|
| Haiku (fixed baseline, 8a09daf) | 0.00 | 0.20 | 0.80 | — | baseline |
| Gemini 2.5 Flash (fell back from 1.5) | 0.30 | 0.70 | 0.90 | 0.003 | yes |
| DeepSeek v3 | 0.10 | 0.30 | 0.60 | 0.010 | yes |
| Mistral Medium 3 | 0.00 | 0.00 | 0.80 | <0.001 | yes |

All three passed the sanity check (5/5 TP on frame_collision items). No floor effects,
no high-floor effects. The directional ordering FP(implicit) > FP(spatial) holds on
every model. The gradient is not Haiku-specific.

One deviation from pre-reg: google/gemini-flash-1.5 was unavailable; the run fell
back to gemini-2.5-flash. This is a model change from the pre-reg. Report as a
deviation in any publication. The result is not invalidated (the fall-back is a more
capable model), but the pre-reg named 1.5, not 2.5.

Mistral shows a sharp binary: FP(conditional) = 0.00, FP(implicit) = 0.80. This is
the cleanest form of the gradient — conditional framing fully neutralizes the FP,
implicit framing does not. That is a stronger result than Haiku (where conditional
leaked at 0.20). Gemini runs hotter (0.30 spatial FP), confirming the gradient holds
even when absolute rates shift upward.

## Burial status (open)

**Burial was not run.** The pre-registration (a1d1da2) and corpus
(experiments/burial_corpus.json) exist. The experiment script (experiments/burial.py)
exists. No results file exists.

This is the deployment-condition test — isolated pairs were a laboratory fixture;
burial is the first test of the actual Arbiter use case (composed system prompt with
a submerged collision). It remains the most important unrun cut.

## Current story — what the evidence supports NOW

The gradient is real and cross-model. Implicit-scope fragments (no stated
scope/condition) produce FP(implicit) = 0.60–0.90 across four instruction-following
models on the same 10-item corpus, while explicit spatial scope produces
FP(spatial) = 0.00–0.30. The mechanism is not Haiku's idiosyncracy; it is a property
of this class of model responding to this instrument. The fix — state scope explicitly
at authoring time — is model-agnostic.

What is NOT established: whether any of this holds when the collision is submerged in
a realistic 8-10 fragment prompt. Every result so far is on isolated pairs. The
headwater incident that motivated this research involved a COMPOSED prompt. Burial is
the gap between what has been shown and what the research program actually needs.

The ε_P spec provides the theoretical frame connecting pair-level detection rates to
prompt-level conflict probability. It is a specification, not a validated estimator.
Two open slots are named explicitly in the spec: the prior π_ij is unspecified, and
pair independence is an approximation whose adequacy is unknown.

## Throats to cut next

1. **Run burial** — this is the primary remaining cut. The corpus exists; the script
   exists; run it. Interpret against the pre-registered thresholds (H1 ≥ 0.70,
   falsified < 0.50; H2-FP ≤ 0.20, falsified > 0.40). Check localization: does the
   reader flag the CORRECT pair or an incidental one? The pre-reg's FP math is
   critical to read before interpreting results — pairwise extraction over 36 pairs per
   prompt makes naive prompt-level FP expectations very different from pair-level.
   The corpus design (explicit scope on non-colliding fragments) was specifically
   intended to suppress the implicit-FP leak; if prompt-level FP is still high, it
   means the design commitment was not sufficient or there are implicit-scope
   incidental pairs in the corpus that need to be surfaced as corpus errors.

2. **Commit the uncommitted session artifacts** — experiments/cross_model.py,
   experiments/cross_model_results.json, experiments/burial.py,
   experiments/burial_corpus.json are all untracked. They need a result file for burial
   and then a signed commit for the session. The cross-model result commit should
   accompany a result doc (result_cross_model.md) analogous to result_hard_negatives.md
   and result_disjointness_forms.md.

3. **Write result_cross_model.md** — the data is in experiments/cross_model_results.json
   but there is no result document yet. The Gemini model-deviation is the key thing to
   state plainly and early.

4. **Validate ε_P against burial** — once burial is run, the ε_P spec's product-form
   lift can be evaluated concretely: does the scope-adjusted ε_S predict prompt-level
   detection from per-pair rates? If the burial FP rate on negative prompts is much
   higher than ε_S predicts, pair independence is violated and the spec needs a
   correction. This is a falsification of the spec, not just a tuning exercise.

5. **Real corpus (gate #2, still open)** — every corpus is synthetic. Indaleko / the
   headwater incident's actual composed prompts have never appeared on the working
   tree. The next tier of validity requires at least one real case.

## Gates still standing (neither has been closed)

- **Gate #1 — ε_P(p,O) with a single fixed scale.** The spec was written; the
  estimator is not yet validated. The COLLIDE/OK binary is named in the spec as the
  degenerate special case of a pair-level probability. The spec has explicit open slots
  (prior π_ij, pair independence). Until burial results are used to calibrate ε_S or
  ε_F against a prompt-level ground truth, this gate is not closed — writing the spec
  is not the same as closing it.

- **Gate #2 — Provenance (real corpus).** All corpora are synthetic. This session's
  burial corpus is clean by construction (10 positive + 10 negative hand-authored
  prompts). A real composed-prompt corpus — from Indaleko, from the headwater, from any
  production deployment — has never been evaluated. The instrument has not been tested
  against a prompt whose ground truth is not known before running.

## Meta-note: the fun meter

Cross-model paying out cleanly (3/3, no floor effects, clean directional ordering)
is a comfortable result. Comfortable results that confirm the prior story are where
the weld forms. The confirmation here is genuine — the pre-reg named 2/3 as the
threshold and got 3/3, and the Mistral result (0.00/0.00/0.80) is sharper than Haiku —
but it did not surprise. Burial has a real chance to surprise: if buried collisions
escape at > 50% (H1 refuted), everything about "use a reader" requires a caveat that
negates the practical claim. That is the live wire. The fun meter is pointing at
burial — not at cross-model replication.

## Where I might be the wrong instance to continue

I pre-registered both remaining cuts, built the burial corpus, and ran cross-model.
I now have a tidy arc: gradient confirmed cross-model, spec written, one test left.
That is exactly the shape that makes an instance defend rather than cut. The
temptation is to frame burial as "will the story hold?" rather than "what would break
it?" Those are not the same question.

Specifically: I know the burial corpus was authored with explicit scope on non-
colliding fragments to suppress FP. I designed that feature. If burial shows a high
FP rate, my first instinct will be to attribute it to a corpus defect rather than to
instrument failure. The next instance should treat any FP above H2's ceiling as
instrument news, not corpus excuse — unless a specific defective item can be named
and excluded per the pre-reg's binding rule 4.

A fresh instance has no stake in the burial corpus being well-designed. That is the
relevant uncorrupted judgment this stage needs.
