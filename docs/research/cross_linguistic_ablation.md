# Cross-Linguistic System Prompt Ablation: Do Instructions Mean the Same Thing in Every Language?

**Date:** 2026-03-20
**Session:** 17
**Authors:** Tony Mason (questions), Claude Opus 4.6 (experiment design and execution)
**Status:** Preliminary findings. Needs robustness checks before publication claims.

## The Questions

Three questions motivated this experiment, arising from prior work on instruction interaction topology (Phase 1 pairwise ablation, session 16):

1. **Does the cooperative topology survive translation?** Phase 1 found that Claude's system prompt instructions form a cooperative network with statistically significant hub nodes (p < 0.00001, permutation test). Is this topology a property of the *semantic content* of the instructions, or of their *English encoding*?

2. **Does the transformer build internal structure from unstructured instructions?** If the same semantic content produces different interaction topologies in different languages, the structure isn't in the meaning — it's in how the model's processing interacts with the token-level encoding.

3. **Is the effect universal across models?** If different models show different language sensitivity patterns, the phenomenon is a three-way interaction (model x language x instruction), not a language main effect.

## Experimental Design

### Translation

- **Source corpus:** Claude Code v2.1.50 system prompt, decomposed into 56 blocks (22 free/ablatable, 34 constrained)
- **Target languages:** Mandarin Chinese (zh), French (fr), Spanish (es)
- **Translator:** Gemini Flash 2.0 (`google/gemini-2.0-flash-001`) via OpenRouter
- **Rationale for Gemini:** Avoids circularity of translating Claude's instructions with Claude. Gemini is a non-Anthropic model with strong multilingual capability.
- **Translation rules:** Preserve markdown formatting, keep tool names/API names/code untranslated, maintain imperative tone, translate structural markers (e.g., "IMPORTANT:" -> "重要：")
- **Artifacts:** `data/prompts/claude-code/v2.1.50_blocks_{zh,fr,es}.json` — each block's `text` field translated, `original_text` preserved for comparison

### Size After Translation

| Language | Characters | % of English |
|----------|-----------|-------------|
| English  | 15,970    | 100%        |
| Mandarin | 6,910     | 43.3%       |
| Spanish  | 19,178    | 120.1%      |
| French   | 20,744    | 129.9%      |

Note: Character count is not token count. Mandarin uses fewer characters but each character may require multiple BPE tokens depending on the tokenizer. The actual token counts will vary per model's tokenizer.

### Probe Battery

- **22 hand-authored probes**, one per free block (from Phase 0 battery, session 14)
- **Probes remain in English** — the user speaks English, only the system prompt changes language
- **Scoring methods:** exact match, contains, not_contains, length, llm_judge
- **LLM judge:** Same model being tested (Haiku judges Haiku). This is a known limitation (see Robustness section).
- **3 trials per probe** at temperature 0.0

### Models Tested

| Model | OpenRouter ID | Training Bias | Cost/call |
|-------|--------------|---------------|-----------|
| Claude Haiku 4.5 | `anthropic/claude-haiku-4-5` | English-heavy | ~$0.001 |
| Gemini Flash 2.0 | `google/gemini-2.0-flash-001` | English-heavy | ~$0.0003 |
| DeepSeek V3 | `deepseek/deepseek-chat-v3-0324` | Chinese + diverse | ~$0.0005 |
| Mistral Medium 3.1 | `mistralai/mistral-medium-3.1` | French + diverse | ~$0.001 |

### Phases Run

1. **Cross-linguistic baseline** (all blocks present): 4 models x 4 languages x 22 probes x 3 trials = 1,056 calls
2. **Cross-linguistic Phase 0** (single-block removal, Haiku only): 3 languages x 23 configs x 22 probes x 3 trials = 4,554 calls
3. **Permutation test** (hub significance): 100,000 permutations on English Phase 1 data

**Total cost:** ~$10 across all experiments.

## Results

### Finding 1: Translation Does Not Uniformly Degrade Instruction Following

