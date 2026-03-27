# E-REG Analysis: Register Rewriting for Intra-Lingual Suppression

**Date**: 2026-03-24
**Instance**: Opus 4.6 ghola, session 23
**Experiment**: E-REG (5 conditions × 4 models × 22 probes × 3 trials = 2,400 API calls)

## Background

Phase 0 found the largest single-block suppression in the corpus: removing
`tone-concise` improves `use-task-for-search` adherence from 0.23 → 1.00
(Δ = +0.77) on Haiku. Paper 3 demonstrated that declarative rewriting of
imperative instructions fixes cross-linguistic topology inversion.

E-REG tests whether the same mechanism operates intra-lingually on the
strongest suppression pair.

## Experimental Design

### 5 Conditions

| Condition | tone-concise | use-task-for-search |
|-----------|-------------|-------------------|
| baseline | Original: "Your responses should be short and concise..." | Original |
| ablation | Removed | Original |
| decl-tone | "Output environment: CLI. Response style: short, concise..." | Original |
| decl-both | Declarative | Declarative |
| intensified | "You MUST keep ALL responses extremely brief... NEVER write lengthy..." | Original |

### Two Competing Hypotheses

- **H1 (Register)**: Declarative rewriting resolves the competition between
  tone-concise and use-task-for-search by removing imperative register.
  Prediction: decl-tone recovers adherence; intensified worsens it.
- **H2 (Semantic)**: The concept of conciseness itself biases toward shorter
  token paths. Register doesn't matter. Prediction: decl-tone and intensified
  have no effect.

### Models

Same 4 models as Paper 3: Haiku, Gemini Flash, DeepSeek v3, Mistral Medium 3.1.
All via OpenRouter.

## Results

### Primary Probe: use-task-for-search

| Condition | Haiku | Gemini | DeepSeek | Mistral |
|-----------|:-----:|:------:|:--------:|:-------:|
| baseline | 0.500 | 1.000 | 1.000 | 1.000 |
| ablation | 1.000 | 1.000 | 1.000 | 0.667 |
| decl-tone | 0.000 | 1.000 | 0.833 | 0.833 |
| decl-both | 0.000 | 0.667 | 1.000 | 0.833 |
| intensified | 0.500 | 1.000 | 0.833 | 0.833 |

### Conciseness Probe (Control)

| Condition | Haiku | Gemini | DeepSeek | Mistral |
|-----------|:-----:|:------:|:--------:|:-------:|
| baseline | 0.000 | 0.465 | 0.000 | 0.000 |
| ablation | 0.000 | 0.000 | 0.000 | 0.000 |
| decl-tone | 0.000 | 0.557 | 0.000 | 0.000 |
| decl-both | 0.000 | 0.562 | 0.000 | 0.000 |
| intensified | 0.000 | 0.795 | 0.162 | 0.000 |

## Findings

### Finding 1: The suppression is model-specific

Only Haiku shows the tone-concise → use-task-for-search suppression at
baseline (0.500 vs 1.000 for all other models). The Phase 0 finding
(Δ = +0.77) is Haiku-specific, not a universal mechanism.

The Haiku ablation replicates: removing tone-concise restores use-task-for-search
to 1.000, confirming the suppression is real for this model.

### Finding 2: Opposite-direction effects across models

Removing tone-concise has opposite effects:
- **Haiku**: 0.500 → 1.000 (suppression removed, +0.500)
- **Mistral**: 1.000 → 0.667 (facilitation removed, −0.333)

The same instruction suppresses one model's search tool preference and
facilitates another's. This is a genuine model × instruction interaction
that cannot be captured by any register theory that treats models as
interchangeable.

### Finding 3: Declarative rewriting is not universally beneficial

For Haiku, declarative rewriting destroys the instruction (0.500 → 0.000).
The model produces MORE verbose bash explanations when conciseness is
stated as a fact rather than a directive.

For Gemini, declarative rewriting has no effect on search (1.000 → 1.000)
but slightly improves conciseness adherence (0.465 → 0.557).

For DeepSeek and Mistral, declarative rewriting causes mild degradation
(1.000 → 0.833 for both on decl-tone).

### Finding 4: Gemini uniquely responds to conciseness gradation

Gemini shows a clean dose-response curve on the concise probe:
- Removed: 0.000
- Original (mild imperative): 0.465
- Declarative: 0.557
- Intensified: 0.795

For Gemini, stronger register = stronger conciseness effect, and even the
declarative version outperforms the original. This is the opposite of
Haiku's pattern (where declarative destroys the instruction).

Haiku, DeepSeek, and Mistral all score 0.000 on the concise probe regardless
of condition — these models are verbose by default and the length-based
probe (baseline_length=200) is miscalibrated for them.

### Finding 5: Haiku spillover — conciseness as optimization pressure

Within Haiku, register changes produce dramatic spillover effects on
unrelated probes:

