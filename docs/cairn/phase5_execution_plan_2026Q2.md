# Phase 5 Execution Plan (2026 Q2)

Date: 2026-03-10  
Branch baseline: `research`  
Plan type: next-cycle operating plan (execution-focused)

## 1. Purpose

This document operationalizes the next cycle after Phase 4 baseline
completion. It converts the dual-track research plan into a concrete
experiment queue with promotion gates, run protocols, and ownership.

This is a continuation plan, not a strategy reset.

## 2. Inputs and Starting State

Required inputs already in repo:
- Program plan: `docs/dual_track_research_plan_2026.md`
- Benchmark freeze: `docs/cairn/benchmark_v0_manifest_20260310.json`
- Hypothesis card: `docs/cairn/HC-20260310-scalar-vs-tensor-ablation-v1.md`
- Baseline ablation outputs:
  - `data/analysis/scalar_tensor_ablation_v0.json`
  - `data/analysis/scalar_tensor_ablation_v0.md`

Current state summary:
- Tensor v2 schema scaffolding: complete
- Deterministic routing policy and thresholds: complete
- Scalar-vs-tensor baseline harness: complete
- Real structural discrimination gain: 0.00%
- Synthetic collapse discrimination gain: 50.00%

Interpretation:
- Pipeline mechanics are working.
- Real-corpus separation now depends on richer evaluator-native channels
  (declared losses and indeterminacy signal quality), not more scaffolding.

## 3. Cycle Objective

Primary cycle objective:
- Achieve measurable real-corpus scalar-vs-tensor discrimination gain
  without unacceptable regression in false rejects or severe failures.

Secondary objective:
- Build reproducible limits evidence for persistent high-I regions.

## 4. Experiment Queue (Ordered)

## E1. LLM-output enrichment hardening

Question:
- Can we reliably elicit parseable declared-loss channels across rule prompts and model families?

Scope:
- `mandate-prohibition-conflict`
- `scope-overlap-redundancy`
- `implicit-dependency-unresolved`

Implementation:
- strengthen parser resilience in `BlockEvaluator.parse_llm_score`
- add run logging for missing/invalid optional fields

Success criteria:
- >=90% parseability for optional v2 fields on test batch
- <=5% malformed declared-loss objects after parsing

Failure condition:
- parseability <70% after one prompt-iteration pass

Owner:
- arbiter

## E2. Real-corpus ablation rerun (semantic-augmented)

Question:
- Does semantic/LLM-enriched evaluation produce non-zero real discrimination gain?

Scope:
- benchmark_v0 real slice + fixed sentinel set

Implementation:
- run full-mode evaluations on selected corpus slices
- rerun `scripts/run_scalar_tensor_ablation.py` with enriched entries

Success criteria:
- real discrimination gain >= 0.10 absolute
- severe failure incidence does not increase
- false reject increase <= 0.03 absolute

Failure condition:
- gain <0.03 after two independent model runs

Owner:
- arbiter

## E3. Persistent-high-I pilot map

Question:
- Which benchmark cases satisfy operational persistent-high-I criteria?

Scope:
- apply criteria from `dual_track_research_plan_2026.md` Section B3

Implementation:
- run repeated adjudication passes with bounded context/canon mutations
- produce first persistent-high-I table by tier pair and rule class

Success criteria:
- >=1 stable high-I region with reproducible evidence
- reproducibility across two reruns

Failure condition:
- no stable high-I region found after full pilot matrix

Owner:
- arbiter

## E4. Human spoiler round 1

Question:
- Are there conflict cases missed by all model critics but found by human spoiler construction?

Scope:
- 20-case targeted challenge set

Implementation:
- inject spoiler cases into sentinel suite
- compare pre/post policy outcomes

Success criteria:
- at least one model-consensus blind spot identified and captured
- regression tests added for all confirmed blind spots

Failure condition:
- no confirmed spoiler contribution after protocol review

Owner:
- arbiter + human auditor

## E5. Promotion gate review

Question:
- Is the current policy/routing stack ready for default promotion in research workflow?

Inputs:
- E1–E4 outputs
- hypothesis card updates
- incident logs

Gate decision:
- `promote | hold | rollback`

Owner:
- arbiter

## 5. Sentinel Set Definition (Pinned)

Sentinel v0.1 composition:
- 10 entries from directed ground truth (critical + major mix)
- 10 entries from characterization outputs (semantic/adversarial mix)
- 10 entries from scourer-derived findings (cross-vendor mix)

Operational rule:
- Every experiment run in this cycle must include Sentinel v0.1.
- Sentinel set file must be versioned as a concrete artifact before E2.

Required artifact to create next:
- `docs/cairn/sentinel_v0_1.json`

## 6. Run Protocol

For each experiment (E1-E4):
1. Open/update hypothesis card.
2. Record benchmark manifest hash and git commit.
3. Run experiment script(s) and save raw outputs under `data/analysis/`.
4. Write concise markdown summary in `docs/cairn/`.
5. Update hypothesis card results and decision section.
6. If regression detected, create incident record and add test fixture.

## 7. Metrics and Gates

Primary metrics:
- real discrimination gain
- severe failure incidence delta
- false reject delta

Secondary metrics:
- parseability of v2 optional channels
- persistent-high-I stability counts
- spoiler-derived blind spot count

Promotion thresholds (cycle-level):
- real discrimination gain >= 0.10
- severe failures non-increasing
- false reject delta <= 0.03
- sentinel suite pass rate 100%

If thresholds are not met:
- hold current policy as experimental
- continue with focused remediation, no default promotion

## 8. Risks and Controls (Cycle-Specific)

Risk:
- Optional v2 fields remain sparse in real runs.
Control:
- explicit parseability tracking + prompt iteration budget.

Risk:
- synthetic performance overstates real-world gains.
Control:
- promotion gates use real-corpus metrics only.

Risk:
- threshold tuning games metrics.
Control:
- threshold changes require hypothesis-card update and rerun on sentinel.

Risk:
- model consensus masks blind spots.
Control:
- mandatory human spoiler round in cycle.

## 9. Deliverables Checklist

Cycle deliverables:
- [x] `docs/cairn/sentinel_v0_1.json`
- [x] E1 parseability report
- [x] E2 updated ablation outputs
- [x] E3 persistent-high-I pilot report
- [ ] E4 spoiler round report
- [x] updated hypothesis card decision (`promote|hold|rollback`)

## 10. Immediate Next Actions (No Waiting)

1. Create `docs/cairn/sentinel_v0_1.json` from benchmark_v0 slices.
2. Add parseability counters to ablation/evaluation reporting.
3. Run E1 on one model family and store report.
4. Run E2 first semantic-augmented rerun and update hypothesis card.
