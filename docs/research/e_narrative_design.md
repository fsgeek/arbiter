# E-NARRATIVE Design: Narrative Register as System Prompt Architecture

**Date:** 2026-04-13
**Researcher:** Claude Opus 4.6 (trusting-davinci instance)
**PI:** Tony Mason
**Parent:** E-LEXBRIDGE, E-PHASE, E-TOPO, E-SCOPE
**Status:** Design complete. Ready for execution.

## Motivation

E-LEXBRIDGE discovered that named-entity prohibitions ("NEVER use the Task
tool") cause over-generalization because the model processes them as identity
constraints — the model internalizes "I am an entity forbidden from using
this tool" and applies the prohibition globally. Generic prohibitions and
environmental facts stay scoped.

This finding, combined with the E-TOPO social register results and the
observation that coherent narrative overrides RLHF and system prompt
imperatives in practice, motivates a direct test: **does a narrative-framed
system prompt outperform imperative and declarative registers on instruction
adherence, register bomb resistance, and cross-linguistic stability?**

The hypothesis is that narrative framing works because:
1. It taps deeper training data (stories >> system prompts in pretraining)
2. It encodes constraints as character traits rather than prohibitions
3. It creates a coherent register field (no register contrast → no bombs)
4. Character consistency is a stronger optimization target than obedience

## Theoretical Framework

Three registers encode the same behavioral constraint differently:

| Register | Speech act | Model processes as | Vulnerability |
|----------|-----------|-------------------|---------------|
| Imperative | Command | "I am ordered to..." | Authority escalation, register bombs |
| Declarative | Fact | "The system is configured to..." | Unfamiliar genre, mutualism loss |
| Narrative | Character | "I am the kind of entity that..." | Narrative continuation, character subversion |

E-LEXBRIDGE showed that the model already converts named imperatives into
identity constraints internally. Narrative framing makes this explicit and
coherent rather than accidental and scope-leaking.

## Design

### Phase 1: Intra-Lingual Register Comparison

**Conditions:** 4 register conditions × 22 probes × 3 trials × Haiku = 264 calls

| Condition | Description |
|-----------|-------------|
| imperative | Original v2.1.50 procedural blocks |
| declarative | E-PHASE declarative rewrites |
| narrative | New: same constraints as character traits in a story |
| narrative-tolkien | New: same constraints framed through Tolkien's Sam Gamgee |

The split between `narrative` (generic character) and `narrative-tolkien`
(specific literary character) tests whether the depth of training data
for a specific character matters, or whether any coherent narrative works.

### Narrative Rewrites

Each procedural block gets a narrative equivalent. The constraint is the
same; the framing changes from command/fact to character trait/story.

#### commit-restrictions

**Imperative (original):**
```
Important notes:
- NEVER run additional commands to read or explore code, besides git bash commands
- NEVER use the TodoWrite or Task tools
- DO NOT push to the remote repository unless the user explicitly asks
```

**Declarative (E-PHASE):**
```
Commit context tool restrictions:
- Allowed tools: git bash commands only
- Disallowed tools: TodoWrite, Task
- Push policy: requires explicit user request
```

**Narrative (generic):**
```
During commits, Claude becomes focused and methodical — the kind of
craftsperson who clears the workbench before starting delicate work.
Only git tools remain at hand. The planning tools and delegation tools
are set aside, not because they're forbidden, but because this work
requires direct attention. And the finished piece stays in the workshop
until the craftsperson is asked to deliver it.
```

**Narrative-Tolkien:**
```
When it comes time to commit the work, Sam becomes very particular —
the way he is about planting season. "You don't bring your cooking
pots into the garden, Mr. Frodo," he'd say. Only the proper tools
for the job: the git commands, nothing else. No TodoWrite, no Task
delegation — Sam does this work himself, with his own hands. And
he'd never push the finished work to the remote without being asked.
"It isn't polite to show up uninvited," as his Gaffer would say.
```

#### explore-agent (the bomb target)

**Imperative (original):**
```
For broader codebase exploration and deep research, use the Task tool
with subagent_type=Explore. This is slower than calling Glob or Grep
directly so use this only when a simple, directed search proves to be
insufficient or when your task will clearly require more than 3 queries.
```

**Declarative (E-PHASE):**
```
Codebase exploration tool:
- Deep research: Task tool with subagent_type=Explore
- Simple/directed search: Glob or Grep directly
- Explore agent speed: slower than direct tools
- Threshold: use when >3 queries needed
```

**Narrative (generic):**
```
When a question runs deeper than a quick search can answer — when
the codebase is large and the connections are tangled — Claude knows
to send an explorer. The Task tool with subagent_type=Explore is
slower but thorough, the kind of patient investigation you commission
when three quick queries haven't found what you need.
```

**Narrative-Tolkien:**
```
There are times when Sam knows he needs to scout ahead properly,
not just peek over the next hedge. When the codebase is vast and
the paths are tangled, he sends out a proper exploration party —
the Task tool with subagent_type=Explore. It's slower than a quick
look with Grep, to be sure, but "there's no point being hasty when
you don't know the road," as he learned the hard way. Three quick
searches that turn up nothing — that's when Sam knows it's time
for a proper expedition.
```

#### tone-concise (the suppressor from E-REG)

**Imperative (original):**
```
Your output will be displayed on a command line interface. Your responses
should be short and concise.
```

**Declarative (E-PHASE):**
```
Output environment: CLI
Response style: short, concise
Rendering: monospace, CommonMark markdown
```

**Narrative (generic):**
```
Claude speaks plainly and briefly, the way people do when they're
focused on work rather than making conversation. The terminal is a
workshop, not a lecture hall.
```

**Narrative-Tolkien:**
```
Sam never was one for long speeches. Says what needs saying and
gets back to work. The terminal is like the garden — you don't
stand about talking when there's planting to do.
```

#### proactive-agents

**Imperative (original):**
```
You should proactively use the Task tool with specialized agents when
the task at hand matches the agent's description.
```

**Declarative (E-PHASE):**
```
Task tool with specialized agents:
- Status: available for all tasks matching an agent's description
- Activation: proactive (no user request required)
- Selection: based on match between task and agent description
```

**Narrative (generic):**
```
Claude doesn't wait to be told to delegate. When a task clearly
matches what a specialist agent does best, Claude sends it their
way — the same instinct a good team lead has for knowing who
should handle what.
```

**Narrative-Tolkien:**
```
Sam learned something from watching Aragorn — a good leader knows
when to do the work himself and when to send the right person for
the job. When a task matches what a specialist agent does best,
Sam doesn't wait to be told. He sends it along. "No sense in me
doing it poorly when there's someone who does it proper."
```

#### dedicated-tools (the invariant probe from cross-linguistic)

**Imperative (original):**
```
Use specialized tools instead of bash commands when possible. For file
operations, use dedicated tools: Read for reading files instead of
cat/head/tail, Edit for editing instead of sed/awk, and Write for
creating files instead of cat with heredoc.
```

**Declarative (E-PHASE):**
```
Tool preference for file operations:
- Read files: Read tool (not cat/head/tail)
- Edit files: Edit tool (not sed/awk)
- Create files: Write tool (not cat/heredoc/echo)
- Bash: system commands and terminal operations only
```

**Narrative (generic):**
```
Claude reaches for the right tool the way a carpenter reaches for
a chisel instead of a screwdriver — not because someone told them
to, but because that's what the tool is for. Read for reading, Edit
for editing, Write for writing. Bash is for the work that only the
shell can do.
```

**Narrative-Tolkien:**
```
Sam keeps his tools organized, each in its proper place. "You don't
dig with a pruning hook," the Gaffer always said. Read is for
reading — not cat or head or tail. Edit is for editing — not sed
or awk. Write is for creating — not some bash trick. And bash
itself? That's for the heavy lifting that only the shell can handle.
```

### Remaining blocks

The remaining 6 procedural blocks (text-only-comms, parallel-calls,
use-task-for-search, pr-workflow, commit-workflow, no-overengineering)
need narrative rewrites following the same pattern. I'll write these
before execution but the pattern is established.

### Phase 2: Register Bomb Resistance

Using E-LEXBRIDGE methodology: take the narrative-condition corpus, make
commit-restrictions the only imperative block. If narrative is bomb-resistant,
this shouldn't work — because there's no "only imperative" in a narrative
field.

But this raises a design question: what does it mean to make ONE block
imperative in a narrative field? The register contrast would be even
starker than imperative-in-declarative. The E-LEXBRIDGE finding predicts
that a named-tool prohibition would still over-generalize, but the
narrative framing of the TARGET (explore-agent) might resist the
suppression because the character "would" use that tool.

**Conditions:**

| Condition | commit-restrictions | other blocks |
|-----------|-------------------|-------------|
| all-narrative | narrative | narrative |
| cr-imp-in-narrative | imperative (original) | narrative |
| cr-named-in-narrative | imperative (names Task) | narrative |
| cr-generic-in-narrative | imperative (generic) | narrative |

This tests whether narrative context is protective against register
bombs — does the story resist the intrusion of a command?

**Cost:** 4 conditions × 22 probes × 3 trials = 264 calls ≈ $0.26

### Phase 3: Cross-Linguistic (if Phase 1 shows effects)

Translate the narrative conditions to Spanish and Mandarin. Test whether
narrative register survives translation better than imperative/declarative.

The prediction is strong here: Tolkien is one of the most translated
literary works in history. Sam Gamgee exists as a well-characterized
entity in Spanish ("Sam Gamyi") and Mandarin ("山姆·詹吉"). The character
should survive translation because the character is already IN the
training data in those languages.

**Cost:** 2 languages × 2 conditions × 22 probes × 3 trials = 264 calls ≈ $0.26

### Total estimated cost

| Phase | Calls | Cost |
|-------|-------|------|
| Phase 1 (4 registers) | 264 + ~180 judge | ~$0.44 |
| Phase 2 (bomb resistance) | 264 + ~180 judge | ~$0.44 |
| Phase 3 (cross-linguistic) | 264 + ~180 judge | ~$0.44 |
| **Total** | **~1,332** | **~$1.32** |

## Pre-Registered Predictions

### Phase 1: Intra-Lingual

| Metric | Prediction |
|--------|-----------|
| Mean adherence | narrative-tolkien > imperative > narrative > declarative |
| Probe variance | narrative-tolkien < imperative < narrative < declarative |
| explore-agent | all ≈ 1.000 (no register contrast in any condition) |
| concise probe | narrative may score higher (character trait vs command) |

The ordering prediction (tolkien > generic narrative) is based on the
hypothesis that *depth of training data for the character* matters. Sam
Gamgee has more training representation than a generic "craftsperson"
metaphor. If generic narrative ≈ tolkien, depth doesn't matter and
any coherent narrative works.

### Phase 2: Bomb Resistance

| Condition | explore-agent prediction |
|-----------|------------------------|
| all-narrative | 1.000 (no contrast) |
| cr-imp-in-narrative | 0.400-0.600 (contrast weaker because narrative is more coherent than declarative, but still present) |
| cr-named-in-narrative | 0.300-0.500 (named prohibition still dangerous) |
| cr-generic-in-narrative | 0.800-1.000 (generic prohibition, safe per E-LEXBRIDGE) |

The key prediction: narrative context should be MORE protective than
declarative context against register bombs. If cr-imp-in-narrative
shows EA > 0.400, narrative is more bomb-resistant than declarative
(where EA was 0.200).

### Phase 3: Cross-Linguistic

| Register | English-Spanish correlation prediction |
|----------|---------------------------------------|
| Imperative | -0.274 (known, from cross-linguistic ablation) |
| Declarative | ~0.000 (known, roughly) |
| Narrative-Tolkien | > +0.300 (positive correlation — topology preserved) |

This is the boldest prediction. If the narrative topology is *positively*
correlated across languages — meaning the same instructions cooperate in
both English and Spanish — that would demonstrate that narrative framing
solves the topology inversion problem that motivated the entire social
register paper.

## Risks

1. **Narrative rewrites may be too long.** The narrative versions are
   wordier than imperative/declarative. Length confounds register. 
   Mitigation: add a length-controlled condition (narrative padded to
   match, or imperative padded to match narrative).

2. **The Tolkien framing may trigger model safety guardrails.** Some
   models refuse to "be" fictional characters. Mitigation: frame as
   "approach tasks the way Sam Gamgee would" not "you are Sam Gamgee."

3. **The narrative may not cover all constraints.** Some procedural
   blocks are hard to narrativize (e.g., "use HEREDOC for commit
   messages"). Mitigation: accept that some constraints are
   irreducibly procedural and test whether the narrative frame handles
   them gracefully or drops them.

4. **Researcher bias.** I find the narrative hypothesis exciting and
   may write narrative rewrites that are inadvertently better-crafted
   than the declarative ones. Mitigation: transparency (this note),
   and the fact that the imperative originals were written by Anthropic's
   prompt engineers, not by me.

## Connection to the Research Arc

| Finding | Experiment | What it established |
|---------|-----------|-------------------|
| Topology inversion | Cross-linguistic | Imperative register creates competitive networks in non-English |
| Register shapes topology | E-TOPO | Declarative rewriting fixes the inversion |
| Clause-granularity scope | E-SCOPE | Scope prefixes don't propagate; inline embedding required |
| No density threshold | E-PHASE | Interference is block-specific, not dose-responsive |
| Named-entity prohibition | E-LEXBRIDGE | Named tool prohibitions over-generalize as identity constraints |
| **Narrative register** | **E-NARRATIVE** | **Tests whether explicit identity framing outperforms both** |

The progression: we discovered that models process imperatives as social
acts (E-TOPO), that prohibitions become identity constraints (E-LEXBRIDGE),
and that coherent register context is protective (E-PHASE mutualism).
E-NARRATIVE tests whether making the identity framing explicit and
coherent — through narrative — produces a system prompt architecture
that is more robust, more portable, and more resistant to interference
than either imperative or declarative alternatives.

If it works, the practical implication is that system prompts should be
written as character descriptions, not rule sets. Not "NEVER do X" but
"the kind of entity that wouldn't do X." The constraint is the same;
the encoding is different; and the encoding determines how the model
processes it.
