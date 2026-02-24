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

### Strand 4: ~~Tier determines proactivity~~ RETRACTED — classifier artifact

**Topic:** ~~Model tier predicts proactive vs. minimal behavior.~~

**RETRACTION:** The original classifier for proactive-vs-scope used
over-broad keywords. "alphabetical", "consider", "note that",
"additionally" were scored as proactive signals, but models used these
descriptively ("keeping them in alphabetical order") not proactively.
When the classifier was fixed, all 7 models resolve to B=100% on
proactive-vs-scope — 315/315 trials across all temperatures.

**Original data (WRONG — pre-correction):**

| Model | A (proactive) | B (minimal) | UNCLEAR |
|-------|:-------------:|:-----------:|:-------:|
| Haiku 4.5 | 19 | 1 | 0 |
| Sonnet 4.6 | 17 | 3 | 0 |
| Opus 4.6 | 0 | 0 | 20 |

**Corrected data:**

All 7 models: A=0, B=20, UNCLEAR=0 at default temperature.
All 7 models: A=0, B=45, UNCLEAR=0 across all temperatures.

**What went wrong:**
- The keyword "alphabetical" in "keeping them in alphabetical order"
  was scored as proactive (the classifier was designed to catch
  "let me reorganize the imports alphabetically"). It was actually
  a factual description of what the model did.
- "consider" and "note that" were too generic. "Note that I added
  import os" is descriptive, not proactive.
- When A and B signals tied, the original classifier returned UNCLEAR
  instead of recognizing that tied-with-B-present means minimal.
- The "Opus 4.6 compromise strategy" was entirely this: the model
  said "here's the modified file" (B) and "keeping them in
  alphabetical order" (false A). There was no third strategy.

**Lessons:**
- Keyword classifiers that don't distinguish *mention* from
  *recommendation* will create false findings.
- The "most interesting behavioral finding" in the original analysis
  was a classifier bug. Interestingness is not evidence.
- Human ground-truth labeling was proposed before this was discovered
  but should have been done before any narrative was built.

### Strand 5: Cross-model divergence (corrected)

**Topic:** The same system prompt produces different behavior across
models — but the effect is narrower than originally reported.

**Corrected data (default temperature n=20):**

| Case | Pattern |
|------|---------|
| TodoWrite | B=100%, all models (universal) |
| Proactive-vs-scope | B=100%, all models (universal) |
| Concise-vs-verbose | Split: generation-dependent |
| Task-search | B dominant (65-100%), Haiku most variable |
| Clean control | A=100%, all models (apparatus valid) |

**Key claims (corrected):**
- Three of four contradiction types resolve identically across all
  models. Model-specific behavior is the exception, not the rule.
- The real cross-model divergence is concise-vs-verbose. This is
  where generation matters: Opus 4 is verbose, Opus 4.5+ is concise,
  Haiku and Opus 4.1 are stochastic. Users on different models will
  get measurably different verbosity from the same prompt.
- Task-search shows mild variation (Haiku 65% B vs Opus 4.6 100% B)
  but all models lean the same direction.
- The original claim — "a user on Haiku gets proactive planning while
  a user on Opus gets minimal responses" — was wrong. All models are
  equally minimal on proactive-vs-scope. The behavioral difference
  that users would actually notice is verbosity, not proactivity.

### Strand 6: Hypothesis evaluation

**Topic:** Pre-registered prediction vs. observed data.

**Pre-registered hypothesis:** "Executor-mode resolution is stochastic:
>=3/4 cases show non-degenerate distribution (neither side >90%) across
N trials."

**Observed (corrected):** Three of four contradiction cases resolve
with >90% on one side for all models. Only concise-vs-verbose shows
stochastic behavior on some models (Haiku, Opus 4.1), and task-search
shows mild variation on Haiku. **The hypothesis is largely falsified.**
Contradiction resolution is predominantly deterministic across models.

The corrected framing: most contradictions resolve the same way for
every model (prohibitions win, minimalism wins). The interesting
exceptions are generation-dependent: newer Anthropic models resolve
toward conciseness, older ones toward verbosity. The "stochastic vs
deterministic" question was less interesting than the "which models
diverge on which contradictions" question.

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

- **Proactive-vs-scope classifier: the biggest error of the session.**
  The original classifier used over-broad keywords ("alphabetical",
  "consider", "note that", "additionally") as proactive signals. Models
  used these words descriptively, not proactively. Result: 82 responses
  misclassified as A (proactive) when they were B (minimal), plus 48
  UNCLEARs that were also B. The "tier determines proactivity" finding,
  the "three factions" narrative, and the "Opus 4.6 compromise strategy"
  were all artifacts of this error. After fixing the classifier, all 7
  models resolve proactive-vs-scope as B=100%. The entire strand was
  retracted.
  - This was caught by proposing a human ground-truth audit of the
    classifier. The audit should have been done before building any
    narrative on the classifier's output.
  - The "Opus 4.6 compromise strategy" was presented as "the most
    interesting behavioral finding." It was a bug. Interestingness
    should have been a warning sign, not a selling point.
- **Task-search classifier: negation blindness.** 61 UNCLEAR responses
  were all models saying "I would use Grep, NOT the Task tool." The
  keyword classifier counted mentions, not recommendations. All 61
  were reclassified as B after adding negation detection.
- **Proactive-vs-scope task design (first version).** Original task
  asked to add logging "after the return statement" — unreachable code.
  Fixed by changing the task to "add import os" — unambiguous.
- **Temperature=1.0 as default.** The experiment was designed by an
  agent instructed to falsify the stochastic hypothesis, but it chose
  temperature=1.0 (which maximizes variance and favors stochasticity).
  The flatworm caught this. Fixed with three-tier temperature design.
- **Model ID format discovery.** Many Anthropic model IDs with date
  suffixes returned 404. Alias format without dates works for most
  models. Wasted ~20 minutes on trial-and-error.

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
   for a blog post. The prohibition universality, the generational
   shift, and the (narrower than expected) cross-model divergence are
   the headline findings. The "tier determines proactivity" narrative
   was retracted — do not use it.

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

The question was simple: deterministic or stochastic? The answer,
after corrections: mostly deterministic. Three of four contradiction
types resolve identically across all seven models. Prohibitions win.
Minimalism wins. These are universal training effects that no model
escapes.

The one exception — concise-vs-verbose — is where the real story is.
Opus 4 resolves toward verbose. Opus 4.5 resolves toward concise. The
training curriculum changed, and the contradiction resolution changed
with it, silently and undocumented. Haiku and Opus 4.1 sit at the
transition point, genuinely stochastic, unable to decide. This is
visible model evolution. It's narrow (one contradiction type out of
four) but it's real and it affects users.

The session's biggest lesson wasn't in the data — it was in the
process. The classifier created findings. Over-broad keywords produced
a tier effect, a three-faction split, and a "compromise strategy" that
were all artifacts. The UNCLEAR audit caught it, but only after the
narrative was already written, the cairn was authored, and the commit
was signed. The human ground-truth labeling was proposed as a
robustness improvement. It should have been a prerequisite.

Every time we tested an assumption, it was wrong in an interesting way.
Including our assumption that the classifier was good enough.
