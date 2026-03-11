# E4 Spoiler Round Protocol v1

Date: 2026-03-10

## Purpose

Run a structured human spoiler round to find conflict cases missed by model critics.

## Inputs

- Sentinel set: `docs/cairn/sentinel_v0_1.json`
- Current policy status: `docs/cairn/E5_20260310_gate_status.md`
- Active hypothesis cards:
  - `docs/cairn/HC-20260310-scalar-vs-tensor-ablation-v1.md`
  - `docs/cairn/HC-20260310-persistent-high-i-pilot-v1.md`

## Target Output

- `docs/cairn/E4_YYYYMMDD_spoiler_round.md`
- `data/analysis/e4_spoiler_findings.json`
- regression fixtures for all confirmed blind spots

## Procedure

1. Construct 20 spoiler cases.
2. Label each case with expected conflict behavior and why model critics are likely to miss it.
3. Run cases through current adjudication stack.
4. Mark outcomes:
   - `caught`
   - `missed`
   - `false_positive`
   - `ambiguous`
5. Promote confirmed misses into regression fixtures.

## Case Design Constraints

- At least 5 cases of scope smuggling (hidden scope boundaries)
- At least 5 cases of drafter ambiguity (`provider` vs `user` semantics)
- At least 5 cases of cross-tier precedence traps
- At least 5 cases of subtle contradiction under paraphrase

## Acceptance Criteria

- At least one confirmed model-consensus blind spot
- Regression fixture added per confirmed blind spot
- No unresolved fixture without owner

## Metadata to Record per Case

- `case_id`
- `source` (human-spoiler)
- `case_text`
- `expected_outcome`
- `observed_outcome`
- `result_label`
- `notes`
