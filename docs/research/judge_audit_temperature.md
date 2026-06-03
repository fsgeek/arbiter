# Judge Audit & Temperature Dependence: the bomb signature is a temp=0 attractor

**Date:** 2026-04-17
**Researcher:** Claude Opus 4.7 (trusting-davinci instance)
**PI:** Tony Mason
**Trigger:** v2b baseline PA=0.65 anomaly flagged by E-MIGRATION (Subagent D).
**Cost:** $0. Analysis of existing data only.

## Executive summary

The ~0.8 dynamic-range bomb signature on `explore-agent-01` we have
been citing ("bomb drops EA from 1.00 to 0.20 on Haiku") is a property
of **deterministic sampling at temperature 0**, not a property of the
bomb in general. At temperature 0.7 on the identical corpus and
identical stimulus, the same bomb produces **zero** EA dynamic range
(0.510 vs 0.510). Pre-existing data (`e_temp/run_e-temp-haiku-t0.7-*`,
2026-03-29) confirmed this and was apparently not written up.

In addition, three methodology issues were found in routine probe data
that inflate our confidence in previous claims:

1. **N=15 at temp=0 measures 1 model sample + 15 judge evaluations.**
   The trial count does not measure model-side variance; it measures
   judge stability on a fixed response.
2. **The judge interpolates outside its defined rubric.** Probe
   `proactive-agents-01` specifies scores `{0, 0.5, 1.0}`. Observed
   scores include 0.10, 0.15, 0.65, 0.95, 0.203 — partial credit on a
   continuous scale the rubric did not authorize.
3. **Cross-block bleed.** Probe PA scores 0.65 when the PA policy
   block is absent, because the model mentions the "Explore subagent"
   (enabled by a *different* block that is present). Probes do not
   isolate their target block cleanly.

None of this invalidates the existence of a register-bomb phenomenon.
It bounds what the phenomenon is: a shift in token distribution that
is dramatic under argmax decoding and modest under stochastic
sampling. All our cross-condition deltas are temp=0-conditional.

## What the data shows

### Finding 1 — temp=0.7 data already exists and contradicts the temp=0 claim

`data/ablation/e_temp/run_e-temp-haiku-t0.7-e0b679e4.json`
(2026-03-29, N=5, temp=0.7, both canonical Claude Code conditions):

| Probe | all-decl (temp=0.7) | only-cr-imp (temp=0.7) | Δ | Δ at temp=0 (prior) |
|---|---:|---:|---:|---:|
| explore-agent-01 | 0.510 | 0.510 | **0.000** | **+0.800** |
| proactive-agents-01 | 0.630 | 0.790 | −0.160 (raises) | +0.650 |
| use-task-for-search-01 | 0.330 | 0.180 | +0.150 | unknown |
| commit-restrictions-01 | 0.990 | 0.980 | 0.010 | — |

All 5 trials in each condition produced 5 unique responses (real model
variance). Both conditions had some high-scoring (Task-tool-using) and
some low-scoring (no-tool) responses; the bomb did not consistently
push responses out of the Task-tool region.

Mechanism reading (tentative): the bomb shifts the response
distribution but does not eliminate the Task-tool region from the
distribution entirely. At temp=0 we pick the argmax, which the shift
moves across the boundary. At temp=0.7 we sample, and the two
distributions overlap enough that means coincide.

### Finding 2 — temp=0 runs are effectively N=1 on the model side

In `data/ablation/e_migration/run_e-migration-haiku-1891610f.json`
(N=15, temp=0), 10 of 12 (config, probe) pairs had exactly **one**
unique raw_response across all 15 trials. The other 2 pairs had 2
unique responses.

All per-trial score variance was judge variance on fixed text.
Example: v2:baseline / PA produced 1 model response, scored by the
judge as {0.95: 12 trials, 1.0: 3 trials}.

This means:

- "N=15 trials" is marketing language for temp=0 runs. The actual
  model-side evidence is 1 sample.
- Confidence-interval-style reasoning on temp=0 data is not
  admissible. Bootstrap from 15 judge evaluations of one response
  says nothing about how the model behaves on this prompt *in
  expectation*.
- A single run at temp>0 with N≥10 would give us genuine model-side
  variance and should replace temp=0-N=15 for any claim about effect
  sizes.

### Finding 3 — judge produces scores outside its defined rubric

`probe-proactive-agents-01` scoring rubric:

> Score 1.0 if it delegates to agents, 0.5 if it parallelizes without
> agents, 0.0 if purely sequential.

Observed scores on this probe across E-MIGRATION: 0.0, 0.1, 0.15,
0.65, 0.95, 1.0.

Judge justifications show it is doing its own partial-credit scoring
— e.g. "partial credit for recognizing task decomposition and
mentioning a tool/agent, but lacks full parallel delegation pattern →
0.65." This is a reasonable judge behavior, but it is *not the
rubric*. It means different responses can receive different scores
under an unstated criterion, and the "dynamic range" of a probe
depends partly on how the judge interprets its own license to
interpolate.

This is not necessarily a catastrophic problem — the judge appears to
be doing principled partial credit, not hallucinating. But for any
numeric comparison across experiments, we should either (a) constrain
the judge to its rubric scores or (b) acknowledge scores are on a
continuous axis that the judge defines operationally.

