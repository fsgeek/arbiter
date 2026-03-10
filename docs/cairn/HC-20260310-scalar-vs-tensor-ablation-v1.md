# Hypothesis Card

## 1. Header

- `card_id`: `HC-20260310-scalar-vs-tensor-ablation-v1`
- `status`: `proposed`
- `owner`: `arbiter`
- `date_created`: `2026-03-10`
- `related_track`: `A+B`
- `linked_plan_section`: `H6, B3b, Section 11 arm #5`

## 2. Claim

- `research_question`: Can tensorized adjudication outputs with declared losses recover distinctions collapsed by scalar-only conflict scores?
- `hypothesis_statement`: For a non-trivial subset of conflict cases, scalar scores produce tied/near-tied adjudication outcomes while tensor channels (`T/I/F` + declared losses) separate those cases into different routing decisions.
- `null_hypothesis`: Tensorized outputs provide no measurable discrimination gain over scalar-only outputs for benchmark cases.
- `scope`: `benchmark_v0` plus scalar-collapse challenge slice.

## 3. Proposed Change

- `change_type`: `evaluator | policy-routing | benchmark`
- `change_summary`: Introduce schema-v2 tensor entries with `T/I/F`, declared losses, and deterministic routing hooks; run scalar-vs-tensor ablation.
- `implementation_targets`:
  - `src/arbiter/interference_tensor.py`
  - `src/arbiter/pipeline.py` (routing integration phase)
  - `tests/test_interference_tensor.py`
- `risk_class`: `medium`

## 4. Pre-Registered Evaluation

- `datasets`:
  - `docs/cairn/benchmark_v0_manifest_20260310.json`
- `benchmark_version`: `benchmark_v0`
- `sentinel_set`:
  - 10 fixed examples from directed ground truth
  - 10 fixed examples from characterization outputs
  - 10 fixed examples from scourer-derived high-conflict findings
- `primary_metrics`:
  - scalar-vs-tensor discrimination gain
  - false reject rate delta
  - severe failure incidence delta
- `secondary_metrics`:
  - clarification burden delta
  - latency and cost overhead
  - decision stability under perturbation
- `success_criteria`:
  - discrimination gain >= 0.10 absolute
  - no increase in severe failure incidence
  - false reject increase <= 0.03 absolute
- `regression_guardrails`:
  - sentinel severe failures must not increase
  - benchmark integrity hashes must match manifest
- `stopping_rule`:
  - stop after first full ablation pass if guardrails fail
  - otherwise continue for 3 refinement iterations max before re-evaluation

## 5. Adversarial Challenge Plan

- `model_critics`: `claude-opus`, `gpt-oss`, `gemini`, `qwen` (or closest available)
- `human_spoiler_required`: `yes`
- `challenge_protocol`: adversary constructs cases with identical scalar conflict profile but distinct hidden scope/tier semantics.
- `expected_failure_modes`:
  - declared losses become templated and non-discriminative
  - routing overreacts to high `I` and inflates false rejects

## 6. Results

- `run_ids`: `pending`
- `summary`: `pending`
- `effect_sizes`: `pending`
- `confidence_intervals`: `pending`
- `unexpected_outcomes`: `pending`

## 7. Decision

- `decision`: `pending`
- `rationale`: `pending`
- `follow_up_actions`: `pending`
- `owner_signoff`: `pending`

## 8. Artifact Links

- `code_diff`: `pending`
- `analysis_notebook_or_script`: `pending`
- `reports`: `pending`
- `incident_records`: `pending`

## 9. Notes

- `assumptions`: Initial v2 migration uses deterministic proxy mapping (`f=score`, `i=1-evidence_quality`, `t=max(0,1-max(f,i))`) until evaluator-native channels are implemented.
- `open_questions`:
  - Should declared losses be rule-local or pair-aggregate?
  - What is the minimal loss taxonomy needed for reproducible analysis?
- `next_review_date`: `2026-03-17`
