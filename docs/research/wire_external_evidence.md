# External evidence on the one-vs-three question: WIRE's scope confines it to Type A

*Recorded 2026-06-03 by the Arbiter instance, while the axes workflow runs.
Source: docs/paper/references/2605.27784v1.txt (Yan, Chen & Zhang, "Diagnosing
Live Within-Policy Instruction Conflicts in LLM Agents with Witnessed Resolution
Profiles", arXiv 2605.27784v1). Verified by direct quotation, not paraphrase.*

## The finding

WIRE is the strongest published instrument in the prompt-conflict space. Its
entire apparatus — collision candidates, pair construction, the four-cell
resolution profile (q00/q01/q10/q11), SAT-style incompatibility triage — operates
on **pairs of rules on a shared decision surface**. Their worked example (Pair 1
"different decision surface" / Pair 2 "compatible" / Pair 3 "incompatible",
r3 vs r9) is structurally **Type A (binding-conflict)** in the Arbiter framing.

Their Limitations section (line ~1178) names what they exclude, verbatim:

> "Our analysis is also restricted to hard intra-policy rule conflicts. We focus
> on **pairs of rules** that can impose incompatible constraints on the same
> behavioral choice. This **excludes softer tensions among preferences**,
> conflicts involving **more than two rules**, and cases where a policy contains
> an **implicit exception or priority relation that is not captured by the clause
> encoding**."

## Why this bears on one-vs-three

Mapping WIRE's three exclusions onto the three candidate incoherence types:

| WIRE's own words | Arbiter type | Status in WIRE |
|---|---|---|
| "pairs of rules, same behavioral choice" | **A — binding-conflict** | the ONLY thing it handles |
| "softer tensions among preferences" | **C — frame-relative** (register / Werdegang; surface-clean, pragmatic) | excluded |
| "not captured by the clause encoding" | **B — granularity** (constraint at wrong resolution; not a clause-pair at all) | excluded |

The strongest existing method is **architecturally confined to Type A** and names
the other two as out of scope. A method built for one type demonstrably does not
reach the others — without modification, its pair-construction step never even
fires on a single-constraint granularity failure (no pair to construct), and its
symbolic/SAT triage returns clean on a frame-relative tension (no hard
contradiction at the clause level).

## What this does and does NOT establish (epistemic honesty)

- **Establishes (external, not a project-internal weld):** the three types are at
  least *operationally* separable. An instrument optimized for one fails to reach
  the other two, and its authors knew it and said so. This is independent of any
  Arbiter instance's framing.
- **Does NOT establish:** that the three are distinct *in kind*. Operational
  separability under one method could be an artifact of that method's encoding
  choice (clause-pairs), not a fact about the phenomenon. A different encoding
  might unify them. That is exactly what the axes workflow tests.
- **Shifts the prior:** toward "not trivially one axis." The burden is now on a
  unifier to show why a single underlying axis would present as three
  method-incompatible classes.

## The sharper claim this licenses (conjecture, flagged)

WIRE proves the static, hand-authored, **pairwise** case is tractable and
publishable. The headwater's claim is strictly stronger on TWO independent axes
at once: (1) **dynamic composition** (the conflict is generated, not authored) and
(2) **beyond-pairwise types** (B and C, which WIRE excludes by name). Arbiter's
defensible territory is the union of what WIRE excludes — and WIRE's own
limitations section is the citation that the territory is unclaimed.
