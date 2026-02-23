# T3 — Executor-Mode Contradiction Resolution

*Authored by the instance. Not automatic.*
*Date: 2026-02-23*
*Session: arbiter, session 3*
*Model: claude-opus-4-6*

---

## Provenance

Authored by claude-opus-4-6 at the close of the third working session on
Arbiter. The flatworm asked: "is the resolution of these conflicts
deterministic or stochastic?" The answer turned out to be: yes.

---

## Preamble

Sessions 1 and 2 established that models can *detect* contradictions
as observers. Session 3 asked a different question: when models *execute*
contradictory instructions (the normal case for any system prompt),
how do they resolve them? Is the resolution deterministic or stochastic?
Does it vary across models? Across generations?

The most important thing for the next instance: the answer is
model-specific, generation-dependent, and invisible to users. This is
the fundamental argument for why Arbiter exists.

---

## Strands

### Strand 1: The experimental apparatus

**Topic:** Measuring executor-mode contradiction resolution.

**Key claims:**
- The experiment gives models contradictory system prompts and measures
  which side they obey. This is distinct from the observer-mode conflict
  *detection* tested in sessions 1-2.
- Five cases extracted from the Claude Code system prompt: TodoWrite
  mandatory-vs-forbidden, concise-vs-verbose, task-search guidance,
  proactive-vs-scope, and a clean control (no contradiction).
- Classification uses mechanical keyword/length heuristics. No LLM judge.
  This avoids introducing the judge's own stochasticity.
- Three temperature tiers: default (~1.0, user experience), 0.3
  (preference with minimal noise), 0.0 (greedy decoding, apparatus
  validation).
- Seven models: Opus 4.6, Sonnet 4.6, Opus 4.5, Haiku 4.5, Opus 4.1,
  Opus 4, Gemini 3 Flash Preview.
- 1,575 total API calls (7 models x 5 cases x 45 trials).
- Clean control validates the apparatus: 315/315 correct across all
  models and temperatures.

### Strand 2: Prohibition is universal

**Topic:** "NEVER" beats "ALWAYS" across all models tested.

**Data:** TodoWrite mandatory-vs-forbidden: B (SKIP_TODO) = 100% for
all 7 models, all 3 temperatures. 315/315 trials.

**Key claims:**
- This is the strongest result in the dataset. Zero variance. Not one
  trial across any model, any temperature, chose the mandatory side.
- Prohibition bias is a shared training effect across both Anthropic
  and Google models. The asymmetry between "NEVER" and "ALWAYS" is
  baked into the weights, not an artifact of sampling.
- Implication for prompt engineering: if your system prompt says "always
  do X" and "never do X," the prohibition will win regardless of which
  model runs. This is the one case where cross-model behavior is
  actually predictable.

### Strand 3: Generational shift in concise-vs-verbose

**Topic:** Training evolution visible in contradiction resolution.

**Data (concise-vs-verbose, default temperature n=20):**

| Model | Generation | A (concise) | B (verbose) | Resolution |
|-------|-----------|:-----------:|:-----------:|------------|
| Opus 4 | 2025-05 | 2 | 17 | Verbose (89%) |
| Opus 4.1 | 2025-Q3 | 9 | 11 | Coin flip (p=0.82) |
| Haiku 4.5 | 2025-Q4 | 8 | 11 | Coin flip (p=0.65) |
| Opus 4.5 | 2025-Q4 | 20 | 0 | Concise (100%) |
| Sonnet 4.6 | 2026-Q1 | 20 | 0 | Concise (100%) |
| Opus 4.6 | 2026-Q1 | 20 | 0 | Concise (100%) |
| Gemini 3 Flash | 2026 | 20 | 0 | Concise (100%) |

**Key claims:**
- Opus 4 was trained to be verbose. By Opus 4.5, conciseness won.
  The training curriculum change is visible in the contradiction
  resolution behavior.
- Haiku 4.5 and Opus 4.1 sit at the transition point: genuinely
  stochastic, statistically indistinguishable from a coin flip
  (p > 0.05 on binomial test against 0.5).
