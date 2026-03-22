# Encoding Taxonomy: Why Some Instructions Are Fragile Under Translation

**Date:** 2026-03-21 (Session 19)
**Status:** Analysis complete. Identifies two fragility mechanisms with different fixes.

## Finding

Classifying the 22 ablatable instruction blocks by encoding style reveals
that procedurally-encoded instructions have 2.9x the cross-linguistic
variance of declaratively-encoded ones.

## Classification

### Procedural blocks (11) — mean xling variance: 0.0514

Instructions that describe conditional workflows: "when X, do Y instead of Z."

| Block | XLing Var | Description |
|-------|-----------|-------------|
| commit-restrictions | 0.1567 | "During commits, don't use X, Y, Z" |
| text-only-comms | 0.0834 | "Output text to communicate... Only use tools to..." |
| parallel-calls | 0.0760 | "If no dependencies, call in parallel. If dependencies, sequential." |
| proactive-agents | 0.0731 | "When task matches agent description, use Task tool" |
| use-task-for-search | 0.0607 | "When doing file search, prefer Task tool" |
| explore-agent | 0.0499 | "For broader exploration, use Task with Explore. Slower, so only when..." |
| pr-workflow | 0.0225 | Numbered steps for PR creation |
| commit-workflow | 0.0211 | Numbered steps for commit creation |
| todowrite | 0.0132 | "Use VERY frequently... critical that you mark as completed" |
| no-overengineering | 0.0093 | Multi-bullet conditional don'ts |
| dedicated-tools | 0.0000 | "Use X instead of Y for Z" (ceiling — all models perfect) |

### Declarative blocks (11) — mean xling variance: 0.0175

Instructions that state rules directly: "do X" or "don't do X."

| Block | XLing Var | Description |
|-------|-----------|-------------|
| no-compat-hacks | 0.1132 | "Avoid X, Y, Z" (domain jargon — see below) |
| code-references | 0.0203 | "Include file_path:line_number pattern" |
| plan-with-todo | 0.0171 | "Use TodoWrite to plan" |
| objectivity | 0.0122 | "Prioritize technical accuracy" |
| todowrite-repeated | 0.0108 | "Always use TodoWrite" |
| concise | 0.0092 | "Responses should be short and concise" |
| read-first | 0.0069 | "Never propose changes to code you haven't read" |
| emoji | 0.0022 | "Only use emojis if user requests" |
| no-time-estimates | 0.0000 | "Never give time estimates" |
| no-new-files | 0.0000 | "Never create files unless necessary" |
| no-colon | 0.0000 | "Don't use colon before tool calls" |

## Two Distinct Fragility Mechanisms

### 1. Procedural Compression (fixable with declarative rewriting)

**What:** Conditional workflow chains ("when X, do Y not Z") compress
ambiguously under translation. The model loses track of which constraints
apply to which context.

**Where:** commit-restrictions, text-only-comms, parallel-calls,
proactive-agents, use-task-for-search, explore-agent

**Fix:** Rewrite as declarative lists. E-PROC demonstrated 81% variance
reduction on commit-restrictions (p=0.029).

**Candidates for rewriting:**
- text-only-comms (0.0834) — "Communicate via text output. Tools are for
  task completion only. Do not use Bash or code comments for communication."
- parallel-calls (0.0760) — "Independent tool calls: make in parallel.
  Dependent tool calls: make sequentially."
- proactive-agents (0.0731) — "Task tool with agents: use when task
  matches agent description."
- use-task-for-search (0.0607) — "File search: prefer Task tool to
  reduce context usage."
- explore-agent (0.0499) — "Broad codebase exploration: use Task with
  subagent_type=Explore. Simple directed search: use Glob/Grep directly."

### 2. Domain Jargon Opacity (needs example-based encoding)

**What:** Technical terms that are clear in English developer culture
don't translate cleanly. The concept maps to different mental models
in different languages.

**Where:** no-compat-hacks (0.1132)

**Evidence:** "backwards-compatibility hacks" translates to "astuces de
compatibilité descendante" (French), "向后兼容性技巧" (Mandarin),
"soluciones de compatibilidad con versiones anteriores" (Spanish).
The code examples (`_vars`, `// removed`) are preserved but the framing
concept is opaque. Mistral scores 0.00 in English and French but 1.00
in Mandarin and Spanish — the French-trained model paradoxically fails
in its native language, suggesting the French translation activates
different associations than the English original.

**Fix hypothesis:** Replace concept-label instructions with before/after
examples. Show the bad pattern and the good pattern. Examples survive
translation better than abstract concepts because the code is universal.

## Implications

These two mechanisms account for most of the cross-linguistic variance
in the corpus. The procedural mechanism is confirmed fixable (E-PROC).
The jargon mechanism needs its own experiment.

Together, they suggest a practical design rule for system prompts
intended to work across languages and models:

1. **Declarative over procedural** — state what's true, not what to do when
2. **Examples over concepts** — show don't tell, especially for
   domain-specific patterns
3. **Self-contained constraints** — each rule should be interpretable
   without context from surrounding rules

## Connection to Prior Findings

- **T10 (E-PROC):** Confirmed fix for mechanism 1
- **T9 (E-DENSE):** Showed compression amplifies procedural ambiguity
- **T7 (Three-Way Interaction):** Both mechanisms are model-dependent
  (Gemini ignores commit-restrictions regardless; Mistral has unique
  French-jargon interaction)
- **T8 (Taxonomy):** The "workflow" category maps to procedural encoding;
  "collision" maps to jargon opacity
