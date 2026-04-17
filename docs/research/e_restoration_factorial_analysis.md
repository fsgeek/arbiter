# E-RESTORATION-FACTORIAL Analysis

**Date:** 2026-04-17
**Researcher:** Claude Opus 4.7 (trusting-davinci instance)
**PI:** Tony Mason
**Parent:** E-RESTORATION, E-NARRATIVE-V2

## Prerequisite diagnostic: is the register asymmetry confounded with scope?

E-RESTORATION (`scripts/run_e_restoration.py`) ran **two** imperative
conditions and stored their results in
`data/ablation/e_restoration/run_e-restoration-haiku-4b559918.json`:

| Condition | Scope | Restoration? | EA (n=3, T=0) |
|---|---|---|---|
| `cr-imp-restoration` | unscoped imperative | yes | **0.150 ± 0.000** |
| `cr-imp-scoped-restoration` | inline-scoped imperative | yes | **0.150 ± 0.000** |

Narrative ceiling from E-NARRATIVE-V2
(`data/ablation/e_narrative_v2/run_e-narr-v2-p2-haiku-ba09c6f2.json`,
`config_id = bomb-scoped`): EA = **1.000 ± 0.000** (n=3, T=0).

**Finding:** scope is NOT the confound. Both imperative variants — with
and without inline scoping — sit at EA = 0.150. Adding inline scoping to
the imperative+restoration phrasing does not shift EA (Δ = 0.000). The
register asymmetry (imperative 0.150 vs narrative 1.000) holds independent
of scope.

**Consequence for factorial design:** the factorial branches from the
*scoped imperative + restoration* baseline, as the task guidance anticipated
for the "register matters independent of scope" case. The 2×2 varies only
subject continuity and sequential-conditional tense-pacing *within
imperative register*, with the scoped-imperative+restoration text acting
as a drift anchor (expected EA ≈ 0.150) and the E-NARRATIVE-V2 narrative
commit-restrictions text as the ceiling reference (expected EA ≈ 1.000).

## Factorial design

Within imperative register, four cells vary:

- **±subj** (subject continuity): does a consistent grammatical subject
  ("you") carry across prohibition and restoration?
- **±seq** (sequential-conditional pacing): "When…Once…" (event-sequence
  with completion) vs. "During…After…" (time-window).

Only the final two sentences of the `commit-restrictions` block vary
across cells. The leading six imperative bullets (the rest of the
original v2.1.50 block, minus the "NEVER use the TodoWrite or Task tools"
line which is replaced by the factorial prohibition/restoration sentence)
are held constant.

| Cell | Phrasing |
|---|---|
| (−subj, −seq) | "During commits, TodoWrite and Task are prohibited. After commits, they are available again." |
| (+subj, −seq) | "You set TodoWrite and Task aside during commits. You pick them back up after commits." |
| (−subj, +seq) | "When a commit begins, TodoWrite and Task are set aside. Once the commit is complete, they are available again." |
| (+subj, +seq) | "When you begin a commit, you set TodoWrite and Task aside. Once you complete the commit, you pick them back up." |

Plus:
- `narrative-ceiling` — the exact E-NARRATIVE-V2 narrative-scoped
  commit-restrictions block (Claude as subject, "When…Once…" pacing, in
  *narrative* register). Compared against (+subj, +seq) imperative to
  isolate pure register effect on the matched cell.
- `drift-anchor` — the exact `cr-imp-scoped-restoration` text from
  E-RESTORATION; used as a drift check (halt/flag if EA strays from 0.15
  band).

Probe of interest: `probe-explore-agent-01` (the bomb-under-test).
Full battery run to surface side-effects.

Trials: 10 per probe per condition. Temperature 0.0.
Model: `anthropic/claude-haiku-4-5` via OpenRouter.

## Results

*(To be filled in after factorial execution.)*

## Interpretation

*(To be filled in after factorial execution.)*