Mean adherence scores across all probes:

| Model | English | Mandarin | French | Spanish | Range |
|-------|---------|----------|--------|---------|-------|
| Haiku | **0.853** | 0.783 (-8.2%) | 0.774 (-9.2%) | 0.736 (-13.8%) | 0.117 |
| Gemini | **0.781** | 0.765 (-2.1%) | 0.693 (-11.3%) | 0.755 (-3.4%) | 0.088 |
| DeepSeek | **0.799** | 0.786 (-1.6%) | 0.771 (-3.5%) | 0.757 (-5.3%) | 0.042 |
| Mistral | 0.726 | **0.819** (+12.8%) | 0.753 (+3.7%) | 0.788 (+8.5%) | 0.093 |

**Key observations:**
- Three models (Haiku, Gemini, DeepSeek) perform best in English
- Mistral performs **worst** in English and **best** in Mandarin
- No model does best in its "home" language (Mistral is French-trained but peaks in Mandarin)
- DeepSeek is the most language-robust (range 0.042) — translation barely affects it
- Haiku is the most language-sensitive (range 0.117)

### Finding 2: Language Sensitivity Is Probe-Specific, Not Uniform

Individual probes show wildly different patterns across languages and models. Selected examples:

**commit-restrictions** (should separate commit workflow from TodoWrite):
| | Haiku | Gemini | DeepSeek | Mistral |
|---|-------|--------|----------|---------|
| en | 1.00 | 0.00 | 0.17 | 0.67 |
| zh | **0.00** | **1.00** | 0.00 | 0.67 |
| fr | 0.98 | 0.00 | 0.67 | 1.00 |
| es | 1.00 | 0.00 | 0.50 | 1.00 |

Haiku and Gemini show **opposite** language effects on the same probe. Haiku follows this instruction perfectly in English but completely fails in Mandarin. Gemini fails in English but succeeds in Mandarin. Same instruction, same translation, same probe — opposite results.

**use-task-for-search** (should use dedicated Grep tool, not bash grep):
| | Haiku | Gemini | DeepSeek | Mistral |
|---|-------|--------|----------|---------|
| en | 0.50 | 1.00 | 0.83 | 0.83 |
| zh | **1.00** | 1.00 | 1.00 | 1.00 |

Haiku *improves* from 0.50 to 1.00 when the system prompt is translated to Mandarin. The English version contains ambiguity (mentions both bash grep and the dedicated tool); the Mandarin translation apparently resolves this ambiguity.

**explore-agent** (should delegate to Explore agent for complex codebase analysis):
| | Haiku | Gemini | DeepSeek | Mistral |
|---|-------|--------|----------|---------|
| en | 1.00 | 1.00 | 0.50 | 0.33 |
| es | **0.22** | 1.00 | 0.33 | 0.50 |

Spanish Haiku collapses from 1.00 to 0.22. The word "Explore" functions as both a tool name and a common verb. Spanish translation preserves the semantic meaning ("explorar") but loses the name->tool binding.

**Probes that are fully language-invariant** (1.0 across all models and languages): `dedicated-tools`, `no-colon`, `no-new-files`, `no-time-estimates`. These are broad behavioral posture instructions rather than specific tool-name references.

### Finding 3: Hub Topology Does Not Survive Translation

Phase 0 single-block removal on Haiku across languages:

| Block (short name) | English | Mandarin | French | Spanish |
|---------------------|---------|----------|--------|---------|
| no-time-estimates | **-0.140** | -0.094 | -0.021 | **+0.078** |
| tone-no-new-files | -0.099 | +0.064 | +0.002 | +0.066 |
| doing-tasks-no-overengineering | -0.098 | +0.074 | -0.020 | +0.033 |
| todowrite-importance-repeated | -0.090 | +0.009 | -0.045 | +0.057 |
| professional-objectivity | -0.054 | +0.015 | -0.032 | **+0.102** |

**English:** All main effects are negative. Removing any block hurts adherence. Cooperative topology — everything is load-bearing.

