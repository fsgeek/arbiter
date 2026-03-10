# Hypothesis Card Template

Use one card per hypothesis or policy delta. Keep cards append-only and
versioned.

## 1. Header

- `card_id`: `HC-YYYYMMDD-<slug>-vN`
- `status`: `proposed | accepted | rejected | deferred`
- `owner`:
- `date_created`:
- `related_track`: `A | B | A+B`
- `linked_plan_section`:

## 2. Claim

- `research_question`:
- `hypothesis_statement`:
- `null_hypothesis`:
- `scope`:

## 3. Proposed Change

- `change_type`: `rule | canon | threshold | decomposition | evaluator | policy-routing | benchmark`
- `change_summary`:
- `implementation_targets`:
- `risk_class`: `low | medium | high`

## 4. Pre-Registered Evaluation

- `datasets`:
- `benchmark_version`:
- `sentinel_set`:
- `primary_metrics`:
- `secondary_metrics`:
- `success_criteria`:
- `regression_guardrails`:
- `stopping_rule`:

## 5. Adversarial Challenge Plan

- `model_critics`:
- `human_spoiler_required`: `yes | no`
- `challenge_protocol`:
- `expected_failure_modes`:

## 6. Results

- `run_ids`:
- `summary`:
- `effect_sizes`:
- `confidence_intervals`:
- `unexpected_outcomes`:

## 7. Decision

- `decision`: `promote | hold | rollback | archive`
- `rationale`:
- `follow_up_actions`:
- `owner_signoff`:

## 8. Artifact Links

- `code_diff`:
- `analysis_notebook_or_script`:
- `reports`:
- `incident_records`:

## 9. Notes

- `assumptions`:
- `open_questions`:
- `next_review_date`:
