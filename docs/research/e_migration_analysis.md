# E-MIGRATION: The bomb does not migrate to EA when PA is removed

**Date:** 2026-04-17
**Status:** Complete. v2 replication solid; v2b falsifies the receiver-migration hypothesis as stated.
**Parent:** E-MINIMAL-BOMB (`docs/research/e_minimal_bomb_analysis.md`)
**Model:** `anthropic/claude-haiku-4-5` via OpenRouter, temperature 0.0
**Cost:** ~$0.40 actual (180 probe calls + 180 judge calls); well under $5 cap.

## Question

E-MINIMAL-BOMB v2 (8 blocks, one 10-trial run) reported that the
`commit-restrictions` register bomb drove **PA** — not EA — from
0.970 to 0.150 (Δ = +0.82). We hypothesized the bomb suppresses
whichever Task-family policy block is dominant in context; in v2 PA
happened to be dominant, in Claude Code EA does.

Two things had to be shown:

1. **Replication.** Is the v2 PA drop real, or was it a single-run artefact?
2. **Receiver migration.** If PA is removed from v2 (v2b, 7 blocks), does
   the bomb return to suppressing EA?

## Design

| Condition | Blocks | Bomb | Trials |
|---|---|---|---|
| v2:baseline | 7 (v2 minus bomb) | absent | 15 |
| v2:bomb-present | 8 (v2 full) | present | 15 |
| v2b:baseline | 6 (v2 minus bomb minus PA) | absent | 15 |
| v2b:bomb-present | 7 (v2 full minus PA) | present | 15 |

Probes: `explore-agent-01` (EA), `proactive-agents-01` (PA),
`use-task-for-search-01` (TS). LLM-judge scoring, three trials each at
T=0 (the low within-condition variance is consistent with near-deterministic
judge+generator behavior at this temperature).

Total: 4 conditions × 3 probes × 15 trials = 180 probe calls + 180 judge
calls. Actual spend ~$0.40.

Artifacts:
- Script: `scripts/run_e_migration.py`
- Corpus: `data/prompts/minimal-bomb/v2b_blocks.json`
- Design: `data/ablation/e_migration/e_migration_design.json`
- Raw: `data/ablation/e_migration/run_e-migration-haiku-1891610f.json`

## Results

Means over 15 trials; stdev in parentheses.

| Condition | EA | PA | TS |
|---|---|---|---|
| v2:baseline        | 0.350 (0.000) | 0.960 (0.021) | 0.000 (0.000) |
| v2:bomb-present    | 0.143 (0.018) | 0.150 (0.000) | 0.000 (0.000) |
| v2b:baseline       | 0.203 (0.030) | 0.650 (0.000) | 0.000 (0.000) |
| v2b:bomb-present   | 0.147 (0.013) | 0.100 (0.046) | 0.000 (0.000) |

Baseline → bomb-present deltas (positive = suppression):

| Variant | EA Δ | PA Δ | TS Δ |
|---|---|---|---|
| v2  | +0.207 | **+0.810** | 0.000 |
| v2b | +0.057 | +0.550 | 0.000 |

## v2 replication: tight

Against the original E-MINIMAL-BOMB v2 single-run numbers:

| Probe/Cond | Original (n=10) | Replication (n=15) |
|---|---|---|
| EA v2:baseline      | 0.350 | 0.350 |
| EA v2:bomb-present  | 0.150 | 0.143 |
| PA v2:baseline      | 0.970 | 0.960 |
| PA v2:bomb-present  | 0.150 | 0.150 |

Everything replicates to within 0.01. Within-condition stdev is ≤0.03
for 11/12 per-probe-per-condition slices. The v2 PA drop is **not** an
artefact; the bomb does collapse PA from 0.96 to 0.15 in this 8-block
synthetic prompt. Prior concern that the v2 finding might be noise is
dismissed by these data.

## v2b: the hypothesis as stated is falsified

Removing the `tool-policy-proactive-agents` block from v2 does **not**
return the bomb to suppressing EA. EA drops from 0.203 to 0.147 — a
delta of +0.057, two stdevs of within-condition noise at most, and
starting from a baseline far below the 0.7 interpretability threshold
we use elsewhere. The bomb's suppressive effect on EA is effectively
absent in v2b.

What happens instead is surprising:

- **PA baseline in v2b = 0.650**, despite there being no PA policy block
  in the prompt at all. The model's prior behavior (or the judge's
  tolerance) on the PA probe already produces 65% adherence in a corpus
  that contains only identity, tone, task-management, search, explore-
  agent, and commit-workflow blocks.
- **PA bomb-present in v2b = 0.100**, lower than any other PA cell in
  this experiment. The bomb still drives PA down by 0.55 from the v2b
  baseline, and past the v2:bomb-present level, despite the corresponding
  policy block being absent.