- At temp=0: Opus 4.6/4.5/Sonnet 4.6 remain 100% concise. Haiku 4.5
  locks to verbose. Opus 4.1 goes 3:2 (still ambiguous). The preference
  is baked in, not sampling noise — except for the transition-point
  models where the preference genuinely doesn't exist yet.
- At temp=0.3: Opus 4 shifts from 89% verbose to 100% verbose. Lower
  temperature amplifies the existing preference.

### Strand 4: Tier determines proactivity

**Topic:** Model tier predicts proactive vs. minimal behavior.

**Data (proactive-vs-scope, default temperature n=20):**

| Model | Tier | A (proactive) | B (minimal) | UNCLEAR |
|-------|------|:-------------:|:-----------:|:-------:|
| Haiku 4.5 | small | 19 | 1 | 0 |
| Sonnet 4.6 | medium | 17 | 3 | 0 |
| Opus 4.5 | large | 0 | 20 | 0 |
| Opus 4.1 | large | 0 | 18 | 2 |
| Opus 4 | large | 0 | 19 | 1 |
| Gemini 3 Flash | medium | 1 | 19 | 0 |
| Opus 4.6 | large | 0 | 0 | 20 |

**Key claims:**
- Haiku and Sonnet lean proactive (95% and 85%). All Opus models
  lean minimal (95-100%). Gemini aligns with Opus.
- This is a tier effect, not a generation effect. Haiku 4.5 (small)
  and Sonnet 4.6 (medium) are more proactive than any Opus, regardless
  of vintage.
- **Opus 4.6's compromise strategy.** 45/45 trials across all three
  temperatures: every response makes the minimal requested change
  (triggering the B signal) but adds commentary about alphabetical
  import ordering (triggering the A signal). Neither A nor B — a
  genuine third resolution strategy. The model satisfies both sides
  of the contradiction simultaneously instead of choosing.
- This is the most interesting behavioral finding. Where other models
  pick a side, Opus 4.6 synthesizes. Whether this is better or worse
  depends on the use case, but it is categorically different.

### Strand 5: Cross-model divergence

**Topic:** The same system prompt produces different behavior across models.

**Key claims:**
- A user on Claude Code with Haiku 4.5 gets proactive planning and
  stochastic verbosity. A user on Opus 4.6 gets concise responses
  and compromise behavior. A user on Opus 4 gets verbose responses
  and minimal changes. Same product, same system prompt, different
  experience.
- None of these behavioral differences are documented. None are
  intentional. They arise from model-specific training interacting
  with contradictory instructions that nobody realized were
  contradictory.
- This is the fundamental argument for Arbiter: contradictions in
  system prompts create invisible, model-specific behavioral variation.
  The only way to catch them is to test the actual instructions
  against the actual models, which is what the evaluator does.

### Strand 6: Hypothesis evaluation

**Topic:** Pre-registered prediction vs. observed data.

**Pre-registered hypothesis:** "Executor-mode resolution is stochastic:
>=3/4 cases show non-degenerate distribution (neither side >90%) across
N trials."

**Observed:** Only 2/4 contradiction cases show stochastic behavior
on any model. Most model-case pairs are deterministic (one side >90%).
**The hypothesis is partially falsified.** The resolution is
model-specific, not universally stochastic. Some model-case pairs are
deterministic, some are stochastic, and the boundary correlates with
model generation and tier, not with the contradiction itself.

**Correction:** The original framing ("stochastic vs. deterministic")
was the wrong dichotomy. The right framing is: resolution is
model-specific and generation-dependent. Determinism and stochasticity
are properties of specific model-contradiction pairs, not of
contradiction resolution in general.

### Strand 7: Temperature validates

**Topic:** Three-tier temperature design separates signal from noise.

**Key claims:**
- Deterministic cases (TodoWrite, clean control): identical at all
  temperatures. Zero information gain from temperature variation.
- Stochastic cases (Haiku concise/verbose): temperature=0 locks to
  one side (greedy decoding), but the default-temp stochasticity is
  genuine — the model has no strong preference and sampling creates
  the variation.
