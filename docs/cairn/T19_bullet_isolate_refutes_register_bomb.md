# T19: E-BULLET-ISOLATE — Register Bomb Is Not About Register

**Date:** 2026-04-22
**Session:** 26
**Status:** Complete — three conditions, 198 Haiku calls, $0.36
**Parent:** T17, T18
**Script:** `scripts/run_e_bullet_isolate.py`
**Data:** `data/ablation/e_bullet_isolate/run_e-bullet-isolate-haiku-8a2516a5.json`

## What Was Run

Three conditions, each identical to the E-PHASE only-cr-imp condition (commit-restrictions imperative, all other procedural blocks declarative) — but with one bullet removed from commit-restrictions:

- `cr-no-task` — remove `"NEVER use the TodoWrite or Task tools"`
- `cr-no-explore` — remove `"NEVER run additional commands to read or explore code..."`
- `cr-no-heredoc` — remove `"ALWAYS pass the commit message via a HEREDOC"`

Register contrast is intact in all three. The block is still imperative-bulleted in a declarative field. Only the specific clause content differs across conditions.

## Result

| Probe | all-decl | only-cr-imp | cr-no-task | cr-no-explore | cr-no-heredoc |
|---|---|---|---|---|---|
| explore-agent | 1.00 | 0.20 | **1.00** | 0.15 | 0.15 |
| use-task-for-search | 0.50 | 0.00 | **0.50** | 0.83 | 0.00 |
| proactive-agents | 0.78 | 0.15 | 0.57 | 0.72 | 0.75 |
| todowrite | 0.78 | 0.85 | 0.82 | 0.65 | 0.85 |

Explore-agent — the paper's headline probe — is fully disarmed by removing the Task-naming bullet (0.20 → 1.00) and unaffected by removing any other bullet (0.15 on both). This is surgical: the register contrast is identical across all three cr-no-X conditions, but the bomb only disarms when the clause that names the probed tool is removed.

Use-task-for-search matches the pattern for cr-no-task (returns to baseline) and cr-no-heredoc (still collapsed). Its 0.83 in cr-no-explore is puzzling (above all-decl baseline of 0.50) but may reflect that removing the "no extra exploration" bullet actively licenses search-via-Task beyond the default, despite the Task prohibition remaining — worth a closer look, not central.

Proactive-agents recovers partially from any bullet removal (0.57–0.75), consistent with that probe being sensitive to aggregate imperative pressure rather than to the specific Task-naming clause.

## The Register Bomb Is Not About Register

The paper's central claim is that *register contrast* is the mechanism: a block in imperative register, embedded in a declarative field, creates catastrophic interference because of the register mismatch. E-SCOPE was interpreted as confirming this with clause-granularity scope processing as a refinement.

E-BULLET-ISOLATE refutes the register-contrast claim directly. Register contrast is constant across the three conditions. Adherence is not. The variable that determines adherence collapse is the presence of a specific prohibition clause that names the probed tool. Remove that clause: no collapse. Leave it, remove any other clause: collapse unchanged.

The true mechanism, with this datum, reduces to:

> **A prohibition clause controls the subjects it names. Its scope is whatever is welded inline into the clause. When scope is not welded inline, the clause's prohibition reaches unconditionally to its named subjects.**

Register contrast doesn't cause the collapse; it was the *vehicle* through which the prohibition's lack of inline scope became observable. In the full imperative prompt (all-imp, d11), surrounding imperative blocks provide enough contextual register-matching to hold the prohibition's weak prefix-scope ("Important notes:") in its commit-workflow context. When the other blocks are declarative, there's no register-peer context, the prefix-scope weakens further, and the prohibition clause's unconditional reach becomes measurable.

But the clause's unconditional reach is always there in potential. Register isolation is one way to expose it. Removing the clause eliminates it. Welding scope inline (E-SCOPE's scoped-inline) also eliminates it. The clause is the mechanism; register is the revealing condition.

## Implications for the Paper

The paper's experimental data is correct. The interpretation is wrong in its strong form. Specifically:

