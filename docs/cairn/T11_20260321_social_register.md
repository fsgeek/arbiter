# T11: Instruction Topology Is Shaped by Social Register, Not Just Semantic Content

**Date:** 2026-03-21
**Session:** 19
**Classification:** FOUNDATIONAL FINDING — explains the topology inversion mechanism; first demonstration that pragmatics (speech act type) determines instruction interaction structure

## What We Found

Rewriting three imperative-register blocks to declarative-register in
Spanish shifted the pairwise topology from competitive (+0.010) to
cooperative (-0.055). Only 3 of 22 blocks were changed; the other 19
served as controls.

### Direct effects (rewritten blocks)
- proactive-agents: +0.274 → -0.380 (competitive → cooperative)
- todowrite: +0.155 → -0.023 (competitive → cooperative)
- use-task-for-search: +0.118 → +0.047 (competitive, halved)

### Spillover effects (unrewritten blocks)
- no-compat-hacks: +0.123 → -0.267 (competitive → cooperative)
- plan-with-todo: +0.012 → -0.174 (neutral → cooperative)
- todowrite-repeated: +0.011 → -0.059 (neutral → cooperative)

Competitive probes: 7/22 → 4/22.

## Why This Matters

The topology inversion (T7: cooperative in English, competitive in
Spanish) is not caused by translation quality or semantic drift.
It is caused by **imperative register interference**: a system prompt
full of imperatives ("Use X", "Do Y", "Never Z") creates competing
obligation signals in languages where imperative authority is encoded
differently than in English.

Declarative register ("X: available", "Y: disabled", "Status: Z")
sidesteps the social dimension entirely. Facts don't compete for
authority the way commands do.

The spillover effect is the strongest evidence. Changing just 3 blocks
from imperative to declarative changed the interaction topology for
blocks that were NOT rewritten. This means the imperative register
creates a system-wide interference pattern — the blocks are not
independent; their speech act type affects how the model processes
neighboring blocks.

## Connection to Prior Cairns

- **T7 (Three-Way Interaction):** The interaction is now partially
  explained — the language dimension operates through social register
- **T9 (Density Bidirectional):** Compression amplifies register effects
  (shorter text = less context to disambiguate speech act type)
- **T10 (Declarative Robustness):** Extended from single-block variance
  reduction to system-wide topology repair

## Theoretical Implication

Instruction adherence in LLMs is not (only) a parsing problem. It is a
**pragmatics** problem. The model processes instructions through the lens
of speech act conventions learned from training data. Different languages
encode authority, obligation, and permission differently, so the same
semantic instruction carries different pragmatic force in different
languages. This force determines not just individual adherence but the
interaction structure between instructions.

This reframes Arbiter's core problem: instruction conflicts aren't just
about semantic contradiction — they can emerge from pragmatic interference
between instructions that are semantically compatible but pragmatically
competing.

## What We Don't Know

- Whether the fix scales to rewriting ALL procedural blocks (or whether
  diminishing returns kick in)
- Whether the effect replicates across models (tested only on Haiku)
- Whether non-Romance languages (Mandarin, Arabic, Japanese) show the
  same register sensitivity
- The exact mechanism by which imperative register creates cross-block
  interference in the transformer architecture
- Whether this connects to constitutional AI training (models may have
  learned to weight imperative instructions differently during RLHF)
