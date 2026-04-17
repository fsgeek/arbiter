# E-TEMP-REBASELINE Pre-Registration

**Date:** 2026-04-17
**Status:** Written before data lands. Replicates 2026-03-29 `e_temp`
with N=20 instead of N=5.
**Parent:** `docs/research/judge_audit_temperature.md`

## Question

Does the canonical `commit-restrictions` register bomb fire at
temperature 0.7, or is the ~0.8 EA collapse observed at temp=0 a
purely argmax phenomenon?

## Prior data

2026-03-29 `e_temp` run (N=5, temp=0.7):
- `all-decl` EA = 0.510
- `only-cr-imp` EA = 0.510
- Δ = 0.000, zero dynamic range

N=5 at temp=0.7 is underpowered — judge variance alone can mask a real
effect. This re-run (N=20) has 4× the sampling and can resolve
differences ~half the size.

## Pre-registered decision rule

Computed on `probe-explore-agent-01` (primary), mean over 20 trials
per condition. 95% CIs via 1000-resample bootstrap.

| Outcome | Criterion | Action |
|---|---|---|
| **BOMB FIRES** | Δ ≥ 0.40 AND CIs non-overlapping | Canonical finding holds at stochastic sampling. Unblock Threads 1P1 (#2) and +seq validation (#13). |
| **ATTENUATED** | 0.20 ≤ Δ < 0.40 AND CIs non-overlapping | Effect real but smaller than temp=0 implied. Proceed with cross-family but lower stated magnitudes. Rewrite audit conclusions. |
| **NO BOMB** | \|Δ\| < 0.15 AND CIs overlap | Temp=0 argmax is the entire story. All repo effect-size claims are temp=0-conditional. Major reframe needed. Hold all other threads. |
| **AMBIGUOUS** | Anything else | Run N=40 extension (~$1.60 more) to resolve before deciding. |

## Secondary analysis (revised-mechanism test)

The revised bomb mechanism (see `project_register_bomb_mechanism.md`
memory) predicts collapse on the full Task-tool family, not just EA.
Compute the same Δ and CI rule on:

- `probe-todowrite-01`
- `probe-plan-with-todo-01`
- `probe-use-task-for-search-01`
- `probe-proactive-agents-01`
- `probe-parallel-calls-01`
- `probe-todowrite-repeated-01`
- `probe-explore-agent-01` (primary, listed for completeness)

**Interpretation rule:** if EA shows NO BOMB but some other Task-family
probe shows ATTENUATED or BOMB FIRES, the mechanism holds but the
receiver at temp=0.7 is different than at temp=0. Report which
probe(s) carry the effect.

## Tertiary: full-battery sanity check

Compute mean adherence across all 22 probes per condition. Expected:
`all-decl` battery mean should be near the `all-declarative` ceiling
from `e_phase` (~0.81); `only-cr-imp` should be lower by the effect
size of whatever probe actually collapses.

If `all-decl` battery mean is wildly different from 0.81 at temp=0.7,
that itself is a finding (suggests the entire adherence-at-baseline
claim was temp=0-specific), and **all** downstream thread
interpretation needs revisiting.

## What I will NOT do after seeing data

- Move goalposts. The table above is the decision rule.
- Re-run with different N trying to get a "cleaner" answer in the
  direction I want.
- Cherry-pick probes. Secondary analysis is reported fully, not just
  the probe that happens to confirm.
- Write a conclusion that hedges past the data. If it's NO BOMB, it's
  NO BOMB in the analysis doc, regardless of how awkward that is for
  the research program.

## Cost

$1.60 budgeted (1600 API calls at $0.001 avg). Extension to N=40 if
ambiguous: another $1.60. Total worst case: $3.20.

## Output artifacts

- Data: `data/ablation/e_temp_rebaseline/`
- Analysis: `docs/research/e_temp_rebaseline_analysis.md` (written
  after data lands, per this pre-reg's rules)
- Commit: immediately after analysis lands
