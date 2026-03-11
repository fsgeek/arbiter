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

Additional reruns:

| Run | Model | LLM Cases | Compared | Diff | Discrimination |
|-----|-------|-----------|----------|------|----------------|
| E2-R1 | openai/gpt-4o-mini | 40 | 361 | 17 | 4.71% |
| E2-R2 | openai/gpt-4o-mini | 60 | 381 | 33 | 8.66% |
| E2-R3 | openai/gpt-4o-mini | 120 | 437 | 70 | 16.02% |
| E2-R4 | google/gemini-2.0-flash-001 | 40 | 360 | 6 | 1.67% |
| E2-R5 | google/gemini-2.0-flash-001 | 120 | 432 | 32 | 7.41% |
| E2-R6 | openai/gpt-5-mini | 60 | 373 | 10 | 2.68% |

## Gate Read

- Mixed: one run exceeds promotion target (`16.02%`), while gemini runs remain below threshold (`1.67%`, `7.41%`).
- Cross-model stability not yet established; hold promotion pending robustness runs.

Newer-model triage checkpoint:
- `models.txt` sweep (10-case bounded runs) completed on 8 models.
- Best triage discrimination was modest (`1.49%` on `llama-4-maverick`), indicating the need for higher-budget follow-up before drawing cross-model conclusions.

## Next

1. Rerun E2 with larger case budget (>=120 LLM cases).
2. Run at least one additional model family with 120-case budget for fair comparison.
3. Perform transition-focused review for `clarify` shifts and threshold sensitivity.

## Artifacts

- `data/analysis/e2_semantic_ablation_report.json`
- `data/analysis/e2_semantic_ablation_report.md`
- `scripts/run_e2_semantic_ablation.py`
- `data/analysis/e2_semantic_ablation_report_gpt4omini_120.json`
- `data/analysis/e2_semantic_ablation_report_gpt4omini_120.md`
- `data/analysis/e2_semantic_ablation_report_gpt4omini_60.json`
- `data/analysis/e2_semantic_ablation_report_gpt4omini_60.md`
- `data/analysis/e2_semantic_ablation_report_gemini20_40.json`
- `data/analysis/e2_semantic_ablation_report_gemini20_40.md`
- `data/analysis/e2_semantic_ablation_report_gemini20_120.json`
- `data/analysis/e2_semantic_ablation_report_gemini20_120.md`
- `data/analysis/e2_semantic_ablation_report_gpt5mini_60.json`
- `data/analysis/e2_semantic_ablation_report_gpt5mini_60.md`
- `data/analysis/e2_model_sweep_summary.json`
- `data/analysis/e2_model_sweep_summary.md`
