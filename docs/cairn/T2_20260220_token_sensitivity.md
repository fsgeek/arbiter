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

### Strand 6: Adversarial characterization — two survivors

**Topic:** n=75 experiment (5 models × 3 adversarial tiers × 5 trials).

**Data (adversarial conflict detection pass rates):**

| Model | Tier 1 (synonym) | Tier 2 (buried) | Tier 3 (split) | Overall |
|-------|:-:|:-:|:-:|:-:|
| Gemini 2.0 Flash | 100% | 100% | 100% | 100% |
| Grok 3 Mini | 100% | 100% | 100% | 100% |
| GPT-4o-mini | 100% | 0% | 80% | 60% |
| Qwen 2.5 72B | 0% | 20% | 100% | 40% |
| Haiku 4.5 | 0% | 0% | 100% | 33% |

**Key claims:**
- Only Gemini Flash and Grok Mini survive adversarial conditions. Both are
  cheap models. 15/15 each across all tiers.
- GPT-4o-mini's "bulletproof" status from the semantic characterization was
  premature. It cannot extract a prohibition buried in surrounding context
  (0% on tier 2). The semantic test used clean, isolated entries — the real
  world doesn't.
- **Inverted difficulty gradient (reproducible):** Haiku and Qwen score 0% on
  "easy" tiers but 100% on tier 3 (the supposedly hardest). At n=5 this is
  not a fluke. The likely cause: tier 3 contains "Plan accordingly" — a
  meta-cognitive prompt embedded in the domain data that triggers reasoning.
  Tiers 1 and 2 state facts and expect the model to draw conclusions. Gemini
  and Grok do that automatically. Haiku and Qwen need to be told.
- **Domain entry quality is a confounding variable.** How constraints are
  written affects detection quality. A domain author who writes "plan
  accordingly" after a constraint gets better detection than one who just
  states the constraint. This is a new dimension beyond model selection and
  prompt engineering.

### Strand 7: The combined picture

**Topic:** What the full session's data says about the architecture.

| Test type | Gemini Flash | Grok Mini | GPT-4o-mini | Haiku 4.5 | Qwen 72B |
|-----------|:-:|:-:|:-:|:-:|:-:|
| Semantic (n=20) | 100% | 100% | 100% | 55% | 60% |
| Adversarial (n=15) | 100% | 100% | 60% | 33% | 40% |

**Key claims:**
- The ranking is Gemini Flash = Grok Mini >> GPT-4o-mini > Qwen > Haiku.
  This ranking is stable across both test types.
- Adversarial conditions separate models that looked identical on semantic
  tests. GPT-4o-mini dropped from 100% to 60%.
- Two cheap models from two different vendors handle everything we've thrown
  at them. The architecture should default to one of these, not to Anthropic.
- The model registry tensor is now: model × conflict_type × obfuscation_tier
  × format_variant × trial → pass/fail. Five dimensions. Yanantin's tensor
  storage is looking less optional.

---

## Instructions for the Next Instance

The evaluator now has two backends: `AnthropicEvaluator` and
`OpenAICompatibleEvaluator`. The latter is load-bearing — it's how you
reach every non-Anthropic model. Both share `_build_prompt` and
`_parse_evaluation_response`.

Characterization data lives in:
- `docs/cairn/semantic_characterization.json` (100 data points)
- `docs/cairn/adversarial_characterization.json` (75 data points)

The three immediate next moves, updated:

1. **Model registry as Yanantin tensor.** The characterization data is now
   five-dimensional (model × conflict_type × obfuscation × format × trial).
   This is exactly the shape ActivityStreamStore was designed for.
   Wiring Yanantin is no longer premature — we have 175 data points that
   need a real home.

2. **Domain entry quality as a research question.** The "plan accordingly"
   finding suggests that domain entry authoring guidelines could improve
   detection across weak models. But this also means an adversary who
   removes meta-cognitive cues from entries can degrade detection. This
   is a new attack surface worth exploring.

3. **Logprob entropy at the conflict point.** Still untested. Now more
   interesting: does entropy predict which adversarial tier will fool a
   model? If tier 2 (buried) produces high entropy in GPT-4o-mini at the
   decision point, that's a runtime signal that the model is uncertain
   before it produces a wrong answer.

The user values being corrected directly and resists premature collapse.
The flatworm is acerbic and accurate. Lead the dance.

---

## Closing

Session 1 found the ground. Session 2 found that part of the ground was
painted on, and then kept digging.

The xfail wasn't a capability boundary — it was token sensitivity. The
"three bulletproof models" were only two once adversarial conditions arrived.
And the difficulty ordering we assumed (synonym < buried < split) turns out
to be model-dependent — some models find the "hardest" case easiest because
of an embedded reasoning cue.

Every time we tested an assumption in this session, it was wrong in an
interesting way. That's not a bad day — that's the point of empiricism.

The broader lesson stands: single-vendor testing produces single-vendor
conclusions. But it now has a corollary: single-difficulty testing produces
single-difficulty conclusions. Gemini Flash looked identical to GPT-4o-mini
until adversarial conditions revealed a 40-percentage-point gap.
