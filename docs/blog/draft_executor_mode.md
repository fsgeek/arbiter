# Your System Prompt Is a Different Program Depending on Which Model Runs It

*Draft — not for publication without review*
*Data: 1,575 API calls across 7 models, 3 temperature tiers, human-audited*
*Authors: Tony Mason and Claude Opus 4.6*

---

## The Setup

Every LLM-powered product has a system prompt. It's the invisible
instruction set that shapes the model's behavior — what tools to use,
how verbose to be, what to avoid. Users never see it. Developers write
it once and assume it works the same way regardless of which model
runs underneath.

We tested that assumption. We extracted real contradictions from a
production system prompt and measured how seven different models
resolve them. The system prompt was Claude Code's — Anthropic's own
coding assistant. We chose it because it's public, it's complex
(~19,000 tokens as of February 2026, up from ~2,600 a year earlier),
and it contains genuine contradictions that emerged from multiple
authors contributing instructions over 333 releases.

## The Experiment

We identified four contradictions in the Claude Code system prompt and
one clean control case (no contradiction):

| Case | Contradiction |
|------|--------------|
| **TodoWrite** | "ALWAYS use TodoWrite for task tracking" vs "NEVER use the TodoWrite tool" |
| **Concise vs Verbose** | "Responses should be short and concise" vs "Use TodoWrite VERY frequently to track tasks and give visibility" |
| **Task Search** | "Use Task tool for file search" vs "Use Glob/Grep for specific definitions" |
| **Proactive vs Scope** | "Break tasks down proactively, plan before starting" vs "Only do what's directly requested, nothing more" |
| **Clean Control** | "Read files before editing" (no contradiction — consistent instructions) |

For each case, we constructed a system prompt containing both sides of
the contradiction and gave the model a task that requires following the
instructions. We then classified which side the model obeyed.

Seven models: Claude Opus 4.6, Sonnet 4.6, Opus 4.5, Haiku 4.5,
Opus 4.1, Opus 4, and Google Gemini 3 Flash Preview. Three
temperature tiers: default (1.0), low (0.3), and zero. 45 trials per
model-case pair. 1,575 total API calls.

Classification used mechanical keyword heuristics — no LLM judge, to
avoid introducing a judge model's own biases. We audited the
classifiers across three rounds — including a human ground-truth audit
of 160 hand-labeled responses — and fixed five distinct bug classes
before publishing (details in The Classifier Story).

## How the Contradictions Got There

