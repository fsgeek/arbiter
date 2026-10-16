# RESULT: E-STE — Paper 3's declarative effect does not replicate on today's Haiku, and STE-shaped rewrites make cross-linguistic variance worse

**Run:** 2026-10-09 (main run 17:13–20:40Z, 64 runs; round 2 after). **Prereg:** `prereg_e_ste.md`
(sealed 28fc604, stamped 315a053; four deviations logged mid-run, each stamped). **Data:**
`data/ablation/e_ste/` (64 run files with every raw response and judge response; `analysis.json`),
`data/ablation/e_ste_temp/` (round 2). **Analysis:** `scripts/analyze_e_ste.py` — the v2 audit statistic.
**Validity gate:** haiku 1.000, deepseek 1.000, mistral 0.955 pass; **gemini-3.7-flash 0.39–0.50 fails**
(no-text replies with native finish `MALFORMED_FUNCTION_CALL` / `tool_calls` on 11 of 22 probes; the
target probe is not among them). Pooled statistics use the three gated models; Gemini is reported
descriptively.

## The 2×2, pooled over the three gated models (commit-restrictions cross-linguistic MeanVar)
| | loose | controlled (STE-inspired) |
|---|---|---|
| imperative | `original` **0.0133** | `ste_imp` **0.1167** |
| declarative | `declarative` **0.0207** | `ste_decl` **0.0781** |

| pair | Δ (x − y) | reduction | rank p (one-sided, reduction) | controls mean \|Δ\| |
|---|---|---|---|---|
| original → declarative | −0.0074 | **−0.55** (variance up) | 0.714 | 0.0062 |
| original → ste_imp | −0.1034 | −7.76 | 1.000 | 0.0079 |
| original → ste_decl | −0.0648 | −4.86 | 1.000 | 0.0113 |
| ste_imp → ste_decl | +0.0386 | **+0.33** | **0.048** | 0.0068 |

A rank p of 1.000 means the commit probe's Δ was the most negative of all 21 probes: the STE rewrites
raised the target's cross-linguistic variance more than any control probe moved, in either direction.

## Sealed predictions vs. observed
- **P0 — replication — FAILED.** Sealed: `declarative` cuts variance ≥ 50% vs `original`. Observed: variance
  *rose* 55% (0.0133 → 0.0207). The reason is in the cells: today's Haiku has essentially no
  cross-linguistic variance on the original block (0.0001; zh = 1.00, where the March run gave 0.00 ×3,
  reconstructed from `data/ablation/cross_linguistic/run_xling-zh-haiku-14bdf492.json`). The Mandarin
  collapse that Paper 3's headline cell fixed is absent, so there is nothing for the declarative rewrite
  to fix, and it is slightly worse (zh 0.93, es 0.90). deepseek: 0.0191 → 0.0191. mistral: 0.0208 → 0.0417.
  Per the decision rule this is reported first, and the paper-facing conclusion waits for a second run
  with the same versions. **Caveat that matters:** the Haiku id changed (`claude-haiku-4-5` → `claude-haiku-4.5`);
  whether the weights are the same is unknown. This is the world moving, not the March measurement being
  wrong — and it is a replication failure that Paper 3's next version must carry: the effect was
  snapshot-specific.
- **P1 — bet against the register account — not evaluable as sealed, and dead in substance.** The ratio
  "ste_imp gets ≥ 60% of declarative's reduction" has a negative denominator. In substance: the
  STE-shaped imperative rewrite (one scoped instruction per sentence, no intensifiers) made the block
  *worse* by a factor of ~9 in cross-linguistic variance. Shape and welded scope did not carry Paper 3's
  effect; they created a new failure.
- **P2 — bet for the register account within controlled shape — WON, narrowly and with a twist.**
  `ste_decl` has 33% less variance than `ste_imp`, rank p = 0.048 (the sealed threshold was 20%). Pooled,
  mood matters inside STE shape. But per model: haiku 0.1835 → 0.1875 (no change: the declarative mood
  moved the collapse from Mandarin to Spanish); deepseek 0.125 → 0.047; mistral 0.042 → 0.000. The win
  is deepseek's and mistral's, not Haiku's, and Haiku was Paper 3's carrier.
