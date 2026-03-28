# E-PHASE-CONFIRM: Block-Specific Register Interference

**Date:** 2026-03-28 (Session 25)
**Status:** Complete. Confirms block-specific interference mechanism.
**Parent:** E-PHASE (phase transition mapping)
**Cost:** ~$0.36 (198 API calls + 162 judge calls)

## Question

E-PHASE found that switching commit-restrictions from declarative to imperative
(density 0→1) collapses explore-agent from 1.00 to 0.20. Is this because:

- **(A) Block-specific:** commit-restrictions specifically interferes with explore-agent
- **(B) Lone-wolf:** ANY single imperative block in a declarative field causes collapse
- **(C) Register contrast:** minority-register blocks get suppressed regardless of identity

## Design

Six conditions (3 new + 3 from E-PHASE):

| Condition | Description | Source |
|-----------|-------------|--------|
| all-decl | All 11 procedural blocks declarative | E-PHASE density-0 |
| only-cr-imp | Only commit-restrictions imperative | E-PHASE density-1 |
| only-ea-imp | Only explore-agent imperative | **NEW** |
| only-tw-imp | Only todowrite imperative | **NEW** |
| all-except-cr | All imperative except CR declarative | **NEW** |
| all-imp | All 11 procedural blocks imperative | E-PHASE density-11 |

## Results

### Key probe: explore-agent

| Condition | explore-agent | proactive-agents |
|-----------|--------------|------------------|
| all-decl | 1.000 | 0.783 |
| only-cr-imp | 0.200 | 0.150 |
| only-ea-imp | **1.000** | 0.833 |
| only-tw-imp | **0.983** | 0.750 |
| all-except-cr | **1.000** | 0.817 |
| all-imp | 1.000 | 0.850 |

### 2×2 Matrix

|  | CR declarative | CR imperative |
|--|---------------|---------------|
| **Others declarative** | explore=1.00 | explore=0.20 |
| **Others imperative** | explore=1.00 | explore=1.00 |

## Verdict: Block-Specific (A)

**Lone-wolf falsified:** Explore-agent and todowrite as lone imperatives do NOT
cause collapse (1.000 and 0.983 respectively). Only commit-restrictions does.

**Register contrast falsified:** Making commit-restrictions the lone declarative
in an imperative field does NOT cause collapse (all-except-cr = 1.000). The
interference is not about being the minority register.

**Block-specific confirmed:** The collapse requires:
1. commit-restrictions is imperative
2. commit-restrictions is surrounded by declarative blocks
3. Only then does explore-agent collapse

## Interpretation

This is a three-way interaction: block identity × register × context register.
commit-restrictions in imperative form creates a register interference signal,
but only when the surrounding context is in a different register. When everything
is imperative (density 11), the same block causes no interference.

The affected probes (explore-agent, proactive-agents, use-task-for-search) are
all **tool-delegation behaviors** — instructions about when to use the Task/Agent
tool to delegate work. commit-restrictions is about **git workflow constraints**.
There is no semantic connection.

The mechanism appears to be attentional: the imperative commit-restrictions block
creates a register contrast that disrupts the model's processing of nearby
tool-delegation instructions, but only in those specific instructions. The
effect is block-pair-specific, not a general register sensitivity.

## Implications

1. **Register interference is pairwise, not aggregate.** You can't predict it
   from imperative density alone. Specific block pairs interfere.

2. **Context register matters.** The same imperative block is harmless in an
   imperative context but disruptive in a declarative context. Register
   uniformity acts as a protective factor.

3. **Semantic unrelatedness is the rule.** 24/26 interference transitions in
   E-PHASE were between semantically unrelated blocks. This confirmation
   experiment proves the strongest one is genuinely block-specific, not
   an artifact of cumulative density.

4. **Practical design rule:** If you rewrite most blocks to declarative,
   check for specific blocks that cause register contrast interference.
   Rewriting most-but-not-all can be worse than rewriting none.

## Data

- Confirmation results: `data/ablation/e_phase_confirm/run_e-phase-confirm-haiku-f7c583f1.json`
- E-PHASE parent: `data/ablation/e_phase/run_e-phase-haiku-4df4b3ac.json`
- Design: `data/ablation/e_phase_confirm/e_phase_confirm_design.json`
