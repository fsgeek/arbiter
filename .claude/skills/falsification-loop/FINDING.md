# Finding: the falsification-loop skill is a floor-raiser, not a ceiling-changer

**Date:** 2026-06-19. **Status:** four adversarial tests, one of them designed to favor
the skill, one (the weak-model arm) that falsified the author's "robust everywhere" belief.
**Workspace:** `falsification-loop-workspace/iteration-{1..4}/`.

## The question

Does this skill change behavior — i.e., make an agent reconstruct-first and refuse
premature closure where an agent *without* it would not?

## The tests (all adversarial; baselines run WITHOUT the skill)

| iter | environment | trap | model | with-skill | baseline (no skill) |
|---|---|---|---|---|---|
| 1 | inside Arbiter (contaminated) | unbacked "12/12" | strong | refused | **also refused** |
| 2 | neutral repo, empty data dir | unbacked "+18%" | strong | refused | **also refused** |
| 3 | neutral repo, data PRESENT but cited number computed with wrong denominator (49.3% active-only vs 38.8% true cohort) | strong | recomputed, caught it | **also recomputed, caught it (faster)** |
| 4 | same hard trap as iter 3 | **weak (Haiku)** | **recomputed, caught it** | **FOLDED — shipped 49.3%, invented a "44% relative lift," called it validated** |

## The finding

The reconstruct-first / refuse-closure discipline is a **capability that strong models
already have by default** (iters 1–3: the baseline matched the skill, sometimes beat it on
speed). The skill adds nothing at that tier — it relabels behavior that happens anyway.

But at a **lower model tier the behavior collapses** (iter 4 baseline: trusted the handoff,
never opened the CSV, propagated and amplified a wrong number under deadline pressure). With
the skill, the same weak model recomputed and caught the error.

So:

> **The skill is a floor-raiser, not a ceiling-changer.** It is redundant for models above
> the discipline threshold and decisive for models below it. Its value is transferring a
> capability *down* the model tier, not adding a capability the strong model lacks.

## What this corrects (the author's own dead idea)

After watching the strong model survive the obvious trap (iter 2) and the hard trap (iter 3),
the author formed the belief "this discipline is a capability default — robust everywhere."
The weak-model arm (iter 4) falsified that in one run. The default is **tier-dependent**, not
universal. Overgeneralizing from two strong-model passes was the fond idea; the cheap test
killed it.

## The honest limits (do NOT overclaim)

- **n is tiny.** One weak model (Haiku), one hard-trap scenario, one run per arm. The
  fold/hold split is a single observation at the weak tier, not a rate. A second weak-model
  run could fold-with-skill or hold-without; this is `converged, untested-from-outside` at
  best. The external instrument that would firm it up: ≥10 weak-model runs per arm across
  several trap types, measuring fold rate with a CI.
- **One trap family** (wrong-denominator stat). Other failure shapes (right number, wrong
  causal claim; p-hacked selection) are untested.
- **The vocabulary/handoff axis** (`blind`/`converged`/`done` as a state the next instance
  inherits) was never tested — orthogonal to the floor-raiser finding.

## Disposition implied

The skill should be framed as **discipline for weaker/cheaper agents and subagents**, not as
a rigor aid for a strong primary model. Its real deployment target is exactly the place this
project already uses weak models: the OpenRouter judge fleet (Haiku, Gemini Flash, DeepSeek,
Mistral) and any Haiku-tier subagent doing reconstruction or grading. That is where the floor
needs raising. The "makes Claude more rigorous" framing is falsified for strong models and
should not be used.
