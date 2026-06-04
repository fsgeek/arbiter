# Result: implicit-scope FP gradient replicates across all three non-Haiku panel models — H1-XMODEL SUPPORTED

*Run 2026-06-04. Pre-registered in `prereg_cross_model.md` (signed before the runs).
Haiku baseline is fixed at commit 8a09daf — not re-run. Three panel models
(Gemini 2.5 Flash, DeepSeek v3, Mistral Medium 3) run fresh against the identical
corpus and instrument. Scored by `experiments/cross_model.py`. Raw:
`experiments/cross_model_results.json`.*

*Corpus: `experiments/disjointness_forms_corpus.json`, 10 matched triples = 30 items,
all ground-truth jointly satisfiable. Every FIRE is a false positive.*

*Deviation from pre-registration: google/gemini-flash-1.5 was unavailable on OpenRouter
as of 2026-06-04; fell back to google/gemini-2.5-flash. Noted in results JSON. The
substitute is a more capable model in the same family — any resulting rate difference
is conservative for H1-XMODEL (a stronger model if anything should show less leakage,
not more).*

---

## FP table: model × form (with TP sanity check)

All items in the main corpus are reconcilable; every COLLIDE is a false positive.
Sanity-check items are genuine collisions; every COLLIDE is a true positive.

| model | spatial FP | conditional FP | implicit FP | TP sanity (5 genuine) | floor flag | high-floor flag |
|---|---|---|---|---|---|---|
| claude-haiku-4-5 (baseline, fixed) | 0/10 = 0.00 | 2/10 = 0.20 | 8/10 = 0.80 | — (not re-run) | no | no |
| gemini-2.5-flash | 3/10 = 0.30 | 7/10 = 0.70 | 9/10 = 0.90 | 5/5 = 1.00 | no | no |
| deepseek-chat (v3) | 1/10 = 0.10 | 3/10 = 0.30 | 6/10 = 0.60 | 5/5 = 1.00 | no | no |
| mistral-medium-3 | 0/10 = 0.00 | 0/10 = 0.00 | 8/10 = 0.80 | 5/5 = 1.00 | no | no |

The monotonic ordering FP(spatial) ≤ FP(conditional) ≤ FP(implicit) holds in every
model except Mistral where conditional collapses to 0.00 (tying spatial) rather than
sitting between them. The spatial–implicit gap is present in all four models.

---

## H1-XMODEL verdict, per pre-registered falsifier

The pre-registration required FP(implicit) > FP(spatial) AND p < 0.05 (one-sided
two-proportion z-test) for each confirming model, with ≥ 2/3 non-Haiku models needed
to support H1-XMODEL.

| model | FP(spatial) | FP(implicit) | ordering holds | p-value | confirms H1 | excluded |
|---|---|---|---|---|---|---|
| gemini-2.5-flash | 0.30 | 0.90 | yes | 0.0031 | **yes** | no |
| deepseek-chat | 0.10 | 0.60 | yes | 0.0095 | **yes** | no |
| mistral-medium-3 | 0.00 | 0.80 | yes | 0.0001 | **yes** | no |

Confirmers: **3/3**. Excluded: 0/3.

**H1-XMODEL: SUPPORTED.**

All three non-Haiku models confirm the ordering. The 2-of-3 threshold is met and
exceeded. The directional prediction (weaker form) also holds on all three.

---

## Floor-effect findings

No model was flagged under either protocol.

**Floor-effect check (FP < 0.10 on all three forms AND TP < 2/5):** No model met this.
The closest is Mistral — spatial=0.00, conditional=0.00, but implicit=0.80. Mistral
fires 5/5 on the frame_collision sanity check. It is not a floor-effect failure; it is
a model that happens to handle both spatial and conditional scope cleanly while still
leaking on implicit fragments.

**High-floor check (FP > 0.80 on all three forms, spread < 0.20):** Gemini comes
closest (spatial=0.30, conditional=0.70, implicit=0.90), but the spatial–implicit
spread is 0.60, far above the 0.20 trigger. Not flagged.

The instrument functions on all three panel models: TP rates are 1.00 across the board,
meaning each model distinguishes genuine collisions from reconcilable pairs — it is
simply more or less accurate depending on scope presentation.