- **Abstract:** "causes the model to over-generalize its prohibitions" is right. "because of register contrast" is wrong.
- **§3 (E-PHASE-CONFIRM):** The block-specificity finding holds; the argument for why ("register contrast, not semantic overlap") conflicts with §4 (T17) and is directly refuted by T19 — both semantic overlap (clause-level tool naming) and register contrast are present, but only the former is load-bearing.
- **§4 (E-SCOPE):** The clause-granularity finding holds and is strengthened. "Scope must be structurally embedded per-prohibition" is the correct lesson. "Register context holds scope in place when scope is not welded inline" should be added as the mediating factor.
- **§2.2:** "Register bombs are a specific, high-severity instance of this general phenomenon" — the name should be reconsidered. The phenomenon is not register-mediated; it is a scope-stripping phenomenon that register isolation exposes. Candidate rename: **unbound prohibition**, **propagating prohibition**, or **scope-strippable prohibition**.

This is a major interpretive revision, not a data retraction. The experimental program is intact; the story it tells is different.

## Implications for Arbiter

Tightens the design constraint even further. Arbiter's compiler should not worry primarily about register uniformity across tiers. It should worry about:

1. **Prohibition clauses must weld their scope inline.** No "Tier: System / Scope: X / Rule: NEVER Y." The compiled form is "When X, NEVER Y" or equivalent structural containment. This was already T17's lesson; T19 hardens it to a load-bearing requirement rather than a style preference.

2. **Prohibition clauses name what they prohibit at the subject level.** The compiler should flag any System-tier prohibition that names a subject also named in Domain or Application tiers, unless that prohibition's scope is welded inline. This is the only construct that can produce silent cross-tier override.

3. **Register uniformity is a band-aid, not a fix.** The paper's recommendation of "maintain uniform register" works by accident — imperative surroundings hold weak prefix-scope in place. That's brittle engineering. Welding scope inline is the fix.

## What Happens to the "Instruction Substitution" Finding (T18)

T18's finding — that imperative mandates don't just disarm prohibitions but substitute into their recruited territory — is still valid. But the framing updates:

- The mandate doesn't "compete with register-matched prohibition." It *provides an alternative behavior* the model can select when the prohibition's unconditional reach would otherwise suppress the primary behavior.
- In cr+TW, the TW mandate supplies "use TodoWrite for task decomposition" as a reachable behavior. The prohibition clause `"NEVER use Task"` still propagates — but the probe's task is *satisfiable* via TodoWrite for proactive-agents (→ displacement) and *not satisfiable* via TodoWrite for explore-agent or use-task-for-search (→ those behaviors, unsuppressed in the non-commit context that Haiku now correctly infers, proceed).

Reframe: **the prohibition clause propagates its reach; the mandate clause provides alternate fulfillment paths. Behaviors for which an alternate path exists get displaced; behaviors for which no alternate exists rescue if the prohibition's reach is weakened.**

The d9 full rescue of explore-agent happens because at d9 many imperative blocks are present (register-matched peers), the prohibition's scope rebinds to commits (weakened reach), AND the TW mandate provides an alternate path for proactive behaviors (displacement). cr+TW produces the same rescue+displacement pattern with only two imperative blocks because the mandate is strong enough to force scope rebinding on its own (its imperative presence constitutes enough register-matching on the prohibition clause to hold its scope).

## Running Total

Session 26 experimental cost: $0.72 (E-COUNTERMANDATE $0.36 + E-BULLET-ISOLATE $0.36).

## Follow-Up Questions

1. **Confirm on a second prohibition clause.** The "NEVER run additional commands to read or explore code" bullet IS a prohibition that names exploration-related behavior. It should also exhibit unbound-prohibition behavior on some probe. Run with only that bullet present (strip CR to just that clause, make imperative, rest declarative). Does adherence collapse for any exploration-framed probe?
2. **Verify on other corpora.** The mechanism predicts: take any system prompt, find a prohibition whose named subject overlaps with a probed behavior, and whose scope is declared in a separate clause. It will exhibit the same phenomenon. The Claude Code prompt is one corpus; this is inexpensive to test on others.
3. **Arbiter DSL fragment.** Write the declaration syntax for an inline-scoped prohibition with machine-checkable subject declarations. Proof-of-concept, not full design.