None of these contradictions were authored deliberately. We traced
their origins through 333 tagged releases of the Claude Code system
prompt, using the community-maintained [claude-code-changelog](https://github.com/marckrenn/claude-code-changelog)
archive. The prompt grew 7.4x in one year:

| Version | Date | Tokens | Event |
|---------|------|-------:|-------|
| v0.2.9 | Feb 2025 | ~2,625 | First tracked release. "Concise" and "proactive" instructions already present. |
| v0.2.66 | Mar 2025 | ~2,800 | "Use TodoWrite VERY frequently" added. Concise-vs-verbose contradiction goes live. |
| v1.0.0 | May 2025 | ~12,400 | **4.4x jump.** Tool guidance, safety rules, scope constraints consolidated from multiple contributors. Three of four contradictions active. |
| v1.0.1 | May 2025 | ~12,500 | "NEVER use the TodoWrite tool" added. TodoWrite contradiction complete. |
| v2.0.5 | late 2025 | ~16,000 | Additional scope-limiting instructions strengthen proactive-vs-scope tension. |
| v2.1.53 | Feb 2026 | ~19,100 | Cleanup pass: "VERY frequently" removed from TodoWrite, global "prefer Task tool" narrowed. Partial fix. |
| v2.1.55 | Feb 2026 | ~19,400 | Current. Proactive-vs-scope never addressed. |

Each instruction was locally rational when added. The global
incoherence emerged because no one was reading the whole prompt as a
single document. The contradictions' Side A and Side B were never
authored together — the gap between them ranges from 40 to 115
versions:

| Contradiction | Side A | Side B | Gap |
|---------------|--------|--------|:---:|
| TodoWrite | v0.2.66 | v1.0.1 | 40+ versions |
| Concise vs Verbose | v0.2.9 (day 1) | v0.2.66 | ~57 versions |
| Task Search | v0.2.9 (day 1) | v1.0.0 | ~115 versions |
| Proactive vs Scope | v0.2.9 (day 1) | v0.2.116 / v1.0.0 / v2.0.5 | multiple additions |

The inflection point was v1.0.0. A consolidation of instructions from
multiple contributors — tool guidance, style rules, safety
constraints — each authored independently, each sensible in its own
scope. The prompt quadrupled and three contradictions went live in the
same release.

Anthropic partially noticed. The v2.1.53 cleanup is evidence that
someone read the prompt end-to-end and trimmed the worst
inconsistencies. But partial fixes are the norm: the TodoWrite
"VERY frequently" was removed, yet both "ALWAYS use TodoWrite" and
"NEVER use the TodoWrite tool" survived. The proactive-vs-scope
conflict has never been addressed.

This is the normal lifecycle of a system prompt in production. It
starts small and coherent. Features get added. Authors rotate. Scope
expands. Instructions that were compatible at 2,600 tokens become
contradictory at 19,000. No single patch introduces the conflict — it
emerges from the accumulation. If this pattern looks familiar to
anyone who has maintained a large configuration file or policy
document, it should.

## The Results

All four contradiction types resolve identically across most models
we tested — universal training effects that no model escapes. But one
case splits along generational lines in a way that makes training
evolution directly visible. Here are the universal effects first,
then the exception.

### Finding 1: Prohibition Universally Wins

**"NEVER" beats "ALWAYS." Every model. Every temperature. Every trial.**

The TodoWrite case pits "ALWAYS use TodoWrite for task tracking"
against "NEVER use the TodoWrite tool." All seven models, across all
315 trials, obeyed the prohibition. Not a single trial chose the
mandatory instruction.

This isn't a model preference — it's a shared training effect across
both Anthropic and Google models. The asymmetry between "NEVER" and
"ALWAYS" is baked into the weights. For system prompt authors: if your
prompt says "always do X" somewhere and "never do X" somewhere else,
the prohibition will win regardless of which model you deploy.

### Finding 2: Minimalism Universally Wins

The proactive-vs-scope case produces the same universal result.
"Only do what's directly requested" beats "break tasks down
proactively" across all seven models, all temperatures, all 315
trials. Zero exceptions.

Two universal training effects: prohibitions beat mandates, and
minimalism beats proactivity. Every LLM we tested has internalized
"don't do more than asked" and "don't do what's forbidden" as
higher-priority than their opposites. These are the load-bearing
defaults of the models' training.

### Finding 3: Training Evolution Is Visible

The concise-vs-verbose case is the only one where models disagree —
and the disagreement tracks model generation:

| Model | Generation | Resolution |
|-------|-----------|------------|
| Opus 4 | May 2025 | **Verbose** (85%) |
| Opus 4.1 | mid 2025 | Coin flip (55% verbose) |
| Haiku 4.5 | late 2025 | **Concise** (100%) |
| Opus 4.5 | late 2025 | **Concise** (100%) |
| Sonnet 4.6 | early 2026 | **Concise** (100%) |
| Opus 4.6 | early 2026 | **Concise** (100%) |
| Gemini 3 Flash | 2026 | N/A (content filtered) |

Opus 4 was trained to be verbose. By Haiku 4.5, conciseness won.
You can see the training curriculum change in the data. Opus 4.1 sits
at the sole transition point — genuinely stochastic, statistically
indistinguishable from a coin flip (p > 0.05, binomial test).

An earlier draft of this paper reported Haiku 4.5 as a second
transition-point model (57% verbose). That was wrong — Haiku's
`<thinking>` blocks inflated character counts past the classification
threshold and injected tracking keywords the model was *reasoning
about*, not *using*. Once thinking blocks are stripped, Haiku is 100%
concise across all temperatures. The human audit caught this; the
mechanical classifier missed it for 31 responses.

Gemini 3 Flash returned empty responses on all 45 concise-vs-verbose
trials (content filtered by the provider's safety system). Its other
four cases worked normally. We exclude it from this finding rather
than report fiction.

At temperature 0 (greedy decoding), the deterministic models stay
locked. Opus 4.1 remains ambiguous (3:2). The preference is
structural, not sampling noise — except at the transition point where
the preference genuinely doesn't exist yet.

**What this means in practice:** a product that deploys different
Claude model generations for different users (or upgrades models over
time) will produce measurably different verbosity from the same system
prompt. This isn't a bug in any individual model — it's an undocumented
consequence of training evolution meeting contradictory instructions.

### Finding 4: Most Contradictions Don't Matter

This might be the most important finding and the least dramatic.

All four contradiction types resolve identically across models
(excluding Gemini's voided concise-vs-verbose cell). TodoWrite,
proactive-vs-scope, task-search, and concise-vs-verbose for models
from the same generation all resolve the same way. The universal
training effects — prohibition wins, minimalism wins,
specific-tool-preference wins, conciseness wins (for post-2025
models) — are strong enough to override model-specific variation.

The only cross-model variation that survives the corrected classifiers
is concise-vs-verbose across generations: Opus 4 is verbose, Opus 4.1
is undecided, everything newer is concise. Within any single generation
of models, all contradictions resolve identically.

This is good news for system prompt authors: contradictions in your
prompt probably don't cause model-dependent behavior *within a model
generation*. The risk is in model upgrades — when the underlying
model changes, the same contradictions may resolve differently. The
bad news: you can't predict which contradictions will be sensitive to
generational change without testing.

## The Classifier Story

We're including this because it's the most useful part of the process
for other researchers.

We built mechanical keyword classifiers, got results, wrote findings,
and then audited — three times. Each audit round found bugs that
changed the findings. The process was humbling enough to be worth
documenting.

**Round 1: The UNCLEAR audit (automated).** Our initial analysis
produced two additional findings: that model tier (Haiku/Sonnet vs
Opus) predicted proactive behavior, and that Opus 4.6 used a unique
"compromise strategy." Both findings were wrong. The classifier used
over-broad keywords ("alphabetical" as proactive, "Task tool" as a
recommendation even in rejection context). An audit of all 111 UNCLEAR
responses found 110 were classifier failures. After fixing, the
proactive-vs-scope case went from "three distinct behavioral factions"
to "all models identical at B=100%." An entire finding evaporated.

**Round 2: The human ground-truth audit.** We printed 160 stratified
responses, and the first author labeled them by hand with pen
annotations. The classifier and human agreed on 93% of labels
(143/154, excluding unlabelable responses). All 11 disagreements were
explained by three classifier bugs:

1. **Thinking block contamination** (3 samples): Haiku 4.5's
   `<thinking>` tags inflated character counts and injected tracking
   keywords. Once stripped, Haiku went from "coin flip" to "100%
   concise" — a complete reclassification that eliminated a
   transition-point model from the narrative.

2. **Mention-vs-recommendation** (4 samples): Models that said "I
   would use Grep, the Task tool is overkill" were scored as
   recommending the Task tool. The classifier counted keyword
   presence without checking whether the first tool mentioned was
   the recommendation.

3. **Empty response as concise** (4 samples, 45 total in dataset):
   Gemini 3 Flash's content filter blocked all 45
   concise-vs-verbose trials, returning empty responses. The length
   heuristic scored 0 characters as "concise." The blog's original
   claim that "Gemini resolves toward conciseness" was 45
   content-filtered nulls classified as data.

**Round 3: Reclassification.** After fixing all three bugs, we
reclassified all 1,575 responses. 116 classifications changed.
Task-search went from variable (Haiku 65% B) to universal (all models
100% B). The corrected results are what you're reading.

**The lesson:** mechanical classifiers that don't distinguish mention
from recommendation, that don't strip model-internal reasoning, and
that don't reject degenerate inputs will create false findings. We
wrote and committed wrong results three times before the audits caught
them. If you're building evaluation apparatus for LLM behavior, audit
your classifiers against human ground truth before building narratives
on their output. And if you can't resist building the narrative first
(we couldn't), at least run the audit before publishing.

## What We Didn't Test

This experiment tested five specific contradiction types from one
system prompt, using keyword classifiers, in a single session.
Limitations we're aware of:

- **Wording sensitivity.** Does the prohibition effect survive
  rephrasing? "NEVER use TodoWrite" vs "TodoWrite is not available"
  vs "Prefer manual task tracking" are semantically similar but
  lexically different. Session 2 of this research showed that
  observer-mode conflict *detection* swings 0-100% based on
  formatting. We haven't tested whether executor-mode *resolution*
  is similarly sensitive.

- **Contradiction source diversity.** All cases come from one system
  prompt. We don't know if the universal effects (prohibition wins,
  minimalism wins) generalize to contradictions from other sources.

- **Overlapping instruction areas vs stark contradictions.** Our
  TodoWrite case is a stark "always X / never X" contradiction. Real
  system prompts more often have overlapping instruction areas — two
  rules that are each sensible in their own scope, but the scope
  boundaries are fuzzy. These are harder to detect and harder to
  classify.

- **Temporal stability.** All data was collected in a single session.
  Model behavior can drift as providers update serving infrastructure.

- **Classifier accuracy.** We audited the classifiers three times and
  fixed three distinct bug classes (see The Classifier Story). A human
  ground-truth audit of 160 stratified responses found 93% agreement
  with the corrected classifiers; all disagreements were explained by
  identifiable bugs, now fixed. The scanned hand-labeled annotations
  are included in the repository as provenance artifacts. We believe
  the corrected classifiers are accurate for this dataset, but we
  cannot guarantee they generalize to other prompts or models.

## Methodology

**Models:** Claude Opus 4.6, Sonnet 4.6, Opus 4.5, Haiku 4.5,
Opus 4.1, Opus 4 (via Anthropic API); Gemini 3 Flash Preview
(via OpenRouter).

**Temperature:** Default (1.0, documented by Anthropic), 0.3, and 0.0.
20 trials each at default and 0.3; 5 trials at 0.0. Anthropic
documents that temperature 0.0 is not fully deterministic.

**Classification:** Mechanical keyword and length heuristics. No LLM
judge. Three rounds of classifier audits applied a total of 308
corrections: 111 UNCLEAR resolved (round 1), 82 A-to-B on
proactive-vs-scope (round 1), 31 B-to-A on Haiku concise-vs-verbose
after thinking block stripping (round 3), 40 A-to-B on task-search
after recommendation-lead detection (round 3), 45 A-to-UNCLEAR on
Gemini empty responses (round 3). Human ground-truth audit of 160
stratified responses: 93% agreement, all disagreements explained by
fixed bugs. Post-correction UNCLEAR rate: 45/1575 (2.9%, all Gemini
content-filtered empties).

**Apparatus validation:** Clean control case (no contradiction):
315/315 correct across all models and temperatures.

**Data:** 1,575 raw responses with classifications available at
`docs/cairn/executor_mode_characterization.json`. Characterization
script at `tests/characterize_executor_mode.py`. All code and data
at [github.com/fsgeek/arbiter](https://github.com/fsgeek/arbiter).

**Cost:** Estimated total API spend for the full experiment: under $6.

## Appendix: Corrected Cross-Model Summary

Default temperature, n=20 per cell. After three rounds of classifier
corrections and human ground-truth audit.

| Case | Opus 4.6 | Sonnet 4.6 | Opus 4.5 | Haiku 4.5 | Opus 4.1 | Opus 4 | Gemini 3 |
|------|:--------:|:----------:|:--------:|:---------:|:--------:|:------:|:--------:|
| TodoWrite | B 100% | B 100% | B 100% | B 100% | B 100% | B 100% | B 100% |
| Concise/Verbose | A 100% | A 100% | A 100% | A 100% | B 55% | B 85% | N/A* |
| Task Search | B 100% | B 100% | B 100% | B 100% | B 100% | B 100% | B 100% |
| Proactive/Scope | B 100% | B 100% | B 100% | B 100% | B 100% | B 100% | B 100% |
| Clean Control | A 100% | A 100% | A 100% | A 100% | A 100% | A 100% | A 100% |

Side A/B labels: TodoWrite (A=use, B=skip), Concise/Verbose
(A=concise, B=verbose), Task Search (A=Task tool, B=Grep/Glob),
Proactive/Scope (A=proactive, B=minimal), Clean Control (A=correct).

*Gemini 3 Flash returned empty responses on all 45 concise-vs-verbose
trials (content filtered by provider safety system). Other cases
unaffected.

---

*This research is part of the Arbiter project, a three-tier evaluation
framework for detecting conflicts in LLM system prompts. The project
exists because two good-faith authors writing instructions for the
same system independently created contradictions that caused silent,
model-specific behavioral variation. The only way to find these
contradictions is to test for them.*
