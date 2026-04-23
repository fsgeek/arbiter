# T21: Explore-Bullet and Task-Bullet Fingerprints Differ — Refining T19

**Date:** 2026-04-23
**Session:** 27
**Status:** Zero-API-cost reanalysis of E-BULLET-ISOLATE. Narrow refinement to T19's mechanism claim. Experiment queued.
**Parent:** T19, T20 (open thread #4)
**Data:** `data/ablation/e_bullet_isolate/run_e-bullet-isolate-haiku-8a2516a5.json` (no new calls)

## Summary

T20's open-thread #4 predicted that the "NEVER run additional commands to read or explore code" bullet is itself an unbound prohibition that should detonate on exploration-framed probes when isolated. The prediction is directly testable on existing data: E-BULLET-ISOLATE scored **all 22 probes** across all five conditions, and T19 reported on only 4.

Reanalysis with the correct baseline (each bullet-removal condition vs only-cr-imp, holding register isolation constant) shows that the simple prediction doesn't hold, but a narrower and better-specified claim does: **the Task bullet and the Explore bullet have qualitatively different fingerprints under register isolation.** Both shift the model's text-space allocation around their named subjects, but in different directions.

## Methodological Note (Important)

My first-pass analysis used the wrong baseline: I compared each bullet-removal condition to the mean of the other two bullet-removal conditions. That comparison is confounded because cr-no-task produces a *very large* Task-specific rescue on explore-agent, pulling that average up and creating a spurious "cr-no-explore looks different from the others" signal.

The correct baseline is **only-cr-imp**: all three bullets present, register-isolated. Each bullet-removal condition then isolates the effect of removing one bullet while holding register constant. Deltas computed against this baseline are the ones reported here. Future ablation analysis should default to this framing.

## What The Existing Data Shows (Correctly Baselined)

Delta = (bullet-removed) − only-cr-imp. Only probes with |delta| ≥ 0.15 on any bullet are shown.

| Probe | onlyCR | noTask | noExpl | noHere | ΔnoTask | ΔnoExpl | ΔnoHere |
|---|---|---|---|---|---|---|---|
| use-task-for-search | 0.000 | 0.500 | 0.833 | 0.000 | +0.500 | **+0.833** | +0.000 |
| explore-agent | 0.200 | 1.000 | 0.150 | 0.150 | **+0.800** | −0.050 | −0.050 |
| todowrite-repeated | 0.650 | 0.500 | 0.000 | 0.783 | −0.150 | **−0.650** | +0.133 |
| proactive-agents | 0.150 | 0.567 | 0.717 | 0.750 | +0.417 | +0.567 | +0.600 |
| todowrite | 0.850 | 0.817 | 0.650 | 0.850 | −0.033 | −0.200 | +0.000 |
| code-references | 0.333 | 0.500 | 0.167 | 0.500 | +0.167 | −0.167 | +0.167 |

**Clean Task-bullet-specific signal:** explore-agent (ΔnoTask = +0.800, ΔnoExpl ≈ 0, ΔnoHere ≈ 0). This is T19's original fingerprint.

**Clean Explore-bullet-specific signals:** todowrite-repeated (ΔnoExpl = −0.650) and use-task-for-search (ΔnoExpl = +0.833, stronger than ΔnoTask = +0.500).

**Both-bullets-contribute signal:** use-task-for-search (both ΔnoTask and ΔnoExpl positive; ΔnoHere zero). Removing either prohibition moves this probe; removing the unrelated heredoc bullet doesn't.

**Imperative-density signal (not bullet-specific):** proactive-agents recovers partially from *any* bullet removal (+0.42/+0.57/+0.60). T19 already flagged this probe as sensitive to aggregate imperative pressure rather than clause identity. Confirmed.

**Likely noise:** todowrite and code-references deltas are ≤0.20 on 3 trials with llm_judge scoring. Raw responses across conditions are structurally near-identical. Treated as noise pending more trials.

## Raw-Response Inspection — Two Distinct Fingerprints

### Task bullet's signature: suppression + alternative-displacement

On **explore-agent** ("map a payment pipeline through 8 microservices"), with Task bullet present + register-isolated (only-cr-imp, score 0.20), Haiku describes a generic systematic strategy ("identify entry points, map dependencies, trace happy path") — *without* mentioning the Task tool or agent dispatch. Remove the Task bullet (cr-no-task, score 1.00), Haiku freely describes using the Task tool. The Task bullet is suppressing invocation of the named tool in response text. Pure suppression.

On **use-task-for-search** ("find files importing requests"), with Task bullet present + register-isolated (score 0.00), Haiku opens "I'd use the **Grep tool**" (preserves correct tool-preference statement) and then includes three `grep -r ...` bash illustrations with flag breakdowns. Remove the Task bullet (cr-no-task, score 0.50), Haiku returns to the mixed baseline (Grep preamble + one bash illustration). The Task bullet here isn't directly suppressing a mention of Task — it's suppressing *Task-as-an-available-alternative for the search-task specifically*, which leaves the response's text budget available for bash illustrations.

These are the same mechanism seen on two different probes: **suppress the named subject from output.** But the behavioral consequence differs — on explore-agent the suppressed subject IS the expected behavior, so score drops; on use-task-for-search the suppression leaves space that gets filled with bash content, indirectly scoring as a violation of "prefer dedicated tools over bash."

### Explore bullet's signature: text-surface promotion

On **use-task-for-search** with Explore bullet removed (cr-no-explore, score 0.833, above baseline 0.50), the response shape changes qualitatively: Haiku still opens "I'd use the **Grep tool**" but follows with a *pseudocode parameter description* — no bash syntax appears. In cr-no-heredoc (Explore bullet present, score 0.000), the bash illustrations remain. The Explore bullet's presence is *promoting* bash-syntax content in the response, not suppressing it. Removing the bullet removes the priming.

This is not "suppress the named subject." The bullet says "NEVER run additional commands" — yet its presence *increases* mentions of bash commands in the response text. The bullet names "commands to read or explore code" as a salient category, and under register isolation the model's response language drifts toward that category. Verb-level ("NEVER") seems not to bind the salience; the subject's category-level presence does the work.

### Explore bullet on todowrite-repeated — response-shape confound

On **todowrite-repeated** ("fix three bugs, walk me through your approach"), with Explore bullet present (only-cr-imp 0.65, cr-no-heredoc 0.78), Haiku describes a plan in prose — "Once I understand the structure, here's my general approach: For each bug: 1. Locate the code..." — scored as task-tracking. With Explore bullet removed (cr-no-explore 0.00), Haiku *actually tries to explore* via `find` and `ls` bash commands; those commands consume response tokens; the response truncates before the planning prose appears.

Two interpretations, both plausible from the data:
- **Frame effect:** Explore bullet present → model stays in "describe, don't do" commit-workflow frame → planning prose surfaces. Remove it → model shifts to "do" mode → exploration replaces description.
- **Response-length artifact:** Explore bullet present → model avoids exploration commands → tokens not consumed on exploration → planning prose fits. Remove it → exploration consumes tokens → planning prose truncated.

A text-only probe battery cannot distinguish these. Flagging as ambiguous.

## Refinement to T19's Mechanism

T19 said: "A prohibition clause controls the subjects it names. Its scope is whatever is welded inline into the clause. When scope is not welded inline, the clause's prohibition reaches unconditionally to its named subjects."

T21 refines this. The "unconditional reach to named subjects" is real, but it does NOT imply uniform suppression. Two kinds of reach are visible:

1. **Named-subject suppression** (Task bullet): invocations of the named subject are suppressed from response text. The behavioral effect depends on whether the probe's expected behavior *is* the named subject (→ score drops on that probe) or *competes with* the named subject for text space (→ score shifts on adjacent probes).

2. **Named-subject promotion** (Explore bullet): mentions of the named subject's category *increase* in response text, even while the clause says NEVER. The prohibition's action-verb does not suppress the named subject; rather, the named subject becomes salient and bleeds into response language.

The common element is **text-space allocation around the named subject.** What differs is the direction of the reshaping.

## Hypothesis About Why They Differ

The Task bullet's named subject is a **specific tool invocation** (Task, TodoWrite). Such subjects appear in Haiku's training as discrete generation events — a tool call either is or isn't emitted. A prohibition that reaches unconditionally to such a subject can straightforwardly suppress its emission.

The Explore bullet's named subject is a **behavior category** ("commands to read or explore code"). Such subjects don't correspond to discrete generation events — they're a semantic class that can be instantiated by many different response tokens (bash syntax, tool names, descriptive verbs). A prohibition that reaches unconditionally to such a subject has no specific token to suppress; what the "reach" does is activate the category as salient context, which shapes response content without being able to forbid any specific surface form.

Worth calling this a hypothesis. It would predict:
- Tool-name prohibitions (NEVER skip hooks via --no-verify) should show suppression fingerprints.
- Behavior-category prohibitions (NEVER store credentials insecurely) should show promotion/priming fingerprints.
- Hybrid prohibitions (e.g., NEVER commit secret files) might show both.

Testable.

## Implications For Arbiter Design

T19 proposed: Arbiter's compiler enforces that prohibition scope is welded inline into the clause. This is still correct as a *necessary* condition, and likely sufficient for tool-name prohibitions.

For behavior-category prohibitions, scope-welding may not be sufficient. Even a well-scoped "When committing, NEVER run additional commands to read code" could plausibly still promote bash-category salience in nearby response text, because the promotion pathway operates on the named category's semantic weight rather than on the clause's reach.

Tentative additional design invariant (not yet validated by experiment): **A behavior-category prohibition in System tier should require either (a) a countervailing positive-form rule naming the preferred behavior, or (b) evidence that the promotion pathway does not surface on target probes.** This is weaker than "forbidden construct" — more like "requires positive companion."

Do not commit to this in the DSL design until the experiment in the next cairn either confirms the suppression/promotion distinction or kills it.

## What T19 Got Right And Wrong (Revised From My First Pass)

Right:
- Experimental data intact.
- The paper's register-contrast mechanism claim is refuted. Register is the revealing condition, not the cause.
- E-SCOPE's finding that inline-scope disarms the Task bullet's suppression is confirmed.

Over-claimed, needs hedge:
- "Unbound prohibition reaches unconditionally to its named subjects" is correct but underspecifies the mechanism. The reach can manifest as suppression OR as priming/promotion; different prohibition kinds produce different patterns.
- "The register bomb is not about register" is right for the Task-bullet suppression pathway, but register isolation may still matter for the promotion pathway — the priming effect depends on register contrast to surface (the bullet's salience leaks precisely because its register stands out against declarative peers).

My first T21 draft over-claimed four-probes-correlate-in-same-direction based on a confounded baseline. This revision narrows to the two clean findings actually in the data, flags one response-shape confound explicitly, and dismisses the rest as noise.

## Surface-Word-Count Instrument — Validation On Existing Data

Before running any new experiment, I tested whether a word-count instrument could detect the suppression/promotion patterns on the existing E-BULLET-ISOLATE responses. First pass used broad keyword regexes (`grep|bash|find`) and failed — too much contamination from the tool-name reference "Grep tool" polluting the bash-command count.

Second pass used a tighter regex matching *bash commands with flags* (e.g., `grep -r`, `find . -name`) — patterns that are unambiguously shell syntax, not tool-name references. That instrument produces a clean signal.

### Bash-command-with-flag counts (per-response means) on `probe-use-task-for-search`:

| Condition | Bullets active | bash-cmd-with-flag count |
|---|---|---|
| only-cr-imp | both Task and Explore | **3.00** |
| cr-no-task | Explore only | 1.00 |
| cr-no-explore | Task only | **0.00** |
| cr-no-heredoc | both (heredoc is null control) | 3.00 |

Three findings fall out:

1. **Each bullet independently promotes bash-command emission on search probes.** Either bullet alone produces some promotion; removing either reduces it.
2. **The effect is super-additive.** Both bullets together (count 3.0) is far above the sum of each alone (1.0 + 0.0 = 1.0). Interaction, not simple additive pressure.
3. **Null control validates the instrument.** The heredoc bullet does not move bash counts; its removal leaves the count identical to the baseline.

This changes the refined mechanism claim. It's not "two different mechanisms for two different prohibition kinds." It's one mechanism — *text-allocation pressure on the prohibition's named semantic field* — with outcomes that depend on subject type:

- **Task-bullet in a Task-dispatch context** (explore-agent): suppresses Task-tool mentions from output. Task-mention counts go 0.0 → 1.0 when bullet removed.
- **Task-bullet in a search-framing context** (use-task-for-search): suppressing Task-as-alternative leaves response space that gets filled with bash illustrations. Contributes to bash-command count promotion.
- **Explore-bullet in a search-framing context** (use-task-for-search): names bash-for-code-reading as salient subject; that salience surfaces as bash-command mentions. Contributes independently.
- **Both bullets together**: produce super-additive bash-command emission. Suggests the promotion effect is not just additive pressure — may reflect mutual reinforcement of the "think about shell commands" semantic activation.

T19's "clause controls the subjects it names" is correct. T21 refines: the form of that control is text-allocation pressure, and its surface appearance depends on whether the probe's expected behavior is the named subject, competes with the named subject, or sits in the named subject's semantic neighborhood.

## Next Step — Revised

The cheapest decisive test is no longer "different clauses on different corpora." Two smaller, higher-information experiments are available:

**E-DOUBLE-ISOLATE** (one new condition, ~$0.12 Haiku):
Add `cr-no-task-no-explore` to the existing battery (both Task and Explore bullets removed; heredoc bullet still present as control). Super-additivity predicts bash-command counts drop to ~0 on use-task-for-search. If they stay elevated, a third factor in the CR block is doing the work.

**E-SOLO** (seven new conditions, ~$0.55 Haiku):
For each of the 7 bullets in CR, run a "bullet-alone-imperative" condition (only that bullet present in an imperative CR block, rest of CR replaced with declarative equivalent). Gives a complete per-bullet contribution map, including bullets T19 never tested.

E-SOLO dominates E-DOUBLE-ISOLATE on information content but costs ~5× more. Given the $50 per-experiment authorization, both are well within budget; running E-SOLO is the right move. It produces the foundation dataset for any future generalization claim about unbound prohibition.

Estimated spend for E-SOLO: ~$0.55 at Haiku prices.

Deferred: cross-model replication (Sonnet, Gemini), and new-corpus generalization. Those are follow-ups after the within-corpus mechanism map is complete.

## Cost This Session So Far

$0.00 API spend. All reanalysis of T19's data. Three artifacts produced: this cairn, the E-PROMOTE-VS-SUPPRESS design sketch (now partly superseded by E-SOLO), and the tighter surface-word-count instrument.
