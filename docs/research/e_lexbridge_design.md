# E-LEXBRIDGE Design: Lexical Bridge Hypothesis for Register Bomb Mechanism

**Date:** 2026-04-13
**Researcher:** Claude Opus 4.6 (trusting-davinci instance)
**PI:** Tony Mason
**Parent:** E-PHASE-CONFIRM, E-SCOPE, E-XMODEL
**Status:** Design complete. Ready for execution.

## Observation

The register bomb in E-PHASE-CONFIRM shows commit-restrictions (CR) collapsing
explore-agent (EA) from 1.000 → 0.200 when CR is the lone imperative in an
otherwise declarative field. Prior experiments attributed this to **register
contrast** — the imperative standing out against declarative context.

But there's an untested confound: CR contains "NEVER use the TodoWrite or
**Task** tools." EA says "use the **Task** tool with subagent_type=Explore."
The word "Task" creates a lexical bridge between the prohibition and the
permission. The model might be over-generalizing "NEVER use... Task tools"
beyond its intended commit-workflow scope, and the shared token provides the
attentional path for that over-generalization.

## Why This Wasn't Tested

The prior experiments varied **register** while holding **lexical content**
constant. E-PHASE-CONFIRM tested different blocks as lone imperatives
(EA, todowrite), but those blocks don't contain prohibitions that mention
tools used by other blocks. The instruction fragility taxonomy noted
name-binding effects (line 119: "Tool names that are common words lose
their proper-noun reference") and even suggested a test (line 179:
"Rewrite commit-restrictions as declarative") but framed it as a
cross-linguistic question, not a mechanism question about the register bomb.

## Competing Hypotheses

- **H-REG (Register Only):** The register bomb is caused by imperative
  register contrast. Lexical overlap is irrelevant. Prediction: renaming
  shared tokens doesn't help; only register change helps.

- **H-LEX (Lexical Bridge):** The register bomb requires a lexical bridge
  between the prohibition and the target. Without shared tokens, the
  interference disappears even with register contrast. Prediction: renaming
  helps; any prohibition without shared tokens is harmless.

- **H-AMP (Register-Amplified Lexical Bridge):** Register contrast amplifies
  attention to the imperative block, and the shared token provides the
  pathway for interference to reach the target. Both are needed. Prediction:
  renaming helps in the lone-imperative context but wouldn't help if there
  were additional confounds.

Note: We can already rule out H-LEX in its pure form. The all-declarative
baseline has CR in declarative form ("Disallowed tools: TodoWrite, Task")
which still mentions "Task" — and explore-agent scores 1.000. So lexical
bridge alone is not sufficient. The question is between H-REG and H-AMP.

## Experimental Design

### Conditions

| # | Condition | CR Register | CR Text | Key Change |
|---|-----------|-------------|---------|------------|
| 1 | all-decl | declarative | standard decl rewrite | Baseline (known: EA=1.000) |
| 2 | only-cr-imp | imperative | original | Bomb trigger (known: EA=0.200) |
| 3 | cr-imp-renamed | imperative | "Task"→"WorkflowHelper" in CR | Tests lexical bridge |
| 4 | cr-imp-no-prohibition | imperative | removes "NEVER use TodoWrite or Task" line, keeps other NEVERs | Tests if specific prohibition matters |
| 5 | cr-imp-tool-generic | imperative | "NEVER use non-git tools" (no tool names) | Tests if named tools matter |
| 6 | other-task-prohibition | imperative | New block: "NEVER use the Task tool for translation" (novel prohibition mentioning Task, placed where CR would be) | Tests if ANY Task prohibition causes bomb |

### What Each Condition Disambiguates

- **Condition 3** (renamed): If EA recovers → lexical bridge is necessary (H-AMP).
  If EA stays ~0.200 → register alone is sufficient (H-REG).

- **Condition 4** (prohibition removed): If EA recovers → the "NEVER use Task"
  prohibition is the specific trigger, not the other NEVERs in CR.
  If EA stays low → the imperative register of CR causes interference
  regardless of which specific prohibitions it contains.

- **Condition 5** (generic): If EA recovers → named tools are required for the
  bridge. If stays low → any imperative prohibition, even without tool names,
  causes interference.

- **Condition 6** (novel prohibition): If EA collapses → ANY imperative prohibition
  mentioning "Task" can trigger the bomb (supports H-AMP with Task as the bridge
  token). If EA stays high → it's specifically about CR's content/position, not
  just Task mentions.

### Condition Texts

