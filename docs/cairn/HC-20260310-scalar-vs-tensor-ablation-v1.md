# Hypothesis Card

## 1. Header

- `card_id`: `HC-20260310-scalar-vs-tensor-ablation-v1`
- `status`: `in_progress`
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

- `run_ids`:
  - `2026-03-10-scalar-tensor-ablation-v0`
  - `2026-03-10-e1-parseability-openrouter-gpt4o-mini-8cases`
  - `2026-03-10-e2-semantic-ablation-openrouter-gpt4o-mini-40cases`
  - `2026-03-10-e2-semantic-ablation-openrouter-gpt4o-mini-60cases`
  - `2026-03-10-e2-semantic-ablation-openrouter-gpt4o-mini-120cases`
  - `2026-03-10-e2-semantic-ablation-openrouter-gemini-2.0-flash-40cases`
  - `2026-03-10-e2-semantic-ablation-openrouter-gemini-2.0-flash-120cases`
- `summary`:
  - real structural slice: 327 comparisons, 0 decision differences (0.00% discrimination gain)
  - synthetic collapse slice: 6 comparisons, 3 decision differences (50.00% discrimination gain)
  - E1 parseability batch (8 cases, OpenRouter gpt-4o-mini): 100% optional-channel coverage, 0% JSON failures
  - E2 semantic-augmented run (40 LLM cases + structural baseline): 361 comparisons, 17 decision differences (4.71% discrimination gain)
  - E2 semantic-augmented run (60 LLM cases + structural baseline, gpt-4o-mini): 381 comparisons, 33 decision differences (8.66% discrimination gain)
  - E2 semantic-augmented run (120 LLM cases + structural baseline, gpt-4o-mini): 437 comparisons, 70 decision differences (16.02% discrimination gain)
  - E2 semantic-augmented run (40 LLM cases + structural baseline, gemini-2.0-flash): 360 comparisons, 6 decision differences (1.67% discrimination gain)
  - E2 semantic-augmented run (120 LLM cases + structural baseline, gemini-2.0-flash): 432 comparisons, 32 decision differences (7.41% discrimination gain)
- `effect_sizes`:
  - discrimination gain (real): `0.00`
  - discrimination gain (synthetic): `0.50`
  - discrimination gain (semantic-augmented real): `0.0471`
  - discrimination gain (semantic-augmented real, gpt-4o-mini 60-case): `0.0866`
  - discrimination gain (semantic-augmented real, gpt-4o-mini 120-case): `0.1602`
  - discrimination gain (semantic-augmented real, gemini-2.0-flash 40-case): `0.0167`
  - discrimination gain (semantic-augmented real, gemini-2.0-flash 120-case): `0.0741`
- `confidence_intervals`: `not computed in baseline harness`
- `unexpected_outcomes`:
  - real structural baseline produced no scalar-vs-tensor separation, indicating current structural-only channel lacks sufficient ambiguity signal
  - semantic augmentation improved real discrimination but remains below promotion threshold (`0.10`)
  - cross-model variance is large: gpt-4o-mini run exceeds threshold while gemini run remains low, suggesting model-dependent channel quality
  - gemini improves with larger budget (`1.67%` -> `7.41%`) but still below threshold; parseability quality remains lower than gpt runs

## 7. Decision

- `decision`: `hold`
- `rationale`: mechanics validated and threshold exceeded in one model family (`0.1602`), but cross-model stability is not yet established (`0.0167` on gemini run); hold until robustness criteria are met.
- `follow_up_actions`:
  - add evaluator prompt templates that request declared losses and decision traces
  - rerun E2 with larger case budget and second model family
  - investigate high-impact transition categories (`reject->clarify`, `rewrite->clarify`) for threshold tuning
  - run E2 with additional model families and consistent case budgets for fair comparison
- `owner_signoff`: `arbiter (provisional)`

## 8. Artifact Links

- `code_diff`: `research branch commits 398d0ab, 36b821e`
- `analysis_notebook_or_script`: `scripts/run_scalar_tensor_ablation.py`
- `reports`:
  - `data/analysis/scalar_tensor_ablation_v0.json`
  - `data/analysis/scalar_tensor_ablation_v0.md`
  - `data/analysis/e1_parseability_report.json`
  - `data/analysis/e1_parseability_report.md`
  - `data/analysis/e2_semantic_ablation_report.json`
  - `data/analysis/e2_semantic_ablation_report.md`
  - `data/analysis/e2_semantic_ablation_report_gpt4omini_120.json`
  - `data/analysis/e2_semantic_ablation_report_gpt4omini_120.md`
  - `data/analysis/e2_semantic_ablation_report_gpt4omini_60.json`
  - `data/analysis/e2_semantic_ablation_report_gpt4omini_60.md`
  - `data/analysis/e2_semantic_ablation_report_gemini20_40.json`
  - `data/analysis/e2_semantic_ablation_report_gemini20_40.md`
  - `data/analysis/e2_semantic_ablation_report_gemini20_120.json`
  - `data/analysis/e2_semantic_ablation_report_gemini20_120.md`
- `incident_records`: `none`

## 9. Notes

- `assumptions`: Initial v2 migration uses deterministic proxy mapping (`f=score`, `i=1-evidence_quality`, `t=max(0,1-max(f,i))`) until evaluator-native channels are implemented.
- `open_questions`:
  - Should declared losses be rule-local or pair-aggregate?
  - What is the minimal loss taxonomy needed for reproducible analysis?
- `next_review_date`: `2026-03-17`
