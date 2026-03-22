# T9: Information Density Has Bidirectional Effects on Model Agreement

**Date:** 2026-03-21
**Session:** 19
**Classification:** EXPERIMENTAL FINDING — falsifies simple compression hypothesis from T8, reveals two opposing mechanisms

## What We Found

Padding Mandarin prompts to English length does NOT uniformly increase
cross-model variance. Instead, density operates through two mechanisms:

1. **Compression aids procedural focus.** Shorter prompts help smaller
   models track complex tool-policy instructions. Padding Mandarin
   caused Haiku to lose explore-agent behavior (1.0→0.28) and
   use-task-for-search (1.0→0.50).

2. **Compression causes mode confusion.** Overly terse instructions
   can cause models to misparse the expected behavioral mode. Padding
   fixed Gemini's text-only-comms (0.0→1.0, switched from tool_code
   to natural language) and Haiku's commit-restrictions (0.0→1.0,
   stopped interleaving TodoWrite with commits).

The net effect is near-zero in aggregate (variance 0.1189→0.1041) because
the two mechanisms cancel. The T8 correlation (shorter prompt → higher
agreement) is real but the causal mechanism is not simple convergence.

## Why This Matters

- The three-way interaction (T7) remains irreducible — information density
  is one axis, not the driver
- Prompt engineering for instruction adherence faces a fundamental tradeoff:
  compress for focus OR expand for disambiguation
- This tradeoff is model-dependent (Gemini invariant, Haiku highly sensitive)

## Connection to Prior Cairns

- **T8 (Information Density):** Correlation confirmed, causal mechanism revised
- **T7 (Three-Way Interaction):** Still irreducible. Density is a contributing
  factor, not the explanation.

## What We Don't Know

- Where the threshold lies (how much padding before mode confusion resolves?)
- Whether compressing English has the symmetric effect
- Whether declarative rewrites (E-PROC) can get both benefits simultaneously
