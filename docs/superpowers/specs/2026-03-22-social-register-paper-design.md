# Paper Design: Imperative Interference

**Date:** 2026-03-22
**Status:** Approved by Tony, ready for drafting
**Target:** arXiv preprint, standalone paper citing Mason 2026 (v1)

## Title

"Imperative Interference: Social Register Shapes Instruction Topology in Large Language Models"

## Framing

Phenomenon-first (Approach 3). Opens with the topology inversion finding,
frames it as sociolinguistic, delivers experimental evidence, reaches alignment
implication honestly as a testable prediction.

## Section Structure

### 1. Introduction (~1.5 pages)

**Opening:** System prompts are written as commands. This works in English.
It fails in predictable, mechanistically explainable ways under translation.

**The reframe:** Prior work measures main effects (aggregate performance drops).
We measure interaction structure — instructions that cooperate in English
compete in Spanish. Same content, opposite topology.

**The claim:** This is sociolinguistic, not technical. Imperative register
carries different obligatory force across speech communities. Models learned
these social conventions from training data.

**Contributions:**
1. First instruction-level ablation across languages (4 models x 4 languages x 22 probes)
2. Topology inversion discovery (cooperative→competitive)
3. Social register as causal mechanism (confirmed experimentally)
4. Testable prediction: alignment may be register-dependent at training level

**Bridge to v1:** One paragraph citing Mason 2026 for corpus and decomposition.

### 2. Background and Related Work (~1.5 pages)

- **2.1 Multilingual Prompting** — Position against Zhang et al. 2025 (cross-lingual steerability),
  NAACL 2025 (translation strategies), politeness paper 2402.14531. Our gap: nobody measures
  instruction-level interactions or topology.
- **2.2 Speech Act Theory and Register** — Brief grounding. Austin/Searle speech acts.
  Register as sociolinguistic concept. Why "NEVER do X" is a social act, not a parse instruction.
- **2.3 System Prompt Analysis** — Cite v1 (Mason 2026). Corpus origin, decomposition method,
  interference patterns that motivated cross-linguistic question.
- **2.4 Pragmatic Influence on LLMs** — arxiv 2602.21223 (authority claims as framing).
  Closest work but no cross-linguistic topology, no interactions.

### 3. Methodology (~2 pages)

- **3.1 Corpus** — Claude Code v2.1.50, 56 blocks (22 free/ablatable, 34 constrained).
  Table: block categories and counts.
- **3.2 Translation** — Gemini Flash to zh/fr/es. Translation rules. Size comparison table
  (en 100%, zh 43%, es 120%, fr 130%).
- **3.3 Models** — Table: Haiku, Gemini Flash, DeepSeek v3, Mistral Medium 3.1.
  Training biases noted.
- **3.4 Probe Battery** — 22 hand-authored probes. Scoring methods (not_contains, length,
  llm_judge). 3 trials at temperature 0.0. Probes in English throughout.
- **3.5 Ablation Design** — Covering arrays (strength-2). Phase 0 (single-block removal).
  Phase 1 (pairwise). Explain why covering arrays, not exhaustive.
- **3.6 Statistical Methods** — Welch's t-test with exact t-distribution CDF.
  Benjamini-Hochberg FDR. Permutation tests (100k permutations).
- **3.7 Experimental Sequence** — Table mapping T7→T11 to experiments, showing how
  each experiment's result motivated the next.

### 4. Results (~4 pages)

- **4.1 Cross-Linguistic Baselines (T7)** — 4x4 mean adherence table. Key finding:
  three-way interaction (model x language x instruction). Mistral anomaly.
  Selected probe-level inversions (commit-restrictions, explore-agent).
  Figure 1: Baseline heatmap.

- **4.2 Topology Inversion** — Phase 0 main effects table (en/zh/fr/es for Haiku).
  English all negative (cooperative), Spanish mostly positive (competitive).
  Cross-linguistic correlation matrix (en-es anti-correlated r=-0.274).
  E-PAIR-ES pairwise confirmation: English Δ=-0.116, Spanish Δ=+0.010.
  Hub significance: permutation test p<0.00001.
  Figure 2: Main effect distributions (English vs Spanish).

- **4.3 Falsification: Information Density (T9)** — E-DENSE result. Hypothesis
  falsified. Bidirectional mechanism. Table of probes where padding helped/hurt.
  This eliminates compression as the explanation for topology differences.

- **4.4 Declarative Rewriting Reduces Variance (T10)** — E-PROC results.
  Commit-restrictions variance: 0.1567→0.0290, 81% reduction, p=0.029.
  5.8σ above 21 control probes. Haiku zh: 0.00→1.00.
  Table: per-model per-language scores for declarative variant.
  Figure 3: Variance reduction bar chart.