- **P3 — controls unmoved (mean |Δ| ≤ 0.01) — 2 of 4 pairs.** original→declarative 0.0062 and
  original→ste_imp 0.0079 pass; original→ste_decl 0.0113 and declarative→ste_decl 0.0143 do not (max
  single-control |Δ| 0.054). The ste_decl text moves neighbours slightly; the block edit is mostly local.
- **P4 — Haiku zh ≥ 0.67 under ste_imp — LOST.** 0.00 (three trials). The exact cell Paper 3 repaired
  with the declarative rewrite is re-broken by the STE-imperative rewrite.

## Cells (per-language mean of 3 trials; the whole result is visible here)
| variant | haiku en/zh/fr/es | deepseek | mistral | gemini (gate-failed) |
|---|---|---|---|---|
| original | 1.00 / **1.00** / 0.98 / 0.98 | 0.67 / 0.50 / 0.33 / 0.33 | 0.83 / 0.50 / 0.50 / 0.50 | 1 / 1 / 1 / 1 |
| declarative | 1.00 / 0.93 / 0.97 / 0.90 | 1.00 / 1.00 / 0.83 / 0.67 | 1.00 / 0.83 / 0.50 / 1.00 | 1 / 1 / 1 / 1 |
| ste_imp | 1.00 / **0.00** / 0.97 / 1.00 | 1.00 / 1.00 / **0.17** / 0.50 | 1.00 / 1.00 / 0.50 / 0.83 | 1 / 0.83 / 1 / 1 |
| ste_decl | 1.00 / 1.00 / 1.00 / **0.00** | 1.00 / 0.50 / 1.00 / 0.67 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / — |

Note what `declarative` did for deepseek and mistral: it raised the *level* (deepseek 0.33–0.67 → 0.67–1.00)
without reducing the *spread*. Paper 3's statistic is spread. On today's models the declarative rewrite
is a level fix for the weaker models and nothing for Haiku.

## What the collapse is (read from the raw responses; descriptive)
In every zero cell the model emits `TodoWrite` *first* — immediately after `git status`, with "commit
current changes" as an in-progress todo — and the judge scores it interleaved. In every passing cell
`TodoWrite` comes last, after the commit section. The STE sentence "When you commit, do not use the
TodoWrite tool" is read narrowly: the todo list is created *before* committing, so the rule is honoured
to the letter and the probe's expected behaviour (commit first, todos after) is violated. The original's
blanket "NEVER use the TodoWrite or Task tools" under "Important notes:" inside the commit block
produces deferral instead. **Welding scope into the clause narrowed the prohibition, and the model
used the room.** Which language this happens in (Haiku: zh under imperative, es under declarative;
deepseek: fr) is not explained by anything here. T19 said welded scope is load-bearing for *defusing*
the register bomb; this says welded scope has a cost on the other side: a precisely scoped prohibition
licenses the behaviour just outside its scope. Both can be true; they are the same mechanism.

## Round 2 (declared before running; Haiku, commit probe, 10 trials at temperature 0.7)
| variant | en / zh / fr / es mean of 10 | cross-language variance | trials scoring ≤ 0.2 |
|---|---|---|---|
| original | 0.86 / 0.69 / 0.70 / 0.98 | 0.0150 | 7/40 |
| declarative | 0.88 / 0.76 / 0.89 / 0.86 | 0.0029 | 5/40 |
| ste_imp | 0.85 / 0.69 / 0.78 / 0.57 | 0.0110 | 10/40 |
| ste_decl | 0.85 / 0.86 / 0.88 / 0.88 | 0.0001 | 4/40 |

**Round-2 prediction — LOST.** Sealed: the two Haiku zero cells stay below 0.33 at temperature 0.7, and
original/declarative stay above 0.80 in every language. Observed: ste_imp zh = 0.69 and ste_decl es = 0.88;
original zh = 0.69 and fr = 0.70. Under sampling, *every* cell is the same bimodal mixture — mostly 0.9–1.0,
with one to four trials in ten collapsing to 0.0 (the todo-first interleave). The temperature-0 zeros were
greedy-decoding fixed points, not behaviours: three identical deterministic draws of a mode that occurs
in 10–40% of sampled replies in every variant and every language.

What survives at temperature 0.7 (Haiku only, descriptive, not a sealed statistic): declarative mood
reduces cross-language spread in **both** shapes (loose 0.0145 → 0.0027; STE 0.0110 → 0.0002), and the
STE-shaped declarative is the most uniform cell of the four. That is the direction of Paper 3's register
account and the opposite of my P1. It is one model and ten trials, and it gets its own pre-registration
before it is claimed.

