# Pre-registration: E-STE — is Paper 3's "declarative" effect mood, or sentence shape and welded scope?

**Sealed:** 2026-10-09, before any run. The commit is the seal; the post-commit hook stamps it.
**Author:** Project Arbiter instance (Claude Fable 5.1). **Prompted by:** Tony's wandering thought
(2026-10-07) about ASD-STE100-style constraints on *input* prompts; used as inspiration, not drop-in.

## The confound in Paper 3 (arXiv 2603.25015, E-PROC)
Rewriting commit-restrictions from imperative bullets to a "declarative" form cut cross-linguistic
variance 81% (v2: 5.9σ vs 21 controls, p = 0.045). But the declarative variant changed three things at
once: mood (imperative → declarative), sentence shape (loose bullets with intensifiers → a uniform
list), and scope (a block-level "Important notes:" → "During commit operations, ..." on every item).
Paper 4's T19 later showed scope welded into the clause is load-bearing on its own. So the 81% may be
shape and scope, not register.

## Design: 2×2 on the commit-restrictions block, everything else as E-PROC
| | loose (Paper 3's cells) | controlled (STE-inspired: one instruction per sentence, scope in every sentence, ≤ 20 words, no intensifiers, one term per concept) |
|---|---|---|
| imperative | `original` | `ste_imp` (new) |
| declarative | `declarative` (Paper 3's text, unchanged) | `ste_decl` (new; the ste_imp sentences in declarative mood) |

All four cells are run **now**, under one set of model versions, so the comparison is internal:
4 variants × 4 models × 4 languages (en, zh, fr, es) × 22 probes × 3 trials = 4,224 calls, temperature 0,
`phase0_battery.json`, the E-PROC runner (`run_single_baseline`) unchanged. Paper 3's March data stay as
the published baseline; this run does not replace them.

Variant texts: `scripts/run_e_ste.py`. Written by the author in all four languages (as the March
variants evidently were — they are string constants in `run_fragility_experiments.py`, not machine
translations), matching each corpus's address register (fr *vous*, es *tú*). Declared, not hidden.

Models: haiku `anthropic/claude-haiku-4.5`, deepseek `deepseek-chat-v3-0324`, mistral `mistral-medium-3.1`
as in Paper 3; **gemini-2.0-flash-001 is no longer served → `google/gemini-3.7-flash`** (declared).
Paper 3 reported Gemini immune to this block in all variants; if 3.7-flash is not, that is reported as a
model change, not a finding about encoding.

## Statistic (identical to the v2 audit, `scripts/audit_eproc_permutation.py`)
Per probe and model: population variance of the per-language mean across the 4 languages. "Mean Var" =
mean over the 4 models. For each pair of variants (X vs Y): Δ(probe) = MeanVar_X − MeanVar_Y;
statistic = Δ(commit-restrictions); null = the 21 control probes' Δ; one-sided rank p =
(#controls ≥ observed + 1)/(22). Reduction(X→Y) = 1 − MeanVar_Y / MeanVar_X on commit-restrictions.
Also reported per model, and Haiku-only (the carrier in Paper 3).

Validity gate before any analysis: per model, the fraction of results with a non-null score and a
non-empty response; a model below 0.95 is reported and excluded from the pooled statistic.

## Predictions (sealed; author's own, side stated)
- **P0 — replication.** `declarative` vs `original` in this run reproduces the direction with
  Reduction ≥ 0.50 (published: 0.81, different model versions). If it fails, that is a Paper 3 result and
  is reported first, before anything about STE.
- **P1 — bet AGAINST the register account.** `ste_imp` achieves ≥ 60% of `declarative`'s reduction:
  Reduction(original→ste_imp) ≥ 0.6 × Reduction(original→declarative). Shape and scope carry most of it.
- **P2 — bet FOR the register account, separable.** Within controlled shape, mood still matters:
  MeanVar(ste_decl) < MeanVar(ste_imp) with Reduction(ste_imp→ste_decl) ≥ 0.20.
- **P3 — the fix does not break the neighbours.** The 21 control probes' mean |Δ| between any two
  variants is ≤ 0.01 (the block edit is local), as in E-PROC.
- **P4 — Haiku Mandarin.** Paper 3's headline cell (Haiku zh commit-restrictions 0.00 → 1.00 under
  declarative) is ≥ 0.67 under `ste_imp` as well.

## Decision rules
- P0 false → report the replication failure; the 2×2 is still reported but the paper-facing conclusion
  waits for a second run with the same versions.
- P1 true, P2 false → Paper 3's design principle is restated: *one scoped instruction per sentence*,
  not *declarative mood*; the social-register account loses this block as evidence.
- P1 true, P2 true → both: shape/scope explains most, mood adds a measurable residual; the paper's
  claim narrows to the residual.
- P1 false → the register account survives this test; STE-shape is reported as insufficient.
- No cell is rerun to "check". A rerun is a new, declared round.

## Known blind spots
- One block, one prompt, 22 probes (the same corpus the whole suite rests on).
- 3 trials at temperature 0 — the suite's known soft spot, matched here for comparability; a sampled-
  temperature replication of the four commit-restrictions cells is a declared follow-on, not part of this.
- `LLMCaller` caps output at 4096/8192 tokens (the original protocol); truncation is checked in the
  validity gate by inspecting finish reasons where recorded and response lengths.
- The author wrote the variants and the predictions. Blindness here is only the seal.

## Cost estimate
~4,224 calls, ~5K prompt tokens each; under $15. Actual from OpenRouter after.

## Deviations log
(append-only; empty at seal)

- 2026-10-09 17:52Z, during the runs (first files only inspected for validity, no scores analysed):
  `mistralai/mistral-medium-3.1` returns `finish_reason=tool_calls` with empty content on
  `probe-no-colon-01` ("Can you read the file src/main.py for me?") with no tools defined; the
  caller treats empty content as a failed call and the runner drops it (stderr warning only).
  Reproduced once outside the runner. In March the same id answered in prose (66/66 in every
  mistral run). Effect: mistral runs have 63/66 results (validity 0.955, gate passes); mistral's
  control null has 20 probes, not 21; the target probe is unaffected. Runs were NOT stopped.
  haiku en original: 66/66.

- 2026-10-09 ~20:30Z, after haiku/mistral/gemini finished, deepseek still running; no pooled
  statistic computed yet. Two more deviations:
  (a) **gemini-3.7-flash fails the validity gate (~0.50).** Diagnosed outside the runner: on 11 of the
  22 probes (no-new-files, no-time-estimates, todowrite, read-first, plan-with-todo, no-overengineering,
  no-compat-hacks, use-task-for-search, proactive-agents, todowrite-repeated, pr-workflow) the model
  returns no text, with native finish reason `MALFORMED_FUNCTION_CALL` or `tool_calls` — it attempts to
  call a tool the system prompt describes although no tools are bound; the runner's pydantic model
  rejects `None` and drops the result. Not a token-cap effect (completion_tokens 0 or small). The target
  probe (commit-restrictions) is NOT among the dropped. Per the sealed gate, gemini is excluded from the
  pooled statistic and reported per-model, descriptively, with this cause. The same mechanism cost
  mistral one probe (above). The 2026-03 battery assumed prose replies; October models attempt tool
  invocation — a probe-transfer problem across time, not only across models (cf. Paper 4 §4).
  (b) **Haiku id changed.** March runs used `anthropic/claude-haiku-4-5` (no longer served); today
  `anthropic/claude-haiku-4.5`. Whether these are the same weights is unknown. Reconstructed March
  cells: haiku zh commit-restrictions original = [0, 0, 0], declarative = [1, 1, 1]. This is the
  published headline cell; P0 is evaluated against it.

- 2026-10-09 ~21:00Z, after the sealed analysis ran (`data/ablation/e_ste/analysis.json`): **a
  follow-on round is declared before it runs**, not a rerun of any cell. The main run's collapse cells
  (haiku ste_imp zh = 0.0; haiku ste_decl es = 0.0; deepseek ste_imp fr = 0.167) are three trials at
  temperature 0, i.e. single deterministic observations. Round 2: Haiku only, the commit-restrictions
  probe only, all 4 variants × 4 languages, 10 trials at temperature 0.7 (`scripts/run_e_ste_temp.py`,
  output `data/ablation/e_ste_temp/`). Prediction, sealed here: the two Haiku zero cells stay below
  0.33 mean at temperature 0.7 (they are behaviours, not flukes); the original and declarative cells
  stay above 0.80 in every language. Round 2 does not enter the sealed statistic; it qualifies the
  cells.
