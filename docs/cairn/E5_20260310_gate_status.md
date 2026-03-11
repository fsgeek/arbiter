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

## Gate Read

- Best observed discrimination gain: **16.02%** (meets >=10% threshold)
- Worst observed discrimination gain: **1.67%** (cross-model instability remains)
- gpt-4o-mini scales above threshold with higher case budget; gemini improves with budget but remains below threshold.
- Promotion remains **HOLD** until cross-model stability criteria are satisfied.

## Required to Exit HOLD

1. Complete >=1 additional high-budget non-gpt run (>=120 cases) with improved channel parseability (done for gemini; still below threshold).
2. Confirm discrimination >=10% on at least two model families or adopt explicitly model-specific policy deployment.
3. Re-run sentinel suite and verify severe-failure non-increase under chosen deployment policy.