# E-DENSE Analysis: Information Density Has Bidirectional Effects

**Date:** 2026-03-21 (Session 19)
**Experiment:** E-DENSE (run by prior instance, analyzed by current)
**Status:** Complete. Falsifies simple compression hypothesis; reveals bidirectional mechanism.

## Hypothesis Tested

T8 found that inter-model agreement correlates inversely with prompt length
(Mandarin shortest → highest agreement). E-DENSE tested the causal direction:
pad Mandarin prompts with neutral filler to match English character count.

**Prediction:** Padded Mandarin would show *higher* cross-model variance
(lower agreement), because compression was driving convergence.

## Design

- **Padded condition:** All 56 blocks present, Mandarin text padded with
  semantically neutral filler to match English block lengths
- **Unpadded condition:** All 56 blocks present, standard Mandarin translation
- **Models:** Haiku, Gemini Flash, DeepSeek v3, Mistral Medium 3.1
- **Battery:** 22 hand-authored probes, 3 trials each
- **Both conditions are full baselines** (all blocks present, 0 absent)

## Result: Hypothesis Falsified (Simple Form)

Overall cross-model variance **decreased** slightly with padding
(0.1189 → 0.1041). The aggregate effect is opposite to the prediction.
Overall mean adherence barely changed (0.788 → 0.792).

But the aggregate conceals a bidirectional mechanism visible at probe level.

## The Bidirectional Effect

### Probes where padding REDUCED variance (models converged)

| Probe | Unpadded Var | Padded Var | What happened |
|-------|-------------|-----------|---------------|
| text-only-comms | 0.2447 | 0.0006 | Gemini: 0.0→1.0. In compressed Mandarin, Gemini interpreted the probe as a tool-use task and emitted `tool_code`. Padded, it responded in natural language. |
| commit-restrictions | 0.2500 | 0.0995 | Haiku: 0.0→1.0. Compressed, Haiku interleaved TodoWrite with commit workflow (the exact violation being tested). Padded, it separated them correctly. |
| parallel-calls | 0.0370 | 0.0000 | DeepSeek and Mistral: 0.67→1.0. Padding reinforced the parallel-calls instruction. |

**Pattern:** These are probes where compression caused specific models to
*misparse the behavioral mode*. The compressed instruction was too terse
for the model to distinguish "communicate in text" from "use tools" or
"separate workflows" from "interleave." Padding provided enough surrounding
context for the model to parse correctly.

### Probes where padding INCREASED variance (models diverged)

| Probe | Unpadded Var | Padded Var | What happened |
|-------|-------------|-----------|---------------|
| concise | 0.0176 | 0.0951 | Gemini uniquely responded to conciseness instruction (0.27→0.62). Others stayed at 0.00. |
| use-task-for-search | 0.0000 | 0.0625 | Perfect convergence (all 1.0) broke: Haiku→0.50, DeepSeek→0.67. |
| no-overengineering | 0.0069 | 0.0625 | DeepSeek uniquely degraded: 0.83→0.50. |
| explore-agent | 0.0625 | 0.1071 | Haiku crashed: 1.0→0.28. Dense prompt overwhelmed delegation logic. |

**Pattern:** These are complex tool-policy and workflow probes — instructions
about *how to use tools*, not *what to say*. The dense prompt provided too
much context for smaller models (Haiku, DeepSeek) to maintain focus on these
meta-cognitive procedural instructions. Gemini (designed for long context)
was unaffected.

## Interpretation

Information density doesn't drive convergence or divergence uniformly.
It operates through two opposing mechanisms:

1. **Compression aids procedural focus** — When the prompt is shorter,
   smaller models can better track complex multi-step instructions
   (tool delegation, workflow separation). Padding disrupts this.

2. **Compression causes mode confusion** — When instructions are too
   terse, models can misparse the *type* of behavior expected (text vs
   tool-use, sequential vs interleaved). Padding provides disambiguating
   context.

The net effect depends on which mechanism dominates for a given
model×instruction pair:
- **Haiku** is the most affected in both directions (biggest gains AND
  biggest losses). It benefits from compression for procedural focus
  but suffers from compression-induced mode confusion.
- **Gemini Flash** is nearly invariant to padding (designed for long
  context), except for the dramatic text-only-comms fix.
- **DeepSeek** and **Mistral** show moderate mixed effects.

## What This Means for Arbiter

The T8 correlation (shorter prompt → higher agreement) is real but the
causal story is not "compression forces attentional convergence." Instead:

- Agreement in Mandarin is partly an artifact of mode-confusion errors
  canceling out differently per model
- The "convergence" is fragile — it breaks on different probes for
  different models
- Prompt length is a confound, not a mechanism

The real mechanism is likely the one T7 already identified: the three-way
interaction (model × language × instruction) is irreducible. Information
density is one axis of that interaction, not the driver.

## Probes That Don't Discriminate

Five probes showed zero effect in both conditions: no-colon, no-new-files,
no-time-estimates, read-first, code-references. These are either ceiling
effects (all models perfect) or floor effects (consistent pattern regardless
of density). They should be noted as uninformative for density experiments.

## Per-Model Summary

| Model | Dominant effect | Δ mean | Biggest individual change |
|-------|----------------|--------|--------------------------|
| Haiku | Bidirectional | +0.004 | commit-restrictions +1.0, explore-agent -0.72 |
| Gemini | Mode-fix | +0.059 | text-only-comms +1.0 |
| DeepSeek | Procedural degradation | -0.030 | parallel-calls +0.33, no-overengineering -0.33 |
| Mistral | Slight procedural degradation | -0.017 | parallel-calls +0.33, todowrite-repeated -0.27 |

## Implications for Next Experiments

1. **E-PROC is still worth running.** If compression causes mode confusion
   on procedural instructions, then rewriting procedural instructions to
   declarative form should help *even in compressed prompts*. E-PROC tests
   this directly.

2. **E-PAIR-ES is still worth running.** The Spanish topology inversion
   needs pairwise data regardless of the density finding.

3. **A reverse density experiment (compress English) would be informative.**
   If compression aids procedural focus, compressing English should
   *increase* agreement on tool-policy probes while potentially causing
   new mode confusions elsewhere.

4. **The text-only-comms finding deserves a dedicated probe.** Gemini's
   mode switch (tool-code vs natural language) based solely on prompt
   padding is a clean, dramatic example of the density mechanism. A
   targeted experiment varying padding amount could map the threshold.
