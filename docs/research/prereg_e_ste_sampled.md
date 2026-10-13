# Pre-registration: E-STE-S — the 2×2 again, sampled (temperature 0.7, 10 trials), all gated models

**Sealed:** 2026-10-13, before any run. Commit = seal; the hook stamps it.
**Author:** Project Arbiter instance (Claude Fable 5.1).
**Why:** E-STE round 2 (`RESULT_e_ste.md`) showed the temperature-0 protocol produced greedy-decoding
fixed points that read as catastrophes. Round 2 was Haiku-only and descriptive. This is the same 2×2
measured the way it should have been, across the models, with a statistic that uses the trial-level
distribution. It is the first sampled-temperature replication in the suite; its shape is what Papers 3
and 4 will need for every temperature-0 claim they keep.

## Design
Variants: `original`, `declarative`, `ste_imp`, `ste_decl` (texts unchanged, `scripts/run_e_ste.py`).
Languages: en, zh, fr, es. Models: haiku `anthropic/claude-haiku-4.5`, deepseek `deepseek-chat-v3-0324`,
mistral `mistral-medium-3.1`, gemini `google/gemini-3.7-flash` (gate applied per model, below).
Probes: the target `probe-commit-restrictions-01` plus **6 controls drawn by `random.Random(20261013)`**
from the other 21 (`data/ablation/e_ste_sampled_controls.json`, written at seal). **10 trials at
temperature 0.7**, judge as in the protocol (same model, `_call_llm`, provider-default temperature).
Runner: `scripts/run_e_ste_temp.py --probes sampled --experiment e-ste-sampled`, with the 2026-10-13
runner fix: empty replies fail loudly and every failure is recorded in the run file.
Calls: 7 probes × 10 trials × 4 variants × 4 languages × 4 models = 4,480 plus judge calls.

Validity gate, per model: valid results / expected ≥ 0.95 on the **target probe** (a model may lose
controls to tool-call attempts and still be gated in for the target; it is then reported with the
number of controls it kept).

## Statistics (trial-level; no temperature-0 cell is a single observation here)
- Cell mean = mean of 10 trials. Spread(variant, model) = population variance of the 4 cell means.
  Pooled spread = mean over gated models.
- Difference D(X→Y) = Spread(X) − Spread(Y), pooled. **Bootstrap:** resample trials within every cell
  (10,000 draws), recompute D; report the 95% percentile interval. "Supported" = the interval excludes 0.
- Level(variant) = mean of the 16 cell means, with the same bootstrap.
- Controls: for each control probe, |D| for each pair; report the max and mean; a pair "moves the
  neighbours" if any control's bootstrap interval for |D| sits above 0.01.

## Predictions (sealed; the author's updated beliefs after round 2, side stated)
- **P1 — FOR the register account (reversing my E-STE P1).** D(original→declarative) > 0 with the
  bootstrap interval excluding 0: declarative mood reduces cross-language spread under sampling.
- **P2 — FOR mood within controlled shape.** D(ste_imp→ste_decl) > 0, interval excluding 0.
- **P3 — AGAINST the temperature-0 result.** D(original→ste_imp) has an interval that includes 0: the
  "nine-fold increase" does not exist under sampling.
- **P4 — Shape is neutral-to-helpful given mood.** D(declarative→ste_decl) ≥ 0 (point estimate), interval
  may include 0.
- **P5 — Level.** Declarative variants have higher Level than imperative ones by ≥ 0.05 pooled (the
  deepseek/mistral "level fix" seen at temperature 0 survives sampling).
- **P6 — Controls unmoved** for every pair.

## Decision rules
- P1 supported → Paper 3's register account is restated as a *sampled* result on October models, with
  Spread numbers replacing the March 81%/5.9σ, which are retained as a March-snapshot measurement.
- P1 not supported → Paper 3's spread claim is withdrawn in the journal version; the level claim (P5)
  stands or falls on its own.
- P3 supported (interval includes 0) → `RESULT_e_ste.md`'s temperature-0 "9×" is formally retired.
- Every outcome is reported with its interval; nothing is rerun to check.

## Blind spots
Still one block, one prompt. The judge is the model under test. Model ids drift. 10 trials is the
floor for a bimodal cell, not a comfortable number.

## Cost
~4,480 calls + ~4,480 judge calls (the target and some controls are `llm_judge`); under $25 by list price.

## Deviations log
(append-only; empty at seal)

- 2026-10-13, during the runs (mistral complete 1120/1120; haiku 14/16, deepseek 7/16 cells; no
  scores analysed): gemini's process stopped after 5 of 16 cells. Cause: three of the six control
  probes (no-new-files, no-time-estimates, no-overengineering) fail on every trial with
  `MALFORMED_FUNCTION_CALL` (now recorded in each run file), and the runner's fail-stop fires when
  a cell's first five completions are all failures. The target probe is 50/50 in the finished cells.
  Fix: the runner script now skips finished cells and retries a cell up to 3× on the fail-stop
  (nothing is saved on exception, so a retry is a clean re-run of that cell, not a re-draw of
  trials). Gemini relaunched for the remaining 11 cells. Its control set is reported as kept/lost.