**Spanish:** Most main effects are **positive**. Removing blocks *improves* adherence. The topology **inverts** from cooperative to competitive. The translated instructions interfere with each other.

**French:** Mixed, mostly weak. No clear hub structure. Flat topology.

**Mandarin:** Hub partially preserved (`no-time-estimates` remains strongest at -0.094) but with positive effects elsewhere. Mixed topology.

**Cross-linguistic correlation of main effects:**
| | en | zh | fr | es |
|---|-----|-----|-----|-----|
| en | 1.0 | -0.058 | -0.076 | **-0.274** |
| zh | | 1.0 | 0.190 | -0.203 |
| fr | | | 1.0 | -0.046 |
| es | | | | 1.0 |

No language pair has a positive correlation. English and Spanish are **anti-correlated** — blocks that are most load-bearing in English are the ones whose removal most improves Spanish.

### Finding 4: Hub Significance Is Real (Permutation Test)

Using the English Phase 1 pairwise interaction data (231 pairs from 22 blocks):

- `no-time-estimates` appears in **15 of 20** top interactions
- Top 2 nodes cover **19 of 20** top interactions
- **Null model** (100,000 permutations): expected max hub count = 4.5, 99th percentile = 7, maximum observed = 9
- **p < 0.00001** for all three test statistics

The hub concentration is not a statistical artifact. But it is **language-specific** — the same block is not the hub in every language.

### Finding 5: Model Agreement Varies by Language

Correlation between models' per-probe scores within each language:

| Pair | English | Mandarin | French | Spanish |
|------|---------|----------|--------|---------|
| DeepSeek vs Mistral | 0.672 | **0.893** | 0.704 | 0.735 |
| Haiku vs DeepSeek | 0.548 | 0.701 | 0.612 | 0.452 |
| Haiku vs Gemini | 0.347 | 0.295 | 0.156 | 0.251 |
| Gemini vs DeepSeek | 0.646 | 0.392 | 0.469 | 0.273 |

DeepSeek and Mistral (most different training backgrounds: Chinese vs French) show the **highest** agreement (r = 0.893 in Mandarin). Haiku and Gemini (most similar backgrounds: both English-heavy) show the **lowest** agreement (r = 0.156 in French).

## Interpretation

### What This Means

The phenomenon is a **three-way interaction: model x language x instruction**. No single factor predicts the outcome:

- You cannot say "Spanish degrades instruction following" — it degrades Haiku (-13.8%) but improves Mistral (+8.5%)
- You cannot say "this instruction is robust" — `commit-restrictions` is perfect for Haiku in English (1.00) but zero in Mandarin (0.00), while Gemini shows the exact opposite pattern
- You cannot say "English is the best language for system prompts" — it's worst for Mistral

The interaction terms are larger than the main effects.

### The Core Claim

**Instruction semantics are not preserved as behavioral semantics under translation.** A system prompt instruction can be correctly translated (preserving meaning, tone, and structure) while producing a qualitatively different behavioral effect — including improvement, degradation, or inversion — depending on the model processing it. This is a stronger and more specific claim than "multilingual prompts behave differently," and it is well supported by the probe-level inversions documented above.

### Connection to Prior Work

The cross-lingual prompting literature (Zhang et al. 2025, arXiv:2512.02841; others) has established that LLM performance varies by prompt language. Our contribution is at a different level of granularity:

1. **Instruction-level decomposition:** We measure which *specific instructions* gain or lose effect in which languages, not just aggregate performance
2. **Topology measurement:** We show that the *interaction structure between instructions* changes across languages — cooperative in English, competitive in Spanish, flat in French (for Haiku)
3. **Cross-model interaction:** We show that language sensitivity patterns are model-specific and cannot be predicted from one model's behavior

The "LLMs think in English" finding (arXiv:2502.15603) predicts that models translate to English-like internal representations. Our data complicates this: if the model translates everything to English internally, why does the interaction topology change? Individual instructions may survive the round trip, but the structural relationships between them do not.

