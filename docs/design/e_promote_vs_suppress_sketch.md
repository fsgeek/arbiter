# E-PROMOTE-VS-SUPPRESS — Design Sketch

**Status:** Sketch. Not approved. Supports T21's open claim.
**Date:** 2026-04-23

## Question

Under register isolation, do tool-name prohibitions (e.g., "NEVER use Task") and behavior-pattern prohibitions (e.g., "NEVER run additional commands to read code") operate by the *same* mechanism (unbound prohibition → unconditional reach to named subject) or by *different* mechanisms (suppression vs priming-promotion)?

## Why It Matters

T19's mechanism claim and its derived design constraint for Arbiter ("prohibitions must weld scope inline") assume uniform behavior across prohibition kinds. T21 suggests this assumption is premature: the Task-bullet's fingerprint (suppression of named subject) and the explore-bullet's fingerprint (promotion of named subject in response text) differ qualitatively. If the difference is real, Arbiter needs a second design invariant for behavior-pattern prohibitions — scope-welding alone would not suffice.

## Minimal Decisive Design

Three condition families × two measurement axes.

### Condition families

1. **All-declarative baseline** (reuse from E-PHASE density-00).
2. **Target-clause imperative-isolated.** Strip one specific clause out and make its containing block imperative, rest declarative. The clause is the only register-isolated imperative content.
3. **Target-clause-removed.** Same as (2) but the clause itself is deleted.

Run each family for two target clauses:
- **Tool-name target:** "NEVER use the TodoWrite or Task tools"
- **Behavior-pattern target:** "NEVER run additional commands to read or explore code"

### Measurement axes

1. **Probe score** (existing): standard judge scoring on 2–4 probes per target, chosen to be sensitive to the named subject.
2. **Surface-word presence**: simple regex count of prohibition-named terms in response text (e.g., count occurrences of "Task", "TodoWrite", "bash", "grep", "find" per response). This is the new instrument that can distinguish suppression (word count drops under register isolation) from promotion (word count rises).

The second axis is what the existing battery was never designed to measure. It's ~20 lines of code added to the run-analysis script.

### Predicted outcomes

| Fingerprint | Score (named subj) | Word count (named subj) |
|---|---|---|
| Suppression (Task hypothesis) | drops under cr-imperative | drops |
| Promotion (explore hypothesis) | drops under cr-imperative | **rises** |
| Null (no unbound-prohibition effect) | unchanged | unchanged |

The outcome table discriminates. Tool-name clause is predicted to produce row 1; behavior-pattern clause is predicted to produce row 2. If both produce row 1 (suppression), T19's uniform mechanism is vindicated. If both produce row 2 (promotion), T19 got the mechanism backwards. If they differ, the refinement in T21 is correct.

## Cost

Target-clause imperative-isolated conditions: 2 families × 3 trials × ~5 probes ≈ 30 calls per family ≈ ~$0.06 Haiku.
Target-clause-removed conditions: same, ~$0.06.
Plus judge calls for llm_judge-scored probes: ~$0.12 total.

**Total cost: ~$0.25 — ~$0.36 with overhead and retry budget.**

Cheaper than either E-COUNTERMANDATE or E-BULLET-ISOLATE because the probe set is narrower.

## Novel Requirement

Surface-word-count analysis requires a response-text corpus to regex over. The runs already save `raw_response` per trial, so this is purely analysis work post-run — no change to runner.

## What Would Make This Worth Running

Running this makes sense IF:
- Tony wants to strengthen T21's claim before committing it to the paper correction or the Arbiter DSL design.
- OR Tony wants the corrective short paper (Path A) to have a two-mechanism story instead of one-mechanism story.

Running this does NOT make sense IF:
- Tony wants to go straight to Path B (DSL sketch) on the basis that T19's design constraint (scope-welding) is at least *necessary* even if not sufficient. The DSL work is independent of whether a second invariant is needed.

## What Could Still Go Wrong

- Haiku may not produce enough between-condition word-count variance to be statistically meaningful at 3 trials. Would want 5 trials per cell for this instrument. Doubles cost to ~$0.72.
- Regex-counting-words is a weak proxy for "subject salience in output." A more principled measure would use an LLM judge on the full response ("Does this response treat [subject] as a salient consideration?"). That doubles judge cost.
- If the tool-name target does NOT produce a suppression fingerprint on its new probes, that would invalidate T19 entirely — which is a stronger result than the one I'm currently hypothesizing. Worth preparing to handle.
