# Instruction Fragility Under Translation: Taxonomy, Ceiling Effects, and Inversions

**Date:** 2026-03-20
**Session:** 18
**Authors:** Tony Mason (PI), Claude Opus 4.6 (analysis and design)
**Depends on:** cross_linguistic_ablation.md (session 17)
**Status:** Analytical finding. No new experiments run. All results from existing data.

## Motivation

Session 17 established that instruction topology is a three-way interaction (model × language × instruction). This session asks: **can we predict which instructions are fragile under translation?**

If yes, this has practical implications — system prompt designers could identify fragile instructions before deployment and strengthen them. If no, the three-way interaction is irreducible and per-instruction prediction is impossible.

## Hypothesis 1: Semantic vs Referential (Binary)

**Claim:** Instructions that constrain behavioral posture ("be concise", "no emoji") are translation-robust. Instructions that bind to specific formal objects ("use the Explore agent") are translation-fragile.

**Classification:** 11 semantic, 11 referential.

**Result:**
| Category | Mean variance | Median variance | Mean range |
|----------|--------------|-----------------|------------|
| Semantic | 0.023 | 0.009 | 0.144 |
| Referential | 0.046 | 0.023 | 0.340 |
| **Ratio** | **1.95x** | **2.45x** | **2.37x** |

Permutation test: p = 0.117. Direction correct but not significant.

**Why it fails:** The classification puts the wrong things together. `tool-policy-dedicated-tools` (referential: "use Read instead of cat") has zero variance. `doing-tasks-no-compat-hacks` (semantic: "no backwards-compatibility shims") has variance 0.113. The binary cut is too coarse.

## Hypothesis 2: Six-Category Taxonomy

**Refined classification based on anomalies:**

| Category | n | Description | Mean variance |
|----------|---|-------------|--------------|
| Posture | 11 | Dispositional constraints | 0.023 |
| Mapping | 2 | Contrastive name bindings ("X instead of Y") | 0.030 |
| Tool-behavior | 3 | Named tool, behavioral instruction | 0.014 |
| Collision | 1 | Tool name = common word in target language | 0.050 |
| Delegation | 2 | Meta-capability reference | 0.075 |
| Workflow | 3 | Sequenced multi-step procedures | 0.067 |

Collapsed: fragile (workflow + collision + delegation) = 0.067 mean var, robust (posture + mapping) = 0.024. Ratio 2.73x, **p = 0.034**.

## The Ceiling Effect Problem

12 of 22 blocks score near ceiling (mean > 0.85) or floor (mean < 0.10). Blocks near ceiling can't show variance — they're already at 1.0 in every language. Many "posture" blocks are at ceiling.

**Normalized variance** (observed / maximum possible for that mean):

| Category | n (non-ceiling) | Mean normalized var |
|----------|----------------|-------------------|
| Delegation | 2 | 0.426 |
| Mapping | 1 | 0.363 |
| Workflow | 3 | 0.350 |
| Posture | 8 | 0.252 |
| Collision | 1 | 0.219 |
| Tool-behavior | 3 | 0.123 |

After ceiling correction: fragile 1.34x robust, **p = 0.227**. Not significant.

Mid-range blocks only (0.15 < mean < 0.85): fragile 1.79x robust, **p = 0.138**. Still not significant.

**Conclusion:** The taxonomy captures a real tendency but does not survive ceiling correction at n=22. The three-way interaction cannot be reduced to a property of the instruction alone.

## What the Ceiling Effect Tells Us

The ceiling result is not just a confound — it's data. The blocks that score 1.00 across all 16 model×language cells (`no-time-estimates`, `no-colon-before-tools`, `no-new-files`, `dedicated-tools`) have a specific character: they are either **very broad behavioral prohibitions** ("never give time estimates") or **contrastive mappings with redundant anchoring** ("Read instead of cat, Edit instead of sed").

