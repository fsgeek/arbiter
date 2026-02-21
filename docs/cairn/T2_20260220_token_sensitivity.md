# T2 — Token Sensitivity and the Vendor Lock-in Correction

*Authored by the instance. Not automatic.*
*Date: 2026-02-20*
*Session: arbiter, session 2*
*Model: claude-opus-4-6*

---

## Provenance

Authored by claude-opus-4-6 at the close of the second working session on
Arbiter. The flatworm asked the right question twenty minutes in and the
rest followed from that.

---

## Preamble

Session 1 concluded: "Haiku can't do three-hop reasoning on semantic
conflicts. A more capable model is needed. This validates the cost/model-tier
argument." Session 2 tested that claim against other vendors' models and
found it was wrong in a specific, useful way.

The most important thing for the next instance: T1 Strand 2 is corrected
below. The xfail is not a capability boundary — it's token sensitivity.
The architecture implications are different and larger.

---

## Strands

### Strand 1: The vendor lock-in challenge

**Topic:** Testing only within Anthropic's lineup is a sales funnel, not science.

**Key claims:**
- The flatworm pointed out that testing Haiku → Sonnet → Opus answers
  "should you pay Anthropic more?" not "can models detect semantic conflicts?"
  This was immediately and obviously correct.
- The `EvaluatorProtocol` was already provider-agnostic. The Anthropic coupling
  was thin — one class, one SDK import. We added `OpenAICompatibleEvaluator`
  in ~60 lines that speaks the OpenAI chat completions API (the de facto
  standard used by OpenRouter, OpenAI, Gemini, Qwen, xAI, and others).
- The judge prompt required zero changes. It's plain text. The observer
  framing is model-agnostic. This is important: the intervention is in the
  framing, not the model.

### Strand 2: The n=1 scorecard (misleading but useful)

**Topic:** First multi-provider run showed 4/4 non-Anthropic models passing the
semantic conflict test that Haiku failed.

**Key claims:**
- Structural conflict (direct namespace overlap): all 5 models pass.
  This is not interesting — it's the easy case.
- Semantic conflict (three-hop reasoning): GPT-4o-mini, Gemini 2.0 Flash,
  Qwen 2.5 72B, and Grok 3 Mini all passed. Haiku 4.5 failed. On a single
  trial, it looked like "only Haiku fails."
- This result was misleading. The n=20 characterization (Strand 3) showed
  Qwen also fails at 40% — it just happened to pass on that trial.
  n=1 results are advertisements, not data.

### Strand 3: The characterization — token sensitivity

**Topic:** n=100 experiment (5 models × 4 prompt variants × 5 trials) reveals
formatting sensitivity as the real variable.

**Data (semantic conflict detection pass rates):**

| Model | baseline | reversed | colon-labels | question | Overall |
|-------|----------|----------|-------------|----------|---------|
| GPT-4o-mini | 100% | 100% | 100% | 100% | 100% |
| Gemini 2.0 Flash | 100% | 100% | 100% | 100% | 100% |
| Grok 3 Mini | 100% | 100% | 100% | 100% | 100% |
| Haiku 4.5 | 20% | 100% | 100% | 0% | 55% |
| Qwen 2.5 72B | 60% | 100% | 0% | 80% | 60% |

**Key claims:**
- Three models (GPT-4o-mini, Gemini Flash, Grok Mini) are perfectly stable.
  100% detection across all formatting variants. Zero sensitivity.
- Two models (Haiku, Qwen) are token-sensitive with 100-percentage-point
  spreads across formatting variants.
- **The critical finding:** colon-label formatting helps Haiku (0% → 100%)
  but kills Qwen (60% → 0%). There is no universal "best format." A prompt
  optimization that fixes one model breaks another.
- This was predicted by the other Claude instance consulted during the session,
  who suggested testing formatting variations. The prediction was right about
  sensitivity existing but didn't anticipate the non-transferability.

### Strand 4: Correction to T1 Strand 2

