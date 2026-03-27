# T12 Cairn: E-REG Experiment Handoff

**Date**: 2026-03-24
**Instance**: Opus 4.6 ghola, session 22
**Status**: Design complete, implementation not started (Tinkuy context pressure)

## What This Instance Did

1. **Paper 3 edits** — Three changes based on Perplexity review:
   - Line 73: "mechanistically explainable" → "structurally characterizable" (we have behavioral evidence, not internal instrumentation)
   - Discussion 5.1: Rewrote to advance argument rather than recap evidence
   - Conclusion: Added caveat that "English"/"Spanish" are proxies for register-encoding patterns, not language-intrinsic properties
   - Code availability: Updated placeholder URL to https://github.com/fsgeek/arbiter and Zenodo DOI (Tony getting DOI)

2. **Scourer sweep** — Three independent passes across data/, src/, docs/. Full synthesis below.

3. **E-REG experiment designed** but not built (Tinkuy paging prevented implementation)

## Scourer Findings — The Truffle Map

### Tier 1: Research-ready

**TRUFFLE #1 (SELECTED FOR NEXT EXPERIMENT): tone-concise ↔ use-task-for-search suppression**
- Phase 0 data: removing `tone-concise` improves `use-task-for-search` from 0.23 → 1.00 (delta +0.77)
- This is the largest single-block suppression effect in the corpus
- Mechanism hypothesis: conciseness is a *style* imperative that suppresses a *behavioral* imperative
- Under register theory: the model resolves competing imperatives by prioritizing the one with stronger register force
- This is the INTRA-LINGUAL version of Paper 3's cross-linguistic topology inversion
- Connection: Paper 1 found the ecology, Paper 3 found it's language-dependent, E-REG would show the mechanism operates within a single language

**TRUFFLE #2: Probe generation instability (Jaccard 0.00–0.05 for behavioral prohibitions)**
- Surface-level probes for behavioral instructions are essentially random across battery generations
- Only concrete tokens (emoji, git flags) are stable
- The fix (judge_criteria) addresses testing but not generation
- Implication: behavioral prohibitions don't have stable surface signatures — they're register constraints, not token constraints

**TRUFFLE #3: Probe generator exhibits the interference it detects**
- 27% of auto-generated probes broken: adversarial inversion (3) + cross-probe contradiction (3)
- The generator was given conflicting meta-instructions and resolved them by confabulating
- Naturally-occurring specimen of the phenomenon Arbiter studies

### Tier 2: Abandoned threads worth revisiting

- **E4 Spoiler Round**: Fully designed, never executed
- **Entropy/logprob from ai-honesty**: T1 notes AUC 0.72–1.00 for fabrication detection, never tested on conflict detection
- **Persistent high-I**: Formal criterion defined, pilot N=10, 1 persistent case (10%), never scaled
- **Court-mode panel adjudication**: Scoped in dual-track plan, three-reviewer finding supports it, never built

### Tier 3: Structural observations

- **Convergent vendor architecture**: All 3 vendors converged on same section taxonomy independently
- **Label reuse bug**: All OpenRouter experiments show as `arbiter-e-topo`, experiment-level cost attribution impossible
- **Episodes system**: Only 2 entries logged — either norms rarely violated or logging isn't happening

## E-REG Experiment Design

**Name**: E-REG (Register Rewriting for Intra-Lingual Suppression)
**Hypothesis**: The tone-concise → use-task-for-search suppression is register-mediated, and declarative rewriting will recover adherence without removing the conciseness instruction.

**4 conditions:**
1. **Baseline** — both blocks, original imperative form (expect ~0.23 adherence on use-task-for-search)
2. **Ablation** — tone-concise removed (replicates Phase 0: expect ~1.00)
3. **Declarative tone** — tone-concise rewritten from imperative to declarative, both present
4. **Both declarative** — both blocks rewritten declarative

**Predicted outcomes:**
- If condition 3 recovers adherence → register is the mechanism (same as Paper 3's Spanish fix)
- If condition 3 fails but condition 4 works → both blocks' register matters, not just the suppressor
- If both fail → suppression is semantic, not register-mediated (falsifies the hypothesis)

**Infrastructure notes:**
- Ablation framework (`run_ablation.py`) is removal-only — uses `AblationConfig` with `removed_blocks` list
- Need to extend it OR create rewritten block variants as alternative files and swap them in
- System prompt blocks are in `data/system_prompts/claude-code/`
- Scoring uses `judge_criteria` (model-as-judge), which is correct for behavioral probes
- IMPORTANT: Ask Tony before choosing models for API calls

**What the next instance needs to do:**
1. Read `src/arbiter/ablation/run_ablation.py` and `src/arbiter/ablation/config.py` to understand the runner
2. Read `data/system_prompts/claude-code/` block files for tone-concise and use-task-for-search content
3. Create declarative rewrite variants of both blocks
4. Either extend AblationConfig to support block substitution, or create a minimal E-REG runner
5. Ask Tony which models to use
6. Run the 4 conditions
7. Analyze: does declarative rewriting recover adherence?

## Prior Ghola's Neutrosophic Observation

Preserved and annotated. The claim: 0.5 (ambiguous) probe scores map to neutrosophic indeterminacy (I), and the three-way interaction might decompose through (T, I, F). My assessment: this is either a genuine theoretical lens or framework-shopping. The test is whether 0.5 scores cluster by register type rather than distributing uniformly. Not yet tested. Connects to persistent high-I (E3 pilot).

## Paper Status

- **Paper 1** (`docs/paper/main.tex`): Structural ablation. English-only. Cooperative topology, hub fragility. Complete.
- **Paper 2**: AST structural analysis. Measurements exist, no finding. Parser became infrastructure for Papers 1 & 3. Not written up.
- **Paper 3** (`docs/paper/social_register/main.tex`): Cross-linguistic register. Edited this session. Ready for Rikuy review. Tony getting Zenodo DOI.

## Perplexity Review Summary (on Paper 3)

Saved to memory. Key points:
- "Mechanistic" overclaim — VALID, fixed
- Repetition in Discussion — VALID, fixed
- Abstract density — DISAGREE (fine for arXiv)
- Cross-linguistic caution — VALID, fixed
- Falsification logic — ALREADY HANDLED in paper
- Suggested three passes: abstract/intro tightening, related work repositioning, contribution precision. Only the first was needed; related work and contributions were already well-positioned.