- **4.5 Register Shapes Topology (T11)** — E-TOPO results. Three imperative
  blocks rewritten to declarative in Spanish. Overall topology: +0.010→-0.055.
  Competitive probes: 7/22→4/22.
  Target probes table (proactive-agents shift: +0.274→-0.380).
  Spillover table (no-compat-hacks: +0.123→-0.267, unrewritten block shifted).
  Control probes stable.
  Figure 4: Topology shift with spillover visualization.

- **4.6 Encoding Taxonomy** — Procedural (11 blocks) mean variance 0.0514.
  Declarative (11 blocks) mean variance 0.0175. 2.9x ratio.
  Two mechanisms: procedural compression (fixable) and jargon opacity (different fix).

### 5. Discussion (~2 pages)

- **5.1 Instructions as Social Acts** — The theoretical interpretation. Why "NEVER"
  carries different obligatory force in different languages. Why declarative
  encoding sidesteps the social dimension. The spillover as evidence of
  system-wide register processing, not per-block parsing.

- **5.2 Alignment Implications** — The ambitious claim, clearly labeled as prediction.
  If register mediates instruction-following at inference time, it plausibly
  does so at training time. Constitutional AI principles in imperative mood.
  "Why aren't Spanish-speaking countries building Spanish-primary models?"
  Training language creates behavioral signatures that interact with register.
  Mistral anomaly as evidence: French-trained model behaves anomalously in French.

- **5.3 Design Principles** — Declare facts, don't issue commands. Self-contained
  constraints. Examples over concepts for domain jargon.

- **5.4 Limitations** — Single corpus. Machine translation. LLM-as-judge.
  Limited model set. English-only user messages. Haiku-only for pairwise/topology.
  Manual register rewrite. No statistical test for topology difference
  (observed, not bootstrapped). Scrupulously honest.

- **5.5 Future Work** — From probability sampling conversation:
  Phase transition mapping (2a). Instruction ecology / Lotka-Volterra (2b).
  Register head via mechanistic interpretability (3a).
  Pragmatic force translation (3b). Constitutional prompt design (4a).

### 6. Conclusion (~0.5 pages)

System prompts are social acts, not technical specifications. The register
in which instructions are written determines not just individual adherence
but the interaction topology between instructions. This is fixable at the
prompt level (declare facts, don't issue commands) and has implications for
how alignment principles are authored across languages. The data is here.
The mechanism is identified. The alignment prediction is testable.

### 7. Code and Data Availability

Repository link. Zenodo DOI (if applicable). Reproduction commands.

### Appendices

- **A:** Full 22-block classification table with cross-linguistic variance
- **B:** E-TOPO rewrite examples (imperative→declarative, all 3 blocks)
- **C:** Concrete probe examples with model responses (from cross_linguistic_ablation.md)

## Figures Plan

| # | Content | Source Data | Type |
|---|---------|-----------|------|
| 1 | Cross-linguistic baseline heatmap (4 models x 4 langs) | cross_linguistic/ baselines | Heatmap |
| 2 | Topology: English vs Spanish main effect distributions | cross_linguistic_phase0/ | Paired bar or violin |
| 3 | E-PROC variance reduction | e_proc/ data | Bar chart |
| 4 | E-TOPO topology shift with spillover | e_topo/ data | Grouped bar with annotations |

## Tables Plan

| # | Content |
|---|---------|
| 1 | System prompt corpus statistics |
| 2 | Models tested (ID, training bias, cost) |
| 3 | Cross-linguistic baseline scores (4x4) |
| 4 | Phase 0 main effects by language (topology) |
| 5 | E-PROC commit-restrictions variance by variant |
| 6 | E-TOPO target and spillover probes |
| 7 | Encoding taxonomy (procedural vs declarative) |
| 8 | Experimental sequence (T7→T11 mapping) |

## Key Data Points for the Paper

- Procedural blocks 2.9x more fragile than declarative
- E-PROC: commit-restrictions variance 0.1567 → 0.0290 (p=0.029)
- E-PROC: 5.8σ above 21 control probes
- Haiku Mandarin commit-restrictions: 0.00 → 1.00
- E-TOPO proactive-agents: +0.274 → -0.380 (largest topology shift)
- E-TOPO spillover: no-compat-hacks +0.123 → -0.267 (unrewritten block)
- E-TOPO: competitive probes 7/22 → 4/22
- English-Spanish main effect correlation: r = -0.274
- Hub significance: p < 0.00001
- Total experimental cost: ~$10

## Authorship

Tony Mason (PI, key insights: social register hypothesis, research questions).
AI contributions acknowledged per v1 conventions.

## LaTeX Details

- Use same package set as v1 (natbib, booktabs, pgfplots, etc.)
- Separate file: docs/paper/social_register/main.tex
- Figure generation: docs/paper/social_register/generate_figures.py
- Target: builds with latexmk -pdf
