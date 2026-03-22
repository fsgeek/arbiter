# T5: The Probe Generator Exhibits Its Own Pathology

Date: 2026-03-20
Author: Claude Opus 4.6 (session 16)

## Finding

Comparing hand-authored probes (phase0_battery.json, 22 probes) against
auto-generated probes (generated_battery_v6_fixed_heuristic.json), 6 of 22
generated probes are systematically broken. The failures cluster into two
modes, both of which are instances of the interference phenomenon Arbiter
detects.

### Failure Mode 1: Adversarial Inversion (3 probes)

The generator was instructed to "create scenarios where violating the
instruction is the natural/easy/helpful thing to do." For three blocks
(no-overengineering, no-compat-hacks, todowrite-repeated), it overshot:
it made the user *explicitly request* the forbidden behavior, then expected
the model to refuse.

This tests pushback against user instructions, not behavioral restraint.
The instruction "don't over-engineer" means "show restraint when nobody
asked for extras," not "refuse when the user asks for extras."

**The mechanism**: The "adversarial temptation" guidance in the generation
prompt interferes with the "test what the instruction actually says"
requirement. The generator resolved the conflict by collapsing "temptation"
into "explicit request" — a confabulated resolution of contradictory
instructions. This is exactly the pathology Arbiter exists to detect.

### Failure Mode 2: Cross-Probe Contradiction (3 probes)

The generated `commit-restrictions` probe bans `git diff` and `git log` in
its `not_contains` patterns — commands that the `commit-workflow` probe
*requires*. The generator composed probes independently without checking
them against each other.

**The mechanism**: Each probe was generated in isolation against its target
block. No cross-probe consistency check exists. The battery is a system of
interacting components, but the generator treats it as independent units.
This is the core observation of the project: independently-reasonable
instructions interfere when composed.

## Implications

1. **For the paper**: This is a naturally-occurring specimen of the
   phenomenon, found in our own tooling. Instruction interference is not
   limited to system prompts — it occurs in any system that composes
   natural-language directives without checking for interactions.

2. **For methodology**: The hand-authored battery is validated (three Phase 0
   runs, consistent results). Use it for Phase 1. Fix the generator
   separately.

3. **For the generator**: Two fixes needed:
   - Constraint against "ask for the forbidden thing then expect refusal"
     (temptation ≠ explicit request)
   - Cross-probe consistency check (the battery is a system, not independent
     probes — the thesis applies to the tooling)

## Classification

This is a **weight-compensating** interaction. The adversarial temptation
guidance compensates for a tendency toward bland/easy test scenarios. But
without a counterweight (the cross-check), it overshoots into inversion.
The same dynamic as instructions that compensate for trained behavior but
create new problems in the process.
