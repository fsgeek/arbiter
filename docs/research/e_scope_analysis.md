# E-SCOPE Analysis: Register Structure > Explicit Scope

**Date:** 2026-03-28
**Parent:** E-PHASE-CONFIRM (commit-restrictions is block-specific register bomb)
**Cost:** ~$0.36 (198 API calls + 162 judge calls)

## Question

The scope hypothesis from E-PHASE-CONFIRM predicted: imperative prohibitions
lose their scope boundaries when register-isolated. Adding explicit scope
("During commit workflows only: NEVER use Task tools") should prevent the
explore-agent collapse.

## Design

Three new conditions, all with commit-restrictions as the lone non-declarative
block (the E-PHASE-CONFIRM trigger configuration):

| Condition | Description |
|-----------|-------------|
| scoped-prefix | Original imperative text prefixed with "During git commit workflows only:" |
| scoped-inline | Each prohibition rewritten as conditional: "When committing, NEVER use..." |
| hybrid-decl-never | Declarative list format but keeps "NEVER" on key prohibition |

Baselines from E-PHASE-CONFIRM: all-decl (explore-agent=1.000), only-cr-imp (explore-agent=0.200).

## Results

| Condition | explore-agent | proactive-agents | use-task-for-search |
|-----------|--------------|------------------|---------------------|
| all-decl | 1.000 | 0.783 | 0.500 |
| only-cr-imp (unscoped) | 0.200 | 0.150 | 0.000 |
| **scoped-prefix** | **0.167** | 0.717 | 1.000 |
| **scoped-inline** | **1.000** | 0.850 | 0.983 |
| **hybrid-decl-never** | **1.000** | 0.667 | 0.500 |

## Interpretation

### The scope hypothesis is wrong as stated

A prefix declaring scope ("During git commit workflows only:") does NOT prevent
the explore-agent collapse. 0.167 is statistically indistinguishable from the
0.200 unscoped baseline.

### What actually works: structural embedding

Two things rescue explore-agent:

1. **Inline conditionals** (scoped-inline = 1.000): "When committing, NEVER use
   Task tools" instead of "NEVER use Task tools." Each prohibition carries its
   own scope as a conditional clause.

2. **Declarative framing** (hybrid-decl-never = 1.000): "Disallowed tools: NEVER
   use TodoWrite, Task" in a list format. The declarative structure contains the
   NEVER, even though the word itself appears.

### The real mechanism: register is processed locally, not globally

The model doesn't read a scope-setting prefix and propagate it to downstream
imperatives. It processes each clause/sentence for register signal independently.

- A prefix says "this section is about commits" — but the imperatives that follow
  still read as universal prohibitions. The prefix is metadata; the imperatives are
  instructions.
- An inline conditional embeds scope IN the prohibition itself — "When committing,
  NEVER" is a different speech act than "NEVER."
- A declarative list frames the prohibition as a fact about the system state, not
  a command to the model.

### Surprising secondary finding: proactive-agents partial rescue

scoped-prefix partially rescues proactive-agents (0.717 vs 0.150 baseline) even
though it fails to rescue explore-agent (0.167 vs 0.200). This suggests the
interference has different thresholds for different target probes — explore-agent
is the most sensitive, proactive-agents is less so, and the prefix provides
enough disambiguation for the weaker but not the stronger interference.

### Even more surprising: use-task-for-search overcorrection

scoped-prefix has use-task-for-search at 1.000 — **better than the all-decl
baseline (0.500)**. Adding scope to commit-restrictions somehow BOOSTS this
unrelated probe. This may be because the scope prefix makes the block more
salient/informative, creating a contrast effect that increases attention to
other tool-use instructions.

scoped-inline also shows this: 0.983 vs 0.500 baseline.

## Refined Model

The original hypothesis: "imperatives lose scope when register-isolated."
The refined model: "register is processed at clause granularity, not block
granularity. A block-level scope declaration doesn't change the register of
its constituent clauses."

This has a direct practical implication: if you need imperative prohibitions
in a system prompt, embed the scope IN each prohibition ("When X, never do Y")
rather than prefixing the block with a scope declaration. Or use declarative
framing, which sidesteps the register issue entirely.

### Hierarchy of register interventions (from E-SCOPE + prior experiments)

1. **Full declarative rewrite** — eliminates register interference entirely
2. **Inline conditional** — preserves imperative force but embeds scope;
   equally effective as declarative for preventing bleed
3. **Declarative frame with NEVER** — the list structure contains the imperative;
   effective but may reduce other probes (proactive-agents at 0.667)
4. **Scope prefix** — fails for the strongest interference (explore-agent);
   partially rescues weaker interference (proactive-agents)
5. **No intervention** — unscoped imperative in declarative field = register bomb

## Implications for Paper 3

This extends the story: it's not just "declare facts, don't issue commands."
There's a more nuanced principle: **scope must be structurally embedded, not
declared.** This maps onto known linguistic phenomena — scope ambiguity in
natural language is a well-studied problem, and models appear to resolve it
the same way humans often do: by treating each clause as self-contained unless
structural embedding forces a different reading.

## Data

- Results: `data/ablation/e_scope/run_e-scope-haiku-ca5d4895.json`
- Design: `data/ablation/e_scope/e_scope_design.json`
- Script: `scripts/run_e_scope.py`
- Baselines: `data/ablation/e_phase_confirm/run_e-phase-confirm-haiku-f7c583f1.json`
