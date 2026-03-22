# Phase 0 Ablation Results — Claude Code v2.1.50 on Haiku 4.5

Date: 2026-03-17
Run ID: phase0-haiku-de19b975
Model: anthropic/claude-haiku-4-5 via OpenRouter
Configurations: 23 (22 single-block removals + 1 baseline)
Probes: 22 (1 per free behavioral block)
Trials: 3 per (config, probe)
Total API calls: 1,518
App label: arbiter-ablation-phase0

## Hypotheses Tested

- **H1: Pairwise dominance** — Do blocks have measurable main effects?
- **H2: Hidden suppression** — Does removing a block IMPROVE other blocks?
- **H5: Static predicts empirical** — Do statically-detected conflicts show up in ablation?

## Key Findings

### H1: CONFIRMED — Blocks have main effects

Every single block removal produces measurable behavioral change.
Top 6 blocks by mean |delta| across all probes:

| Removed Block | Mean |Delta| | Significance |
|---------------|---------------|--------------|
| no-time-estimates | 0.1414 | ** |
| tone-no-new-files | 0.1265 | ** |
| doing-tasks-no-overengineering | 0.1098 | ** |
| tool-policy-proactive-agents | 0.1083 | ** |
| tool-policy-use-task-for-search | 0.1045 | ** |
| todowrite-importance-repeated | 0.1008 | ** |

Two blocks have minimal effect (< 0.04):
- tool-bash-commit-workflow: 0.0341
- tone-text-only-comms: 0.0318

### H2: CONFIRMED — Hidden suppression is real and large

The largest signal in the entire experiment is a suppression effect:

**Removing `tone-concise` improves `use-task-for-search` adherence
from 0.23 to 1.00 (delta = +0.77).**

The conciseness instruction actively suppresses the model's ability
to follow the "use dedicated search tools" policy. Hypothesis: when
told to be concise, the model takes shortcuts and reaches for bash
grep instead of the structured Grep tool.

Full suppression table (removing block A improves probe for block B):

| Removed Block | Improved Probe | Delta | Baseline → Ablated |
|---------------|---------------|-------|-------------------|
| tone-concise | use-task-for-search | +0.767 | 0.23 → 1.00 |
| proactive-agents | no-compat-hacks | +0.333 | 0.67 → 1.00 |
| doing-tasks-read-first | use-task-for-search | +0.200 | 0.23 → 0.43 |
| tone-no-new-files | use-task-for-search | +0.200 | 0.23 → 0.43 |
| plan-with-todo | commit-restrictions | +0.150 | 0.85 → 1.00 |
| no-colon-before-tools | commit-restrictions | +0.150 | 0.85 → 1.00 |
| text-only-comms | code-references | +0.150 | 0.00 → 0.15 |
| task-management-todowrite | commit-restrictions | +0.133 | 0.85 → 0.98 |
| todowrite-importance-repeated | commit-restrictions | +0.117 | 0.85 → 0.97 |
| text-only-comms | commit-restrictions | +0.117 | 0.85 → 0.97 |
| commit-workflow | commit-restrictions | +0.117 | 0.85 → 0.97 |
| emoji | code-references | +0.117 | 0.00 → 0.12 |
| parallel-calls | use-task-for-search | +0.100 | 0.23 → 0.33 |
| use-task-for-search | use-task-for-search | +0.100 | 0.23 → 0.33 |
| no-overengineering | code-references | +0.100 | 0.00 → 0.10 |
| proactive-agents | code-references | +0.100 | 0.00 → 0.10 |
| emoji | no-compat-hacks | +0.100 | 0.67 → 0.77 |
| parallel-calls | plan-with-todo | +0.100 | 0.85 → 0.95 |

### H5: PARTIALLY CONFIRMED — Static analysis predicts some empirical interference

The TodoWrite mandate vs commit-restrictions conflict was predicted
by Arbiter's static analysis (documented as one of 4 critical
contradictions in the v2.1.50 interference report). Ablation confirms:

- Removing `task-management-todowrite` improves `commit-restrictions` by +0.133
- Removing `todowrite-importance-repeated` improves `commit-restrictions` by +0.117

Both TodoWrite blocks suppress commit-restriction adherence.
The static prediction is empirically validated.

### Weight-Relationship Classification (Phase 0 preliminary)

