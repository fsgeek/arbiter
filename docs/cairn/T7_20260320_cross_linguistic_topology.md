# T7: Cross-Linguistic Instruction Topology Is a Three-Way Interaction

**Date:** 2026-03-20
**Session:** 17
**Classification:** FOUNDATIONAL FINDING — instruction topology is not a property of instructions or models, but of model×language×instruction interaction

## What We Found

Translating Claude's system prompt into Mandarin, French, and Spanish and testing against 4 models (Haiku, Gemini Flash, DeepSeek V3, Mistral Medium 3.1) revealed:

1. **Mistral performs worst in English and best in Mandarin.** The French-dominant model follows Claude's instructions better when they're in Mandarin (+12.8%) than in English. No model does best in its "home" language.

2. **The same instruction has opposite effects in different models.** `commit-restrictions` scores 1.00 for Haiku in English but 0.00 in Mandarin. For Gemini, it's 0.00 in English and 1.00 in Mandarin. Same instruction, same translation, opposite results.

3. **Hub topology inverts across languages.** In English (Haiku), all main effects are negative (cooperative — every block is load-bearing). In Spanish, most effects flip positive (competitive — blocks interfere with each other). Hub significance confirmed by permutation test (p < 0.00001) but the hub structure is language-specific.

4. **Mandarin resolves ambiguities that English creates.** The `use-task-for-search` probe improves from 0.50 to 1.00 in Mandarin (Haiku) because the English version's ambiguity between bash grep and the dedicated Grep tool is resolved by translation.

5. **"Explore" as verb eats "Explore" as tool name.** Spanish Haiku drops from 1.00 to 0.22 on the explore-agent probe because the Spanish translation preserves "explorar" as meaning but loses the proper-noun reference to a specific tool.

## Why This Matters

The phenomenon is not "translation degrades performance." It's that different languages produce qualitatively different functional mappings. The interaction terms (model×language, language×instruction, model×instruction) are larger than the main effects.

This means:
- The cross-lingual prompting literature that tests one model and reports language effects is measuring a shadow of a shadow
- English system prompts are not universally optimal — they're worst for at least one production model (Mistral)
- Instruction interaction topology is emergent from encoding-processing interaction, not from semantic content alone

## Connection to Prior Cairns

- **T5 (Generator as Specimen):** The probe generator showed instruction interference within English. T7 shows that translation can both create and resolve interference.
- **T6 (Three Reviewers):** Different system prompts find different problems. T7 extends this: the same system prompt in different languages creates different behavioral profiles.

## What We Don't Know

See the robustness section in `docs/research/cross_linguistic_ablation.md`. Key gaps: translation quality unverified, same-model judging, single corpus, probes in English only.
