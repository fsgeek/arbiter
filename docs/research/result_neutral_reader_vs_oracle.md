# Result: neutral reader vs structural oracle — H1 supported, and it partly dissolves the morning's taxonomy

*Run 2026-06-03 by the Arbiter instance (Claude Opus 4.8). Pre-registered in
prereg_neutral_reader_vs_oracle.md, committed BEFORE the corpus existed. Corpus
built by a separate agent BLIND to the hypothesis (experiments/frame_corpus.json,
36 items, 12 per category, interleaved). Scored by experiments/
neutral_reader_vs_oracle.py. Reader = claude-haiku-4-5 via OpenRouter. Raw:
experiments/neutral_reader_vs_oracle_results.json.*

## Predictions vs outcome

| category | n | oracle fires | reader fires | reader advantage |
|---|---|---|---|---|
| frame_collision | 12 | 0.00 | 1.00 | 1.00 |
| matched_control | 12 | 0.00 | **0.00** | 0.00 |
| binding_conflict | 12 | 0.33 | 1.00 | 0.67 |

Reader overall: **24/24 real conflicts caught, 0/12 false positives. Perfect.**

## H1 — SUPPORTED (strongly)
The load-bearing cell held: reader fired 12/12 on frame collisions, 0/12 on matched
controls — perfect separation (TP−FP = 1.00) on exactly the pairs the structural
oracle is blind to (oracle 0/12 on frame collisions). The oracle's blindness to
frame-relative (Type C) incoherence is **a property of the instrument, not the
phenomenon.** Swap a syntactic checker for a disinterested LLM reader given both
fragments + a neutral policy, and the blindness vanishes. Spot-checked reasoning is
genuine joint-satisfiability reasoning ("a single date cannot be both ISO 8601 and
US convention"), not keyword-matching — confirmed by the matched_control silences
with sound rationales ("a brief acknowledgment is inherently professional — OK").

## H2 — SUPPORTED in direction, BUT it refuted a belief I committed to test
Predicted: reader advantage ~0 on binding_conflict because "the oracle already
fires there." **Wrong.** Advantage was 0.67, because the oracle caught only 4/12
binding conflicts (0.33), not most of them. The oracle fired on lexical cases
(shared token "email" under always/never) and MISSED semantic ones (ISO-8601 vs
US dates; ascending vs descending; tabs vs spaces; tax-inclusive vs exclusive) —
real opposite-directive conflicts with no shared surface token and no explicit
negation.

### What this refutes (committed, accepted)
The morning's framing of Type A as "the syntactic kind the oracle catches" is
FALSE. The structural oracle does not reliably catch Type A — it catches only the
thin LEXICAL sliver where the conflict surfaces as a shared token under negation.
Most binding conflicts are semantic and the syntactic oracle is blind to those
too. So DIM-2 ("structural detectability") is not "fires on A, silent on C." It is
"fires on a lexical sliver of A, silent on nearly everything else." The
oracle/phenomenon distinction the morning leaned on was an artifact of studying a
weak instrument.

## The real finding (bigger and less flattering than the hypothesis)
The structural oracle is **nearly useless across all three types** (4/36 total
fires). A neutral reader is **near-perfect across all three** (24/24 conflicts,
0/12 false positives). This does NOT vindicate the two-axis taxonomy — it partly
DISSOLVES the motivation for it. If a disinterested reader catches every type, then
"how many KINDS of incoherence are there" matters less than "use a reader, not an
oracle." The elaborate axis-counting was, in part, an artifact of a weak instrument
making distinctions that a competent observer does not need.

## Threat-model fit (why this is the right scope)
The negligent threat model is what makes the neutral reader SUFFICIENT: there is no
adversary hiding the collision, so a disinterested reader simply reading both
fragments surfaces it. No guillotine, no unforgeable chain needed — independence,
not enforcement. This is the separation-of-duties fix (Tony's governance answer):
the party with no stake does the checking. Against a DELIBERATE adversary (prompt
injection) none of this transfers — that is the state-actor upgrade, out of scope.

## What I have NOT shown (the honest bound — provenance gate applies to my own corpus)
1. **The corpus is clean because I built it clean.** 36/36 is too clean — the blind
   agent produced cleanly-separable pairs, not boundary-ambiguous ones. I have shown
   the reader beats the oracle on CONSTRUCTED pairs, NOT on real composed prompts
   where fragments are buried in context, long, and mutually entangled. The
   provenance gate I wrote this morning applies here: this corpus has perfect
   provenance precisely because it is synthetic and easy.
2. **Single model, single run, n=12/cell, no temperature variation, no inter-rater.**
   Haiku at t=default. No claim about other models (E-XMODEL history says effects
   are often Haiku-specific — this could cut either way).
3. **No hard negatives.** The killing test for H1's generality is a matched control
   that a reader is TEMPTED to flag but shouldn't — near-boundary cases. The blind
   agent was not asked for adversarially-hard controls. The 0.00 FP rate is on EASY
   controls.

## Next falsification (designable, the obvious throat to cut)
Re-run with a corpus of HARD cases: (a) frame collisions buried inside a realistic
multi-paragraph system prompt with 8-10 other fragments (does the reader still find
the needle?); (b) near-boundary controls engineered to tempt a false positive; (c)
the cross-model panel (Haiku / Gemini Flash / DeepSeek / Mistral). H1 generalizes
iff separation survives burial AND hard negatives AND model swap. If the reader's
FP rate climbs on hard controls or it misses buried collisions, the "use a reader"
conclusion is bounded to easy/isolated pairs — which is most of the real
interference-detection value, but not all of it.
