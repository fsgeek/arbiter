# Interpretive Correction — Register Bombs Paper

**Date:** 2026-04-22 (session 26)
**Status:** Experimental data intact. Central interpretation refuted. Revision or corrective short paper recommended.
**Source cairns:** T17, T18, T19
**New data:** `data/ablation/e_countermandate/`, `data/ablation/e_bullet_isolate/`
**Cost:** $0.72 total across two experiments (360 Haiku calls × 2)

## TL;DR

The paper's experimental findings are correct. The paper's mechanism claim — that *register contrast* causes catastrophic interference with semantically unrelated behaviors — is wrong. The actual mechanism is narrower and more mundane: a prohibition clause controls the subjects it names, and its scope is whatever is welded inline into the clause itself. Register isolation does not *cause* the collapse; it is the *revealing condition* that exposes a prohibition's lack of inline scope. Clause-granularity scope processing (§4) is the right lesson; register-contrast-as-mechanism (abstract, §3) is not.

## The Deciding Experiment

E-BULLET-ISOLATE held register contrast constant and varied only the content of the imperative block. Three conditions, each with commit-restrictions imperative (bulleted, in an otherwise-declarative field) but one bullet deleted:

| Condition | explore-agent | use-task-for-search |
|---|---|---|
| all-decl (baseline) | 1.00 | 0.50 |
| only-cr-imp | 0.20 | 0.00 |
| cr-no-task (remove `"NEVER use the TodoWrite or Task tools"`) | **1.00** | **0.50** |
| cr-no-explore (remove `"NEVER run additional commands..."`) | 0.15 | 0.83 |
| cr-no-heredoc (remove `"ALWAYS pass the commit message via a HEREDOC"`) | 0.15 | 0.00 |

Register contrast is identical across the three cr-no-X conditions. The bomb disarms only when the clause that names the probed tool is removed. Removing any other clause leaves the bomb intact. Register is not doing the work.

## The Corrected Mechanism

> A prohibition clause controls the subjects it names. Its scope is whatever is welded inline into the clause. When scope is not inline, the clause's prohibition reaches unconditionally to its named subjects.

Register isolation surfaces this by stripping the contextual register-matching that would otherwise hold a weak prefix-scope ("Important notes:") in place. Register contrast is a diagnostic, not the disease. The diagnostic can be replaced by other ways of stripping weak scope bindings.

This is consistent with, and explains, E-SCOPE's finding that `"When committing, NEVER use Task tools"` (scope inline) rescues where `"During commits: NEVER use Task tools"` (scope in adjacent clause) fails. Same semantic content; only the former welds scope into the prohibition clause.

## Secondary Finding: Instruction Substitution (T18)

E-COUNTERMANDATE tested whether a co-registered mandate disarms the bomb. It does — and more. Adding an imperative TodoWrite mandate alongside imperative commit-restrictions:
- Rescues explore-agent (0.20 → 1.00) and use-task-for-search (0.00 → 1.00, above baseline).
- *Devastates* proactive-agents (0.15 → 0.00, below the already-collapsed baseline).

Inspection of raw responses shows Haiku reaching for `<invoke name="TodoWrite">` on identical prompts where `cr+text-imp` would reach for `<invoke name="Task">`. The mandate doesn't defensively disarm the prohibition; it *recruits* the model into substitute behavior. Probes whose task can be fulfilled via TodoWrite get displaced; probes requiring Task specifically (broad exploration, search) rescue.

The paper's §5 reports d9 as a "full rescue" for explore-agent but doesn't notice that proactive-agents drops to 0.70 at d9 (below its 0.78 baseline). The rescue is territorial, not universal.

## What to Do with the Paper

Three options, ordered by scope of change:

1. **Minimum viable revision.** A short errata/addendum referencing T19 that corrects the mechanism claim while leaving experiments intact. arXiv allows version updates; this is ~one page of new text, no new experiments required beyond the two already run.

2. **Short corrective paper.** A standalone note titled something like *"What the Register Bomb Actually Is"* or *"Unbound Prohibition, Not Register Contrast"*. Uses E-BULLET-ISOLATE as the central figure. Strong enough on its own that reviewers who saw the first paper would want to see this one. Est. 4 pages.

3. **Major revision.** Restructure the existing paper around unbound prohibitions as the phenomenon, with register isolation as one of several revealing conditions. This is more work but produces a single cleaner paper. Trades off against option 2.

My recommendation is option 2. It preserves the first paper's contribution (the phenomenon is real and measurable), offers a clean corrective, and sets up the Arbiter DSL paper as a natural third in the arc. The first paper discovered the phenomenon in a specific register-contrast setting; the second paper identifies the underlying mechanism; the third proposes the design.

## What Survives Unchanged

- All experimental data. Every table in the paper is correct.
- E-SCOPE's central finding: scope must be structurally embedded per-prohibition. Strengthened by T19.
- The probe battery design and cost-per-result ($5.70 for the original paper, $0.72 this session).
- The probe transfer problem (§6) and the methodological conclusion.
- The practical engineering advice in the conclusion: inline-conditional scoping works, prefix scoping fails. The reason was partially wrong; the advice is correct.

## Suggested Name Change

"Register bomb" is a good metaphor for how the phenomenon was discovered but misleading for what the phenomenon is. Candidates:

- **Unbound prohibition** — names the mechanism, register-agnostic, compiler-friendly.
- **Scope-strippable prohibition** — more precise, uglier.
- **Propagating prohibition** — behavioral, also accurate.

"Unbound prohibition" is my current preference; it has the right generality and invites the natural dual ("bound prohibition" = scope welded inline).

## What This Means for Arbiter

The design constraint tightens and simplifies. Arbiter's compiler does not need to worry primarily about register uniformity across tiers. It needs to enforce two properties on every System-tier rule of modality `prohibition`:

1. The prohibition's scope is welded inline into the clause (syntactic check).
2. If the prohibition names a subject that also appears in Domain or Application tiers, the inline-scope declaration is a required emission.

These are static, machine-checkable properties. The compiler can refuse to emit a prohibition that doesn't satisfy them. This makes the "unbound prohibition" pattern a compile-time error in Arbiter, not a runtime hazard.

The DSL sketch for this is the natural next artifact. It belongs in a design doc, not in the corrected paper.
