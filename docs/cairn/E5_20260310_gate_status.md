# E5 Gate Status Snapshot (2026-03-10)

Status: HOLD (provisional)

## E2 Run Summary

| Artifact | Model | LLM Cases | Discrimination | Declared-Loss Presence |
|---|---|---:|---:|---:|
| `e2_semantic_ablation_report.json` | `openai/gpt-4o-mini` | 40 | 4.71% | 97.50% |
| `e2_semantic_ablation_report_gpt4omini_60.json` | `openai/gpt-4o-mini` | 60 | 8.66% | 98.33% |
| `e2_semantic_ablation_report_gpt4omini_120.json` | `openai/gpt-4o-mini` | 120 | 16.02% | 99.17% |
| `e2_semantic_ablation_report_gemini20_40.json` | `google/gemini-2.0-flash-001` | 40 | 1.67% | 35.00% |
| `e2_semantic_ablation_report_gemini20_120.json` | `google/gemini-2.0-flash-001` | 120 | 7.41% | 52.50% |
| `e2_semantic_ablation_report_gpt5mini_60.json` | `openai/gpt-5-mini` | 60 | 2.68% | 100.00% |
| `e2_semantic_ablation_report_llama4maverick_120.json` | `meta-llama/llama-4-maverick` | 120 | 16.71% | 100.00% |
| `e2_semantic_ablation_report_gpt5mini_120.json` | `openai/gpt-5-mini` | 120 | 7.46% | 99.17% |
| `e2_semantic_ablation_report_claudehaiku45_120.json` | `anthropic/claude-haiku-4.5` | 120 | 7.03% | 100.00% |

## Gate Read

- Best observed discrimination gain: **16.71%** (meets >=10% threshold)
- Worst observed discrimination gain: **1.67%** (cross-model instability remains)
- gpt-4o-mini and llama-4-maverick both exceed threshold at 120-case budget.
- gpt-5-mini, gemini-2.0-flash, and claude-haiku-4.5 now cluster near ~7% discrimination at 120-case budget with generally good parseability (gemini remains weakest on declared-loss coverage).
- Interpretation: current policy appears model-family sensitive; a single default may not be justified without sentinel non-regression evidence.
- Promotion remains **HOLD** until cross-model stability criteria are satisfied.

## Newer-Model Sweep Checkpoint (10-case triage)

- Completed models from `models.txt`: 8
- Top discrimination in bounded triage:
  - `meta-llama/llama-4-maverick`: 1.49%
  - `allenai/olmo-3.1-32b-instruct`: 0.60%
  - `x-ai/grok-4.1-fast`: 0.30%
- Remaining completed models showed 0% discrimination in this low-budget triage.
- Three models stalled/omitted under provider latency constraints:
  - `z-ai/glm-5`
  - `qwen/qwen3.5-397b-a17b`
  - `moonshotai/kimi-k2.5`

Interpretation:
- We are no longer relying on old-model-only evidence.
- The low-case-budget sweep is useful for triage but insufficient for promotion decisions.
- Next evidence step is high-budget reruns on the best newer-model candidates.

## Required to Exit HOLD

1. Re-run sentinel suite and verify severe-failure non-increase under chosen deployment policy.
2. Decide promotion mode: cross-family default vs explicit model-conditioned deployment.
3. If choosing cross-family default, tune thresholds on sentinel and rerun E2 confirmation.
