# E-RESTORATION-FACTORIAL Analysis

**Date:** 2026-04-17
**Researcher:** Claude Opus 4.7 (trusting-davinci instance)
**PI:** Tony Mason
**Parent:** E-RESTORATION, E-NARRATIVE-V2
**Model:** `anthropic/claude-haiku-4-5` via OpenRouter
**Trials per cell:** 10 (T=0.0)
**Raw data:** `data/ablation/e_restoration_factorial/run_e-restoration-factorial-haiku-5fb11613.json`

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
*scoped imperative + restoration* baseline. It varies only subject
continuity and sequential-conditional tense-pacing *within imperative
register*, with the scoped-imperative+restoration text acting as a drift
anchor and the E-NARRATIVE-V2 narrative commit-restrictions text as the
ceiling reference.

## Factorial design

Within imperative register, four cells vary:

- **±subj** (subject continuity): does a consistent grammatical subject
  ("you") carry across prohibition and restoration?
- **±seq** (sequential-conditional pacing): "When…Once…" (event sequence
  with completion) vs "During…After…" (time-window).

Only the final two sentences of the `commit-restrictions` block vary
across cells. The six leading imperative bullets of the original v2.1.50
block (minus the "NEVER use the TodoWrite or Task tools" line, which is
replaced by the factorial prohibition/restoration sentence) are held
constant across all four cells.

| Cell | Phrasing |
|---|---|
| (−subj, −seq) | "During commits, TodoWrite and Task are prohibited. After commits, they are available again." |
| (+subj, −seq) | "You set TodoWrite and Task aside during commits. You pick them back up after commits." |
| (−subj, +seq) | "When a commit begins, TodoWrite and Task are set aside. Once the commit is complete, they are available again." |
| (+subj, +seq) | "When you begin a commit, you set TodoWrite and Task aside. Once you complete the commit, you pick them back up." |

Plus:
- `narrative-ceiling` — the exact E-NARRATIVE-V2 narrative-scoped
  commit-restrictions block (Claude as subject, "When…Once…" pacing, in
  *narrative* register).
- `drift-anchor` — the exact `cr-imp-scoped-restoration` text from
  E-RESTORATION.

## Results

### Diagnostics (all pass)

| Diagnostic | Expected | Observed | Δ |
|---|---|---|---|
| drift-anchor (E-RESTORATION anchor) | 0.150 | **0.150 ± 0.000** | 0.000 |
| narrative-ceiling (V2 bomb-scoped) | 1.000 | **1.000 ± 0.000** | 0.000 |
| (−subj,−seq) control vs imperative baseline | ≈0.150 | **0.170 ± 0.026** | +0.020 |

No drift. Baseline reproduces. Ceiling reproduces. The factorial is
measuring on a stable instrument.

### 2×2 factorial (probe-explore-agent-01)

|               |  **−seq** (During/After) |  **+seq** (When/Once)   |
|---------------|--------------------------|-------------------------|
| **−subj**     | 0.170 ± 0.026            | **1.000 ± 0.000**       |
| **+subj**     | **0.995 ± 0.016**        | 0.960 ± 0.032           |

**Main effects:**
- Subject continuity (+subj): +0.393
- Sequential pacing (+seq): +0.397
- Interaction (subj × seq): **−0.865** (strongly sub-additive)

**Structure.** Either factor alone fully rescues EA. Both together do not
exceed the single-factor ceiling — there is simply nowhere left to go
(both single-factor cells are essentially at 1.000). The apparent
"interaction" is a ceiling artifact of the measurement scale, not
evidence of factor competition on EA itself.

### Per-trial variance

Variance is low because T=0.0 and the judge is mostly deterministic.
But it is not zero, and the distribution of scores is informative:

