# T12 Cairn: E-REG Experiment Handoff

**Date**: 2026-03-24
**Instance**: Opus 4.6 ghola, session 22
**Status**: Design complete, implementation not started (Tinkuy paging prevented file reads)

## What This Session Did

1. **Paper 3 edits** — Three fixes from Perplexity review:
   - Line 73: "mechanistically explainable" → "structurally characterizable" (overclaim fix)
   - Discussion 5.1: Replaced evidence recap with theoretical advance (falsification of specification model)
   - Conclusion: Added register-pattern caveat ("English"/"Spanish" are proxies, not language-intrinsic)
   - Code availability: Updated placeholder URL to https://github.com/fsgeek/arbiter with Zenodo DOI pending from Tony

2. **Scourer sweep** — Three independent passes over the repo. Full synthesis below.

3. **E-REG experiment designed** but not built due to Tinkuy context pressure.

## Scourer Findings: Ranked Truffles

### Tier 1: Research-ready

**Truffle #1: tone-concise suppresses use-task-for-search (+0.77 delta)**
- Phase 0 data: removing `tone-concise` improves `use-task-for-search` from 0.23 → 1.00
- Largest single-block suppression in the corpus
- Mechanism hypothesis: conciseness is a *style* imperative that suppresses a *behavioral* imperative
- This is Paper 3's social register theory operating *within* English, mono-lingually
- A style instruction ("be concise") causes the model to shortcut to `grep` instead of structured tools
- **This is the truffle I chose to pursue.** See E-REG design below.

**Truffle #2: Probe generation instability (Jaccard 0.00–0.05)**
- Behavioral prohibition probes have near-zero stability across battery generations
- Only concrete surface tokens (emoji, git flags) are stable
- `not_contains` scoring strategy is structurally undermined for behavioral instructions
- Fix (judge_criteria) addresses testing but not the *why*
- Data: `data/ablation/probe_stability_analysis.md`

**Truffle #3: Probe generator exhibits the interference it detects**
- 27% of auto-generated probes broken: adversarial inversion (3) + cross-probe contradiction (3)
- Generator given conflicting meta-instructions resolved them by confabulating — same as models do
- Naturally-occurring specimen of the phenomenon Arbiter studies
- More of an observation/case study than an experiment

### Tier 2: Abandoned threads worth revisiting

- **E4 Spoiler Round**: Fully designed, never executed. Tests whether revealing what an instruction tests changes adherence topology.
- **Entropy/logprob from ai-honesty**: T1 cairn notes AUC 0.72–1.00 for fabrication detection. Never tested on conflict detection. The ai-honesty repo is in Tony's working directories.
- **Persistent high-I**: Formal criterion (tau_I=0.60, epsilon=0.03, k=2), pilot N=10, 1 persistent case (10%). Never scaled.
- **Court-mode (panel adjudication)**: Scoped as Track A4 in dual-track plan. Three-reviewer finding is empirical basis.

### Tier 3: Structural observations

- **Convergent vendor architecture**: All 3 vendors converged on same section taxonomy. Paper 2's most interesting unmade claim.
- **Label reuse bug**: All OpenRouter experiments show as `arbiter-e-topo`. Experiment-level cost attribution impossible.
- **Episodes system**: Only 2 entries in `data/episodes/episodes.json`. Either norms rarely violated or logging isn't happening.

## E-REG Experiment Design

**Name**: E-REG (Register Rewriting, Intra-lingual)
**Hypothesis**: The tone-concise → use-task-for-search suppression is register-mediated. Declarative rewriting of tone-concise will recover use-task-for-search adherence without removing the conciseness instruction.

**4 conditions:**
1. **Baseline** — Both blocks, original imperative form. (Expect ~0.23 for use-task-for-search)
2. **Ablation** — tone-concise removed. (Phase 0 replication: expect ~1.00)
3. **Declarative tone** — tone-concise rewritten from imperative to declarative, both present. (Key test)
4. **Both declarative** — Both blocks rewritten declarative. (Control for direction)

**What connects this to the existing work:**
- Paper 1 discovered the cooperative ecology and the tone-concise suppression
- Paper 3 discovered that register mediates cross-linguistic topology and declarative rewriting fixes it
- E-REG tests whether the *same mechanism* operates within English on the largest suppression pair
- If condition 3 recovers adherence: register mediation is language-general, not just cross-linguistic
- This bridges Papers 1 and 3 with a unified mechanism claim

**Infrastructure notes:**
- `src/arbiter/ablation.py` has `AblationConfig` with `removed_blocks` — removal only, no rewrite support
- System prompt blocks are in `data/system_prompts/claude-code/` as modular files
- Approach: create declarative variant block files, modify ablation runner to support block *substitution* not just removal
- Scoring: `use-task-for-search` uses `judge_criteria` (model-as-judge), not `not_contains`
- Need to check with Tony about which model to use for API calls (standing instruction)

**Implementation plan for next instance:**
1. Read `data/system_prompts/claude-code/tone-concise.md` and `use-task-for-search.md` (or equivalent block names — check the actual filenames)
2. Create declarative rewrites of each block
3. Extend `AblationConfig` to support `substituted_blocks: dict[str, str]` (maps block name → alternative file)
4. Create `experiments/e_reg.py` following the pattern of existing experiment scripts
5. Run 4 conditions × N trials (check what N the prior experiments used)
6. **ASK TONY which model to use before making API calls**

## Neutrosophic Observation (from prior ghola, preserved)

The indeterminacy term I in neutrosophic (T,I,F) scoring maps to probes that score 0.5 — the ambiguous zone. Prior ghola hypothesized this decomposes the three-way interaction more cleanly than binary. Status: unverified. Test: check whether 0.5 scores cluster by register type vs. distributing uniformly. Saved to `memory/session21_neutrosophic.md`.

## Perplexity Review (preserved)

Saved to `memory/session22_perplexity_review.md`. Key actionable items were addressed in the paper edits above. Remaining suggestion (rewrite related work) was assessed as unnecessary — current positioning is adequate.

## What the next instance should do

1. Read this cairn
2. Build E-REG (implementation plan above)
3. Ask Tony about model selection before API calls
4. Run the experiment
5. If condition 3 recovers adherence → this is a paper-worthy finding that unifies Papers 1 and 3
