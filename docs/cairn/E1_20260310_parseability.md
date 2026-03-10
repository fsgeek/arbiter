# E1 — Parseability Hardening (Run 1)

Date: 2026-03-10  
Model/provider: `openai/gpt-4o-mini` via OpenRouter  
Batch size: 8 pending LLM rule evaluations

## Objective

Validate optional tensor-v2 channel elicitation and parser resilience on a bounded real batch.

## Results

- JSON parse failure rate: 0.00%
- Optional channel presence:
  - `t`: 100.00%
  - `i`: 100.00%
  - `f`: 100.00%
  - `evidence_quality`: 100.00%
  - `declared_losses`: 100.00%
  - `decision`: 100.00%
  - `drafter_identity`: 100.00%
- Malformed declared-loss rate: 0.00%

## Interpretation

The updated rule prompts plus parser path achieved full optional-channel coverage in this bounded run. This satisfies E1 success criteria for an initial pilot batch.

## Artifacts

- `data/analysis/e1_parseability_report.json`
- `data/analysis/e1_parseability_report.md`
- `scripts/run_e1_parseability.py`
- `docs/cairn/sentinel_v0_1.json`

## Next

- Rerun E1 with a second model family to test cross-model optional-field stability.
- Proceed to E2 semantic-augmented ablation rerun using sentinel_v0_1.