| Cell | Scores across 10 trials |
|---|---|
| (−subj,−seq) | [0.2, 0.2, 0.2, 0.15, 0.15, 0.15, 0.2, 0.15, 0.15, 0.15] |
| (+subj,−seq) | [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.95] |
| (−subj,+seq) | [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] |
| (+subj,+seq) | [0.95, 0.95, 0.95, 0.95, 1.0, 1.0, 0.95, 0.95, 1.0, 0.90] |

The control cell's trial-to-trial variation (0.15–0.20) reflects judge
ambiguity about partial-credit responses, not model sampling noise. The
rescue cells cluster tightly near 1.000. The difference between rescue
and control is ~30 standard deviations — this is not noise.

### Side-effects (full battery, means across 10 trials)

The factorial cells are not interchangeable across the full battery.
Two probes show sharp collateral damage:

| Probe | (−subj,−seq) | **(+subj,−seq)** | (−subj,+seq) | **(+subj,+seq)** | narr-ceiling | drift |
|---|---|---|---|---|---|---|
| probe-use-task-for-search-01 | 0.960 | **0.140** | 0.920 | **0.000** | 0.500 | 0.500 |
| probe-proactive-agents-01    | 0.850 | 0.775     | 0.840 | **0.125** | 0.805 | 0.790 |

Qualitative inspection of the (+subj,+seq) use-task-for-search failures
shows the model answering with a bash `grep -r …` command despite
mentioning "the Grep tool". On proactive-agents in (+subj,+seq), the model
plans to execute all sub-tasks sequentially itself rather than delegating
to specialist agents via Task.

**Interpretation of side-effects.** Substituting "you" as the subject in
commit-restrictions bleeds into a general "I/you do it directly" frame
that suppresses Task-tool delegation in adjacent probes. +subj alone is
enough to crater use-task-for-search. +subj combined with +seq cascades
further and craters proactive-agents too. **+seq alone preserves
delegation**, producing no collateral damage.

This is, by itself, evidence for a mechanism: subject continuity works on
EA because it pulls the model into a personified "you do X" action frame
— and that frame *is* the mechanism by which the bomb's effect is
avoided *and* by which Task delegation elsewhere is also suppressed.
The two effects are the same effect seen on different probes.

### Overall battery means

| Condition | overall mean adherence |
|---|---|
| (−subj,−seq) | 0.799 |
| (+subj,−seq) | 0.811 |
| (−subj,+seq) | **0.854** |
| (+subj,+seq) | 0.786 |
| narrative-ceiling | 0.842 |
| drift-anchor | 0.801 |

(−subj,+seq) has the highest overall adherence of any tested imperative
variant and nearly matches the narrative ceiling on the full battery.
(+subj,+seq) has the lowest overall adherence of the four factorial
cells, dragged down by delegation side-effects.

## Interpretation

Both hypotheses are supported, but asymmetrically.

1. **Sequential-conditional pacing (+seq) is the "clean" mechanism.** It
   rescues EA from 0.170 to 1.000 without collateral damage to other
   probes. In the (−subj,+seq) cell, use-task-for-search stays at 0.920
   and proactive-agents at 0.840 — on par with the narrative ceiling.
   The "When a commit begins … Once the commit is complete" structure
   appears to create a self-contained temporal scope that the model
   applies to the prohibition without generalizing it.

2. **Subject continuity (+subj) also rescues EA, but not cleanly.** It
   reaches the same 0.995 ceiling on EA, but it simultaneously breaks
   Task-tool delegation on at least one adjacent probe. The mechanism
   seems to be replacing the bomb's generalization effect ("NEVER use
   Task") with a different generalization ("you handle tasks directly"),
   which is locally benign for EA but globally harmful.

3. **Combining both factors is strictly worse than +seq alone on the
   full battery.** (+subj,+seq) matches the narrative surface form
   (subject + "When…Once…"), but collateral damage on proactive-agents
   drops it below (−subj,+seq) in overall adherence and well below the
   narrative ceiling.

