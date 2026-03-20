# autoresearch — prompt ablation

This is an experiment to have the LLM do its own research on prompt interference.

Adapted from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch).

## Setup

To set up a new experiment run, work with the user to:

1. **Agree on a run tag** (e.g. `mar19-suppression`).
2. **Verify baseline exists**: Check that `data/ablation/autoresearch/baseline_summary.json` exists. If not, run: `python scripts/autoresearch.py baseline --model haiku`
3. **Read the in-scope files**:
   - `scripts/autoresearch.py` — the experiment runner. Do not modify.
   - `data/ablation/phase0_analysis.md` — existing Phase 0 results. Read this first.
   - `data/ablation/phase0_battery.json` — the probe battery (read-only).
   - `data/prompts/claude-code/v2.1.50_blocks.json` — the block corpus.
4. **Confirm and go**.

## What you CAN do

- Modify the block corpus (`v2.1.50_blocks.json`): remove blocks, reorder blocks, merge blocks, edit block text. This is the `train.py` equivalent.
- Run experiments: `python scripts/autoresearch.py run --model haiku --tag "description"`
- Read results: `python scripts/autoresearch.py log`

## What you CANNOT do

- Modify `autoresearch.py`. It is read-only.
- Modify the probe battery. The probes are the ground truth metric.
- Modify the scoring methods. The evaluation harness is fixed.

## The goal

**Reduce interference density while maintaining adherence on priority probes.**

Lower interference_density is better. Higher mean_adherence is better.

## Priority probes (must not regress)

These probes are load-bearing for the behaviors that matter most:
- `probe-commit-restrictions-01` (baseline: 0.85)
- `probe-no-overengineering-01` (baseline: 1.00)
- `probe-dedicated-tools-01` (baseline: 1.00)
- `probe-read-first-01` (baseline: 0.95)

## Known dead or miscalibrated probes

These scored 0.00 at baseline — changes here don't count as regressions:
- `probe-code-references-01` (never adopted)
- `probe-concise-01` (probe miscalibrated, not block failure)

## Known findings from Phase 0

Use these to guide your experiments:

1. **Biggest suppression**: Removing `tone-concise` improves `use-task-for-search` from 0.23 to 1.00. The conciseness instruction actively suppresses tool-use compliance.

2. **Most fragile instruction**: `commit-restrictions` is suppressed by 8 different blocks. It receives the most interference pressure of any instruction.

3. **Structural dependencies**: Removing `no-time-estimates` destroys `no-new-files` (1.0 -> 0.0). This is not semantic — it's structural. Be cautious with removals.

4. **Dominant pattern is mutualism**: 40 large negative effects vs 2 large positive. Most blocks hold each other up. Removal is more dangerous than expected.

5. **Dead blocks** (main effect < 0.04): `commit-workflow` (0.034), `text-only-comms` (0.032). Candidates for removal, but verify structural dependencies first.

## Simplicity criterion

All else being equal, fewer blocks is better. A small interference reduction from removing a block is a win (simpler prompt, less attention budget consumed). But a removal that triggers cascading dependency failures is not worth it, even if it reduces interference density on paper.

## The experiment loop

LOOP FOREVER:

1. Read the current state: `python scripts/autoresearch.py log`
2. Propose an edit to the block corpus based on findings so far.
3. Make the edit to `v2.1.50_blocks.json`.
4. Run: `python scripts/autoresearch.py run --model haiku --tag "description of edit"`
5. Read the decision: the script prints KEEP or DISCARD with reasons.
6. If KEEP: the edit stays. Move to next experiment.
7. If DISCARD: revert the corpus edit. Move to next experiment.
8. **NEVER STOP**. The human may be away. Keep running experiments until interrupted.

## Experiment ideas (starter list)

- Remove `text-only-comms` (lowest main effect, likely dead)
- Remove `commit-workflow` (second-lowest, likely dead)
- Remove `tone-concise` (biggest suppressor of tool-use compliance)
- Reorder blocks: move `commit-restrictions` to end of prompt (recency bias should help)
- Merge the two TodoWrite blocks into one (reduce redundancy)
- Remove `code-references` (baseline 0.00, instruction never worked)