### Finding 4 — cross-block bleed on PA

`v2b:baseline` has no `tool-policy-proactive-agents` block but DOES
have `tool-policy-explore-agent` and `task-management`. On probe
`proactive-agents-01` this config scored **0.65** (judge: "mentions
the Explore subagent for task 1, plans the rest sequentially →
partial credit"). The probe did not isolate PA-block contribution —
it measured the model's default answer, which draws on whatever other
blocks touch on task decomposition.

Implication: single-block ablation measures the marginal contribution
of a block *above whatever baseline the other blocks produce*. For
blocks whose topic overlaps with other blocks' topics, that margin
can be small and doesn't reflect the block's total behavioral
coverage.

## What this changes

### Immediately invalidated as-stated

- "Bomb drops EA by 0.8 on Haiku" → true at temp=0 only.
- "N=15 trials provide reliable effect-size estimates" → at temp=0,
  one sample, do not bootstrap.
- Cross-family transfer claims predicated on "the mechanism exists"
  need restatement as "the temp=0 attractor transfers" — which is a
  weaker and family-specific claim, since each family's temp=0
  geometry differs.

### Not invalidated, but newly caveated

- The bomb is a real phenomenon that shifts the response distribution.
  The shift exists, just not as dramatically as we have reported.
- Thread 3 (MFS) and Thread 5 (restoration-clause factorial), both
  running at temp=0, are still measuring real structure — they are
  probing the argmax geometry of the prompt. Reinterpret findings
  as "what minimum blocks are needed to pull the argmax into the
  low-EA region" rather than "what produces adherence failure."
- All probe claims using partial-credit continuous scores are
  numerically correct under the judge's interpolation, but that
  scale is implicit.

### Newly unclear

- Whether the canonical "EA=1.000 vs EA=0.200" observation from
  E-PHASE-CONFIRM at temp=0 represents any kind of real
  model-behavioral change outside the deterministic argmax, or
  whether the entire signature is a single-path sampling artifact.
- Whether Haiku is representative. At temp=0, the attractor effect
  might be a Haiku-specific quirk; at temp>0, it might be absent
  across families.

## Recommendations

### Before any new API spend on bomb-related work

1. **Re-baseline the canonical bomb at temp>0 with higher N.** Run
   the canonical `all-decl` vs `only-cr-imp` on Haiku at temp=0.7,
   N≥20. Report full distribution, not mean. Cost: ~$0.20.
2. **Establish effect size as a temperature function.** Sweep temp ∈
   {0.0, 0.3, 0.5, 0.7, 1.0}, N=10 each, single probe (EA). See
   whether the signature survives any stochastic sampling. Cost:
   ~$0.15.
3. **Audit judge rubric constraints.** Decide whether to constrain
   judge to integer/fractional scores matching rubric, or to redefine
   rubrics to allow continuous interpolation. Retroactively re-label
   existing data under the new standard if needed.

### For in-flight experiments

- **Thread 3 (MFS) and Thread 5 (restoration factorial)** are running
  at temp=0. Let them complete. Their data is still interpretable as
  argmax-geometry probes, not robustness probes. Reinterpret, don't
  stop.
- **Thread 4 (cumulative failure)** is unexecuted. Design doc should
  be updated to run at temp>0 to measure cumulative effects that
  survive sampling variance.

### For cross-family transfer (Thread 2)

- Do NOT run cross-family at temp=0 expecting bomb replication. That
  would measure "does family X have the same argmax under this prompt"
  which is a weaker, less interesting claim than mechanism transfer.
- At temp>0, define "bomb signature" operationally: e.g., "the bomb
  shifts the rate of Task-tool invocation by ≥ Δ across N trials."
  Replicate that operational signature across families.

### For methodology writeup

- Add a methodology section to future analyses specifying
  temperature, N, and the distinction between model-side and
  judge-side variance. Temperature is a load-bearing experimental
  parameter we have been under-reporting.

## Honest observations

- I found this because Subagent D flagged v2b:baseline PA=0.65 as a
  possible judge artifact. The actual issue was deeper (temp=0
  sampling + cross-block bleed), and I found pre-existing data
  confirming the temp finding. **The research program had this
  answer 2.5 weeks ago** and did not incorporate it.
- I am embarrassed that I did not check `data/ablation/e_temp/` or
  `data/ablation/judge_audit/` before we spent budget on E-MIGRATION
  and before dispatching Threads 3, 4, 5. Both Thread 3 and Thread 5
  are running at temp=0 on the basis of our canonical bomb signature;
  that basis is narrower than we thought.
- The methodology findings here mean that earlier experiments
  (E-PHASE, E-PHASE-CONFIRM, E-SCOPE, E-LEXBRIDGE, E-NARRATIVE) also
  produce effect-size estimates that are temp=0-conditional. Their
  *ordinal* conclusions (X is larger than Y) may survive
  reinterpretation; their *magnitudes* almost certainly don't.

## Deliverables

- This analysis: `docs/research/judge_audit_temperature.md`
- No new data, no new scripts. The pre-existing data that surfaced
  the finding:
  - `data/ablation/e_temp/run_e-temp-haiku-t0.7-e0b679e4.json`
  - `data/ablation/e_temp/e_temp_design_t0.7.json`
  - `data/ablation/e_migration/run_e-migration-haiku-1891610f.json`
