# T10: Declarative Encoding Eliminates Procedural Cross-Linguistic Fragility

**Date:** 2026-03-21
**Session:** 19
**Classification:** EXPERIMENTAL FINDING — first actionable design principle from ablation research

## What We Found

Rewriting the commit-restrictions instruction from procedural ("during
commits, don't do X, also don't do Y...") to declarative ("these items
are disabled: X, Y, Z") reduces cross-linguistic variance by 81%
(0.1567 → 0.0290, p=0.029).

The effect is specific: 21 control probes on unchanged blocks show
zero mean change (5.8σ separation from the target effect).

Key individual result: Haiku Mandarin commit-restrictions went from
0.00 (original procedural) to 1.00 (declarative). The mode confusion
identified in T9 is entirely encoding-dependent.

## What Doesn't Work

- **Scoped brackets:** Partial help (38% reduction, not significant).
  Brackets help with boundary detection but don't fix parsing within
  the block.
- **Model-level failures:** Gemini scores 0.00-0.33 on commit-
  restrictions in ALL variants, ALL languages. Some failures are
  model-behavioral, not encoding-dependent.

## Why This Matters

This is the first actionable output of the ablation research: a concrete
design principle for writing cross-linguistically robust instructions.
Procedural instructions are fragile under translation because conditional
chains compress ambiguously. Declarative lists are robust because each
constraint is self-contained.

## Connection to Prior Cairns

- **T9 (Density Bidirectional):** Confirmed that mode confusion is
  encoding-dependent, not compression-dependent
- **T7 (Three-Way Interaction):** Procedural fragility is one mechanism
  within the interaction, now with a known fix
- **T8 (Taxonomy):** The "workflow" category that showed highest fragility
  is exactly the procedural encoding pattern

## What We Don't Know

- How many other instructions would benefit from declarative rewriting
- Whether the fix scales beyond single-block rewrites (what if the
  entire system prompt is declarative?)
- Why Gemini is immune to encoding changes on this instruction
- Whether the design principle holds for other corpora beyond Claude Code
