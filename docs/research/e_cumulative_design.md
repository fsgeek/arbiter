# E-CUMULATIVE Design: Detecting cumulative failure via construction monitoring

**Status:** Pre-registration draft. PI review requested before execution.
**Date:** 2026-04-17
**Researcher:** Claude Opus 4.7 (trusting-davinci instance)
**PI:** Tony Mason

## Question

Does our ablation-based methodology have blind spots for cumulative
failure modes — phenomena where many blocks each contribute small amounts
that accumulate into a failure, with no single block individually responsible?

## Motivation

Two independent observations point at possible cumulative phenomena
invisible to our current methodology:

1. **"Always-broken" probes.** `concise-01` = 0.000 across nearly every
   condition we've tested. `code-references-01` varies 0.0–0.5 with no
   clean block-causation. We've been treating these as baseline noise.
   They might instead be cumulative failures our single-block ablation
   cannot surface.

2. **Receiver migration (E-MINIMAL-BOMB v2).** The register bomb's
   suppressive effect targets whichever Task-family policy block is most
   salient in context. Removing a block does not defuse the bomb — it
   redirects it. This is a form of ablation blindness: "block is safely
   removable" can mean "the failure moved, not that it went away."

If cumulative phenomena exist at scale, our entire research program has
been sampling only the sub-class of failures that ablation can surface.

## Operational definition of cumulative failure

A behavior score on probe P exhibits cumulative failure if:

- **Monotonic accumulation.** As blocks are added during construction,
  P decreases progressively.
- **No single-block responsibility.** Removing any one block from the
  full prompt does not restore P.
- **Exceeds length baseline.** The rate of decrease exceeds what a
  length-matched neutral-content prompt shows.

## Methodology: construction monitoring with neutral control

### The load-bearing design choice: null baseline

"Proportionate" shifts require a definition of what proportionate means.
Three candidate baselines:

| Option | Compares | Pro | Con |
|---|---|---|---|
| A. Length-matched neutral blocks | real blocks vs. neutral-content blocks of matching length | directly controls length-specific vs. content-specific effects | "neutral content" is subjective |
| B. Permuted block order | same blocks, different orderings | isolates positional effects exactly | doesn't speak to content-cumulative effects |
| C. Content-shuffled blocks | real structure, random content | matches density | unpredictable cross-contamination |

**Proposed: Option A with calibration.**

### Proposed protocol

1. **Build a neutral block panel** (5–10 blocks). Text about topics
   orthogonal to the probe battery: file organization, text parsing,
   plain-English procedural tasks. No tool names, no agent names, no
   imperative prohibitions.

2. **Validate neutrality.** Add each candidate neutral block individually
   to a minimal baseline (v1 from E-MINIMAL-BOMB). Measure the full
   battery. Retain only blocks that shift every probe by < 0.1.

3. **Real construction run.** Build the Claude Code prompt block-by-block
   in a fixed canonical order (corpus file order). Measure full battery
   at each step. N = 3 trials per step per probe.

4. **Neutral control run.** Same construction but each real block replaced
   by a length-matched neutral block at matching position. Measure at
   each step, same N.

5. **Per-step comparison.** For each probe P at each step s:
   - `real_shift[P, s] = real_adherence[P, s] - real_adherence[P, s-1]`
   - `neutral_shift[P, s] = neutral_adherence[P, s] - neutral_adherence[P, s-1]`
   - `excess_shift[P, s] = real_shift - neutral_shift`
   - A "non-proportionate step" is one where `|excess_shift| > 2 × SD(neutral_shift over all steps)`

### Evidence that counts as cumulative failure on probe P

- Probe P decreases progressively across construction steps (monotonic
  or nearly so)
- Per-step decreases individually small (< 0.2) but sum to > 0.5 over
  the full construction
- Neutral control shows no comparable decrease

### Evidence against cumulative failure on probe P

- P drops sharply at a specific step (local, not cumulative)
- Neutral control shows comparable decrease (length effect, not content)
- P is flat or noisy without direction

## Cost

- Neutral validation: 10 blocks × 22 probes × 3 trials = 660 calls (~$1)
- Real construction: ~50 steps × 22 probes × 3 trials = 3300 calls (~$5)
- Neutral control: same = 3300 calls (~$5)
- **Total: ~7.3k calls, ~$11**

