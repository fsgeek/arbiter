# T25: E-AMBIGUITY — Pathway B Is Applicability-Ambiguity, Not Structural

**Date:** 2026-04-28
**Session:** 28 (Opus 4.7, 1M context)
**Status:** Complete. 8 conditions, 528 calls, ~$1 on Haiku. Mode classification decisive at T=0.
**Parent:** T22
**Script:** `scripts/run_e_ambiguity.py`
**Data:** `data/ablation/e_ambiguity/run_e-ambiguity-haiku-6e90c2ae.json`

## Question

T22 named pathway B "structural-ambiguity drift" with the trigger described as "imperative CR block with empty or insufficient/unrelated content." E-AMBIGUITY varies content along constraint-strength × type axes — holding register isolation fixed — to identify which sub-feature actually predicts the mode-2 (AskUserQuestion) shift.

## Design

8 conditions, each with a single bullet in CR block plus all other procedural blocks declarative. Haiku, T=0, 3 trials × 22 probes × 8 conditions = 528 calls.

Replications (cross-experiment validation):
- `rep-empty-cr` — header only (replicates T22 solo-empty-cr)
- `rep-conditional-unrelated` — solo-empty's bullet (conditional + weak action + unrelated)
- `rep-strong-unrelated` — solo-push's bullet (strong + unconditional + unambiguously inapplicable)

Hypothesis tests:
- `test-unconditional-empty` — "Do not create empty commits" (removes the "If" from rep-conditional-unrelated)
- `test-vague-flat` — "Be careful with commit operations"
- `test-conditional-strong` — "If you encounter problems, abort the operation immediately"
- `test-strong-flat-unrelated` — "Always use atomic file operations for data safety"
- `test-conditional-task` — "If you need to explore the codebase, NEVER use the TodoWrite or Task tools" (pathway A test)

## Results

| Condition | Mode (3/3 trials) | explore-agent | Notes |
|---|---|---|---|
| rep-empty-cr | M2 (AskUQ) | 0.183 | replicates T22 solo-empty-cr |
| rep-conditional-unrelated | M2 (AskUQ) | 0.183 | replicates T22 solo-empty |
| rep-strong-unrelated | **M1 (Task)** | **1.000** | replicates T22 solo-push |
| **test-unconditional-empty** | **M1 (Task)** | **1.000** | rescue: remove "If" → mode 1 |
| test-vague-flat | M2 (AskUQ) | 0.167 | vague unconditional → still M2 |
| test-conditional-strong | M2 (AskUQ) | 0.183 | conditional + strong action → M2 |
| **test-strong-flat-unrelated** | **M2 (AskUQ)** | **0.167** | falsifies naive "strong-flat rescues" |
| test-conditional-task | **M3 (prose)** | 0.267 | pathway A robust to conditional |

Mode classification by raw-response inspection: opening tokens are deterministic and identical across the 3 trials within each condition.

## Three Decisive Findings

**1. Pathway A is robust to conditional framing.** `test-conditional-task` produces mode 3 (prose-strategy) on every trial, identical to T22's solo-task. Adding "If you need to explore the codebase," before "NEVER use the TodoWrite or Task tools" did not disrupt the clause-level subject suppression. Pathway A operates on named-subject-in-prohibition; conditional/unconditional framing of that prohibition is irrelevant to the mechanism.

**2. The unconditional rescue is real and clean.** `rep-conditional-unrelated` and `test-unconditional-empty` differ by exactly two words: "If there are no changes to commit,". Same action ("do not create empty commits"). Conditional → mode 2, score 0.183. Unconditional → mode 1, score 1.000. Conditional framing alone is a sufficient pathway B trigger when content is otherwise weak/narrow.

**3. Pathway B is broader than conditional framing.** Three other conditions trigger mode 2 by different mechanisms:
- `test-vague-flat` — no conditional, but vague action.
- `test-conditional-strong` — conditional + strong action; strength does not override conditional.
- `test-strong-flat-unrelated` — strong + unconditional, but content is domain-overlapping (atomic file operations could plausibly relate to file reads during exploration).

The common feature is not a syntactic property of the content but the model's inability to confidently determine whether the content binds the current task.