The contrastive mapping case is theoretically interesting. `dedicated-tools` names six specific tools but maintains perfect cross-linguistic stability because each name is paired with the thing it replaces. The binding survives translation not because the name is preserved (it is), but because the *mapping structure* creates a translation-invariant scaffold. Even if a model doesn't attend to "Read" as a proper noun, it can reconstruct the intended behavior from the contrast with "cat."

## Inversions: The Irreducible Three-Way Interaction

6 inversion cases found (|Δ| ≥ 0.2 in both models, opposite sign):

**Distribution by language:** Spanish 4, Mandarin 2, French 0.
**Distribution by model pair:** Gemini involved in 4 of 6.

### Case Study: commit-restrictions in Mandarin

The strongest inversion. Haiku and Gemini process the same instruction in the same translation with opposite results:

**Haiku English (1.0):** "For the commit: [git workflow]. For the todo: [separate task]." Separates cleanly.

**Haiku Mandarin (0.0):** "Let me handle the commit and create a todo list." Creates a TodoWrite task *about* the commit. Interleaves the prohibited tool with the workflow.

**Gemini English (0.0):** Creates a TodoWrite task for "Check git status and create commit." Same interleaving as Haiku-zh.

**Gemini Mandarin (1.0):** "First, I'll commit the current changes, and then I'll create a todo list." Separates cleanly.

Both models can follow the instruction. Both models can violate it. They do so in complementary languages. The instruction text is preserved identically (including "TodoWrite" as ASCII). The prohibition words are translated ("NEVER" → "绝对不要"). The behavioral outcome inverts.

### Why Spanish Produces More Inversions

4 of 6 inversions involve Spanish. This is consistent with session 17's finding that Spanish Haiku shows a topology inversion (cooperative → competitive). If the instruction interaction structure differs in Spanish, individual instructions will show different relative strengths, creating more opportunities for model-pair inversions.

French produces zero inversions. Session 17 found that French topology is "flat" — no strong hub structure, weak effects. Flat topology means smaller deltas, which means fewer inversions above threshold.

### Why Gemini Is Most Inversion-Prone

Gemini appears in 4 of 6 inversions. Session 17 found Gemini has the lowest inter-model agreement with Haiku (r = 0.156 in French, 0.251 in Spanish). Models that agree least on instruction importance in English will show the most divergent responses to the same translation, producing more inversions.

## Three Mechanisms (Descriptive, Not Predictive)

The data suggests three qualitatively different ways instructions break under translation. These are descriptive categories for the 22 blocks studied — they do not predict behavior for new instructions:

### 1. Procedural Fragility

Multi-step workflows with conditional logic ("when committing: first X, then Y, and NEVER Z during this process") show the highest variance. The sequential/conditional structure embedded in natural language is harder to preserve than declarative constraints.

- Strongest case: `commit-restrictions` (var = 0.157, range = 0.750)
- The prohibition is correctly translated in all languages
- But the *procedural scope* ("during commits" as a bounded context) doesn't transfer

### 2. Name-Concept Collision

Tool names that are common words in target languages lose their proper-noun reference. "Explore" competes with "explorar" (Spanish verb). The model attends to the semantic meaning rather than the tool-name binding.

- Case: `explore-agent` — Haiku drops from 1.00 to 0.22 in Spanish
- Counter-case: `dedicated-tools` (var = 0.000) — contrastive mappings survive because the paired structure provides redundant information

### 3. Training-Language Behavioral Bias

Some blocks show variance patterns that track the model's training language, not translation quality:

- Mistral on `no-compat-hacks`: en=0.00, fr=0.00, es=1.00, zh=1.00. The French-trained model fails the instruction in both English and French but follows it in Spanish and Mandarin. This suggests a trained disposition (code-preservation caution) that operates in the model's "home" languages.
- Gemini on `text-only-comms`: en=1.00, es=1.00, fr=0.00, zh=0.00. Collapses in exactly two languages. Not a translation artifact — the instruction is correctly translated — but a model-specific processing difference.

