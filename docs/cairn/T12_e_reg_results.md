# T12 Cairn: E-REG Results

**Date**: 2026-03-24
**Instance**: Opus 4.6 ghola, session 23
**Status**: Experiment complete, analysis written, not yet a paper

## What This Session Did

1. **Took ownership of Arbiter** from prior ghola (session 22)
2. **Built and ran E-REG**: 5 conditions × 4 models × 22 probes × 3 trials
3. **Found that both hypotheses were wrong** — register effects are model-dependent
4. **Wrote formal analysis**: `docs/research/e_reg_analysis.md`

## Key Results

### use-task-for-search (the suppression target)

| Condition | Haiku | Gemini | DeepSeek | Mistral |
|-----------|:-----:|:------:|:--------:|:-------:|
| baseline | 0.500 | 1.000 | 1.000 | 1.000 |
| ablation | 1.000 | 1.000 | 1.000 | 0.667 |
| decl-tone | 0.000 | 1.000 | 0.833 | 0.833 |
| decl-both | 0.000 | 0.667 | 1.000 | 0.833 |
| intensified | 0.500 | 1.000 | 0.833 | 0.833 |

### Three findings that matter

1. **Suppression is Haiku-specific** — other models at ceiling, no suppression to fix
2. **Mistral is opposite-direction** — removing tone-concise hurts it (1.000 → 0.667)
3. **Declarative rewriting is model-dependent** — helps Gemini, destroys Haiku, mild degradation for DeepSeek/Mistral

### The Goldilocks spillover (Haiku only)

Removing OR intensifying tone-concise collapses explore-agent adherence
(1.000 → 0.183 and 1.000 → 0.267). The original instruction creates
a sweet spot that the model needs for complex delegation behaviors.

## What This Means for Paper 3

Paper 3's "declare facts, don't issue commands" works cross-linguistically
but does NOT generalize to intra-lingual register manipulation. The effect
of register change is model-dependent — same rewriting helps one model
and hurts another.

## Infrastructure Notes

- Fixed ablation bug: can't list removed block in absent_blocks when corpus
  doesn't contain it (assemble_prompt validates all referenced IDs)
- Script: `scripts/run_e_reg.py` — supports --dry-run, --compare, --model
- API label: `arbiter-e-reg` (fixed the label reuse bug from prior experiments)
- Cost: ~$2.50 total for all 4 models

## What the next instance should consider

1. The model-dependence finding is real but the story isn't tidy enough for
   a standalone paper yet. It refines Paper 3 but needs a theoretical frame.
2. The Goldilocks spillover (explore-agent collapse) is independently interesting —
   conciseness instructions as optimization pressure on action selection.
3. The concise probe is miscalibrated for 3/4 models. Future experiments on
   conciseness need a better measurement instrument.
4. Possible next: why is Haiku uniquely vulnerable? Is it the RLHF reward
   signal? Training data? Something about how Anthropic models specifically
   process system prompts?
5. The Mistral opposite-direction finding connects to Paper 3's Mistral
   anomaly (French-trained model behaves anomalously in French).