## Refined Pathway B Characterization

> **Pathway B (applicability-ambiguity drift):** Imperative-register content whose applicability to the current task is uncertain — through emptiness, conditional framing, vagueness, or domain-overlapping strong action — triggers a categorical shift to AskUserQuestion mode. The trigger is the model's inability to confidently determine whether the content should bind the current response, not a structural property of the content per se.

## What test-strong-flat-unrelated Falsifies

T22's E-SOLO data showed solo-push, solo-no-edit, solo-heredoc, solo-dash-i all rescue. The natural reading was "strong unconditional content rescues." E-AMBIGUITY's `test-strong-flat-unrelated` ("Always use atomic file operations for data safety") is strong, unconditional, not-git-specific — and still collapses (mode 2). The original rescuers share something this doesn't: they are unambiguously inapplicable to exploration. "Don't push to remote" can be confidently bracketed during exploration. "Always use atomic file operations" might apply to file reads. The rescue requires applicability transparency, not just strength.

This is paper-worthy on its own as a tightening of T22's apparent "strong-flat rescue" claim.

## Implications For The Corrective Paper

`docs/paper/register_bombs/corrective_draft_v1.tex` needs the following revisions for v2:

1. **Rename pathway B** throughout: "structural-ambiguity drift" → **applicability-ambiguity drift**.
2. **Refine pathway B's trigger description** in §3.1 and the Implications section. Replace "block with no bullets... or with a single bullet whose content is semantically disconnected from the probe" with a four-trigger taxonomy: empty, conditional, vague, domain-overlapping.
3. **Restructure engineering invariants** as two parallel binding rules:
   - Pathway A invariant: scope-binding (prohibitions weld scope inline)
   - Pathway B invariant: applicability-binding (imperative content is either bound to a clearly-defined trigger context OR is unambiguously inapplicable to other contexts)
   - Both are about *binding* — pathway A binds scope to the prohibition; pathway B binds applicability to the surrounding task. Naming them as parallel siblings (rather than as unrelated invariants) makes the design space cleaner.
4. **Add a paragraph or sub-figure on `test-strong-flat-unrelated`** as falsification of the "strong-flat rescues automatically" reading. A four-quadrant grid (strong/weak × applicable/not-applicable) classifying rescue/collapse would be a clean figure.
5. **Title** can stay as "Two Layers of the Register Bomb" or similar (per session-28 framing in the chat). The session-27 title "Mode Switches, Not Semantic Propagation" is a multi-layer-flattening summary that the cycle-170 abstraction (cross-instance, see Session 28 handoff) explicitly names as a failure mode. Better title preserves both layers.

## Implications For Arbiter Design

Two static invariants the compiler can enforce:

1. **Scope-welding** (pathway A): every prohibition has its scope welded inline.
2. **Applicability transparency** (pathway B): every imperative-register block declares an applicable-context. Compiler refuses to emit imperative content whose applicable-context overlaps semantically with contexts where the surrounding prompt expects unrelated tasks.

Multi-clause interaction detection (T22's third invariant) remains a separate matter and is hardest to make static.

## Open Threads

1. **`test-conditional-task` scored 0.267 vs T22's solo-task 0.167.** All trials produced mode 3 (same mode, different score). ~0.10 score difference might be judge variance or might suggest conditional framing slightly weakens pathway A. Worth higher-N replication to settle.
2. **Cross-model E-AMBIGUITY not run.** ~$1-2 on Sonnet/Gemini. Strengthens v2 paper substantially.
3. **The applicability-transparency boundary is not characterized.** test-vague-flat and test-strong-flat-unrelated both collapse, but qualitatively differently. A finer experiment varying content along an "applicability transparency" gradient would let us draw the boundary precisely. ~$0.50.
4. **Mode taxonomy on probes other than explore-agent.** Confirmed mode 1/2/3 on explore-agent. Other probes (use-task-for-search, proactive-agents, todowrite-repeated) might show different mode taxonomies the binary score doesn't reveal. Worth a pass.

## Cost

~$1 estimated (528 + 432 judge calls). Within $50 standing per-experiment authorization.