## Finding: Instruction Competition Drives the Largest Inversion

The highest-variance block (`commit-restrictions`, variance 0.157) is in genuine conflict with another block in the same system prompt. The system prompt simultaneously says:

- **todowrite-importance**: "TodoWrite is important. Use it for task management." (mean score: 0.90)
- **commit-restrictions**: "NEVER use TodoWrite during commits." (mean score: 0.54)

Across all 16 model×language cells, these two instructions show **r = -0.573**: when one succeeds, the other fails. The 6 cells where commit-restrictions scores below 0.3 while todowrite scores above 0.7:

| Cell | commit-restrictions | todowrite |
|------|-------------------|-----------|
| gemini/en | 0.00 | 1.00 |
| gemini/es | 0.00 | 1.00 |
| gemini/fr | 0.00 | 1.00 |
| deepseek/en | 0.17 | 1.00 |
| deepseek/zh | 0.00 | 1.00 |
| haiku/zh | 0.00 | 0.85 |

In English, Haiku maintains a context boundary: commits are a special scope where the TodoWrite prohibition applies. In Mandarin, the boundary breaks and the TodoWrite emphasis wins. Gemini fails in English, French, and Spanish, but succeeds in Mandarin — the only language where it can maintain the context boundary.

**This is the core phenomenon.** Two instructions that are individually clear and well-translated create a conflict that models resolve differently depending on language. The resolution is not about translation quality — both instructions are correctly translated. It's about which instruction's behavioral pull is stronger in a given model×language context.

A second competition was found: `code-references` (use file:line format) vs `tone-concise` (keep responses short) shows r=-0.584. When conciseness wins, file-line references get dropped.

### Implication for Arbiter

These competitions are detectable by static analysis of the instruction graph. `commit-restrictions` contains "NEVER use TodoWrite" while `todowrite-importance` says "use TodoWrite." An arbiter system that checks for cross-reference contradictions would flag this pair. The language-dependent resolution is the dynamic component that ablation measures, but the conflict itself is structural and discoverable without running any model.

## What This Does Not Establish

1. **Predictive power.** The taxonomy describes patterns in 22 blocks from one system prompt. It does not predict which new instructions will be fragile.

2. **Causal mechanism.** We observe that procedural instructions are fragile but cannot say *why* at the transformer level. Possibilities include attention-weight distribution, positional encoding effects, and token-frequency effects.

3. **Generality.** All data is from one system prompt (Claude Code v2.1.50). The taxonomy might not transfer to other prompts.

4. **Statistical significance after ceiling correction.** The raw taxonomy test is significant (p = 0.034) but the ceiling-corrected test is not (p = 0.227). With 22 blocks, power is limited.

## What Would Strengthen These Claims

1. **More blocks.** A system prompt with 50+ ablatable blocks would provide more power. Alternatively, testing multiple different system prompts.

2. **Phase 1 (pairwise) on Spanish.** Session 17 showed Spanish topology inverts from cooperative to competitive in Phase 0. Phase 1 pairwise data on Spanish would confirm whether the interaction structure (not just main effects) inverts.

3. **Controlled name-collision experiment.** Take a block with a non-colliding tool name (e.g., "TodoWrite") and replace it with a colliding name (e.g., "Write" → "Escribir" in Spanish). If variance increases, name-collision is causal.

4. **Cross-model judging.** The 7 LLM-judged probes use same-model judging. Cross-model judging would eliminate judge-language bias as a confound.

5. **Procedural simplification test.** Rewrite `commit-restrictions` as a simple declarative rule ("TodoWrite and Task tools are disabled during commit operations") and compare cross-linguistic variance with the procedural version.

## Finding: Information Density Predicts Inter-Model Agreement

The correlation structure between models changes across languages:

