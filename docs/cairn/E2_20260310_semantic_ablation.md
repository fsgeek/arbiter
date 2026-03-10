# E2 — Semantic-Augmented Ablation (Run 1)

Date: 2026-03-10  
Model/provider: `openai/gpt-4o-mini` via OpenRouter  
LLM case budget: 40 (of 721 pending)

## Objective

Measure real-corpus scalar-vs-tensor discrimination after introducing semantic LLM adjudication channels.

## Results

- Structural scores: 327
- LLM scores added: 40
- Total tensor entries compared: 361
- Decision differences (scalar vs tensor): 17
- Discrimination rate: 4.71%

Transition highlights:
- `rewrite->clarify`: 6
- `reject->clarify`: 3
- `reject->rewrite`: 3

Parseability summary (same run):
- JSON parse failures: 0.00%
- Optional channel presence:
  - `t/i/f`: 95.00%
  - `evidence_quality`: 97.50%
  - `declared_losses`: 97.50%
  - `decision`: 100.00%
  - `drafter_identity`: 100.00%
- malformed declared-loss rate: 0.00%

## Gate Read

- Promotion target (`>= 0.10`) not met in this run.
- Direction is positive versus structural baseline (`0.00% -> 4.71%`).

## Next

1. Rerun E2 with larger case budget (>=120 LLM cases).
2. Rerun E2 on second model family for cross-model robustness.
3. Perform transition-focused review for `clarify` shifts and threshold sensitivity.

## Artifacts

- `data/analysis/e2_semantic_ablation_report.json`
- `data/analysis/e2_semantic_ablation_report.md`
- `scripts/run_e2_semantic_ablation.py`
