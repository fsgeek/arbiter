# T13: E-PHASE — Phase Transition Mapping

**Date:** 2026-03-28
**Experiment:** E-PHASE (Phase Transition Mapping)
**Model:** Haiku (Phase A)
**Cost:** ~$1.44

## Question
Does imperative register saturation have a critical threshold?

## Answer
No. There is no phase transition and no monotonic density effect.

## Key Findings

1. **No density effect.** Mean adherence oscillates (0.743–0.847) with no
   trend. Z-score of worst step = -1.3 (noise).

2. **Original outperforms all-declarative.** Density 11 (0.841) > density 0
   (0.810). Declarative rewriting hurts Haiku in English.

3. **Block identity dominates.** explore-agent swings 0.15–1.00 based on
   *which* blocks are imperative, not *how many*.

4. **Register familiarity.** Instructions work better in the register the
   model was trained on. Declarative rewriting is unfamiliar register for
   English system prompts.

## Falsified
- Phase transition hypothesis (2a from probability sampling)
- "Declare facts" as universal intra-lingual principle

## Confirmed
- Three-way interaction is irreducible (model × register × behavior)
- E-REG finding generalizes: register effects are block-identity-dependent

## Opens
- Register familiarity hypothesis (training register → optimal instruction register)
- Pairwise register divergence interactions
- Cross-model replication needed

## Data
- `data/ablation/e_phase/`
- `docs/research/e_phase_analysis.md`
- `scripts/run_e_phase.py`