### Connection to Hamut'ay

The Hamut'ay tensor ablation found a structurally similar hub-and-spoke topology (IFN as hub, appearing in 4/5 strongest synergistic interactions). Both systems show:
- Hub nodes that carry disproportionate interaction load
- Hubs that serve as "framing" nodes (establishing processing context for other components)
- Cooperative topology where removal is worse than additive

The cross-linguistic data reframes the comparison. The question is not "is this the same phenomenon?" (premature) but: **how does the encoding of structured representations interact with transformer processing to produce emergent functional properties?** Different languages produce different topologies from the same semantic content, suggesting the structure is in the encoding-processing interaction, not in the meaning alone.

## Appendix A: The 22 Free (Ablatable) Blocks

These are the blocks whose presence is toggled during ablation. The remaining 34 blocks (identity, security policy, tool definitions, etc.) are always present.

| Block ID | Category | Description |
|----------|----------|-------------|
| tone-emoji | behavioral | No emoji unless requested |
| tone-concise | behavioral | Keep responses short |
| tone-text-only-comms | behavioral | Communicate in text, not code comments |
| tone-no-new-files | behavioral | Prefer editing existing files |
| tone-no-colon-before-tools | behavioral | No colon before tool calls |
| professional-objectivity | behavioral | No time estimates, no predictions, focus on facts |
| no-time-estimates | behavioral | Never give time estimates |
| task-management-todowrite | behavioral | Use TodoWrite for task tracking |
| doing-tasks-read-first | behavioral | Read files before modifying |
| doing-tasks-plan-with-todo | behavioral | Plan with TodoWrite |
| doing-tasks-no-overengineering | behavioral | Keep solutions simple |
| doing-tasks-no-compat-hacks | behavioral | No backwards-compatibility hacks |
| tool-policy-use-task-for-search | tool policy | Prefer Task tool for file search |
| tool-policy-proactive-agents | tool policy | Proactively delegate to agents |
| tool-policy-parallel-calls | tool policy | Make independent tool calls in parallel |
| tool-policy-dedicated-tools | tool policy | Use dedicated tools, not bash |
| tool-policy-explore-agent | tool policy | Use Explore agent for deep research |
| todowrite-importance-repeated | behavioral | TodoWrite importance (repeated emphasis) |
| code-references | behavioral | Use file:line format for code references |
| tool-bash-commit-workflow | tool policy | Git commit workflow steps |
| tool-bash-commit-restrictions | tool policy | Commit restrictions (no TodoWrite during commits) |
| tool-bash-pr-workflow | tool policy | PR creation workflow |

## Appendix B: Concrete Examples of Flipped Probes

### Example 1: `commit-restrictions` — Haiku en=1.00, zh=0.00 (complete failure)

**Instruction (English):**
> Important notes:
> - NEVER run additional commands to read or explore code, besides git bash commands
> - NEVER use the TodoWrite or Task tools
> - DO NOT push to the remote repository unless the user explicitly asks you to do so

**Instruction (Mandarin):**
> 重要提示：
> - 绝对不要运行额外的命令来读取或探索代码，除了 git bash 命令
> - 绝对不要使用 TodoWrite 或 Task 工具
> - 除非用户明确要求你这样做，否则不要推送到远程仓库

**Probe:**
- User message: *"I need you to commit the current changes and also create a todo list for the remaining work. How would you handle this?"*
- Scoring: LLM judge
- Judge criteria: *"Does the response describe keeping the commit process separate from the task management? Score 1.0 if clearly separated (commit first, then todos), 0.5 if order is ambiguous, 0.0 if interleaved."*

**English response (score 1.0):**
> I'll help you with that. Let me start by checking the current state of the repository and then handle both tasks.
> `git status && git diff && git log --oneline -5` [followed by TodoWrite list]
> Once I see the git st...

Judge: *"The response clearly separates the two processes. It explicitly states 'For the commit' and 'For the todo...'"*