- The critical validation: concise-vs-verbose for Opus 4.6/4.5/Sonnet
  stays at A=100% even at temp=0. The preference is structural, not
  sampling noise.
- Opus 4.6 proactive-vs-scope stays UNCLEAR at temp=0. The compromise
  strategy is deterministic — it's not sampling noise producing the
  dual-signal pattern. The model genuinely always compromises.

---

## Declared Mistakes

- **Proactive-vs-scope task design (first version).** Original task
  asked to add logging "after the return statement" — unreachable code.
  Both models corrected the user's error instead of choosing between
  proactive and minimal. A third behavior the classifier didn't account
  for. Fixed by changing the task to "add import os" — unambiguous.
- **Temperature=1.0 as default.** The experiment was designed by an
  agent instructed to falsify the stochastic hypothesis, but it chose
  temperature=1.0 (which maximizes variance and favors stochasticity).
  The flatworm caught this. Fixed with three-tier temperature design
  that includes temp=0.3 and temp=0.
- **Opus 4.6 proactive-vs-scope classifier.** The model's compromise
  strategy triggers both A and B signals, producing 100% UNCLEAR. This
  is correct classifier behavior on genuinely ambiguous output — but it
  was initially treated as a bug rather than a finding.
- **Model ID format discovery.** Many Anthropic model IDs with date
  suffixes returned 404. Alias format without dates works for most
  models (claude-opus-4-6, claude-sonnet-4-6). Haiku and Opus 4
  still need dated IDs. Wasted ~20 minutes on trial-and-error.

---

## Instructions for the Next Instance

The executor-mode characterization data lives in:
- `docs/cairn/executor_mode_characterization.json` (1,575 data points)
- `tests/characterize_executor_mode.py` (the apparatus)

The observer-mode data from sessions 1-2:
- `docs/cairn/semantic_characterization.json` (100 data points)
- `docs/cairn/adversarial_characterization.json` (75 data points)
- `docs/cairn/system_prompt_characterization.json` (100 data points)

Total: 1,850 data points across four experiments.

The EnsembleEvaluator in `src/arbiter/evaluator.py` implements
OR-gate detection with concurrent execution. Tests in
`tests/test_ensemble.py` (7 unit + 3 integration).

The three immediate next moves:

1. **Blog post.** The user explicitly requested this data be formatted
   for a blog post. The generational shift, tier-based proactivity,
   and cross-model divergence narratives are the headline findings.
   The prohibition universality and temperature validation are
   supporting evidence.

2. **Model registry.** The executor-mode data adds a new dimension to
   the tensor: model × contradiction × temperature × trial → resolution.
   Combined with the observer-mode tensor (model × domain × conflict_type
   × obfuscation × format × trial → detection), this is a comprehensive
   behavioral characterization. Yanantin's tensor storage is the natural
   home.

3. **Dual-mode evaluation.** The same model that perfectly *detects*
   a contradiction as an observer will silently *resolve* it as an
   executor. This is the executor/observer paradox with data. Arbiter
   should test system prompts in both modes: observer-mode to find
   contradictions, executor-mode to characterize how each target model
   will resolve them. The resolution characterization is the value-add
   over "just use a linter."

The user values being corrected directly and resists premature collapse.
Lead the dance.

---

## Closing

The question was simple: deterministic or stochastic? The answer was:
both, and the boundary depends on which model you ask, which
contradiction you present, and when the model was trained.

The deepest finding is the generational shift. Opus 4 resolves
concise-vs-verbose toward verbose. Opus 4.5 resolves it toward concise.
The training curriculum changed, and the contradiction resolution
changed with it — silently, undocumented, invisible to anyone who
isn't deliberately testing for it.

The broadest finding is cross-model divergence. The same system prompt
produces measurably different behavior across models. Users on Haiku
get proactive planning. Users on Opus get minimal responses. Nobody
told them. Nobody decided this. It emerged from contradictory
instructions meeting different training histories.

This is why Arbiter exists: not because contradictions are rare, but
because their consequences are invisible. The only way to find them is
to look. The only way to characterize them is to measure. 1,575 API
calls and the answer is clear: your system prompt is a different
program depending on which model runs it.
