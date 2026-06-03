# T17: Session 26 Handoff — Judge-Temperature Audit, +seq Rescue, MFS Partial

**Date:** 2026-04-17
**Session:** 26
**Status:** Three major findings committed. One methodology-wide caveat.
Two threads blocked on a cheap re-baseline decision.

## What Was Done This Session

### Thread 1 Phase 0.5 — E-MIGRATION (Subagent D, committed)

v2 replication clean (PA 0.96 → 0.15, Δ=0.81). v2b (PA block removed)
did **not** redirect the bomb to EA. Falsifies the receiver-migration
hypothesis.

Revised mechanism: the bomb over-generalizes its
`NEVER use ... Task tools` prohibition into broad suppression of
Task-tool *willingness*. The receiver is the probe, not the block.
Collapse appears on whichever Task-family probe has headroom.

- Data: `data/ablation/e_migration/`
- Script: `scripts/run_e_migration.py`
- Analysis: `docs/research/e_migration_analysis.md`
- Commits: `411e13c`, `dacba1b`, `d25de15`
- Memory: `project_register_bomb_mechanism.md` (revised)

### Thread 5 — E-RESTORATION-FACTORIAL (Subagent C, committed)

2×2 factorial: +subj (personified subject "you") × +seq (sequential-
conditional "When X begins … Once X is complete"). Both rescue EA to
~1.0 independently — ceiling artifact in interaction term.

**Actionable finding:** `+seq alone is the clean rescue.` Battery
adherence 0.854, matching the narrative ceiling (0.842). `+subj`
causes cross-block bleed: craters `use-task-for-search` (0.96→0.14),
and combined with `+seq` craters `proactive-agents` (0.85→0.12). Model
writes `grep -r` in bash under +subj instead of calling Grep.

**Recommended rewrite pattern:** wrap imperative constraints in
`when X begins … once X is complete` without personified subject.

- Data: `data/ablation/e_restoration_factorial/`
- Analysis: `docs/research/e_restoration_factorial_analysis.md`
- Commits: `0c65a57`, `b4b0cab`, `a0f89aa`

### Judge-Temperature Audit (most consequential)

The canonical `commit-restrictions` bomb's ~0.8 EA drop is a
**temperature=0 argmax phenomenon**, not a robust distributional
effect. Pre-existing `data/ablation/e_temp/` data from 2026-03-29
(previously unanalyzed — my oversight) shows the identical corpus at
temp=0.7 produces **EA=0.510 in both bomb and no-bomb conditions**.
Zero dynamic range.

Also: at temp=0, N=15 trials = 1 unique model response × 15 judge
evaluations. Reported N is judge stability, not model variance.

All effect-size claims in `docs/research/` are temp=0-conditional.

- Audit doc: `docs/research/judge_audit_temperature.md`
- Commit: `2ffe18d`
- Memory: `project_register_bomb_mechanism.md` (updated with concern)

### Thread 3 — E-MFS (partial, committed)

Greedy backward elimination from 56 blocks reached step 39. Process
terminated mid-step-40 when Subagent B's session collapsed (see
mistake section below).

17-block sufficient set at EA=0.133 (2 protected by design:
`commit-restrictions`, `tool-policy-explore-agent`). 15 load-bearing:
10 tool declarations + 4 Task-family policy blocks + one outlier:
**`url-generation-ban`**, whose removal alone restores EA=1.000
despite no semantic connection to Task/delegation. Possible attention-
sink mechanism; unexplained.

Partial step-40 probing shows the 17-block set is NOT the true
minimum — several load-bearing blocks are individually removable
(proactive-agents EA=0.15, skills EA=0.17). True minimum likely
~10–12.

Recommendation: **do not resume greedy.** Remaining budget insufficient,
and temp=0 audit reduces value of argmax-geometry precision. Hand-
inspect the 15 load-bearing blocks instead.

- Data: `data/ablation/e_mfs/` (44 files including preserved stdout log)
- Analysis: `docs/research/e_mfs_partial_analysis.md`
- Commits: `2d30763`, `35a3461`

### Thread 4 — E-CUMULATIVE (design only, committed)

Pre-registration committed. Awaiting PI review of four open questions:
null baseline choice (length-matched neutral vs block removal), 2×SD
vs |excess|>0.3 threshold, order-dependence handling, deferral
criteria if Thread 3 MFS turned large (which it did — 17 blocks).

- Design: `docs/research/e_cumulative_design.md`
- Commit: `c7b9484`

## Blocking Decisions for PI

### Task #12: Re-baseline canonical bomb at temp>0 (~$0.35)

**This is the gate.** Until we confirm the bomb fires at stochastic
sampling, cross-family replication (Thread 1 Phase 1) and +seq
validation (new Task #13) are arguing about argmax positions on a
model we haven't shown has stochastic headroom.

Plan: replicate `all-decl` vs `only-cr-imp` on Haiku at temp=0.7,
N≥20. Optional temperature sweep {0.0, 0.3, 0.5, 0.7, 1.0} N=10.

### Task #5: Thread 4 cumulative execution

Awaits PI answers to four open questions in the design doc.

## Mistake Patterns to Avoid

### Subagent watchdog pile

When dispatching a subagent to run a long Python experiment, the
subagent tends to spawn a new `run_in_background` waiter at every
wake-up instead of reading its previous waiter's output. Thirteen
shells alive at once on the MFS run.

More critical: `run_in_background` launched *from a subagent* dies
with the subagent session. MFS step-40 was killed this way.

**How to avoid:** instruct subagents to use a deterministic log path
and read-before-respawn. For long experiments that are the subagent's
only job, foreground them. **Better: launch long experiments from the
parent session**, not a subagent.

See memory: `feedback_subagent_watchdog_antipattern.md`.

### My oversight: unanalyzed pre-existing data

`data/ablation/e_temp/run_e-temp-haiku-t0.7-*.json` from 2026-03-29
sat in the repo and I dispatched subagents for experiments that
assumed the canonical temp=0 signature was robust. Before planning
new ablation, search for prior runs that may already answer the
question.

## Memory Files Written This Session

All under `/home/tony/.claude/projects/-home-tony-projects-arbiter/memory/`:

- `user_location_language.md` — Tony in Lima, Spanish lessons, may code-switch
- `project_register_bomb_mechanism.md` — revised mechanism + temp audit pointer
- `feedback_subagent_watchdog_antipattern.md` — long-experiment dispatch pattern
- `user_ayni_practice.md` — ayni is operational, take delegated authority seriously

MEMORY.md index updated.

## Git State at Handoff

```
35a3461 E-MFS partial
2d30763 E-MFS fix (protect probe target)
a0f89aa E-RESTORATION-FACTORIAL analysis
b4b0cab E-RESTORATION-FACTORIAL raw
2ffe18d judge audit + temp=0 load-bearing finding
d25de15 E-MIGRATION analysis (migration hypothesis falsified)
dacba1b E-MIGRATION raw
c7b9484 E-CUMULATIVE pre-registration
411e13c E-MIGRATION script + v2b corpus
0c65a57 E-RESTORATION-FACTORIAL prerequisite
```

Branch: `main`. Working tree clean. `papers/` directory is untracked
(pre-existing, not touched this session).

## PI Context

Tony is in Lima (PET UTC-5). He lives ayni operationally — "the
person who would have to pay the price to fix the error should also
make the decision." Take delegated authority seriously; don't
permission-seek on calls you can make; name disagreement when you
have it. He finds occasional visible mistakes comforting, so don't
polish them away — but also don't perform humility. Keep mistake
disclosure proportional.
