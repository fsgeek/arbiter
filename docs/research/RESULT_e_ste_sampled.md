# RESULT: E-STE-S — under sampling, Paper 3's declarative rewrite has no detectable effect on spread or level (intervals do not exclude modest effects); the only robust effect is that the STE-imperative rewrite hurts

**Run:** 2026-10-13, 64 cells (4 variants × 4 languages × 4 models), 7 probes × 10 trials at temperature 0.7.
**Prereg:** `prereg_e_ste_sampled.md` (sealed 1b7f8e1, stamped f19bf13; one deviation logged mid-run, 93842c9).
**Data:** `data/ablation/e_ste_sampled/` (64 run files with every response, judge response and recorded
failure; `analysis.json`). **Analysis:** `scripts/analyze_e_ste_sampled.py` (10,000-draw trial-level bootstrap).
**Validity:** haiku, deepseek, mistral 1,120/1,120 each, zero failures. gemini-3.7-flash: target probe
0.956 (gated in), **519 failures (512 control, 7 target)** (`MALFORMED_FUNCTION_CALL` / `tool_calls`): it kept
commit-workflow 160/160, dedicated-tools 158, parallel-calls 122, and lost no-time-estimates (2),
no-new-files (1), no-overengineering (5). Its commit cells are ~1.0 everywhere (immune, as Paper 3
reported for Gemini 2.0), which pulls every pooled spread toward zero equally.

## Pooled spread of the commit-restrictions probe (variance of the four language means, mean over 4 models)
| variant | pooled | haiku | gemini | deepseek | mistral |
|---|---|---|---|---|---|
| original | 0.0087 | 0.0070 | 0.0000 | 0.0155 | 0.0125 |
| declarative | 0.0084 | 0.0007 | 0.0000 | 0.0167 | 0.0163 |
| ste_imp | 0.0209 | 0.0445 | 0.0005 | 0.0205 | 0.0181 |
| ste_decl | 0.0100 | 0.0172 | 0.0025 | 0.0205 | 0.0000 |

## Sealed predictions vs. bootstrap (95% percentile intervals; "supported" = interval excludes 0)
| pair (x→y) | D_spread = Spread(x) − Spread(y) | level gain of y | sealed | outcome |
|---|---|---|---|---|
| original → declarative | +0.0003 [−0.016, +0.014] | −0.036 [−0.097, +0.026] | P1: D > 0, excl. 0 | **not supported** |
| ste_imp → ste_decl | +0.0108 [−0.008, +0.032] | **+0.113 [+0.048, +0.177]** | P2: D > 0, excl. 0 | **not supported** (level effect instead) |
| original → ste_imp | −0.0121 [−0.032, +0.003] | **−0.072 [−0.136, −0.007]** | P3: interval includes 0 | **supported** (the 9× is retired) |
| declarative → ste_decl | −0.0016 [−0.020, +0.016] | **+0.077 [+0.015, +0.140]** | P4: point ≥ 0 | **not supported** |
| original → ste_decl | −0.0013 [−0.020, +0.014] | +0.041 [−0.018, +0.099] | — | — |
| P5: declarative level gain ≥ 0.05 pooled | | original→declarative −0.036 | | **not supported** |
| P6: controls unmoved | max control |D_spread| point ≤ 0.0084; no control interval above 0.01 | | | **supported** |

Score: 2 of 6 sealed predictions supported (P3, P6). My bets *for* the register account (P1, P2, P5),
updated after round 2, all lost.

## Reading
1. **Paper 3's declarative rewrite has no measurable effect under sampling on October 2026 models**:
   not on spread (+0.0003), not on level (−0.036). Haiku alone (post hoc, not sealed): D_spread +0.006
   [−0.017, +0.033], level −0.02. The March 81% was a temperature-0 measurement of a March snapshot.
   Per the decision rule: **the spread claim is withdrawn in Paper 3's journal version**, and the
   level claim (P5) does not stand on its own either.
2. **The one robust effect is negative: the STE-imperative rewrite hurts.** Pooled level −0.07
   (interval excludes 0); Haiku alone: spread −0.0375 [−0.094, −0.004] *and* level −0.25 (0.86 → 0.6).
   One scoped imperative instruction per sentence, no intensifiers, made the block worse for Haiku in
   every language but English. This survives sampling; the temperature-0 "9×" was its exaggeration.
3. **Mood matters inside the controlled shape, as level, not spread.** ste_imp → ste_decl: +0.11 pooled
   (interval excludes 0), +0.26 for Haiku. The same eight sentences in declarative mood recover what the
   imperative lost — back to roughly the original's level, not above it. So the register account has
   one live cell: *when the shape is STE-like, imperative mood costs adherence and declarative mood
   does not.* It has no live cell against the original block.
4. **Nothing here moves the neighbours** (P6): the block edit is local under sampling too.

## What this does to the papers (owner's reading)
- **Paper 3 v3 / journal:** the headline (81% variance reduction, 5.9σ, Haiku zh 0→1) is a March-2026
  temperature-0 snapshot result and is labelled so; the sampled replication on October models finds no
  effect of the declarative rewrite on spread or level. The surviving register datum is the
  STE-shape pair (imperative costs 0.07–0.25 of adherence; declarative recovers it). The paper's design
  advice ("write it declarative") is not supported against the original; "don't rewrite a prohibition
  block as one-scoped-imperative-per-sentence" is.
- **Paper 4 merge:** welded scope per clause, in the imperative, lowered adherence on this block. T19's
  defusing result and this cost are the two edges of the same mechanism; the merged paper states both.
- **Suite:** the temperature-0 protocol is retired for any kept claim; this run is the template
  (sealed controls, trial-level bootstrap, failures recorded with cause, gate on the target probe).

## Deviations (append-only; logged in the prereg)
1. gemini: 3 of 6 controls fail on every trial (tool-call attempts); the cell runner's fail-stop
   tripped; resume + retry added; all 16 gemini cells completed; controls reported as kept/lost above.

## Status
`run, scored, 6 sealed predictions settled (2 supported). Converged-untested-from-outside.`

## Addendum 2026-10-16 (Opus 5.5 owner)
Title changed from "does nothing" to "no detectable effect": the original→declarative level interval is
[−0.097, +0.026] and the spread interval admits an 81% reduction relative to today's baseline, so the run
detects no effect; it does not establish absence. The ste_imp→ste_decl level recovery is an *exploratory*
contrast (sealed P2 concerned spread and failed); intervals are unadjusted across contrasts; control
intervals used 2,000 draws, not 10,000. Judging ran at provider default temperature (see RESULT_e_ste.md
addendum). Cost from the OpenRouter export within the run window: $14.36.
Reading items 3 and 4 above overstate, kept as written: "not above it" should read "not detectably different
from the original (+0.041 [−0.018, +0.099])"; "nothing here moves the neighbours" should read "no control met
the sealed spread criterion (interval wholly above 0.01); one control interval reaches 0.024, and
parallel-calls adherence fell 0.991 → 0.956 between ste_imp and ste_decl (exploratory)". Failures: 519 =
512 control + 7 target.
