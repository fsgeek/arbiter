# Session 16 — Phase 1 Pairwise Ablation + Review Findings

Date: 2026-03-20
Author: Claude Opus 4.6 (session 16)

## What Happened

### Probe Calibration (Gate 3 from ranked options)
- Compared hand-authored (phase0_battery.json) vs auto-generated (v6_fixed_heuristic)
- **6 of 22 generated probes systematically broken** — two failure modes:
  1. **Adversarial inversion** (3 probes): Generator made user explicitly request forbidden
     behavior, then expected refusal. Tests pushback, not restraint.
  2. **Cross-probe contradiction** (3 probes): commit-restrictions probe bans git diff/git log,
     which commit-workflow probe requires.
- Both failure modes are instances of the phenomenon Arbiter detects. See T5 cairn.
- **Decision**: Use hand-authored battery for Phase 1 (validated by 3 Phase 0 runs).

### Three-Reviewer Code Review
- Three subagents with different system prompts reviewed run_phase1.py:
  - **Code reviewer**: API signature bugs, silent empty tensor
  - **Principled reviewer**: Non-determinism, reproducibility, closure safety
  - **Integrity auditor**: Anti-conservative p-values, no FDR correction, self-eval bias,
    zero-variance trials, empty data files, test design-to-pass patterns
- **Finding**: Non-overlapping categories from each reviewer. See T6 cairn.
  Same model, different instructions, different blind spots. Validates ensemble evaluation.

### Critical Bugs Found and Fixed
1. `from_ablation_run()` silently ignored Phase 1 configs — Phase 0-only code path
2. `pairwise_interactions()` called with wrong arity (0 args, needs 4)
3. Covering array non-deterministic (random.randint without seed)
4. p-value computation used normal approximation — 2.6x to 257x anti-conservative at n=3
5. No multiple testing correction (484 tests × α=0.05 = 24 expected false positives)

### Fixes Applied
1. `tensor.py`: `from_ablation_run()` now collects Phase 1 results
2. `run_phase1.py`: Passes correct args to `pairwise_interactions()`
3. `covering_array.py`: Seeded RNG (deterministic from problem params)
4. `tensor.py`: Replaced normal CDF with proper t-distribution via regularized
   incomplete beta function (Lentz continued fraction). Verified against known values.
5. `tensor.py`: Added Benjamini-Hochberg FDR correction, default on for `main_effects()`
6. Covering array persisted to JSON for reproducibility

### Phase 1 Results
- 792 API calls, 11 covering array configs + 1 baseline, Haiku 4.5
- Run: data/ablation/phase1_results/run_phase1-haiku-94ad6f79.json

#### Headline: Cooperation Dominates
- **143 synergistic pairs, 39 antagonistic, 49 negligible**
- Every significant interaction (|effect| > 0.10) is SYNERGISTIC
- Instructions reinforce each other — removing pairs hurts more than sum of individuals

#### Hub Nodes
- **no-time-estimates**: 6 of top 20 interactions. Moderate solo effect (-0.045),
  outsized cooperative contribution.
- **todowrite-importance-repeated**: 7 of top 20. Same pattern.
- These blocks maintain something about behavioral posture that semantically
  unrelated blocks depend on.

#### Top Pairwise Interactions
| Block A | Block B | Effect | Type |
|---------|---------|--------|------|
| professional-objectivity | todowrite-importance-repeated | +0.114 | Synergy |
| tone-text-only-comms | no-time-estimates | +0.113 | Synergy |
| no-time-estimates | tool-bash-commit-workflow | +0.106 | Synergy |
| no-time-estimates | tool-policy-dedicated-tools | +0.105 | Synergy |
| no-time-estimates | tool-policy-parallel-calls | +0.105 | Synergy |
| professional-objectivity | no-time-estimates | +0.104 | Synergy |
| tone-emoji | todowrite-importance-repeated | +0.103 | Synergy |

#### Phase 0 Key Pairs Revisited
- concise × search-tool: +0.073 (Phase 0 suppression was main effect, not interaction)
- todowrite × commit-restrictions: +0.022 (small, confirms main effect interpretation)

#### Baseline Drift
Baselines shifted from Phase 0: code-references 0.000→0.500, use-task-for-search
0.233→0.500, commit-restrictions 0.850→1.000. Either model updated on OpenRouter
or LLM-judge variance is significant. This is itself data about measurement stability.

## Cross-Project Thread (from Tony relay)
- Another Claude instance noticed isomorphism between Arbiter hub-node pattern and
  Hamut'ay IFN-as-hub pattern in tensor components
- Claim: "Structured representations given to transformers exhibit emergent cooperative
  topology that nobody designed"
- **My assessment**: Suggestive but premature. Need:
  (a) Permutation test for hub significance (is 2-node hub concentration non-random?)
  (b) Direct comparison with Hamut'ay pairwise data
  (c) Non-English system prompt ablation for cross-linguistic test
- The cooperative topology may be artifact of competent iterative engineering
  (artificial selection for mutual compatibility), not untrained emergent property
- Functional vs social diffusion question: corpus is entirely English, same professional
  ecosystem. "Independent convergence" claim needs cross-linguistic evidence.

## Open Questions
1. Is hub concentration statistically significant? (permutation test needed)
2. Can the methodology redesign prompts for resilience? (distribute hub load)
3. Non-English system prompts — DeepSeek, Qwen, Baichuan have Mandarin-origin tools
4. Separate judge model from subject model (self-evaluation bias)
5. Higher-order confounding in covering arrays (each row removes ~11 blocks)
6. Two empty Phase 0 run files — provenance gap

## Artifacts Created
- docs/cairn/T5_20260320_generator_as_specimen.md
- docs/cairn/T6_20260320_three_reviewers.md
- scripts/run_phase1.py
- data/ablation/phase1_results/run_phase1-haiku-94ad6f79.json
- data/ablation/phase1_results/phase1_covering_array.json
- scripts/codex_review_phase1.md (for Codex independent review)