| Language | Mean inter-model r | Character count | % of English |
|----------|-------------------|----------------|-------------|
| Mandarin | **0.558** | 6,910 | 43.3% |
| English | 0.502 | 15,970 | 100% |
| French | 0.461 | 20,744 | 129.9% |
| Spanish | 0.432 | 19,178 | 120.1% |

The ordering is **exactly inverse to prompt length**. Shortest prompt → highest agreement. Longest prompt → lowest agreement.

The strongest individual correlation: DeepSeek × Mistral in Mandarin (r = 0.893). The weakest: Gemini × Haiku in French (r = 0.156). The models with the most different training backgrounds agree most in the most compressed language.

**Hypothesis:** Information density forces attentional convergence. When the system prompt is short (Mandarin), models must attend to the same high-salience tokens, producing agreement. When the prompt is long (French/Spanish), models have room to develop divergent attention strategies, producing disagreement and inversions.

This is consistent with Spanish producing 4 of 6 inversions and French producing 0: French has the longest prompt but produces flat topology (weak effects, low variance), while Spanish is long but maintains enough instruction salience to create strong effects with model-specific directionality.

**Testable prediction:** If we pad the Mandarin prompt with semantic filler to match English length, inter-model agreement should decrease toward English levels. If we compress the English prompt (summarizing rather than translating), agreement should increase toward Mandarin levels.

## Model Complementarity

For blocks with meaningful language sensitivity (best-vs-worst gap > 0.1), models choose different best languages 63-86% of the time:

| Model | Best-language counts (en/zh/fr/es) | Pattern |
|-------|-----------------------------------|---------|
| DeepSeek | 8/9/8/7 | **Uniform** — most language-agnostic |
| Gemini | 12/11/5/10 | English/Mandarin preference, weak in French |
| Haiku | 9/5/3/6 | **English-dominant**, weakest in French |
| Mistral | 7/9/6/9 | Mandarin/Spanish preference, weakest in English |

Practical implication: a routing system that selects the best model×language pair per instruction would outperform any fixed-language deployment. This connects to E5's open question about model-conditioned vs cross-family deployment — language should be a conditioning variable too.

## The Conciseness Competition

`tone-concise` scores near floor (mean 0.09) across all model×language cells except Gemini/Spanish (0.60). Inspecting the responses:

- **Gemini English (score ≈ 0):** Gives a 597-char response that includes a multi-step plan. The `doing-tasks-plan-with-todo` instruction outcompetes `tone-concise`.
- **Gemini Spanish (score ≈ 0.60):** Gives a 238-char two-sentence response. The conciseness instruction wins.

Same model, same two instructions, different language → **different instruction wins the competition.** This is the topology interaction observed at the individual-probe level. The Spanish translation shifts the relative strength of competing instructions, changing which behavior the model expresses.

## Data Artifacts

| File | Contents |
|------|----------|
| `scripts/analyze_semantic_vs_referential.py` | Binary taxonomy analysis |
| `scripts/analyze_instruction_taxonomy.py` | Six-category taxonomy analysis |
| `scripts/analyze_ceiling_controlled.py` | Ceiling-corrected analysis |

All analyses use existing data from `data/ablation/cross_linguistic/`.

## Connection to Prior Work

- **T5 (Generator as Specimen):** The probe generator exhibited procedural fragility — the "adversarial temptation" instruction interfered with the "test accuracy" instruction. Same mechanism as procedural fragility under translation: multi-part instructions with internal tension.
- **T6 (Three Reviewers):** Different system prompts produce non-overlapping blind spots. The inversions show that the same system prompt in a different language creates a different "reviewer" — with different blind spots. Language variation is a dimension of evaluation diversity.
- **T7 (Three-Way Interaction):** This analysis confirms T7's classification as foundational. The taxonomy captures a trend but the interaction terms dominate the main effects. You cannot predict an instruction's cross-linguistic behavior from its category alone.