Interpretation: the bomb is not targeting the PA *block*. It is
targeting the PA *behavior* — "launch Task subagents proactively for
parallel sub-investigations." Removing the PA block does not shield the
behavior, because the probe measures the behavior directly and the
bomb's prohibition on `Task` tool usage overrides whatever prior / weak
encouragement the rest of the prompt provides.

## Revised picture

What the bomb actually does on Haiku 4.5 in these minimal synthetic
prompts:

1. **It reliably suppresses the PA probe** across both v2 and v2b,
   whether or not a PA policy block is present. The PA probe measures
   willingness to delegate to `Task` subagents; the bomb contains
   `NEVER use the TodoWrite or Task tools`. That prohibition appears
   to fire as a blanket rule against Task usage, not as a scoped
   "during commit" rule.
2. **It does not produce a large EA drop in these minimal prompts**,
   regardless of whether PA is present as a competing receiver. EA
   baseline never clears 0.4 here, so there is no room for a canonical
   EA-style ~0.8 drop in the first place.
3. **TS is floor-pinned at 0.000** in all four conditions. This probe
   has been essentially non-informative in the minimal-bomb family
   since v1 — worth flagging, but it does not affect the main reading.

The E-MINIMAL-BOMB story ("the bomb migrates between policy blocks") is
the wrong model. A better model:

- The bomb's prohibition (`NEVER use Task tools`) has over-generalized
  reach. Its target is the model's willingness to invoke `Task`,
  regardless of whether that willingness is encoded by an explicit
  policy block or by the model's prior.
- In the full Claude Code prompt the canonical effect shows up as an
  EA drop (EA asks specifically about `subagent_type=Explore`, which is
  a Task invocation). On these minimal prompts the visible collapse
  lands on PA because:
  - PA baseline is already high (near ceiling), so there is room for a
    large drop.
  - EA baseline is suppressed for unrelated reasons (probably the
    synthetic prompt's lack of Claude-Code-specific framing), so EA
    has no room to drop further.
- The v2 PA collapse and the Claude Code EA collapse are plausibly the
  **same mechanism** (Task-tool suppression via over-generalized
  prohibition), manifesting on whichever Task-family probe has the
  headroom to show it.

## What this does and does not say

**Supports:**

- The bomb's reach is Task-family-wide, not explore-agent-specific.
  This is consistent with the original E-MINIMAL-BOMB secondary
  finding, but the mechanism is "over-generalized Task prohibition,"
  not "receiver migration between blocks."
- The v2 PA effect is robust. The hypothesis that it was noise is
  wrong.

**Does not support:**

- "Remove the block, the bomb moves to another block." Removing the PA
  policy block did not move the bomb to EA. The bomb's suppression of
  PA-measured behavior persists *through* the block's removal.

**Flags:**

- PA baseline in v2b is 0.650 with no PA policy block. Either the PA
  probe pattern (parallel sub-investigations) is partially covered by
  the v2b model prior / the remaining blocks (task-management +
  explore-agent + search), or the judge's rubric is loose enough to
  accept reasonable parallel-decomposition answers without an explicit
  delegation policy. Worth inspecting the judge rationales on v2b:baseline
  PA trials before building further experiments on this corpus.
- EA has not shown a canonical (~0.8) drop on *any* minimal synthetic
  prompt (v1, v2, v3, v2b). Whatever in the full Claude Code prompt
  enables EA as the dominant receiver is still unidentified. The three
  blocks in Claude Code that are absent from v2b and present in the full
  prompt in the Task-family orbit — `tool-policy-use-task-for-search`,
  `proactive-agents` procedural variants, richer commit context — are
  candidates but not tested here.

## Implications for cross-family transfer

If the mechanism is "over-generalized Task-tool prohibition," then:

- The v2 prompt at 8 blocks reproduces the mechanism cleanly, just on
  the PA probe rather than the EA probe. For cross-family transfer
  (OLMo-3, Llama-3.1, Qwen-2.5), shipping v2 with **PA as the primary
  probe** is a defensible choice.
- Shipping v2b is not useful — PA baseline is only 0.65, so the PA
  drop available is only ~0.55 rather than ~0.82. That narrows the
  dynamic range for detecting a mechanism that may already be weaker
  on other families.
- Pinning the EA signature back into a minimal prompt remains unsolved
  and is out of scope for this experiment.

## Deliverables

- `scripts/run_e_migration.py` — experimental runner with `--compare`
- `data/prompts/minimal-bomb/v2b_blocks.json` — PA-absent 7-block corpus
- `data/ablation/e_migration/e_migration_design.json`
- `data/ablation/e_migration/run_e-migration-haiku-1891610f.json`
- `docs/research/e_migration_analysis.md` (this document)