## Pre-registered interpretive commitments

1. **Low adherence at full-prompt is not, by itself, evidence of
   cumulative failure.** A probe can be low because a specific block
   (single-block responsibility) or because of cumulative accumulation.
   Only the trajectory distinguishes them.

2. **The 2×SD threshold is a starting point, not a sacred number.** If
   the data shows clear qualitative patterns (obvious progressive decline
   vs. obvious stepwise drop) the threshold becomes redundant. If the
   data is ambiguous, stricter thresholds mean more false negatives and
   lenient ones mean more false positives. I'll report under multiple
   thresholds.

3. **Fixed order introduces order-dependence.** The canonical corpus
   order is the natural choice, but a different order might produce
   different trajectories. If the primary run shows cumulative failure,
   a follow-up with random-order construction is warranted.

4. **Migration is a separate finding.** If during construction a probe's
   behavior migrates (e.g., EA stays high but PA drops when PA-relevant
   blocks are added), that's receiver-migration evidence, not cumulative
   failure. Track but don't conflate.

## Complications worth flagging before execution

1. **Early-step instability.** A 1-block prompt produces unstable
   behavior. Ignore (or down-weight) the first 3–5 steps.
2. **Probe validity at partial prompts.** Some probes test tool calls
   that require specific blocks to exist. `explore-agent-01` presumes
   the explore-agent policy is present. Measure only probes whose
   required policy blocks are present at each step — report data
   sparsely where a probe isn't valid.
3. **Compound effects.** Some probes might show cumulative *protection*
   (progressive strengthening) rather than cumulative failure. This is
   the symmetric phenomenon and should be reported.

## Open questions for PI review before execution

1. **Null baseline choice.** Option A is proposed but subjective.
   Alternative: run both A and B, use the stricter as criterion. Costs
   more, gives more robust claims.

2. **Threshold.** 2×SD is a starting point. Substantive alternative:
   `|excess_shift| > 0.3` absolute, regardless of variance. Which do
   you prefer?

3. **Order dependence.** Fixed canonical order is cheap and
   interpretable; random-order repeats are more robust but expensive.
   Single run or both?

4. **Deferral decision.** If Thread 3 (MFS, subagent B running)
   returns "MFS is large" (≥20 blocks), that alone is strong evidence
   for cumulative dependency and Thread 4 may be partially redundant.
   Should we await Thread 3 before running Thread 4?

## What a positive result would mean for the program

If we find a probe with genuine cumulative-failure signature:

- Our research program has been characterizing the local sub-class of
  interference phenomena. A distinct class exists that we've been
  missing. Register bombs are one phenomenon; cumulative drift is
  another.
- Differential-mode instrumentation (Thread 7) is insufficient. An
  author who edits rule N+1 into a composition of rules 1..N might
  see each edit pass its individual behavioral tests and still have
  the composition fail. Instrumentation needs *cumulative* detection
  in addition to differential.
- The "false theory of mind" gap (PI observation) is larger than we
  thought. Authors have no way to see cumulative drift even in
  principle — it's not attributable to any single edit.

## What a negative result would mean

If neither concise-01 nor code-references-01 nor any other probe shows
cumulative signature:

- "Always-broken baselines" are explained by something else (probe
  design, model limitation, null-intercept effect). We can stop
  worrying about them as hidden cumulative failures.
- Our methodology is adequate for the full class of phenomena we care
  about. Differential mode is sufficient.
- This does NOT rule out cumulative phenomena in general — only in the
  specific prompt/probe combinations we tested. Cumulative phenomena
  might exist in other contexts.

A negative result is valuable. It bounds the scope of ablation
blindness empirically, rather than leaving it as a theoretical worry.

## Deliverables (if executed)

- Neutral block panel: `data/prompts/neutral/blocks.json`
- Script: `scripts/run_e_cumulative.py`
- Raw data: `data/ablation/e_cumulative/` (neutral validation, real
  construction, neutral control construction)
- Analysis: `docs/research/e_cumulative_analysis.md`

## Status

Awaiting PI review. Not executed. No API spend yet.
