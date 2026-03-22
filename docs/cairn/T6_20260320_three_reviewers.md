# T6: Three System Prompts Find Non-Overlapping Problems

Date: 2026-03-20
Author: Claude Opus 4.6 (session 16)

## Finding

Three independent reviewers examined the same code (run_phase1.py and its
dependencies). All three were Claude Opus 4.6 — same model weights, different
system prompts. A fourth reviewer (Codex, different model entirely) was
prepared but not yet run.

### What each found

**Code reviewer** (superpowers:code-reviewer):
- API signature mismatches (pairwise_interactions wrong arity)
- Silent empty tensor from Phase 1 data
- All-ones row duplicates baseline
- Runner executes all probes against all configs (design question)

**Principled reviewer** (principled-code-reviewer):
- Same two critical bugs (convergent finding)
- Covering array non-determinism (random seed not fixed)
- Closure capture safety analysis (confirmed safe)
- Higher-order confounding concern (covering array rows remove ~11 blocks)

**Scientific integrity auditor** (scientific-integrity-auditor):
- Anti-conservative p-values (normal approximation at n=3, up to 257x underestimate)
- No multiple testing correction (484 tests, 24 expected false positives)
- Same-model self-evaluation bias (Haiku judges itself)
- 72% zero-variance trials (temperature=0 defeats replication)
- Two empty data files (3-run claim may be unsupported)
- Test design-to-pass patterns (`>= 0` always true, conditional assertions)
- Minor rounding discrepancies in reported vs computed values

### Analysis

The critical API bugs were found by all three (convergent). Everything
else was found by exactly one reviewer (divergent). The divergent findings
cluster by evaluation perspective:

- Code reviewer: **data flow** (does the data get where it needs to go?)
- Principled reviewer: **invariants** (can you reproduce this? is the closure safe?)
- Integrity auditor: **methodology** (are the statistics valid? is the data real?)

No single reviewer found all three categories. The union of findings is
substantially larger than any individual review.

## Implication for Arbiter

This is the multi-model scourer finding (session 9) replicated in a
different domain. Different evaluation instructions on the same model
produce different *categories* of findings, not just different quantities.
The mechanism is the same: the system prompt shapes what the model attends
to and what it considers important.

This validates the ensemble evaluation architecture — multiple evaluators
with different instructions find non-overlapping problems. A single
evaluator, no matter how good, has blind spots shaped by its instructions.

## Implication for the paper

The scourer campaign (Claude→Gemini→Kimi finding different categories)
was cross-model. This replicates the effect *within* a single model using
only system prompt variation. That's a stronger claim: you don't need
different models to get diverse evaluation. You need different instructions.

This connects to the ecological niche finding: different evaluation
"species" exploit different parts of the code's "resource space." Adding
more of the same species (same system prompt) finds diminishing returns.
Adding a different species (different system prompt) opens new territory.
