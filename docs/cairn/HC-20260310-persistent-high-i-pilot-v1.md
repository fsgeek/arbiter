# Hypothesis Card

## 1. Header

- `card_id`: `HC-20260310-persistent-high-i-pilot-v1`
- `status`: `in_progress`
- `owner`: `arbiter`
- `date_created`: `2026-03-10`
- `related_track`: `B`
- `linked_plan_section`: `B3, E3`

## 2. Claim

- `research_question`: Which conflict cases show durable high indeterminacy under repeated adjudication?
- `hypothesis_statement`: A measurable subset of semantic conflict cases remains persistently high-I across repeated passes.
- `null_hypothesis`: No cases remain persistently high-I under repeated passes with fixed prompts.
- `scope`: bounded pending-case subset from benchmark corpus.

## 3. Proposed Change

- `change_type`: `benchmark | evaluator`
- `change_summary`: Add pilot script for persistent-high-I detection over repeated passes.
- `implementation_targets`:
  - `scripts/run_e3_persistent_high_i.py`
- `risk_class`: `medium`

## 4. Pre-Registered Evaluation

- `datasets`: `data/prompts/claude-code/v2.1.50_blocks.json`
- `benchmark_version`: `benchmark_v0`
- `sentinel_set`: `not yet applied in pilot; next iteration`
- `primary_metrics`:
  - persistent_count
  - persistent_ratio
- `secondary_metrics`:
  - rule/tier distribution of persistent-high-I cells
  - parseability rates for optional channels
- `success_criteria`:
  - detect at least one persistent-high-I cell under pilot criterion
- `regression_guardrails`:
  - JSON parse failure <= 5%
- `stopping_rule`:
  - pilot pass after one successful run with reproducible script output

## 5. Adversarial Challenge Plan

- `model_critics`: `pending`
- `human_spoiler_required`: `no` (pilot)
- `challenge_protocol`: `deferred to full E3 run`
- `expected_failure_modes`: pilot overstates persistence without canon/context mutation sweeps.

## 6. Results

- `run_ids`:
  - `2026-03-10-e3-persistent-high-i-openrouter-gpt4omini-10x2`
- `summary`:
  - 10 keys evaluated across 2 passes
  - 1 key met persistent-high-I criterion (`tau_i=0.60`, `epsilon=0.03`)
  - persistent ratio: 10.00%
- `effect_sizes`:
  - persistent_ratio: `0.10`
- `confidence_intervals`: `not computed in pilot`
- `unexpected_outcomes`:
  - one stable high-I cell already appears in a small bounded run

## 7. Decision

- `decision`: `hold`
- `rationale`: pilot signal is promising but incomplete; requires larger run + mutation sweeps for validity.
- `follow_up_actions`:
  - rerun with larger case budget
  - add canon/context mutation sweeps
  - run second model family for stability
- `owner_signoff`: `arbiter (provisional)`

## 8. Artifact Links

- `code_diff`: `scripts/run_e3_persistent_high_i.py`
- `analysis_notebook_or_script`: `scripts/run_e3_persistent_high_i.py`
- `reports`:
  - `data/analysis/e3_persistent_high_i_report.json`
  - `data/analysis/e3_persistent_high_i_report.md`
- `incident_records`: `none`

## 9. Notes

- `assumptions`: fixed prompt and rule context; no mutation sweeps in pilot.
- `open_questions`:
  - how stable is persistent-high-I under context/canon mutations?
  - does persistence remain under second model family?
- `next_review_date`: `2026-03-17`
