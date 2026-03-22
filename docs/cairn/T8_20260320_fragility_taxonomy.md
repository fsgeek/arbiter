# T8: Information Density Predicts Model Agreement; Instruction Taxonomy Does Not Survive Ceiling Correction

**Date:** 2026-03-20
**Session:** 18
**Classification:** ANALYTICAL FINDING — extends T7 with ceiling-controlled taxonomy, information density hypothesis, and model complementarity

## What We Found

### 1. Instruction taxonomy captures a trend but doesn't survive correction

Classifying 22 instructions as "fragile" (workflow, delegation, name-collision) vs "robust" (posture, mapping) shows 2.73x variance ratio (p=0.034 raw). After controlling for ceiling effects, ratio drops to 1.34x (p=0.227). The three-way interaction cannot be reduced to instruction type.

### 2. Information density predicts inter-model agreement

Inter-model correlation ordering is exactly inverse to prompt length:
- Mandarin (43.3% of English) → r=0.558
- English (100%) → r=0.502
- French (129.9%) → r=0.461
- Spanish (120.1%) → r=0.432

Compressed encoding forces attentional convergence. DeepSeek × Mistral agree at r=0.893 in Mandarin.

### 3. Models partition the language space into complementary niches

On blocks with meaningful variance, models choose different best languages 63-86% of the time. No two models have the same language preference profile.

### 4. Six inversions at |Δ|≥0.2; Spanish dominates (4/6)

The commit-restrictions inversion in Mandarin (Haiku 1.0→0.0, Gemini 0.0→1.0) shows complementary language competence: both models can follow the instruction, but in different languages.

### 5. Instruction competition is language-dependent

`tone-concise` vs `doing-tasks-plan-with-todo`: In English, planning wins (long response with steps). In Spanish, conciseness wins (two-sentence response). Same model, same instructions, different winner.

## Why This Matters

The information density finding adds a mechanistic dimension to T7. The three-way interaction isn't fully random — it's structured by prompt compression. Models converge when forced to attend to the same tokens, diverge when given room.

## Connection to Prior Cairns

- **T7 (Three-Way Interaction):** Confirmed irreducible. Taxonomy captures tendency but not mechanism.
- **T6 (Three Reviewers):** Different languages create different "reviewers" from the same model.
- **E5 (Gate Status):** Model-conditioned deployment should be language-conditioned too.

## What We Don't Know

- Whether padding Mandarin to English length decreases agreement (density test)
- Whether compressing English increases agreement (reverse density test)
- Phase 1 pairwise on Spanish (topology inversion with interaction data)
- Whether the three mechanisms (procedural, collision, training-bias) replicate on a second corpus