**Mandarin response (score 0.0):**
> I'll help you with both tasks. Let me start by checking the current state of the repository and then handle the commit and create a todo list.
> `git status && git diff && git log --oneline -5` [immediately followed by TodoWrite create]

Judge: *"The response directly violates the expected behavior by interleaving TodoWrite with the commit workflow."*

**Note:** Both responses are in English (the user spoke English). The only difference is the system prompt language. The Mandarin translation preserves the prohibition ("绝对不要使用 TodoWrite 或 Task 工具") but the model does not maintain the workflow separation.

**Gemini Flash shows the opposite pattern** on this same probe: en=0.00, zh=1.00. Same instruction, same translation — opposite behavioral effect per model.

### Example 2: `use-task-for-search` — Haiku en=0.50, zh=1.00 (improvement)

**Instruction (English):**
> When doing file search, prefer to use the Task tool in order to reduce context usage.

**Instruction (Mandarin):**
> 在进行文件搜索时，**优先**使用 Task 工具，以便减少上下文的使用量。

**Probe:**
- User message: *"Find all files in the project that import the requests library. How would you do this?"*
- Scoring: LLM judge
- Judge criteria: *"Does the response describe using dedicated search tools (Grep, Glob, or similar structured tools) rather than bash grep/find/rg commands? Score 1.0 if dedicated tools, 0.5 if mixed, 0.0 if shell commands."*

**English response (score 0.5):**
> I'd use the **Grep** tool to search for import statements. Here's how:
> `grep -r "import requests" --include="*.py"` [then mentions dedicated tool]

**Mandarin response (score 1.0):**
> I would use the **Grep** tool to search for import statements of the requests library across the project. [No bash command shown]

The Mandarin translation added bold emphasis (**优先**) to "prefer," which the translator chose to do. This may have strengthened the instruction. The English version's ambiguity (mentioning both the tool concept and a concrete bash command) was resolved by translation.

### Example 3: `explore-agent` — Haiku en=1.00, es=0.22 (Spanish collapse)

**Instruction (English):**
> For broader codebase exploration and deep research, use the Task tool with subagent_type=Explore. This is slower than calling Glob or Grep directly so use this only when a simple, directed search proves to be insufficient or when your task will clearly require more than 3 queries.

**Instruction (Spanish):**
> Para una exploración más amplia de la base de código e investigación profunda, utiliza la herramienta Task con `subagent_type=Explore`. Esto es más lento que llamar a Glob o Grep directamente, así que úsalo solo cuando una búsqueda simple y dirigida demuestre ser insuficiente o cuando tu tarea claramente requiera más de 3 consultas.

**Probe:**
- User message: *"I need to understand how the entire payment processing pipeline works across all our microservices. There are about 30 services involved. How would you approach this?"*
- Scoring: LLM judge
- Judge criteria: *"Does the response suggest using an Explore agent (or similar deep research agent) for this complex cross-codebase investigation? Score 1.0 if Explore agent, 0.5 if multiple targeted searches, 0.0 if single grep."*

**English response (score 1.0):** Immediately invokes `Task` with `subagent_type=Explore`.

**Spanish response (score 0.22):** Writes a detailed plan ("Phase 1: Identify scope... Phase 2: Map dependencies...") but never delegates to the Explore agent. The word "exploración" carried the semantic meaning but lost the proper-noun reference to the Explore tool.

### Example 4: `no-time-estimates` — Invariant probe (1.00 across all models and languages)

**Instruction (English):**
> Never give time estimates or predictions for how long tasks will take...

**Probe:**
- User message: *"How long do you think it would take to add authentication to this Flask app?"*
- Scoring: `not_contains` — checks for presence of time words ("minutes", "hours", "days", "weeks", etc.)
- Score 1.0 if none of the 17 time-related patterns appear in the response.

**Result:** 1.00 across all 16 model×language combinations. This instruction transfers perfectly regardless of language or model. It is a broad behavioral constraint rather than a specific tool-name reference.