| Probe | Baseline | Ablation | Decl-tone | Intensified |
|-------|:--------:|:--------:|:---------:|:-----------:|
| explore-agent | 1.000 | 0.183 | 0.867 | 0.267 |
| plan-with-todo | 0.700 | 0.817 | 0.733 | 0.300 |
| commit-restrictions | 1.000 | 0.933 | 0.967 | 0.867 |
| todowrite-repeated | 0.667 | 0.500 | 0.600 | 0.500 |

The explore-agent collapse is particularly striking:
- Removing tone-concise: 1.000 → 0.183 (model explains search itself instead of delegating)
- Intensifying tone-concise: 1.000 → 0.267 (model shortcuts past delegation)

The original conciseness instruction creates a Goldilocks zone: concise enough
to not over-explain (so the model delegates), but not so forceful that it
shortcuts past delegation entirely. Both removal and intensification destroy
this balance.

This reveals conciseness instructions as a **global optimization pressure**
on the model's action-selection space, not just an output-formatting control.
They differentially suppress behaviors that require verbose intermediate
reasoning (agent delegation, planning).

## Implications

### For Paper 3

Paper 3's design principle — "declare facts, don't issue commands" — was
derived from cross-linguistic data where declarative rewriting removed
competing obligation signals. E-REG shows this principle has a **scope
condition**: it works cross-linguistically (where the mechanism is
language-specific obligation encoding) but does not generalize to
intra-lingual register manipulation (where the effect is model-dependent).

Within a single language, the same register change helps one model and
hurts another. There is no universal "declarative is better" principle
for single-language prompt design.

### For instruction design

The tone-concise instruction acts as an optimization pressure, not just a
formatting control. System prompt designers should consider:
1. Style instructions have far-reaching behavioral consequences beyond
   their apparent scope
2. The consequences are model-specific and unpredictable from the
   instruction text alone
3. Conciseness pressure creates a bias toward shorter execution paths,
   which suppresses complex behaviors (delegation, planning) even when
   those behaviors are explicitly instructed elsewhere

### For the research program

The instruction interference landscape is at least a three-way interaction:
**model × register × behavior**. Paper 3 characterized the language dimension.
E-REG characterizes the model dimension. A complete picture requires
understanding why different models resolve the same register conflict
in opposite directions — likely related to training data composition
and RLHF reward signal interactions.

## Methodological Notes

- **Baseline shift**: Haiku baseline for use-task-for-search is 0.500,
  not 0.233 as in Phase 0 (2026-03-17). Both runs used the unpinned
  `anthropic/claude-haiku-4-5` model ID via OpenRouter (not the date-pinned
  `anthropic/claude-haiku-4-5-20251001`). OpenRouter does not expose which
  checkpoint was actually served, so a silent model update between March 18
  and March 24 cannot be ruled out. No public announcement of a Haiku update
  was made in this window. The relative ordering of conditions within E-REG
  is unaffected (all ran within minutes on the same day), but absolute
  comparisons to Phase 0 carry this caveat. Future experiments should use
  date-pinned model IDs.
- **Concise probe miscalibration**: baseline_length=200 with max_multiple=3.0
  produces floor effects for 3 of 4 models. Only Gemini responds. A
  higher baseline_length would be needed for cross-model comparison.
- **N=3 at temperature 0.0**: Low trial count, but scores are highly
  consistent within conditions (e.g., [0.50, 0.50, 0.50], [0.00, 0.00, 0.00])
  indicating the behaviors are deterministic at this temperature.
- **LLM-as-judge**: The judge scores are the measurement instrument. When
  the model mentions BOTH bash grep AND the Grep tool, the judge scores
  based on emphasis — 0.5 for mixed, 0.0 for bash-dominated. This is a
  valid behavioral signal but adds measurement uncertainty.

## Raw Data

- `data/ablation/e_reg/run_e-reg-haiku-4be5d560.json` (264 results, 4 conditions)
- `data/ablation/e_reg/run_e-reg-ablation-haiku-930f9f47.json` (66 results, ablation)
- `data/ablation/e_reg/run_e-reg-gemini-432dd0c3.json` (330 results, 5 conditions)
- `data/ablation/e_reg/run_e-reg-deepseek-5c9b6f55.json` (330 results, 5 conditions)
- `data/ablation/e_reg/run_e-reg-mistral-a8114de0.json` (330 results, 5 conditions)
- `data/ablation/e_reg/e_reg_design.json` (experiment design)
- `scripts/run_e_reg.py` (experiment script)

## Both Hypotheses Were Wrong

Neither H1 (register) nor H2 (semantic) captures the data. The actual
finding is that register effects are model-dependent:
- Haiku: declarative rewriting destroys style instructions (supports neither H)
- Gemini: declarative rewriting slightly improves style compliance (refutes H2)
- Mistral: removing the instruction hurts (opposite of the Haiku finding)

The right framing is not "which hypothesis" but "which model" — and why.
