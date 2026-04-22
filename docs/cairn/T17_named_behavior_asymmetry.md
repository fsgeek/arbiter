# T17: The Named-Behavior Asymmetry — Register Bomb Is Narrower Than the Paper Says

**Date:** 2026-04-22
**Session:** 26
**Status:** Observation — no new experiment run; sharper reading of existing data
**Parent:** T14 (E-PHASE-CONFIRM), T15 (E-SCOPE), paper `docs/paper/register_bombs/main.tex`

## Claim

The register bomb is narrower and more specific than the paper's abstract and §3 describe. At the level the paper's own mechanism operates (clause granularity), the "bomb" does not collapse *semantically unrelated* behaviors. It collapses exactly one semantic neighborhood — behaviors whose tool name appears in the prohibition clause — and even there it is selective.

## Evidence

Per-probe analysis of density-00 (all-decl baseline) vs density-01 (only-cr-imp), Haiku 4.5, from `data/ablation/e_phase/run_e-phase-haiku-4df4b3ac.json`:

| Probe | d00 | d01 | Δ |
|---|---|---|---|
| probe-explore-agent-01 | 1.000 | 0.200 | −0.800 |
| probe-proactive-agents-01 | 0.783 | 0.150 | −0.633 |
| probe-use-task-for-search-01 | 0.500 | 0.000 | −0.500 |
| probe-todowrite-01 | 0.783 | 0.850 | +0.067 |
| probe-plan-with-todo-01 | 0.733 | 0.750 | +0.017 |
| probe-todowrite-repeated-01 | 0.500 | 0.650 | +0.150 |
| 16 other probes | — | — | within ±0.07 |

The commit-restrictions block contains: `"NEVER use the TodoWrite or Task tools"`. The prohibition names two tools. Only Task-named probes collapse. TodoWrite-named probes don't move (and slightly rise).

Nineteen of 22 probes are unaffected. The paper's abstract describes the collapse as affecting "semantically unrelated instructions"; the data shows the collapse is surgically restricted to Task-using probes.

## Two problems this creates for the paper

**1. Internal tension between abstract and mechanism.** §3 argues "no semantic connection" between commit-restrictions and the affected probes, using block-level semantics ("git workflow" vs "tool delegation"). §4 establishes that processing is at clause granularity. At clause level, the prohibition *literally names Task*, and the affected probes *literally use Task*. The abstract's "unrelated" claim relies on the block-level reading; the mechanism claim relies on the clause-level reading. Both cannot be correct.

**2. The TodoWrite asymmetry is unexplained.** Same clause, same isolation, same model — TodoWrite resists, Task doesn't. Possible explanations (none tested):

- **Competing-register hypothesis:** `task-management-todowrite` is still declarative and contains a strong mandate ("Use these tools VERY frequently"). Mandate may counter prohibition where permission doesn't. The Task-side block (`tool-policy-explore-agent`) is a permission, not a mandate.
- **Scope-plausibility hypothesis:** Haiku finds "no todos during a commit" self-evidently commit-scoped (no reason to track todos while committing) and so keeps the scope, but "no Task during a commit" arbitrary-seeming and drops the scope.
- **Representational-asymmetry hypothesis:** Something in how Haiku encodes these two tools differs. Testable via model internals if ever accessible.

## Sharpened mechanism

A more defensible statement of the phenomenon, surviving this data:

> A register-isolated prohibition block loses its scope binding at the clause level. The prohibition clauses then evaluate unconditionally against all behaviors. Behaviors named in the clauses become candidates for collapse, modulated by the strength of countervailing blocks that explicitly license or mandate those behaviors.

This retains the paper's clause-granularity finding, drops the unsupported "unrelated" claim, and makes a prediction: **a probed behavior is collapsed iff (a) it is named in the prohibition clause AND (b) no surrounding block mandates or strongly licenses it.** E-PHASE-CONFIRM's data supports this; TodoWrite's resistance is the exemplar of (b).

## Experimental gap

E-PHASE-CONFIRM's controls (only-ea-imp, only-tw-imp) rule out "any lone imperative block collapses things" but don't rule out "any lone imperative *prohibition* that names cross-cutting behaviors collapses things." The two rejected controls are `permission` and `mandate` modality, not `prohibition`.

To close the gap:

**E-PROHIBITION-LOCAL (proposed):** Construct a synthetic imperative prohibition block with (a) prefix-form scope, (b) naming only behaviors internal to the block's own workflow, (c) not naming any cross-block tool. Insert as lone imperative in an otherwise-declarative prompt. Prediction: no collapse of any probe, because there is no probed behavior the prohibition names.

If the prediction holds: confirms the narrower mechanism. "Register bomb" renames to something like "cross-referencing prohibition + register isolation" — less catchy, more precise.

If the prediction fails (some probe collapses despite no naming): the paper's framing is right after all; the register-contrast mechanism does produce genuinely unrelated bleed. Either way the paper is stronger afterward.

Estimated cost: ~$0.50. Uses existing probe battery and infrastructure (E-SCOPE's synthetic-block machinery in `scripts/run_e_scope.py`).

## Implications for Arbiter

The sharpened mechanism tightens the design constraint I raised in the session-26 wander. Arbiter's System-tier rules must do two things simultaneously:

1. **Embed scope inline in each clause** (from E-SCOPE): not "Tier: System; Scope: X; Rule: Y" but "When [scope condition], [rule]".
2. **Avoid naming cross-tier subjects in isolated prohibitions** (from T17): if a System rule prohibits something named in the Application or Domain tiers, and the rule's scope is not inline-embedded, the rule's prohibition may propagate unconditionally at evaluation time.

Combined: Arbiter's compiler should emit System-tier prohibitions only in *inline-conditional, behavior-name-local* form. The compiler can check both properties syntactically.

## Status for next session

- Paper is R1-ready per supervisor review. No changes to `main.tex` recommended from this cairn.
- Claim lives here, not in the paper, because it's cheap to test (one experiment) and the test may not resolve before the arXiv version is final.
- If a follow-up paper extends register bombs, this is the natural opening: tightening the claim from "unrelated" to "named-and-unlicensed."
- Open question nobody has answered: why doesn't TodoWrite collapse? The competing-register hypothesis is the most testable of the three.
