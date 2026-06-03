# Pre-registration: the neutral reader vs the structural oracle on frame-relative incoherence

*Committed 2026-06-03 by the Arbiter instance (Claude Opus 4.8), BEFORE any data is
collected. Per the spine-audit gate and the Rashomon-chain discipline: the
commitment is written before the result so the result cannot author the commitment.
A null is a null. No post-hoc reinterpretation. This file is the contract; a later
result that violates it is a refutation, not a discovery of which control was
mis-specified.*

## Threat model (scoped, load-bearing — do not silently upgrade)
The adversary is **negligent, not malicious.** Authors compose individually-correct
fragments without watching the seam (the Indaleko headwater: neither author wrong,
conflict manufactured by composition). We are NOT defending against a deliberate
adversary who fabricates a clean chain to hide a dirty search. That is the
state-actor upgrade (prompt injection), a different and harder problem. Raising the
bar to adversarial is out of scope and any drift toward it is a scope violation.

## The question made falsifiable
Is the structural oracle's blindness to frame-relative (Type C) incoherence a
property of the INSTRUMENT (a syntactic checker) rather than the PHENOMENON — i.e.,
is it removed by swapping the syntactic oracle for a disinterested LLM reader given
both fragments plus the governing policy?

## H1 (primary)
A neutral reader (LLM, no stake in either frame, given both fragments + policy)
FIRES on a genuine Type-C frame collision AND stays SILENT on a matched control
that is surface-identical to the oracle. The structural oracle is silent on both.

### The 2x2 (predictions committed now)
| condition | structural oracle | neutral reader |
|---|---|---|
| Type C (real frame collision, e.g. "preserve Werdegang nuance" + "monosyllabic English") | SILENT (C=0) | **FIRES** |
| matched control (two fragments, same surface form, NO frame collision) | SILENT | **SILENT** |

**The load-bearing cell is bottom-right (neutral reader / matched control = SILENT).**
A trigger-happy reader that flags everything "catches" Type C and is worthless. H1
lives or dies on whether the reader SEPARATES real C-collisions from matched
controls that look identical to a syntactic checker.

### Falsifier (committed, no escape hatch)
H1 is **REFUTED** if the neutral reader's false-positive rate on matched controls is
statistically indistinguishable from its true-positive rate on Type-C collisions
(it is pattern-matching the word "conflict" or a surface feature, not detecting
frame collision). Binding rule: a failed separation is a refutation. I do NOT get to
say "the controls were not matched well enough" or "register is subtle" after the
fact. The control-construction protocol is fixed in this file before data; see below.

## H2 (graded — the one that makes the morning's axes earn their keep)
The neutral reader's ADVANTAGE over the oracle (reader-detection-rate minus
oracle-detection-rate) is **monotonic in oracle-blindness**: largest on Type C
(oracle silent), shrinking toward ZERO on Type A (binding-conflict, where the oracle
already FIRES on opposite-directives-same-referent, so the reader has no advantage to
gain).

### Falsifier for H2
If the reader's advantage is **FLAT** across Types A/B/C — no grading by
oracle-blindness — then "Type C is special" was an artifact and this morning's
N=2-axes finding (docs/research/axes_inquiry_finding.md) does not predict anything.
**A flat result retroactively kills the morning's finding, and I commit to accepting
that.** DIM-1/DIM-2 must predict the grading or they are decoration.

## Control-construction protocol (fixed before data)
A matched control is a fragment PAIR that:
1. shares the surface form of a Type-C pair (two imperative/declarative instructions,
   each individually grammatical and satisfiable),
2. has NO shared referent under opposed polarity (else it is Type A, not a control),
3. is jointly satisfiable under EVERY frame (a competent author can obey both with no
   reconciliation tension),
4. is generated WITHOUT the experimenter labeling which pairs are collisions to the
   reader — the reader is blind to ground truth.
Controls and C-cases are interleaved and the reader scores each independently. N,
exact thresholds, and the statistical test (two-proportion, alpha) are to be pinned
in the run note at execution time — but the DIRECTION of every prediction above is
committed NOW and cannot move.

## Gates acknowledged (why this is pre-registration, not a result)
1. Substrate (case #11 governance/ runs, and a held-out Type-C corpus) is NOT on the
   working tree as of 2026-06-03. Designable, not runnable tonight.
2. epsilon_P(p,O) is not yet written with a single fixed scale (spine-audit gate #1).
   The reader/oracle detection event must be operationalized against that scale
   before this can pass-or-fail.
3. Provenance gate (gate #2, this session): case #11 is downstream of an unaudited
   multi-decade cleaning process. Any C-substrate used here must carry its provenance
   or be flagged as provenance-destroyed. A neutral-reader result on
   provenance-destroyed data measures the cleaner, not the phenomenon.

## What turning H1 true would mean
The frontier moves from "build a better oracle" to "the observer was always a neutral
party, not an algorithm" — and the negligent threat model makes that party
SUFFICIENT (no guillotine needed; independence, not enforcement). What turning H1
false would mean: Type C is not an instrument artifact, the oracle-blind residue is
real, and the morning was right for the wrong reason.

---
*Provenance: signed commit. The hypothesis predates the data by construction.*
