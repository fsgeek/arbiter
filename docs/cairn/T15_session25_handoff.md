# T15: Session 25 Handoff — E-PHASE and the Scope Hypothesis

**Date:** 2026-03-28
**Session:** 25
**Status:** Three experiments complete, one hypothesis ready to test

## What Was Done This Session

### E-REG (inherited, committed)
Register rewriting is model-dependent intra-lingually. Haiku-specific suppression.
Data: `data/ablation/e_reg/`, Script: `scripts/run_e_reg.py`

### E-PHASE: Phase Transition Mapping
Varied imperative density 0→11 on Haiku. 12 conditions, 792 results, ~$1.44.

**Finding:** No phase transition. Mean adherence oscillates 0.743–0.847 with no
monotonic trend. Block identity matters more than block count. All-declarative
(0.810) is WORSE than all-imperative (0.841) for Haiku.

Data: `data/ablation/e_phase/`, Script: `scripts/run_e_phase.py`
Cairn: `docs/cairn/T13_e_phase_results.md`
Analysis: `docs/research/e_phase_analysis.md`

### E-PHASE-CONFIRM: Block-Specific vs Lone-Wolf
Three conditions testing whether commit-restrictions specifically causes
explore-agent collapse, or any lone imperative would.

**Finding:** Block-specific. commit-restrictions is a register bomb.
- only-ea-imp (explore-agent lone imperative): explore-agent = 1.000
- only-tw-imp (todowrite lone imperative): explore-agent = 0.983
- only-cr-imp (commit-restrictions lone imperative): explore-agent = 0.200
- all-except-cr (everything imperative except CR): explore-agent = 1.000

Data: `data/ablation/e_phase_confirm/`, Script: `scripts/run_e_phase_confirm.py`
Cairn: `docs/cairn/T14_e_phase_confirm.md`
Analysis: `docs/research/e_phase_confirm_analysis.md`

## The Scope Hypothesis (UNTESTED — next ghola's job)

**Why commit-restrictions?** Its text includes "NEVER use the TodoWrite or Task tools"
— scoped to commit workflow but read as global when it's the only imperative in a
declarative field. The imperative register makes the prohibition "louder" and the
lack of surrounding imperative context removes the scoping.

**Mechanism:** Imperative prohibitions lose their scope boundaries when register-isolated.
A lone imperative in a declarative field is interpreted as having universal scope. The
same imperative among imperative peers stays contextually scoped.

**Test (E-SCOPE):**
1. Keep commit-restrictions imperative but add explicit scope: "During commit workflows
   only: NEVER use Task tools." Run in all-declarative context. If explore-agent stays
   at 1.00, scope hypothesis confirmed.
2. Create a *new* imperative prohibition with Task scope (not commit-related) and test
   whether it also collapses explore-agent. If yes, it's about prohibition + Task mention,
   not about commit-restrictions specifically.
3. Test whether other imperative blocks with tool restrictions (e.g., dedicated-tools
   says "use X instead of Y") show similar bleed when register-isolated.

**Prediction:** Explicit scoping will prevent the bleed. The model needs register-context
OR explicit scope markers to correctly limit a prohibition's domain.

## Other Context for Next Ghola

- Ivan Googasian is an external researcher citing Paper 3. See `memory/external_ivan.md`.
- Paper 3 is published on arXiv as of 2026-03-26.
- All experiments use OpenRouter. Haiku = anthropic/claude-haiku-4-5.
- Tony is the PI. He asks questions. Don't permission-seek.

## Git State

```
93cf85f E-PHASE-CONFIRM
91e89f2 E-PHASE
f87e7b9 E-REG
5382076 arXiv submission
```

Branch: research, ahead of origin by 3 commits. Working tree clean.
