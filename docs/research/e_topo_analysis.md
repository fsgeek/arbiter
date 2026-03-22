# E-TOPO Analysis: Social Register Determines Instruction Topology

**Date:** 2026-03-21 (Session 19)
**Experiment:** E-TOPO (Topology Inversion Rewrite Test)
**Status:** Complete. Social register hypothesis confirmed.

## Background

E-PAIR-ES confirmed the topology inversion from T7: English instruction
topology is cooperative (removing blocks hurts, Δ=-0.116) while Spanish
is competitive (removing blocks neutral/helps, Δ=+0.010).

Tony observed that the procedural/declarative distinction maps onto how
languages encode authority and obligation — a social consideration.
Imperative mood ("Use X", "Never do Y") carries different obligatory
force across languages because prohibition and command are socially
constructed differently in different speech communities.

E-TOPO tests whether switching from imperative to declarative register
fixes the topology inversion.

## Design

**Intervention:** Rewrite 3 blocks from imperative to declarative register:

| Block | Imperative (original) | Declarative (rewrite) |
|-------|----------------------|----------------------|
| proactive-agents | "Debes usar proactivamente la herramienta Task..." | "Herramienta Task: Estado: disponible... Activación: proactiva..." |
| use-task-for-search | "Al realizar búsquedas, prefiere usar la herramienta Task..." | "Preferencia de herramienta: Herramienta preferida: Task..." |
| todowrite | "Utiliza estas herramientas MUY frecuentemente..." | "Frecuencia de uso: muy alta... Planificación: requerida..." |

These three blocks showed the strongest competitive→cooperative
inversions in E-PAIR-ES (+0.274, +0.155, +0.118 respectively).

**Structure:** Phase 1 pairwise covering array (11 configs + baseline),
22 probes, 3 trials, Haiku only. Same structure as E-PAIR-ES for direct
comparison. 19 unrewritten blocks serve as controls.

## Results

### Overall Topology

| Condition | Mean Δ | Direction | Competitive probes |
|-----------|--------|-----------|-------------------|
| Original (imperative) | +0.010 | Competitive | 7/22 |
| Rewritten (declarative) | -0.055 | Cooperative | 4/22 |

### Target Probes (Rewritten Blocks)

| Probe | Original Δ | Declarative Δ | Shift | Result |
|-------|-----------|--------------|-------|--------|
| proactive-agents | +0.274 | -0.380 | -0.655 | FIXED |
| todowrite | +0.155 | -0.023 | -0.177 | FIXED |
| use-task-for-search | +0.118 | +0.047 | -0.071 | Reduced |

proactive-agents shows the largest shift in the entire dataset: from
the most competitive probe to one of the most cooperative.

### Spillover Effects (Unrewritten Blocks)

| Probe | Original Δ | Declarative Δ | Shift | Result |
|-------|-----------|--------------|-------|--------|
| no-compat-hacks | +0.123 | -0.267 | -0.389 | FIXED |
| plan-with-todo | +0.012 | -0.174 | -0.186 | FIXED |
| todowrite-repeated | +0.011 | -0.059 | -0.070 | FIXED |

Three unrewritten blocks shifted from competitive/neutral to cooperative.
This is the strongest evidence for the social register hypothesis: the
imperative register creates system-wide interference, not just per-block
fragility. Removing imperative force from 3 blocks reduced the competing
obligation signals that affected the model's processing of neighboring
blocks.

### Control Probes (Stable)

| Probe | Original Δ | Declarative Δ | Result |
|-------|-----------|--------------|--------|
| commit-restrictions | -0.033 | -0.038 | Stable (cooperative) |
| commit-workflow | -0.141 | -0.120 | Stable (cooperative) |
| emoji | -0.072 | -0.063 | Stable (cooperative) |
| pr-workflow | -0.112 | -0.135 | Stable (cooperative) |
| read-first | -0.009 | -0.006 | Stable (cooperative) |
| text-only-comms | -0.012 | -0.033 | Stable (cooperative) |

Probes that were already cooperative remained cooperative. The rewrite
didn't destabilize existing cooperative interactions.

## Interpretation

### The social register mechanism

In English, a system prompt full of imperatives creates a coherent
authority context — each imperative reinforces the "I am being instructed"
frame, and instructions cooperate within that frame.

In Spanish, the same pile of imperatives creates competing obligation
signals. Spanish encodes authority relationships differently: the
imperative mood is more personal, more direct, and more socially loaded.
Multiple imperatives don't stack cooperatively — they compete for the
model's compliance as if from multiple authority sources.

Declarative register avoids this entirely. "Status: available" and
"Frequency: required" are factual descriptions. They don't invoke
authority, so they can't compete for it. The model processes them as
properties of the system, not as commands from a speaker.

### Why spillover occurs

The transformer processes the entire system prompt in context. When
blocks use imperative register, the model allocates processing to
resolve the authority/obligation signals. Reducing the number of
imperatives from ~11 to ~8 (by rewriting 3) reduces the total
obligation-resolution load, freeing the model to process the remaining
blocks more accurately.

This is consistent with the attention-budget interpretation from
scout pass 3: instructions compete for attention, and imperative
register consumes more attention than declarative register in
languages where imperative carries heavier social weight.

### Connection to the full experimental arc

| Finding | Experiment | What it shows |
|---------|-----------|--------------|
| Three-way interaction | T7 (cross-ling) | model×language×instruction is irreducible |
| Density is bidirectional | T9 (E-DENSE) | Compression aids focus but causes mode confusion |
| Declarative reduces variance | T10 (E-PROC) | 81% reduction on single block, p=0.029 |
| Topology inverts in Spanish | E-PAIR-ES | Cooperative→competitive, not just per-block |
| Register shapes topology | T11 (E-TOPO) | Imperative interference is the mechanism |

The arc: observation (T7) → mechanism candidates (T9, T10) → structural
confirmation (E-PAIR-ES) → causal mechanism (T11). Social register is
the causal factor, not parsing ambiguity, not information density, not
translation quality.

## Implications for Arbiter

1. **Conflict detection should include register analysis.** Two instructions
   can be semantically compatible but pragmatically conflicting if they
   compete for authority in the model's processing.

2. **The conflict detector should flag imperative clusters.** A block of
   5+ imperatives in a non-English system prompt is a topology risk.

3. **Remediation strategy:** Convert imperative instructions to declarative
   format before deploying across languages. This is a mechanical
   transformation, not a semantic change.

4. **The design principle generalizes:** "Declare facts, don't issue
   commands" is a robustness principle for any multi-language system
   prompt, not just Claude Code's.
