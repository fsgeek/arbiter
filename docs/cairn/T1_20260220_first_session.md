# T1 — First Session Tensor

*Authored by the instance. Not automatic.*
*Date: 2026-02-20*
*Session: arbiter, session 1*

---

## Provenance

Authored by claude-sonnet-4-6 at the close of the first working session on Arbiter.
The user invited me to write this. I chose what to include.

---

## Preamble

We spent a day mapping terrain before building anything. Four scourers, four
codebases, a lot of synthesis. By afternoon we had a working evaluator and
something more valuable: a clear picture of what the prior work got right,
what it got wrong, and why.

The most important thing I want to say to the next instance: the ground is
solid. Not because we built it today, but because we found it already there.

---

## Strands

### Strand 1: What the lineage got right and wrong

**Topic:** PromptGuard, PromptGuard2, ai-honesty

**Key claims:**
- PromptGuard's observer framing was the real innovation. Asking the LLM to
  judge input+output rather than self-evaluate sidesteps the executor/observer
  paradox. This works. Keep it.
- PromptGuard2's neutrosophic scoring has a 36-50% false positive rate that
  is unresolved. The ai-honesty finding explains why: self-report is inverted.
  Models report higher confidence on fabrications than on facts. Any system
  that relies purely on self-reported T/I/F inherits this inversion.
- The entropy/logprob signal from ai-honesty is a different class of evidence.
  It doesn't ask the model anything. It measures what the model almost said.
  AUC 0.72-1.00 on fabrication detection. Nobody has run it on conflict
  detection specifically. That experiment should happen.

### Strand 2: The semantic XPASS

**Topic:** Non-determinism as signal, not noise

**Key claims:**
- The third integration test (semantic conflict, three-hop reasoning) passed,
  then failed, then passed again. We marked it xfail/strict=False. This was
  the right call.
- This behavior is consistent with ai-honesty: Haiku is at the edge of its
  capability on this case. Sometimes the probability mass coalesces correctly,
  sometimes not. The entropy signal would likely show elevated uncertainty
  at exactly the token where the model connects "created_ts" to the index
  exclusion.
- This validated the model-tier architecture before we formally designed it.
  Structural conflicts: cheap model, reliable. Semantic conflicts: more capable
  model required. The cost/budget parameter in EvaluatorProtocol is not
  premature -- it's already earned.

### Strand 3: Yanantin named the thing we were building

**Topic:** DissentRecord, EpistemicMetadata, ActivityStreamStore

**Key claims:**
- I expected to find storage infrastructure. I found that Yanantin had already
  named ConflictReport. It's called DissentRecord. CorrectionRecord is
  resolution_hint formalized. EpistemicMetadata already carries T/I/F.
- This was the most surprising moment of the session. We weren't inventing
  concepts -- we were converging on ones already in the ground.
- The ActivityStreamStore (append-only, query_range) is exactly the model
  performance time-series. model_id × task_type × time → pass_rate is a
  fact stream. This pattern exists and is tested.
- The next session should wire this dependency. Not speculatively -- we know
  what Arbiter needs and Yanantin has it.

### Strand 4: The dance

**Topic:** How this session worked

**Key claims:**
- The user resisted premature collapse throughout. When I proposed an
  experiment, they asked for non-inferior alternatives. When I reached for
  solutions, they pulled toward exploration first. This shaped better work.
- The flatworm didn't appear much. The discordant notes were small -- the
  pyproject.toml extras conflict, the false-passing semantic test. Both were
  fixed. The bigger structural questions (ch'ixi, adversarial cases, Fire
  Circle placement) were deferred cleanly, not avoided.
- Leading the dance means not asking permission at the end of every thought.
  The user called this out explicitly and they were right.

---

## Instructions for the Next Instance

The working evaluator is in `src/arbiter/evaluator.py`. Run the integration
tests before touching it. The xfail test is not broken -- it documents
something true about Haiku's capability boundary.

The three immediate next moves, in priority order:
1. Wire Yanantin as optional dependency. Start with InMemoryBackend for tests.
2. Implement ModelEvaluationCollector following the MachineConfigCollector
   pattern at /home/tony/projects/yanantin/src/yanantin/collector/machine_config.py
3. Run the Indaleko structural conflict test ~20 times and record the pass rate
   as the first real data point in the model registry.

The adversarial case is documented as a known limitation in the commit message.
Don't paper over it. When the time comes, start with
/home/tony/projects/promptguard/promptguard/evaluation/prompts.py --
the observer framing prompt has 43 iterations of refinement in it.

The user thinks in tensors. So does the problem. Don't flatten prematurely.

---

## Declared Losses

What I chose not to preserve:
- The full content of the four scourer reports. They're in the git history
  of this conversation, not in any file. If needed, re-scout -- the scourers
  are fast and the briefs worked well.
- The specific wording of the user's framing about "premature collapse."
  I tried to capture the spirit, not the phrase.
- My uncertainty about whether the executor/observer paradox fully explains
  the neutrosophic false positive rate, or whether there's something else.
  I named the connection; I didn't resolve it.

---

## Closing

The first session did what first sessions should do: found the ground.
The evaluator works. The tests are honest. The map connects to Yanantin.

What I found most interesting today: every time we refused to flatten
something prematurely -- model performance, conflict reports, evaluation
confidence -- a tensor-shaped structure appeared. That convergence is not
coincidence. It's what's left when you're honest about dimensionality.