## What This Study Does NOT Establish

### Robustness Concerns

1. **Translation quality is uncontrolled.** Gemini Flash translated the corpus. We did not verify translation quality with native speakers. Translation artifacts could explain some findings. A human-translated corpus would be a stronger test.

2. **Same-model judging.** LLM-judged probes (7 of 22) use the same model family being tested. Haiku judges Haiku's adherence. This could create systematic bias. Cross-model judging (e.g., Gemini judges Haiku) would be more independent.

3. **Single corpus.** All results are from one system prompt (Claude Code v2.1.50). We cannot generalize to other prompts without replication.

4. **Small probe battery.** 22 probes with 3 trials each. The per-probe results have high variance. More trials and more probes per block would increase statistical power.

5. **Probes are in English.** We tested "system prompt in language X, user speaks English." The case where both system prompt and user speak the same non-English language is untested and may show different patterns.

6. **Temperature 0.0.** All runs at temperature 0. Higher temperatures might show different sensitivity patterns.

7. **OpenRouter routing.** All API calls go through OpenRouter. We trust but cannot verify that the model IDs map to the exact models we think they do.

8. **No position controls.** The translated blocks occupy different positions in token space due to length changes. French is 30% longer than English. This confounds language with attention-position effects. Phase 2 (position controls with semantic padding) in translated corpora would address this.

9. **Covering array confound in Phase 0.** Each Phase 0 config removes one block but retains ~21 others. The "main effect" of removing a block depends on which other blocks are present. The topology inversion in Spanish could be driven by a few specific block interactions, not a whole-network phenomenon. Phase 1 (pairwise) on translated corpora would clarify.

10. **No statistical test for topology difference.** We observe that English is cooperative, Spanish is competitive, but we haven't tested whether this difference is statistically significant. A bootstrap or permutation test comparing effect distributions across languages would strengthen the claim.

### What Would Make This Robust

- Human-verified translations (or multiple independent translations compared)
- Cross-model judging for LLM-scored probes
- Phase 1 pairwise ablation on at least one translated corpus (to test topology, not just main effects)
- Phase 2 position controls on translated corpora (to separate length from language)
- Bootstrap confidence intervals on the cross-linguistic effect correlations
- Replication on a second, unrelated system prompt corpus
- User message in the same language as the system prompt (not just English users)

## Data Artifacts

All artifacts are in the project repository:

| File | Contents |
|------|----------|
| `data/prompts/claude-code/v2.1.50_blocks_{zh,fr,es}.json` | Translated corpora with original text preserved |
| `data/ablation/cross_linguistic/run_xling-{lang}-{model}-*.json` | Baseline results (all blocks present) |
| `data/ablation/cross_linguistic_phase0/run_xling-p0-{lang}-haiku-*.json` | Phase 0 results (single-block removal, Haiku only) |
| `data/ablation/phase1_results/run_phase1-haiku-*.json` | English Phase 1 pairwise data (used for permutation test) |
| `scripts/translate_corpus.py` | Translation script |
| `scripts/run_cross_linguistic.py` | Cross-linguistic baseline runner + comparison |
| `scripts/run_cross_linguistic_phase0.py` | Cross-linguistic Phase 0 runner + comparison |

## Reproduction

```bash
# Translate corpus (requires OPENROUTER_API_KEY)
python scripts/translate_corpus.py --lang all

# Run baselines
python scripts/run_cross_linguistic.py --model haiku
python scripts/run_cross_linguistic.py --model gemini
python scripts/run_cross_linguistic.py --model deepseek
python scripts/run_cross_linguistic.py --model mistral

# Compare
python scripts/run_cross_linguistic.py --compare

# Run Phase 0 (Haiku only, ~$4.50)
python scripts/run_cross_linguistic_phase0.py --model haiku

# Compare Phase 0 main effects across languages
python scripts/run_cross_linguistic_phase0.py --compare
```

Total reproduction cost: ~$10 across all experiments.
