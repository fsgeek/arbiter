# E-PHASE: Phase Transition Mapping — No Transition Found

**Date:** 2026-03-28 (Session 25)
**Status:** Complete. Phase transition hypothesis falsified. Block identity dominates over density.

## Experiment Design

**Question:** Does imperative register saturation have a critical threshold, or is degradation smooth?

**Method:** 12 conditions varying imperative density from 0 (all 11 procedural blocks rewritten to declarative) to 11 (original corpus, all imperative). Blocks added back to imperative in order of cross-linguistic variance (most fragile first). Haiku, 22 probes, 3 trials each, temperature 0.0.

**Density schedule (blocks added back to imperative):**

| Density | Block Added | XLing Var |
|---------|------------|-----------|
| 0 | (all declarative) | — |
| 1 | commit-restrictions | 0.1567 |
| 2 | + text-only-comms | 0.0834 |
| 3 | + parallel-calls | 0.0760 |
| 4 | + proactive-agents | 0.0731 |
| 5 | + use-task-for-search | 0.0607 |
| 6 | + explore-agent | 0.0499 |
| 7 | + pr-workflow | 0.0225 |
| 8 | + commit-workflow | 0.0211 |
| 9 | + todowrite | 0.0132 |
| 10 | + no-overengineering | 0.0093 |
| 11 | + dedicated-tools (=original) | 0.0000 |

**Predictions:**
- Phase transition: stable until density N, then sudden collapse
- Smooth/linear: monotonic degradation with increasing density

**Cost:** ~$1.44 (792 API calls + judge calls)

## Results

### Aggregate: No Phase Transition, No Monotonic Trend

| Density | Mean Adherence | StdDev |
|---------|---------------|--------|
| 0 | 0.810 | 0.267 |
| 1 | 0.749 | 0.355 |
| 2 | 0.787 | 0.326 |
| 3 | 0.751 | 0.365 |
| 4 | 0.786 | 0.321 |
| 5 | 0.743 | 0.357 |
| 6 | 0.800 | 0.311 |
| 7 | 0.763 | 0.352 |
| 8 | 0.774 | 0.341 |
| 9 | 0.847 | 0.256 |
| 10 | 0.802 | 0.280 |
| 11 | 0.841 | 0.282 |

Largest step drop: density 0→1 (Δ=-0.061). Mean step size: +0.003, SD: 0.048.
Z-score of worst step: -1.3. **No outlier step — pure noise.**

### Critical Finding: Original Corpus Outperforms All-Declarative

Density 11 (original, all imperative): **0.841**
Density 0 (all declarative): **0.810**

The all-declarative rewrite is *worse* than the original for Haiku in English.
This contradicts a naive application of Paper 3's "declare facts, don't issue
commands" principle to intra-lingual contexts.

### Probe-Level: Block Identity Dominates

Probes with range > 0.2 across densities:

| Probe | Range | Pattern |
|-------|-------|---------|
| explore-agent | 0.85 | Chaotic: 1.00→0.20→0.15→...→0.85→0.17→...→1.00 |
| proactive-agents | 0.72 | Drops at density 1, recovers and oscillates |
| use-task-for-search | 0.50 | Binary: 0.50 or 0.00, no density trend |
| code-references | 0.50 | Noisy, unreliable (known weight-conflicting) |
| plan-with-todo | 0.50 | Drops at density 5 and 8, recovers at 9 |
| todowrite-repeated | 0.45 | Oscillating |
| pr-workflow | 0.25 | Gradually improves with density (!!) |

**explore-agent detail** — the most dramatic probe:

| Density | Score | What changed |
|---------|-------|-------------|
| 0 | 1.00 | All declarative — perfect |
| 1 | 0.20 | + commit-restrictions imperative → collapses |
| 6 | 0.85 | + explore-agent itself imperative → recovers |
| 9 | 1.00 | + todowrite imperative → perfect again |
| 11 | 1.00 | Original corpus — perfect |

The model follows the explore-agent instruction better when it's in its
*original imperative form* than when rewritten to declarative. And the
collapse at density 1 isn't about density — it's about commit-restrictions
specifically interfering when converted back to imperative while explore-agent
remains declarative.

## Interpretation

### 1. No Density Effect

Imperative count does not predict adherence. The phase transition hypothesis
is falsified. Register effects are not dose-responsive.

### 2. Block Identity Is Everything

The oscillation pattern shows specific blocks cause specific probe effects
when switched between registers. The interaction is pairwise (which block ×
which probe), not aggregate (how many imperative blocks total).

### 3. Declarative Is Not Universally Better (Intra-Lingually)

Paper 3's finding — declarative rewriting reduces cross-linguistic variance —
has a scope condition. Within English, for Haiku, the original imperative
corpus performs better than the all-declarative rewrite. Some instructions
work better as imperatives for the model that was trained on them.

### 4. E-REG Finding Generalizes

E-REG found register effects are model-dependent. E-PHASE now shows they're
also block-identity-dependent, not dose-responsive. The three-way interaction
(model × register × behavior) is irreducible even within a single language.

### 5. Mutualism Revisited

The session 15 mutualism finding explains why all-declarative underperforms:
some imperative blocks are structurally load-bearing. Rewriting them removes
whatever mutualistic support they provide (likely through coherent register
context). The imperative pile isn't creating competing obligations — it's
creating a coherent authority register that some probes depend on.

## Connection to Prior Work

- **Paper 3 (cross-linguistic):** Declarative rewriting fixes topology
  inversion *across languages*. E-PHASE shows it may *hurt* within the
  training language. The mechanism is different: cross-linguistically,
  declarative avoids register translation ambiguity. Intra-lingually, the
  model already knows the imperative register, and declarative may be
  *unfamiliar* register for system prompts.

- **E-REG:** Found register effects are model-dependent. E-PHASE confirms
  and extends: they're also block-identity-dependent within a single model.

- **Session 15 (mutualism):** Predicted that removing "dead" instructions
  could collapse unrelated behaviors. E-PHASE shows that *rewriting* them
  (not removing) can also collapse behaviors — the register matters, not
  just the presence.

## Design Principle (Updated)

Paper 3's rule was: "Declare facts, don't issue commands" (for cross-linguistic
robustness).

Updated rule: "Declare facts, don't issue commands" works **across languages**
where register translation is ambiguous. **Within the training language**,
preserve the original register — the model has learned to process it.

## What This Opens

1. **Register familiarity hypothesis:** Models perform best on instructions
   in the register they were trained on. Testable by comparing models
   trained on different register distributions.

2. **Pairwise register interactions:** Which specific block pairs cause
   collapses when their registers diverge? The explore-agent ← commit-restrictions
   interaction at density 1 is a candidate for pairwise investigation.

3. **Cross-model replication:** Does the "original beats declarative" finding
   hold for Gemini, DeepSeek, Mistral? Or is it Haiku-specific (again)?

## Data

- Design: `data/ablation/e_phase/e_phase_design.json`
- Results: `data/ablation/e_phase/run_e-phase-haiku-*.json`
- Script: `scripts/run_e_phase.py`