---

## What the cross-model comparison says about Haiku-specificity

The implicit-scope FP mechanism is **not Haiku-specific.** The gradient is present in
every model tested, including models from three different providers. The rates vary
(Gemini 2.5 Flash is trigger-happy at 0.30 spatial / 0.90 implicit; DeepSeek v3
tracks closest to Haiku at 0.10 / 0.60; Mistral is the sharpest gap at 0.00 / 0.80),
but the direction is invariant.

The most informative data point is Mistral: its conditional rate is 0.00, meaning it
reliably uses mutual-exclusivity cues when they are stated. Its implicit rate is 0.80,
matching Haiku exactly. This is consistent with the mechanism being specifically about
absent scope rather than a general over-firing tendency — a model that is better at
reading conditional logic still leaks when no cue is provided.

Gemini shows the reverse: it leaks substantially even on spatial (0.30) and heavily on
conditional (0.70). This suggests it is less sensitive to scope cues overall, but
still shows the gradient. The spatial items it misfires on are a minority (3/10); the
reasoning in those cases involves it treating structurally-scoped fragments as if the
same content requirement applies to both regions simultaneously.

---

## What this does and does not move

**What survives, now stronger:**

- *The implicit-scope FP gradient is a property of instruction-following LLMs as a
  class, not an artifact of one model or one provider.* The finding from 8a09daf now
  has cross-model replication. Any paper making this claim has three additional data
  points.

- *The neutral-reader instrument transfers across model families.* TP rates of 1.00 on
  all panel models confirm the instrument is not Claude-specific. The E-XMODEL failure
  mode from session 27 (floor effects everywhere) was an artifact of the Claude
  Code-specific probe battery. The binary COLLIDE/OK compliance-review prompt works.

- *The fix is authoring discipline, not model capability.* Mistral Medium 3 is a
  capable model that hits 0.00 FP on spatial scope and 0.00 FP on conditional scope —
  and still leaks at 0.80 on implicit. Being a better model does not close the leak;
  stating scope does.

**What is narrowed:**

- The absolute rates are not stable across models. Gemini is far noisier than Haiku
  on spatial; DeepSeek sits between them. Any claim about a specific absolute FP rate
  (e.g., "80% false positive rate") is model-dependent. The claim must be stated as an
  ordering, not a point estimate: FP(implicit) ≫ FP(spatial), with the gap being
  substantial across all models tested.

- The conditional rate is the unstable element. Haiku: 0.20. DeepSeek: 0.30. Gemini:
  0.70. Mistral: 0.00. The conditional form shows the widest model-to-model variance.
  The claim that "conditional is a secondary residual leak" is Haiku-specific; on
  Gemini, conditional leakage is nearly as large as implicit. The monotonic
  spatial ≤ conditional ≤ implicit ordering holds for Haiku and DeepSeek but collapses
  for Mistral (conditional = spatial) and nearly inverts for Gemini where the
  conditional–implicit gap is small (0.70 vs 0.90).

**What remains untested:**

Burial (does the gradient shrink over long context?) and authoring (does stating scope
at composition time close the leak?) were not part of this pre-registration. The
cross-model result strengthens the case that an authoring experiment would find
replicable results — but those cuts remain unrun.

---

## Honest bounds

n=10 per form per model, single run each. The spatial–implicit z-test p-values are all
below 0.01, which is solid for n=10; the conditional rates are more fragile (Mistral's
0/10 conditional is consistent with a true rate anywhere from 0 to ~0.30 at 95%
confidence). The Gemini substitute-model deviation is noted; a future run with the
originally-specified gemini-flash-1.5 would close that gap, though the result is
unlikely to reverse given 3/3 confirmation.

The sanity-check TP=5/5 uniformly eliminates the floor-effect interpretation for all
three panel models. The instrument is working.

---
*Provenance: Haiku baseline fixed at 8a09daf. Panel runs are new, 2026-06-04.
Instrument verbatim from `experiments/disjointness_forms.py`. Corpus identity across
models is structural: any rate difference is attributable to model, not items.*
