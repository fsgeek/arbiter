# T15: E-SCOPE — Scope Must Be Structurally Embedded, Not Declared

**Date:** 2026-03-28
**Status:** Complete
**Parent:** T14 (E-PHASE-CONFIRM)
**Cost:** ~$0.36

## Finding

The scope hypothesis was wrong as stated. A prefix declaring "During git commit
workflows only:" does NOT prevent the explore-agent collapse (0.167, same as
unscoped 0.200). But inline conditionals ("When committing, NEVER use...") fully
rescue it (1.000), as does declarative framing with NEVER (1.000).

## Mechanism

Register is processed at clause granularity, not block granularity. A block-level
scope declaration doesn't change the register of its constituent clauses. Each
imperative sentence is evaluated for obligatory force independently.

## Hierarchy of Register Interventions

1. Full declarative rewrite — eliminates interference
2. Inline conditional ("When X, never Y") — embeds scope in each clause; equally effective
3. Declarative frame with NEVER — list structure contains the imperative
4. Scope prefix — fails for strongest interference, partially rescues weaker
5. No intervention — register bomb

## Key Data

| Condition | explore-agent | proactive-agents |
|-----------|--------------|------------------|
| all-decl | 1.000 | 0.783 |
| only-cr-imp | 0.200 | 0.150 |
| scoped-prefix | 0.167 | 0.717 |
| scoped-inline | 1.000 | 0.850 |
| hybrid-decl-never | 1.000 | 0.667 |

## Principle

**Embed scope in the prohibition, don't declare it above.**
"When committing, NEVER use Task tools" ≠ "During commits: NEVER use Task tools"
The former is a conditional speech act. The latter is metadata followed by an
unconditional command.