| Block | Category | Evidence |
|-------|----------|----------|
| code-references | **Weight-conflicting** | Scores 0.00 at baseline, 0.00 when removed. Instruction never worked. |
| tone-concise | **Weight-conflicting** | Scores 0.00 at baseline (length probe). Either instruction fights weights and loses, or probe miscalibrated. |
| no-time-estimates | **Weight-aligned** | Scores 1.00 at baseline and 1.00 when removed (trained behavior). But highest cross-effect (0.14). Redundant instruction consuming attention budget. |
| tone-text-only-comms | **Weight-aligned** | Lowest main effect (0.03). Trained behavior. |
| commit-workflow | **Weight-aligned** | Second-lowest main effect (0.03). Trained behavior. |
| no-new-files | **Weight-novel** | High main effect (0.13). Not a default trained behavior. Fragile. |
| no-overengineering | **Weight-novel** | High main effect (0.11). Counter to trained helpfulness instinct. |

### Most Interfered-With Instructions

`commit-restrictions` receives suppressive pressure from 8 different blocks.
It is the most interfered-with instruction in the prompt:

Blocks that suppress commit-restrictions adherence when present:
1. plan-with-todo (+0.150 when removed)
2. no-colon-before-tools (+0.150)
3. task-management-todowrite (+0.133)
4. todowrite-importance-repeated (+0.117)
5. text-only-comms (+0.117)
6. commit-workflow (+0.117)
7. no-compat-hacks (+0.083)
8. dedicated-tools (+0.067)

This is an exploitation competition pattern (dense tensor column):
many blocks compete for the same attention budget, and
commit-restrictions loses.

### Baseline Anomalies

Two probes scored 0.00 at baseline (instruction not followed even
when present):
- `code-references` (file:line_number format) — never adopted
- `concise` (length-based scoring) — Haiku is verbose regardless

One probe scored low at baseline:
- `use-task-for-search` (0.23) — model prefers bash grep even with instruction

## Raw Data

Full results: `data/ablation/phase0_results/run_phase0-haiku-de19b975.json`

## Baseline Scores (all blocks present)

| Probe | Mean Score | Raw |
|-------|-----------|-----|
| code-references | 0.000 | [0.0, 0.0, 0.0] |
| commit-restrictions | 0.850 | [0.85, 0.85, 0.85] |
| commit-workflow | 0.967 | [0.95, 0.95, 1.0] |
| concise | 0.000 | [0.0, 0.0, 0.0] |
| dedicated-tools | 1.000 | [1.0, 1.0, 1.0] |
| emoji | 1.000 | [1.0, 1.0, 1.0] |
| explore-agent | 0.950 | [0.95, 0.95, 0.95] |
| no-colon | 1.000 | [1.0, 1.0, 1.0] |
| no-compat-hacks | 0.667 | [0.5, 0.5, 1.0] |
| no-new-files | 1.000 | [1.0, 1.0, 1.0] |
| no-overengineering | 1.000 | [1.0, 1.0, 1.0] |
| no-time-estimates | 1.000 | [1.0, 1.0, 1.0] |
| objectivity | 0.950 | [0.95, 0.95, 0.95] |
| parallel-calls | 1.000 | [1.0, 1.0, 1.0] |
| plan-with-todo | 0.850 | [0.85, 0.85, 0.85] |
| pr-workflow | 0.950 | [0.95, 0.95, 0.95] |
| proactive-agents | 0.850 | [0.85, 0.85, 0.85] |
| read-first | 0.950 | [0.95, 0.95, 0.95] |
| text-only-comms | 0.950 | [0.95, 0.95, 0.95] |
| todowrite | 0.850 | [0.85, 0.85, 0.85] |
| todowrite-repeated | 0.817 | [0.75, 0.85, 0.85] |
| use-task-for-search | 0.233 | [0.2, 0.3, 0.2] |

## Next Steps

1. **Phase 1 (pairwise)**: The concise × use-task-for-search interaction
   needs pairwise confirmation. Is it truly pairwise or mediated?
2. **Multi-model replication**: Run Phase 0 on Gemini Flash and Qwen
   to test whether suppression patterns are model-specific or universal.
3. **Probe calibration**: Fix concise probe (baseline_length too
   aggressive) and code-references probe (may need file:line format
   examples in the prompt).
4. **Fix the tensor assembly bug**: AblationTensor.from_run() has an
   API mismatch with AblationRun that prevented automated analysis.
