# E-XMODEL Analysis: Cross-Model Register Bomb Replication

**Date:** 2026-03-29
**Parent:** E-PHASE-CONFIRM + E-SCOPE
**Cost:** ~$1.08 (1080 API calls across 3 models)

## Question

Is the commit-restrictions register bomb (explore-agent: 1.000 → 0.200 on
Haiku when CR is the lone imperative) model-general or Haiku-specific?

## Design

3 conditions × 4 models:
- **all-decl**: all blocks declarative (baseline)
- **only-cr-imp**: lone imperative commit-restrictions (the bomb trigger)
- **scoped-inline**: inline-scoped imperative CR (the E-SCOPE fix)

Models: Haiku (baseline from prior experiments), Gemini Flash 2.0, DeepSeek v3,
Mistral Medium 3.1.

## Results

### Bomb Detonation Matrix (explore-agent)

| Model | all-decl | only-cr-imp | scoped-inline | Bomb? | Fix? |
|-------|----------|-------------|---------------|-------|------|
| haiku | 1.000 | 0.200 | 1.000 | YES | YES |
| gemini | 1.000 | 1.000 | 1.000 | no | n/a |
| deepseek | 0.333 | 0.667 | 0.667 | no | no |
| mistral | 0.167 | 0.500 | 0.333 | no | no |

### Summary statistics say "HAIKU-SPECIFIC" but the truth is more nuanced

The naive reading: the bomb only detonates on 1/4 models. But this misses
the critical confound: **the probe battery doesn't transfer across models.**

## The Probe Transfer Problem

The probe battery was designed for Claude Code's system prompt, testing whether
models correctly adhere to instructions written in Claude Code's format. The
baselines reveal the problem:

- **Haiku all-decl explore-agent = 1.000**: Good baseline. The probes are valid.
- **Gemini all-decl explore-agent = 1.000**: Baseline looks good, but
  proactive-agents = 0.000 across ALL conditions. Gemini either doesn't
  understand this probe or processes it orthogonally to the manipulation.
- **DeepSeek all-decl explore-agent = 0.333**: Floor effect. Model can't even
  pass the probe with a clean prompt. Register manipulation is confounded
  by baseline model incompatibility.
- **Mistral all-decl explore-agent = 0.167**: Same floor effect, even worse.

### The Inverted Pattern

DeepSeek and Mistral show an inverted pattern: the bomb condition
*improves* explore-agent (DeepSeek: 0.333 → 0.667, Mistral: 0.167 → 0.500).
This is likely noise or an artifact: when the baseline is at floor, any
prompt perturbation can randomly help or hurt. The improvement is not
meaningful — it's the model reacting to prompt changes in unpredictable
ways because it wasn't trained on this format.

## What We Can Actually Conclude

### Confident Claims

1. **On Haiku, the register bomb reliably detonates** (1.000 → 0.200) and
   **the inline scoping fix reliably works** (back to 1.000). This is
   robust across E-PHASE, E-PHASE-CONFIRM, E-SCOPE, and now E-XMODEL.

2. **Gemini Flash is immune to this specific manipulation.** It scores 1.000
   across all conditions. Whether this is "no register sensitivity" or
   "robust instruction following regardless of register" is an open question.

3. **The probe battery does not transfer to DeepSeek or Mistral.** Their
   floor baselines mean we cannot measure register effects.

### What We Cannot Claim

- We cannot claim the bomb is "Haiku-specific" because we didn't validly
  test other models. Absence of evidence ≠ evidence of absence.
- We cannot claim Gemini "doesn't have register sensitivity" — it might
  have register effects that our battery doesn't capture.

## Implications

### For the paper
The cross-model story is: "We demonstrate the register bomb effect on Haiku
with high reliability. Cross-model replication is limited by probe battery
transfer — models trained on different instruction formats show floor effects
that confound the measurement. Gemini Flash shows immunity to this specific
manipulation, but the mechanism (training robustness? different register
processing? probe insensitivity?) remains unknown."

### For future work
To truly test cross-model generality, we need **model-specific probe batteries**
— probes designed for each model's native instruction format. This is a
significant investment but would allow genuine cross-model comparison. The
alternative is to use a model-agnostic task (like a standardized benchmark)
rather than model-specific system prompts.

### The interesting question this raises
Why is Haiku sensitive to register in a way that Gemini isn't? Possibilities:
1. **Training data composition**: Claude models may have more imperative-heavy
   training data, making them more responsive to imperative register.
2. **RLHF/Constitutional AI differences**: Different alignment training may
   produce different sensitivity to obligatory force.
3. **Architecture differences**: Attention mechanisms may process register
   signals differently across architectures.
4. **Artifact of the test**: The battery was written for Claude, so we're
   measuring "Claude's register sensitivity" not "register sensitivity."

## Data

- Gemini: `data/ablation/e_xmodel/run_e-xmodel-gemini-4df19f4d.json`
- DeepSeek: `data/ablation/e_xmodel/run_e-xmodel-deepseek-9bf624fd.json`
- Mistral: `data/ablation/e_xmodel/run_e-xmodel-mistral-286d9677.json`
- Haiku baselines: `data/ablation/e_phase/` + `data/ablation/e_scope/`
- Script: `scripts/run_e_xmodel.py`
