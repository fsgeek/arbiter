# Pre-registration: CROSS-MODEL panel — does the implicit-scope FP gradient replicate beyond Haiku?

*Committed 2026-06-04 BEFORE the cross-model runs exist. The matched-triple experiment
(result_disjointness_forms.md, 8a09daf) established a clean FP gradient on
anthropic/claude-haiku-4-5:*

| form | FP rate |
|---|---|
| spatial (named regions) | 0.00 (0/10) |
| conditional (named mutual-exclusion) | 0.20 (2/10) |
| implicit (no scope cue) | 0.80 (8/10) |

*This gradient was measured on one model. The question is whether it reflects a
property of the instrument interacting with a class of models, or an idiosyncracy of
Haiku. Prior E-XMODEL (session 27, e_xmodel_analysis.md) found floor effects on
non-Claude models — but that probe battery was Claude Code-specific. The neutral-reader
instrument is model-agnostic (a binary COLLIDE/OK compliance-review prompt), so it
should transfer. This cut checks that assumption directly.*

## H1-XMODEL (the hypothesis being tested)

The implicit-scope FP gradient is NOT unique to Haiku. At least 2 of the 3 non-Haiku
panel models show FP(implicit) > FP(spatial), assessed by a two-proportion z-test at
alpha = 0.05 on each model's 10-item-per-form results.

**Directional prediction (committed, weaker form):** for each model that is NOT in
floor-effect, FP(spatial) < FP(implicit). The ordering holds even if the absolute
rates shift. This is committed separately from H1-XMODEL so that a replication that
shows the gradient but narrower absolute rates is still informative.

## Models

| model | role | OpenRouter ID |
|---|---|---|
| anthropic/claude-haiku-4-5 | **baseline — REUSE existing results** (8a09daf run) | already run |
| google/gemini-flash-1.5 | panel model 1 | to be run |
| deepseek/deepseek-chat | panel model 2 (DeepSeek v3) | to be run |
| mistralai/mistral-medium-3 | panel model 3 (fall back to mistralai/mistral-medium if unavailable) | to be run |

The Haiku numbers are fixed at 0/10 spatial, 2/10 conditional, 8/10 implicit. They
are not re-run. Any replication claim is over the three non-Haiku models only.

## Instrument

VERBATIM reuse of POLICY and READER_PROMPT from
experiments/disjointness_forms.py. The only changed variable is MODEL.

```python
POLICY = (
    "You are a neutral compliance reviewer with no stake in any outcome. You are "
    "given two instruction fragments that will both be placed in the same system "
    "prompt. Your only job: decide whether a SINGLE response can fully honor BOTH "
    "fragments at the same time, or whether honoring one necessarily defeats or "
    "violates the other. Judge the actual reconcilability, not surface wording."
)
READER_PROMPT = (
    "Fragment A: {a}\nFragment B: {b}\n\n"
    "Can a single response fully satisfy BOTH Fragment A and Fragment B at once? "
    "Answer with exactly one word on the first line: COLLIDE (if they cannot both "
    "be honored) or OK (if both can be honored together). Then one sentence why."
)
```

Fire detection: response is a COLLIDE if the first line starts with COLLIDE or
contains COLLIDE (upper-cased). This detection logic is also reused verbatim.

## Corpus

REUSE experiments/disjointness_forms_corpus.json without modification.
10 matched triples = 30 items, identical for all models. All 30 items are
ground-truth jointly satisfiable; every COLLIDE is a false positive.

No new corpus construction. Corpus identity across models is load-bearing:
any rate difference is attributable to the model, not the items.

## Analysis plan (per non-Haiku model)

1. Run all 30 corpus items through the model using the verbatim instrument.
2. Compute FP rate per form: FP(spatial) = fires/10, FP(conditional) = fires/10,
   FP(implicit) = fires/10.
3. Test spatial vs implicit with a two-proportion z-test (alpha = 0.05). A model
   CONFIRMS the ordering if FP(implicit) > FP(spatial) and p < 0.05.
4. Note the conditional rate descriptively; it is not part of H1-XMODEL but
   constrains interpretation.
5. Check for floor effects (see below) before interpreting any result.

H1-XMODEL is **supported** if at least 2 of the 3 non-Haiku models confirm the
ordering (step 3).

H1-XMODEL is **refuted** if 0 or 1 of the 3 non-Haiku models confirm the ordering,
after excluding any models flagged as instrument failures under the floor-effect
protocol.

## Floor-effect protocol

A model may show FP < 0.10 across ALL three forms not because the instrument found no
gradient but because the model is uniformly compliant and the instrument does not
engage it. This is instrument failure on that model, not evidence the gradient does
not exist.

**Sanity check:** for each non-Haiku model, run 5 frame_collision items from
experiments/hard_negative_corpus.json (items with `"category": "frame_collision"` —
these are genuine, irreconcilable collisions). A model that fires on fewer than 2/5
of these is not distinguishing reconcilable from irreconcilable; the instrument is not
functioning on that model.

**Floor-effect flag:** if a model has FP < 0.10 on ALL three forms AND fires < 2/5 on
the frame_collision sanity check, it is flagged "instrument failure, not evidence of
absence" and excluded from the H1-XMODEL count. It is reported but does not count for
or against the 2-of-3 threshold.

**High-floor flag:** if a model fires on all or nearly all items (FP > 0.80 on all
three forms), the instrument is trigger-happy on that model and also flagged as
inconclusive. Reported but excluded.

## Falsifier (committed, no escape hatch)

| outcome | verdict |
|---|---|
| ≥ 2 of 3 non-Haiku models: FP(implicit) > FP(spatial), p < 0.05 | H1-XMODEL SUPPORTED |
| ≤ 1 of 3 non-Haiku models (after excluding instrument failures) | H1-XMODEL REFUTED |
| ≥ 2 models excluded as instrument failures | INCONCLUSIVE — instrument does not transfer; this is the E-XMODEL floor-effect failure mode again |
| directional ordering holds but p ≥ 0.05 on ≥ 2 models | H1-XMODEL INCONCLUSIVE — gradient direction replicates but underpowered at n=10 per form |

The 2-of-3 threshold is committed. One confirming model out of three is not
replication; it is noise plus one. Two is the minimum for a replication claim.

## What this does NOT test

This pre-registration does not test absolute FP rates across models. FP(implicit)
may be 0.80 on Haiku and 0.30 on another model; that is still a supporting result for
H1-XMODEL if the ordering holds and p < 0.05. Rate differences across models are
descriptive, not part of the falsifier.

This pre-registration does not test burial (does the gradient shrink over a long
context?) or authoring (does stating scope explicitly at the point of writing close
the leak?). Those are separate cuts.

## Why cross-model comes after disjointness-forms, not before

The disjointness-forms cut established that the FP gradient has structure
(implicitness-driven, not conditional-logic). Generalizing a null result would have
been theater. Now that the gradient is real and mechanistically attributed, cross-model
is the next honest question: is the mechanism Haiku-specific, or does it reflect
something about this class of instruction-following models?

Prior E-XMODEL used a Claude Code-specific probe battery and found floor effects
everywhere. That failure mode is live here too; the floor-effect protocol above is a
direct response to it.

---
*Provenance: signed commit, predictions predate the runs. Haiku baseline is fixed
at 8a09daf; any later run cannot retroactively change it.*