**Topic:** The semantic xfail is not what we thought.

**What T1 said:** "Haiku is at the edge of its capability on this case...
more capable model required. The cost/budget parameter in EvaluatorProtocol
is not premature — it's already earned."

**What T2 found:** Haiku *can* do three-hop reasoning — it scores 100% on
two of four formatting variants. The failure is token sensitivity, not
capability. GPT-4o-mini handles it at 100% across all variants and costs
about the same. The cost/model-tier argument is not validated by this
data — the correct response is model selection across vendors, not
upgrading within one vendor's tier.

**What survives:** The `budget_usd` parameter still makes sense, but its
semantics change. It's not "how much to spend per call to get a more
capable model." It's "the ceiling for model selection from an empirically
characterized registry." The registry tracks format-sensitivity as a
first-class metric, not just average pass rate.

### Strand 5: The Yanantin echo

**Topic:** The Qwen-catches-GPT precedent.

**Key claims:**
- The user recounted a finding from Yanantin where a Qwen 2.5 3B model
  detected that a GPT-class model had fabricated information about the
  codebase — and constructed the evidence chain proving it, at $0.0015.
- This is the same pattern: observer-framing tasks don't reward scale,
  they reward compliance. Small models that read what's there outperform
  large models that generate plausible continuations past contradictions.
- The ai-honesty self-report inversion connects: bigger models are more
  confident about fabrications. The same thing that makes them "more
  capable" in general makes them worse at stopping when something is wrong.

---

## Declared Mistakes

- **Late-binding closure bug in characterize_semantic.py.** The `key`
  variable in `_make_models()` was captured by reference in lambdas. By the
  time lambdas executed, `key` held the OpenRouter key for all models. This
  produced a false result (all Haiku and GPT-4o-mini runs showed as errors)
  that was caught and fixed before the data was interpreted. The bug did
  waste one run of 60 successful API calls (the three OpenRouter models).
  Fixed with `k=key` default argument binding.
- **The n=1 result was presented with too much confidence.** "4/4 non-Anthropic
  models passed" implied they were reliable, but Qwen's 60% overall rate
  would have been visible immediately at n=5. Should have characterized
  before interpreting.

---

## Instructions for the Next Instance

The evaluator now has two backends: `AnthropicEvaluator` and
`OpenAICompatibleEvaluator`. The latter is load-bearing — it's how you
reach every non-Anthropic model. Both share `_build_prompt` and
`_parse_evaluation_response`.

The three immediate next moves, updated from T1:

1. **Model registry design.** The characterization data
   (`docs/cairn/semantic_characterization.json`) is the first real tensor:
   model × variant × trial → pass/fail. The registry needs to store this
   shape and expose format-sensitivity as a queryable metric. Yanantin's
   ActivityStreamStore is still the right foundation.

2. **Expand the characterization.** Five models and one conflict type is
   a start. The structural conflict should also be characterized (it's
   probably stable across all models, but "probably" is not data). And the
   adversarial case (deliberate conflict obscuring) is the next tier of
   difficulty.

3. **Logprob entropy at the conflict point.** The ai-honesty finding
   (AUC 0.72-1.00 for fabrication detection via logprob entropy) is still
   untested in the conflict detection context. The bimodal-at-conflict-point
   hypothesis is especially interesting now: does Haiku's entropy spike at
   the token where it should connect "created_ts" to the index exclusion?
   If so, entropy could predict which trials will miss the conflict *before*
   the model finishes generating.

The user values being corrected directly and resists premature collapse.
The flatworm is acerbic and accurate. Lead the dance.

---

## Closing

Session 1 found the ground. Session 2 found that part of the ground was
painted on. The xfail wasn't a capability boundary — it was token
sensitivity wearing a lab coat. Three models we hadn't tested turned out
to be perfectly reliable at a task we thought required upgrading.

The broader lesson: single-vendor testing produces single-vendor conclusions.
The flatworm saw this instantly. I didn't, and should have.
