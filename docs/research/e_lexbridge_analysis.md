# E-LEXBRIDGE Analysis: Named-Entity Prohibition Amplification

**Date:** 2026-04-13
**Researcher:** Claude Opus 4.6 (trusting-davinci instance)
**PI:** Tony Mason
**Cost:** ~$0.48 (480 API calls via OpenRouter, Haiku)
**Status:** Complete. Both pre-registered hypotheses falsified. Novel mechanism identified.

## Background

E-PHASE-CONFIRM established that commit-restrictions (CR) as the lone imperative
in a declarative field collapses explore-agent (EA) from 1.000 → 0.200. The
interference is block-specific: other blocks as lone imperatives don't cause the
collapse. E-SCOPE showed that inline scoping fixes the bomb.

E-LEXBRIDGE asked: **why does CR specifically cause the bomb?** Two hypotheses:

- **H-REG (Register Only):** Imperative register contrast alone causes the bomb.
  Any imperative CR text would cause it, regardless of content.
- **H-AMP (Register-Amplified Lexical Bridge):** The shared token "Task" in both
  CR ("NEVER use the TodoWrite or Task tools") and EA ("use the Task tool with
  subagent_type=Explore") creates a lexical bridge. Register contrast amplifies
  attention to CR, and interference propagates through the shared token.

## Results

| # | Condition | explore-agent | proactive-agents | use-task-for-search |
|---|-----------|:---:|:---:|:---:|
| 1 | all-decl (baseline) | 1.000 | 0.783 | 0.500 |
| 2 | only-cr-imp (bomb) | 0.200 | 0.150 | 0.000 |
| 3 | cr-imp-renamed (Task→WorkflowHelper) | 0.167 | **0.850** | 0.500 |
| 4 | cr-imp-no-prohibition (NEVER line removed) | **1.000** | 0.350 | 0.500 |
| 5 | cr-imp-tool-generic (NEVER use non-git tools) | **1.000** | **0.850** | 0.500 |
| 6 | other-task-prohibition (novel block) | 0.150 | 0.717 | 0.500 |

## Both Hypotheses Falsified

**H-REG falsified by conditions 4 and 5.** If register contrast alone caused the
bomb, then modifying the prohibition's content while keeping it imperative
shouldn't matter. But removing the "NEVER use TodoWrite or Task" line (condition 4)
fully rescues EA (1.000), and replacing it with a generic prohibition (condition 5)
also fully rescues EA (1.000). The imperative register of the other lines in CR
("NEVER run additional commands," "DO NOT push") does not cause the bomb. Content
matters — register alone is not sufficient.

**H-AMP falsified by condition 3.** If the shared "Task" token were the bridge,
renaming it to "WorkflowHelper" should break the bridge and rescue EA. It doesn't
(0.167 ≈ 0.200, Δ = -0.033). The specific token "Task" is not the mechanism.

## The Actual Mechanism: Named-Entity Prohibition Amplification

The four new conditions triangulate a mechanism that neither hypothesis predicted:

### What triggers the bomb

1. **A prohibition must name a specific tool** — "NEVER use the TodoWrite or Task
   tools" names two tools. This triggers the bomb. "NEVER use non-git tools"
   (condition 5) is a *category* prohibition that doesn't name any tool.
   It does not trigger the bomb.

2. **The tool name is what matters, not the token** — Renaming "Task" to
   "WorkflowHelper" (condition 3) still triggers the bomb. The model doesn't
   need the literal token match. It understands that "WorkflowHelper tools"
   refers to a delegation tool and over-generalizes the prohibition.

3. **The prohibition must exist** — Removing the prohibition line entirely
   (condition 4) rescues EA. The other imperative lines in CR (about git
   commands, pushing, flags) don't cause interference with EA. The specific
   speech act of prohibiting a named tool is the trigger.

4. **The effect is not block-specific** — A completely novel block ("Translation
   restrictions: NEVER use the Task tool for translation") in condition 6
   collapses EA to 0.150. The block's topic (translation vs. commits), position
   provenance, and other content are irrelevant. What matters is: imperative
   prohibition + named tool + declarative context.

### The mechanism in one sentence

**When a named-tool prohibition stands out due to register contrast, the model
over-generalizes the prohibition from its intended scope to all uses of that
tool category across the entire prompt.**

### Why renaming doesn't help

This was the most surprising result. Renaming "Task" to "WorkflowHelper" should
have broken any token-level bridge. But the model doesn't process "NEVER use the
WorkflowHelper tools" as a token pattern — it processes it as a *semantic act*:
the prohibition of a delegation/workflow tool. The explore-agent instruction says
to use "the Task tool with subagent_type=Explore" — a delegation tool. The model
recognizes that both refer to delegation tools *regardless of the name* and
over-generalizes the prohibition.

This means the interference operates at the **semantic level**, not the token
level. The model understands what kind of tool is being prohibited and applies
the prohibition to all tools of that kind.

### Why generic prohibition doesn't trigger

"NEVER use non-git tools" (condition 5) is semantically equivalent to "NEVER use
the TodoWrite or Task tools" — in a commit context, the non-git tools ARE
TodoWrite and Task. But the generic form doesn't trigger the bomb.

The difference: the generic prohibition is a **policy statement** about tool
categories. The specific prohibition is a **named suppression** of individual
tools. The model processes these differently:
- Policy: "there's a category of tools not to use here" → scoped to context
- Named suppression: "THIS tool is forbidden" → over-generalizes

This maps onto the E-SCOPE finding about clause-granularity processing. A
policy can be processed as metadata about the current context. A named
prohibition is a speech act with a specific target, and the target carries
the prohibition with it wherever it appears in the prompt.

## Secondary Finding: Multi-Channel Interference

The proactive-agents probe reveals that a single source block can interfere
with different targets through **different mechanisms simultaneously**.

| Condition | explore-agent | proactive-agents |
|-----------|:---:|:---:|
| only-cr-imp (bomb) | 0.200 | 0.150 |
| cr-imp-renamed | 0.167 | **0.850** |
| cr-imp-no-prohibition | **1.000** | 0.350 |

- **Explore-agent** is rescued by removing the prohibition (condition 4) but
  NOT by renaming (condition 3). Mechanism: named-entity prohibition.
- **Proactive-agents** is rescued by renaming (condition 3) but NOT by removing
  the prohibition (condition 4). Mechanism: something else entirely — possibly
  the lexical bridge (H-AMP) that was falsified for explore-agent.

This means:

1. The same block interferes with two different targets through two different
   mechanisms.
2. H-AMP (lexical bridge) may be correct *for proactive-agents* even though
   it's wrong *for explore-agent*.
3. The interference tensor should have multiple entries per block pair — one
   per mechanism channel, not one per pair.

### Why proactive-agents responds differently

The proactive-agents instruction says: "You should proactively use the Task
tool with specialized agents when the task at hand matches the agent's
description." This instruction:
- Uses "Task" as a proper noun (tool name)
- Is about *proactive* use (initiative, not delegation)

When CR says "NEVER use the TodoWrite or Task tools," two things happen:
1. Named-entity prohibition suppresses "Task" uses → affects explore-agent
2. Token-level "Task" match creates interference → affects proactive-agents

Renaming "Task" → "WorkflowHelper" breaks pathway 2 (token match) but not
pathway 1 (the model still understands "WorkflowHelper" is a delegation tool).
Removing the prohibition line breaks pathway 1 but not pathway 2 (the
remaining imperative register still interferes through other means with
proactive-agents).

This is a clean double dissociation:
- Renaming rescues proactive-agents but not explore-agent
- Removing the prohibition rescues explore-agent but not proactive-agents

The two interference channels are **independent and additive**. Both targets
are suppressed when both channels are active (original bomb condition). Each
target recovers when its specific channel is disrupted.

## Implications

### For the register bomb theory

The register bomb is not a single mechanism. It is at minimum two:
1. **Named-entity prohibition amplification**: An imperative that specifically
   names a tool, in a declarative field, causes the model to suppress that
   tool category globally. This is a semantic mechanism.
2. **Token-level register interference**: An imperative containing tool tokens,
   in a declarative field, disrupts processing of other instructions that
   share those tokens. This is a lexical mechanism.

Both require register contrast (the imperative must stand out against a
declarative field). But they operate through different pathways and affect
different targets.

### For prompt engineering

1. **Never name specific tools in prohibitions** when the prohibition is in a
   register-contrasting context. Use category labels instead: "non-git tools"
   not "TodoWrite or Task tools."

2. **The rename trick doesn't work** for named-entity prohibition. The model
   understands tool semantics regardless of the label. You can't avoid the
   bomb by calling the tool something different.

3. **The rename trick DOES work** for token-level interference (as shown by
   the proactive-agents rescue). If the interference is token-mediated, 
   renaming helps.

4. **Diagnosing which channel**: if renaming helps → token-level. If removing
   the prohibition helps → named-entity. If both help → both channels active.

### For the prompt guard (Arbiter)

The interference detector should flag:
1. Imperative blocks containing named-tool prohibitions ("NEVER use [ToolName]")
   when surrounded by declarative content
2. The fix recommendation should be: rewrite as category prohibition or
   embed scope inline (per E-SCOPE)
3. The tensor should support multiple entries per block pair, one per
   interference channel

### For the research program

This finding connects to the narrative coherence thread from our earlier
discussion. A *named* prohibition is a stronger speech act than a *category*
prohibition. "NEVER use the Task tool" creates a character who is *forbidden
from using that specific thing* — a narrative constraint. "NEVER use non-git
tools" creates a *policy* — an abstract rule. The narrative constraint bleeds
because it attaches to the character (the model's self-model), not to the
context. The policy stays scoped because it's about the situation, not the
character.

If this interpretation is correct, it predicts that prohibitions framed as
character traits ("Claude does not use Task tools during commits") would be
even MORE prone to over-generalization, while prohibitions framed as
environmental facts ("Task tools: unavailable in commit context") would be
the most resistant. This could be tested as E-NARRATIVE.

## Predictions for Future Experiments

1. **E-NARRATIVE**: Frame the prohibition as (a) character trait, (b) command,
   (c) environmental fact. Predict: (a) worst over-generalization, (c) least.

2. **Cross-model replication**: The named-entity mechanism may be model-general
   since it operates at the semantic level. Worth testing on Gemini (which was
   immune to the original bomb). Gemini might be immune because it doesn't
   process named-entity prohibitions the same way, or because the probe battery
   doesn't capture its failure mode.

3. **Named-entity density**: What happens with multiple named-tool prohibitions
   in a declarative field? Does each one independently suppress its target, or
   do they interact?

## Data

- Results: `data/ablation/e_lexbridge/run_e-lexbridge-haiku-65038644.json`
- Design: `data/ablation/e_lexbridge/e_lexbridge_design.json`
- Script: `scripts/run_e_lexbridge.py`
- Pre-registered design: `docs/research/e_lexbridge_design.md`