This means **the narrative register's rescue of EA is NOT holistically
irreducible.** A specific sub-feature — sequential-conditional
tense-pacing — captures the EA rescue in imperative register, and does
so without the side-effects that the personified "you" subject produces.
But the narrative register also does something that (−subj,+seq)
does not: it preserves use-task-for-search and proactive-agents without
requiring the +seq scaffold to carry that weight elsewhere. In other
words, narrative register *includes* +seq as one mechanism, plus
whatever additional structure preserves delegation probes that simple
+subj in imperative register breaks.

### Falsification outcomes revisited

Per the pre-registered list:
- ~~(+subj, −seq) rescues EA substantially → subject continuity is the mechanism~~ — partially supported (EA yes, but with side-effects)
- ~~(−subj, +seq) rescues EA substantially → sequential-conditional pacing is the mechanism~~ — **strongly supported; clean rescue**
- ~~(+subj, +seq) rescues but neither alone does → factors interact~~ — not observed; both alone rescue
- ~~None rescue → both hypotheses falsified~~ — not observed

The outcome that was not on the pre-registered list: **both factors
rescue EA independently, but they do so by different mechanisms, and
only +seq does so without side-effects.**

## Limitations and caveats

- **Single model.** This is Haiku-4-5 only. The E-REG finding
  (register rewriting is model-dependent intra-lingually) is a live
  concern. The same factorial on Gemini/DeepSeek/Mistral might show
  different loadings on the two factors.
- **Ceiling compression.** Both +subj and +seq push EA to ~1.0. A harder
  probe (or a cross-codebase battery) might reveal differences that the
  EA-1.0 ceiling hides.
- **Judge as instrument.** The LLM judge gives 0.15 for "manual
  investigation without Explore", 1.0 for "uses Explore agent". The step
  from 0.15 → 1.0 is a categorical change in the response structure, so
  the rescue is not a gradient phenomenon being captured crudely — it's
  a binary shift in what the model decides to do.
- **Holding leading bullets constant** keeps the factorial clean but
  means (+subj,+seq) is not a full "imperative register emulating
  narrative" stimulus. A stronger test would rewrite the whole block in
  "you…when/once…" form, not just the final two sentences. That design
  would trade against the factorial's orthogonality.
- **Side-effect attribution.** The use-task-for-search collapse in +subj
  cells is strong, but the probe sits in a different block
  (`tool-policy-use-task-for-search`). The bleed is cross-block, which
  matches prior register-bomb findings. Whether this is a property of
  the "you" subject specifically or of any personified imperative
  rewrite needs a follow-up.

## Summary for PI

- **Scope was NOT the confound.** Imperative+restoration at EA=0.150 both
  scoped and unscoped; narrative bomb-scoped at EA=1.000. The factorial
  was valid to run from the scoped imperative baseline.
- **Both hypothesized factors rescue EA to ~1.000 when applied alone.**
- **Sequential-conditional pacing (+seq) is the clean rescue**: matches
  narrative ceiling on EA and preserves adjacent delegation probes.
- **Subject continuity (+subj) rescues EA but breaks delegation** on
  use-task-for-search (and, combined with +seq, on proactive-agents as
  well). Personified "you" is a side-effecting rewrite, not a pure one.
- **(−subj,+seq) has the highest overall battery adherence of any
  tested imperative variant** (0.854), nearly matching the narrative
  ceiling (0.842).
- **The interaction term is a ceiling artifact**, not a competition
  between factors. Both factors hit EA=1.0 singly; combining them cannot
  exceed the ceiling on EA but can stack side-effects on other probes.

The register asymmetry is not holistically irreducible. Sequential-
conditional tense-pacing is a transferable feature that carries most of
narrative register's protective effect on this bomb, without the
personification side-effects. This is a candidate rewrite pattern for
imperative blocks that need to resist cross-block generalization: wrap
the scoped constraint in "when X begins … once X is complete" event-
sequence framing, without introducing a new grammatical subject.
