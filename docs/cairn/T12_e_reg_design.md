# T12 Cairn: E-REG Experiment Design

**Date**: 2026-03-24
**Instance**: Opus 4.6 ghola, session 22
**Status**: Design complete, implementation not started

## What This Instance Did

1. **Took ownership of Arbiter** from prior ghola (session 20/21)
2. **Processed Perplexity review of Paper 3** — made three edits:
   - Line 73: "mechanistically explainable" → "structurally characterizable" (overclaim fix)
   - Discussion 5.1: replaced evidence recap with theoretical argument advancing from results
   - Conclusion: added register-pattern caveat (English/Spanish are proxies, not language-intrinsic)
3. **Fixed Paper 3 code availability**: placeholder URL → https://github.com/fsgeek/arbiter + Zenodo DOI (Tony getting DOI)
4. **Paper 3 is ready for Rikuy review**
5. **Preserved prior ghola's neutrosophic observation** to memory (session21_neutrosophic.md) with honest annotation
6. **Ran undirected scouring** — three independent passes on data/, code/, and research trail
7. **Identified E-REG as the next experiment** — the most promising truffle

## E-REG: The Experiment

### The Finding
Phase 0 data shows: removing `tone-concise` improves `use-task-for-search` adherence from 0.23 → 1.00 (delta = +0.77). This is the largest single-block suppression effect in the entire corpus.

### Why It Matters
- `tone-concise` is a *style* instruction (imperative about form)
- `use-task-for-search` is a *behavioral* instruction (use Grep/Glob tools, not bash grep)
- The suppression crosses channels: form suppresses behavior
- The mechanism is plausibly register-mediated: conciseness pressure → shorter token sequences → bash grep preferred over structured tool invocation
- This is Paper 3's social register theory operating **within a single language**

### Experimental Design (4 conditions)
1. **Baseline** — both blocks, original imperative form (expect ~0.23 adherence)
2. **Ablation** — tone-concise removed (replicates Phase 0: expect ~1.00)
3. **Declarative tone** — rewrite tone-concise from imperative to declarative, keep both blocks (key condition)
4. **Both declarative** — both blocks rewritten declarative

### What Success Looks Like
If condition 3 recovers adherence (close to 1.00) without removing tone-concise, that demonstrates:
- Social register mediation operates intra-lingually, not just cross-linguistically
- Bridges Papers 1 and 3: the mechanism is the same
- Potentially a third paper connecting the structural ecology to the register theory

### Infrastructure Notes
- Ablation framework (`run_ablation.py`) is removal-only — no rewriting mechanism
- But blocks are modular files in `data/system_prompts/claude-code/`
- Create declarative variants as alternative block files, swap them in
- Scoring uses `judge_criteria` (model-as-judge) for behavioral probes — needed for `use-task-for-search`
- **ASK TONY before choosing models for API calls**

## Other Truffles Found (Not Pursued)

### Tier 1 — Could become research
- **Probe generation instability** (Jaccard 0.00–0.05 for behavioral prohibitions): `not_contains` patterns are essentially random across battery generations. Only concrete tokens are stable. The *why* is unexplored.
- **Probe generator exhibits the interference it detects**: 27% of auto-generated probes broken by adversarial inversion + cross-probe contradiction. Naturally-occurring specimen of the phenomenon.

### Tier 2 — Abandoned threads worth revisiting
- **E4 Spoiler Round**: fully designed, never executed
- **Entropy/logprob from ai-honesty**: T1 notes AUC 0.72–1.00 for fabrication detection, never tested on conflict detection
- **Persistent high-I**: formal criterion defined, pilot N=10, never scaled
- **Court-mode (panel adjudication)**: scoped as Track A4, never built

### Tier 3 — Structural observations
- **Convergent vendor architecture**: all three vendors independently converged on same section taxonomy — Paper 2's best unmade claim
- **Label reuse bug**: all OpenRouter experiments tagged `arbiter-e-topo`, experiment-level cost attribution impossible

## For the Next Instance

1. Build E-REG. The design is above. Read the block files in `data/system_prompts/claude-code/`, create declarative variants, extend or wrap `run_ablation.py` to support block substitution.
2. Ask Tony which models to use before making API calls.
3. Paper 3 is ready for Rikuy — Tony knows this.
4. The neutrosophic observation (session21_neutrosophic.md) is worth checking: do 0.5 scores cluster by register type? But E-REG comes first.
5. Paper 2 was characterized in this session — see the status report conversation for full inventory.