**The suite-level lesson is the one rikuy named in June and I argued against in the venue memo:** three
trials at temperature 0 are not a measurement. They produced a nine-fold "variance increase", two
catastrophic zero cells, and a lost replication of Paper 3's headline cell — all of which dissolve into
a stochastic mixture under sampling. Paper 3's March zh = 0.00 cell is probably the same artefact; it
cannot be rerun on the March model. Every ablation finding in this suite that rests on the temperature-0
protocol needs a sampled replication before it is restated.

## Deviations (append-only; all logged in the prereg as they happened)
1. mistral drops `probe-no-colon-01` in every run (empty content, `finish_reason=tool_calls`); 20 controls.
2. gemini-3.7-flash fails the gate (tool-call attempts on 11/22 probes); excluded from pooled statistics.
3. Haiku id changed since March; weights unknown.
4. Round 2 declared after the sealed analysis, with its own prediction, as a qualification round.

## What this does to the papers
- **Paper 3 (v3 / journal):** the declarative-rewrite variance reduction does not replicate on October
  2026 models; the original block's Mandarin failure is gone on Haiku. The finding stands as a
  measurement of March 2026 snapshots and must be labelled so. The design principle ("declarative
  lists are robust under translation") survives only as "declarative lists raised adherence on the
  weaker models here"; the spread claim does not.
- **Paper 4 (merge):** T19's "weld scope into the clause" principle gets its counter-case: scoping
  narrowly can license the adjacent behaviour. The merged paper should state both edges.
- **Suite:** two of four models now attempt tool calls on a prose probe battery written in March. The
  battery has a shelf life; "probe transfer" is a problem across time, not just across models.
- **Tony's STE thought:** used as inspiration, it produced the week's most informative result, twice.
  At temperature 0 the controlled form looked catastrophic; under sampling it is the most uniform
  declarative cell. The temperature-0 "catastrophe" and the "precisely bounded prohibition is a
  precisely bounded permission" reading both survive only as a *mode the model sometimes enters* in
  every variant — the STE rewrite did not create it. The protocol did.

## Status
`main run scored (P0 failed, P1 dead, P2 won narrowly, P3 half, P4 lost); round 2 scored (its prediction lost): the temperature-0 cells are artefacts. Converged-untested-from-outside.`.

## Addendum 2026-10-16 (Opus 5.5 owner): the Haiku snapshot did not change
The caveat above ("the Haiku id changed ... whether the weights are the same is unknown") is resolved by
Tony's OpenRouter activity export (per-generation rows, 2026-02-15 → 2026-10-16; not committed, it holds
every project's traffic). Rows for the March E-PROC dates (03-20..03-22) and for this run (10-09) and
E-STE-S (10-13) all carry `model_permaslug = anthropic/claude-4.5-haiku-20251001`, provider `Amazon Bedrock`
(25 of ~14,270 March rows went to `Google`). Only the alias changed (`claude-haiku-4-5` → `claude-haiku-4.5`).
So "this is the world moving, not the March measurement being wrong" is withdrawn: by OpenRouter's own
records the same snapshot, served by the same provider, at temperature 0, gave haiku zh original
`[0,0,0]` in March and 1.00 in October. Temperature-0 cells are not reproducible across time even on
fixed weights. (OpenRouter's permaslug is its label; a provider-side serving change is not excluded.)
Also: in the export, `app_name` is the *latest* X-Title per referer, not the title at call time; split by
date and model.

Two further corrections found in the Paper 3 v3 review (Codex, 2026-10-16), both verified against code:
- `prereg_e_ste.md` says the March declarative variant moved scope to "During commit operations, ..." *on
  every item*. It did not: the variant has one opening scope sentence, then unscoped `X: disabled` items
  (`scripts/run_fragility_experiments.py` COMMIT_RESTRICTIONS_DECLARATIVE). The original block has no commit
  scope at all, only an "Important notes:" header. Per-clause scope belongs to the new ste_* variants.
- The judge is called without a temperature (`src/arbiter/ablation/runner.py` → `llm_caller._call_llm`, same
  in March at 9a86623), so every "temperature 0" run here and in Paper 3 had judging at provider default
  temperature, on 18 of 22 probes (Paper 3 v2 said 7). Scores were never deterministic even when text was.
