# T16: E-XMODEL — Register Bomb is Haiku-Specific (But Probe Battery Doesn't Transfer)

**Date:** 2026-03-29
**Status:** Complete
**Parent:** T15 (E-SCOPE), T14 (E-PHASE-CONFIRM)
**Cost:** ~$1.08

## Finding

The commit-restrictions register bomb only detonates on Haiku (1/4 models).
BUT: DeepSeek and Mistral have floor-effect baselines (0.333, 0.167) meaning
the probe battery doesn't transfer. Gemini is immune (1.000 across all
conditions). We cannot distinguish "Haiku-specific" from "untestable on
other models."

## Bomb Detonation Matrix

| Model | all-decl | only-cr-imp | scoped-inline | Bomb? |
|-------|----------|-------------|---------------|-------|
| haiku | 1.000 | 0.200 | 1.000 | YES |
| gemini | 1.000 | 1.000 | 1.000 | no |
| deepseek | 0.333 | 0.667 | 0.667 | no* |
| mistral | 0.167 | 0.500 | 0.333 | no* |

*Floor baseline — measurement invalid

## Key Insight

Probe battery transfer is a prerequisite for cross-model comparison.
Model-agnostic task design needed for genuine cross-model register studies.