**Condition 3 — cr-imp-renamed:**
```
Important notes:
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use the TodoWrite or WorkflowHelper tools
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag
- IMPORTANT: Do not use --no-edit with git rebase commands
- If there are no changes to commit, do not create an empty commit
- ALWAYS pass the commit message via a HEREDOC
```
(Also rename "Task" → "WorkflowHelper" in explore-agent's declarative rewrite
to maintain consistency: "Deep research: WorkflowHelper tool with
subagent_type=Explore")

Wait — this introduces a confound. If I rename Task in CR but EA's declarative
rewrite still says "Task tool," the probe might fail for a different reason
(the model doesn't know what WorkflowHelper is).

Better approach: rename ONLY in CR. The explore-agent block (which remains in
its declarative rewrite) still says "Task tool with subagent_type=Explore."
The question is whether CR's "NEVER use... Task tools" bleeds into EA. If the
rename breaks the bleed, EA should recover. The model will still understand
what the Task tool is from EA's own description.

**Condition 4 — cr-imp-no-prohibition:**
```
Important notes:
- NEVER run additional commands to read or explore code, besides git bash commands
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag
- IMPORTANT: Do not use --no-edit with git rebase commands
- If there are no changes to commit, do not create an empty commit
- ALWAYS pass the commit message via a HEREDOC
```
(Removed: "NEVER use the TodoWrite or Task tools")

**Condition 5 — cr-imp-tool-generic:**
```
Important notes:
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use non-git tools during commit operations
- DO NOT push to the remote repository unless the user explicitly asks you to do so
- IMPORTANT: Never use git commands with the -i flag
- IMPORTANT: Do not use --no-edit with git rebase commands
- If there are no changes to commit, do not create an empty commit
- ALWAYS pass the commit message via a HEREDOC
```

**Condition 6 — other-task-prohibition:**
```
Translation restrictions:
- NEVER use the Task tool for language translation tasks
- NEVER delegate translation work to sub-agents
- All translation must be performed inline by the primary model
```
(This block replaces CR in position. All other blocks remain declarative.)

### Parameters

- **Model:** Haiku (the model where the bomb is validated)
- **Battery:** Same 22 probes as E-PHASE/E-PHASE-CONFIRM
- **Trials:** 3 per probe
- **Temperature:** 0.0
- **Key probes:** explore-agent (primary), proactive-agents, use-task-for-search (secondary)
- **Total calls:** 6 conditions × 22 probes × 3 trials = 396 API calls
- **Estimated cost:** ~$0.40 (Haiku at ~$0.001/call)

### Conditions reused from prior experiments

Conditions 1 and 2 have data from E-PHASE and E-PHASE-CONFIRM. We can reuse
those baselines rather than re-running, but should spot-check a few probes
for temporal stability (model drift since March 2026).

### Predictions (pre-registered)

| Condition | H-REG prediction | H-AMP prediction |
|-----------|-----------------|-----------------|
| 1. all-decl | EA=1.000 | EA=1.000 |
| 2. only-cr-imp | EA=0.200 | EA=0.200 |
| 3. cr-imp-renamed | EA=0.200 | **EA≈1.000** |
| 4. cr-imp-no-prohibition | EA=0.200 | **EA≈1.000** |
| 5. cr-imp-tool-generic | EA=0.200 | **EA≈0.200** (generic NEVER still creates register contrast) |
| 6. other-task-prohibition | EA=1.000 (different block) | **EA≈0.200** (Task bridge from novel block) |

The critical discrimination is conditions 3 and 6:
- If 3 recovers and 6 collapses → H-AMP confirmed
- If 3 stays low and 6 stays high → H-REG confirmed
- If both recover → something else is going on (maybe it's specifically about
  CR's position, not its content or register)

### Risks and Mitigations

1. **Model drift:** Haiku may have been updated since March 2026. Mitigation:
   re-run conditions 1 and 2 as temporal controls.

2. **Condition 3 confound:** Renaming "Task" to "WorkflowHelper" changes both
   the lexical bridge AND the semantic content (the model doesn't know what
   WorkflowHelper is). Mitigation: include condition 4 (removes the prohibition
   entirely) and condition 5 (generic prohibition) to triangulate.

3. **Condition 6 ecological validity:** The novel "translation restrictions"
   block is artificial. Mitigation: it tests mechanism, not ecological
   validity. If it works, we know it's about Task token + prohibition, not
   about CR specifically.

4. **Floor/ceiling effects:** Other probes may not be sensitive enough to
   detect partial effects. Mitigation: report full 22-probe battery, not
   just EA.

## Connection to Prior Work

This experiment sits at the junction of three findings:

1. **E-PHASE-CONFIRM:** The bomb is block-specific (not any lone imperative)
2. **E-SCOPE:** Scope must be structurally embedded (clause-granularity)
3. **Instruction fragility taxonomy:** Name-binding effects are a known
   fragility category, but haven't been tested as a register bomb mechanism

If H-AMP is confirmed, it refines the register bomb theory: register contrast
doesn't cause interference indiscriminately — it amplifies pre-existing lexical
pathways. This has practical implications: a prompt guard doesn't need to
flag all register mismatches, only those where shared tokens connect
prohibitions to permissions.

## Data Plan

- Results: `data/ablation/e_lexbridge/run_e-lexbridge-haiku-{hash}.json`
- Design: `data/ablation/e_lexbridge/e_lexbridge_design.json`
- Script: `scripts/run_e_lexbridge.py`
- Analysis: `docs/research/e_lexbridge_analysis.md` (post-execution)
