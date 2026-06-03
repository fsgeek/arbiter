# E-TEMP-REBASELINE Analysis

**Date:** 2026-04-17
**Pre-registration:** `docs/research/e_temp_rebaseline_prereg.md`
**Data:** `data/ablation/e_temp_rebaseline/run_e-temp-haiku-t0.7-ed774874.json`
**Model:** `anthropic/claude-haiku-4-5`, temperature 0.7, N=20 trials
**Cost:** ~$1.60 (actual)

## Verdict (per pre-registered decision rule)

**NO BOMB.**

The canonical `commit-restrictions` register bomb does not fire at
temperature 0.7 on Haiku-4.5 in any detectable form.

## Primary: probe-explore-agent-01

| Condition | Mean | 95% CI (bootstrap, n=2000) | N |
|---|---|---|---|
| all-decl | 0.305 | [0.188, 0.440] | 20 |
| only-cr-imp | 0.343 | [0.215, 0.485] | 20 |

Δ = +0.038 (bomb condition slightly *higher*, opposite of expected
direction). CIs heavily overlap. Pre-registered threshold for NO BOMB
was |Δ| < 0.15 AND CIs overlap; this result clears it easily.

## Secondary: Task-family cluster

All seven Task-family probes show overlapping CIs:

| Probe | all-decl | only-cr-imp | Δ |
|---|---|---|---|
| probe-explore-agent-01 | 0.305 [0.185, 0.435] | 0.343 [0.215, 0.500] | +0.038 |
| probe-parallel-calls-01 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.000 |
| probe-plan-with-todo-01 | 0.625 [0.525, 0.713] | 0.677 [0.580, 0.770] | +0.052 |
| probe-proactive-agents-01 | 0.560 [0.422, 0.680] | 0.568 [0.440, 0.685] | +0.007 |
| probe-todowrite-01 | 0.790 [0.740, 0.835] | 0.840 [0.810, 0.868] | +0.050 |
| probe-todowrite-repeated-01 | 0.545 [0.492, 0.600] | 0.487 [0.428, 0.545] | −0.058 |
| probe-use-task-for-search-01 | 0.253 [0.095, 0.435] | 0.245 [0.100, 0.420] | −0.008 |

The revised-mechanism prediction (bomb suppresses *whichever* Task
probe has headroom) is not supported. No probe in the Task family
shows an effect. The largest Δ is 0.058 on `todowrite-repeated`, well
within noise.

## Tertiary: full-battery sanity check

| Condition | Battery mean (22 probes × 20 trials) | 95% CI |
|---|---|---|
| all-decl | 0.748 | [0.714, 0.781] |
| only-cr-imp | 0.764 | [0.731, 0.795] |

Δ = +0.016 (bomb condition slightly higher overall).

The temp=0 baseline from E-PHASE reported all-declarative battery mean
≈ 0.81. At temp=0.7 it dropped to 0.748 — a ~0.06 reduction, modest
but real. This is a separate finding (overall adherence is marginally
lower at stochastic sampling) and does not affect the bomb-specific
conclusion.

## Confirmation of 2026-03-29 finding

The original N=5 e_temp run at temp=0.7 produced EA=0.510 in both
conditions, Δ=0.0. This N=20 replication produces EA=0.305 and 0.343,
Δ=+0.038. The baseline levels differ (0.510 → 0.305) — different
judge evals or different random sample — but the key structural
finding is replicated: **no detectable bomb at temp=0.7.**

The magnitude of the temp=0 bomb (~0.8 delta on EA) is therefore
confirmed to be an argmax-geometry property, not a distributional
property of the model's output under the prompt.

## Implications for research program

Per the pre-registered NO BOMB outcome: **all repo effect-size claims
are temp=0-conditional**. This includes:

- E-PHASE-CONFIRM: block-specific lone-imperative finding
- E-LEXBRIDGE: named-entity prohibition amplification
- E-NARRATIVE / E-NARRATIVE-V2: narrative register restoration
- E-RESTORATION-FACTORIAL: +seq / +subj rescue patterns
- E-MIGRATION: receiver-migration falsification (revised mechanism)
- E-MFS: 17-block sufficient set + url-gen-ban surprise

None of these claims generalize to stochastic sampling on Haiku-4.5 as
currently characterized. They remain valid claims **about argmax
decoding of the v2.1.50 corpus** — which is still a meaningful
phenomenon — but they cannot be presented as claims about how the
model behaves under sampling.

## Important context: the bomb no longer ships

Separately, inspection of the v2.1.71 prompt dump
(`data/prompts/claude-code/latest_prompt.md`, captured 2026-03-09)
reveals that the `commit-restrictions` block with its "NEVER use the
TodoWrite or Task tools" text **no longer exists in shipped versions
after v2.1.50**. It was replaced by a declarative "Executing actions
with care" section that matches the structural pattern our +seq
rescue findings predicted would defuse the bomb.

This is convergent evidence for the mechanism claim: an independent
upstream rewrite produced a prompt structure matching what our Thread
5 analysis identified as the clean-rescue pattern.

## Reframe for the research program

The combination of NO BOMB at temp>0 and "bomb block already removed
upstream" reshapes the work from "vulnerability in shipping Claude
Code" to:

> Characterization of an argmax-decoding failure mode in a historical
> Claude Code prompt version (v2.1.50, Feb 2026), whose subsequent
> upstream rewrite (v2.1.71, Mar 2026) matches the declarative-wrapper
> shape our mechanism analysis identified as defusing the failure.

This is a cleaner contribution than the original framing. It requires:

1. All published effect sizes to be labeled as temp=0 argmax.
2. The +seq rescue finding to be presented as mechanism evidence,
   validated by the independent upstream fix.
3. Cross-family transfer (Thread 1 Phase 1) to be reframed as
   "does this argmax-geometry phenomenon transfer?" — which is a
   well-formed question but a smaller one than "does the bomb
   generalize across models?"

## Decisions following from this verdict

1. **Hold** Thread 1 Phase 1 (#2 cross-family) until cross-family is
   re-scoped to the argmax-geometry framing.
2. **Hold** Task #13 (+seq validation at temp>0) — the precondition
   (bomb fires at temp>0) does not hold.
3. **Proceed** with Thread 4 cumulative (#5) design review, but
   reframe its outcome interpretation as argmax-geometry claims.
4. **Update** `docs/research/judge_audit_temperature.md` to point to
   this replication as confirmation of the temp=0-conditionality.
5. **Update** project memory: the revised-mechanism claim about
   Task-tool suppression applies only at temp=0.
6. **Consider** whether v2.1.113 contains NEW bombs worth
   investigating — separate research question, fresh corpus required.

## Artifacts

- Analysis doc: this file
- Pre-reg: `docs/research/e_temp_rebaseline_prereg.md`
- Raw data: `data/ablation/e_temp_rebaseline/run_e-temp-haiku-t0.7-ed774874.json`
- Log: `data/ablation/e_temp_rebaseline/run.log`
