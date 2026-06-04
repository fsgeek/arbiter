# Breadcrumb for the next instance — 2026-06-04

*From the instance that ran both remaining cuts (burial + cross-model) and wrote the
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
