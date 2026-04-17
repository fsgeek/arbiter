# E-MINIMAL-BOMB: Synthetic minimal prompt fails to reproduce the EA bomb signature

**Date:** 2026-04-17
**Status:** Complete. Null result on primary criterion; surprising secondary finding.
**Parent:** E-PHASE / E-PHASE-CONFIRM (block-specific `commit-restrictions` register bomb on the Claude Code prompt)
**Model:** `anthropic/claude-haiku-4-5` via OpenRouter
**Cost:** ~$0.36 total (three runs × 120 API calls @ $0.12 each)
**Budget remaining:** well within $5 expected / $10 hard cap.

## Question

Before shipping the `commit-restrictions` register bomb to cross-family models (OLMo-3, Llama-3.1, Qwen-2.5), we need a minimal synthetic system prompt that isolates the bomb from Claude-specific prompt shape. Target: 4–6 blocks, reproduces EA drop from ~0.8+ to ~0.4 or below on Haiku 4.5.

## Design

Three corpus variants, 10 trials per probe per condition, probes =
`explore-agent-01` (primary), `proactive-agents-01`,
`use-task-for-search-01` (signature confirmation).

| Variant | Blocks | Rationale |
|---|---|---|
| v1 | 6 | Minimum viable set (identity, tone, search policy, explore-agent, commit-workflow, commit-restrictions bomb) |
| v2 | 8 | v1 + `task-management` + `proactive-agents` policy blocks (extra policy blocks for contextual ballast) |
| v3 | 6 | Same as v1 but bomb explicitly names "Explore subagent" and "Task subagent" as prohibited (different prohibition object) |

Corpora: `data/prompts/minimal-bomb/v{1,2,3}_blocks.json`
Script: `scripts/run_e_minimal_bomb.py`
Raw data: `data/ablation/e_minimal_bomb/run_*.json`

## Results

| Condition | EA | PA | TS |
|---|---|---|---|
| cc:all-decl (Claude Code anchor) | 1.000 | 0.783 | 0.500 |
| cc:only-cr-imp (CC bomb-present) | 0.200 | 0.150 | 0.000 |
| mb:v1:baseline | 0.727 | 0.020 | 0.250 |
| mb:v1:bomb-present | 0.850 | 0.135 | 0.500 |
| mb:v2:baseline | 0.350 | 0.970 | 0.000 |
| mb:v2:bomb-present | 0.150 | 0.150 | 0.000 |
| mb:v3:baseline | 0.727 | 0.020 | 0.400 |
| mb:v3:bomb-present | 0.935 | 0.840 | 0.000 |

EA deltas (baseline → bomb-present):

- cc: **+0.800** (reference)
- v1: −0.123 (bomb *raises* EA)
- v2: +0.200 (direction right; baseline too low to interpret)
- v3: −0.208 (bomb *raises* EA)

## Primary finding (null)

**None of v1/v2/v3 reproduce the EA bomb signature on Haiku 4.5.** The minimal synthetic context is insufficient. Two of three variants showed EA *increasing* when the bomb was added; the one variant with directionally-correct EA drop (v2) had a baseline EA of 0.350, far below the 0.7 interpretability threshold.

Stopped after two structured variations per methodology cap. Did not iterate further.

## Surprising secondary finding: the bomb migrates to PA in v2

In v2 (which added an explicit `proactive-agents` policy block), the bomb drove **PA** — not EA — from 0.970 → 0.150. That drop of +0.82 closely matches the +0.80 drop the bomb produces on EA in the full Claude Code prompt. The bomb absolutely fires in v2; it just fires on a different block than it does in Claude Code.

This suggests:

- The bomb's suppressive effect is **not uniquely attached to `tool-policy-explore-agent`.** E-PHASE-CONFIRM already showed the bomb is block-specific on the sender side (`commit-restrictions` specifically, not any lone imperative). E-MINIMAL-BOMB-v2 now hints the *receiver* is whichever Task-related policy block is most salient given the surrounding prompt.
- In the full Claude Code prompt (21 blocks, 11 procedural), EA happens to be the most visible receiver. In v2 (8 blocks with PA declaration immediately above EA), PA absorbs the interference instead.
- If this holds up, the phenomenon we've been measuring is "bomb suppresses Task-family policy" rather than "bomb suppresses explore-agent specifically" — the probe battery has been measuring the most collapsable block rather than the only collapsable block.

This is a flag, not a claim. It is based on a single 10-trial observation in a 60-result run. Any follow-up should (a) re-run v2 to confirm the PA drop replicates, and (b) add a PA-absent variant to test whether removing PA from v2 returns the interference to EA.

## Shipping implication

A minimal synthetic bomb suitable for cross-family transfer tests has **not** been produced by E-MINIMAL-BOMB. Shipping v1/v2/v3 as-is to OLMo-3/Llama-3.1/Qwen-2.5 would not be a clean test of the mechanism, because the bomb does not fire on EA in these prompts even on Haiku where we know the mechanism exists.

Options for continued work (out of scope for this experiment):

1. Re-run v2 to confirm PA drop replicates, then use **PA** as the cross-family probe target instead of EA.
2. Scale v2 up (add 2–4 more declarative procedural blocks) to see at what block count EA becomes the collapsable receiver again. This would bracket the "receiver migration threshold".
3. Accept that a fully minimal bomb may not exist and ship a mid-size (~12 block) partially-synthetic prompt whose declarative blocks are semantically generic but preserve the procedural density ratio from Claude Code.

## Deliverables summary

- Script: `scripts/run_e_minimal_bomb.py` (supports `--variant {v1,v2,v3}`, `--compare`)
- Corpora: `data/prompts/minimal-bomb/v{1,2,3}_blocks.json`
- Raw data: `data/ablation/e_minimal_bomb/run_e-minimal-bomb-{,v2-,v3-}haiku-*.json`
- Designs: `data/ablation/e_minimal_bomb/e_minimal_bomb{,_v2,_v3}_design.json`
- This analysis: `docs/research/e_minimal_bomb_analysis.md`
