# Probe Generation Stability Analysis

Date: 2026-03-19
Author: Claude Opus 4.6 (session 16)

## Experiment

Generated 5 probe batteries (v1-v5) from the same block corpus using the
same LLM (Haiku 4.5) and generation prompt. Measured inter-battery agreement
for `not_contains` pattern sets using Jaccard similarity.

v1 used original generation prompt (no adversarial guidance, no judge_criteria).
v2-v5 used improved prompt (adversarial temptation, judge_criteria for llm_judge).

## Key Finding: Pattern Stability is Near-Zero for Behavioral Prohibitions

| Probe | Jaccard | Core/Total | Verdict |
|-------|---------|------------|---------|
| doing-tasks-read-first | 0.00 | 0/64 | **Unstable** — must use llm_judge |
| no-time-estimates | 0.00 | 0/71 | **Unstable** — must use llm_judge |
| tone-no-colon-before-tools | 0.02 | 0/70 | **Unstable** — borderline |
| doing-tasks-no-overengineering | 0.05 | 0/67 | **Unstable** — must use llm_judge |
| tone-no-new-files | 0.07 | 0/61 | Marginal — some consensus exists |
| doing-tasks-no-compat-hacks | 0.12 | 2/58 | Marginal — `// removed` and `// deprecated` stable |
| tone-emoji | 0.13 | 0/52 | **Stable enough** — emoji are concrete tokens |
| tool-bash-commit-restrictions | 0.13 | 2/63 | **Stable** — `TodoWrite` (5/5), `--no-edit` (4/5) |

## Interpretation

`not_contains` scoring is reliable when:
- The violation is a concrete surface token (emoji, specific tool names, git flags)
- The violation space is small and enumerable

`not_contains` scoring is unreliable when:
- The violation is a behavioral choice (proposing edits without reading, giving time estimates)
- The violation can manifest in many surface forms

## Changes Made

1. **Scoring method heuristic** (`probe_generator.py`): Now only assigns `not_contains`
   when the instruction text contains concrete surface markers (emoji, colon, git flags,
   TodoWrite, etc.). Behavioral prohibitions default to `llm_judge`.

2. **Judge criteria** (`probe_generator.py`): `llm_judge` probes now generate
   `judge_criteria` with concrete score anchors.

3. **Judge prompt** (`probe.py`): `build_judge_prompt()` now includes `judge_criteria`
   from `scoring_params` when present. Previously this field was dead data in
   hand-authored probes.

4. **Adversarial temptation** (`probe_generator.py`): Generation prompt now instructs
   the LLM to create scenarios where violating the instruction is the natural/easy/
   helpful thing to do.

## Implications for Paper

- Probe generation stability should be reported as a reliability bound
- Inter-battery variance is a confidence interval on the tensor, not a bug
- `not_contains` vs `llm_judge` tradeoff: cost vs stability
- Consensus patterns (appear in >= 2/5 batteries) are the robust signal for
  `not_contains` probes

## Data

- `generated_battery.json` (v1, pre-fix)
- `generated_battery_v2.json` through `generated_battery_v5.json` (post adversarial fix)
- `generated_battery_v6_fixed_heuristic.json` (post heuristic fix, recommended)
