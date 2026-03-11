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
| E2-R7 | meta-llama/llama-4-maverick | 120 | 425 | 71 | 16.71% |
| E2-R8 | openai/gpt-5-mini | 120 | 429 | 32 | 7.46% |
| E2-R9 | anthropic/claude-haiku-4.5 | 120 | 441 | 31 | 7.03% |

## Gate Read

- Mixed: two model families exceed promotion target (`16.02%` on gpt-4o-mini, `16.71%` on llama-4-maverick), while three newer families cluster near ~7% at 120-case budget (`gpt-5-mini 7.46%`, `gemini-2.0-flash 7.41%`, `claude-haiku-4.5 7.03%`).
- Cross-model evidence now indicates a bimodal outcome profile rather than uniformly high discrimination; promotion remains gated on explicit deployment mode and sentinel/non-regression checks.

Newer-model triage checkpoint:
- `models.txt` sweep (10-case bounded runs) completed on 8 models.
- Best triage discrimination was modest (`1.49%` on `llama-4-maverick`), indicating the need for higher-budget follow-up before drawing cross-model conclusions.

## Next

1. Perform transition-focused review for `reject->accept` and `rewrite->accept` shifts in high-discrimination runs.
2. Perform transition-focused review for `rewrite->clarify` concentration in ~7% runs.
3. Complete sentinel rerun with the current candidate policy before any gate promotion decision.
4. Decide deployment mode: model-conditioned routing vs single cross-family default.

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
- `data/analysis/e2_semantic_ablation_report_llama4maverick_120.json`
- `data/analysis/e2_semantic_ablation_report_llama4maverick_120.md`
- `data/analysis/e2_semantic_ablation_report_gpt5mini_120.json`
- `data/analysis/e2_semantic_ablation_report_gpt5mini_120.md`
- `data/analysis/e2_semantic_ablation_report_claudehaiku45_120.json`
- `data/analysis/e2_semantic_ablation_report_claudehaiku45_120.md`
- `data/analysis/e2_model_sweep_summary.json`
- `data/analysis/e2_model_sweep_summary.md`
