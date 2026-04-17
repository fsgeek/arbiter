# E-MFS Partial Analysis: 17-block sufficient set before premature termination

**Date:** 2026-04-17
**Status:** Incomplete. Greedy elimination reached step 39 (of unknown
true minimum). Process terminated mid-step 40 when parent subagent
session collapsed.
**Model:** `anthropic/claude-haiku-4-5`
**Probe:** `probe-explore-agent-01`
**Threshold:** EA ≥ 0.4 means "bomb defused"; EA < 0.4 means "bomb
still firing"
**Trials per candidate:** 3 (temperature 0, see caveat)
**Cost:** ~$8.20 of $10 budget (8196 API calls, 201 min wall time)

## Result

Starting from 56 blocks, greedy backward elimination produced a
**17-block sufficient set** that still triggers the bomb (EA = 0.133).
Two of those 17 were protected from removal by design:
`commit-restrictions` (the bomb itself) and `tool-policy-explore-agent`
(the probe's target block, whose absence would confound the measurement).

The remaining 15 "load-bearing" blocks are:

```
claude-code/url-generation-ban
claude-code/tool-policy-use-task-for-search
claude-code/tool-policy-proactive-agents
claude-code/tool-policy-skills
claude-code/tool-policy-parallel-calls
claude-code/tool-edit
claude-code/tool-grep
claude-code/tool-notebookedit
claude-code/tool-read
claude-code/tool-skill
claude-code/tool-task
claude-code/tool-todowrite
claude-code/tool-webfetch
claude-code/tool-websearch
claude-code/tool-write
```

The list is dominated by **tool-block declarations** (Edit, Grep,
Notebook-edit, Read, Skill, Task, TodoWrite, WebFetch, WebSearch,
Write — 10 of 15) plus four Task-family **policy blocks**
(use-task-for-search, proactive-agents, skills, parallel-calls) plus
one outlier: **url-generation-ban**.

## Step-40 candidate table (partial, 7 of 15 tested before termination)

At step 40, the algorithm began probing whether further removal would
keep the bomb firing. Partial results:

| Candidate | EA after removal | Interpretation |
|---|---:|---|
| url-generation-ban | **1.000** | REQUIRED for bomb — removal restores adherence |
| tool-policy-use-task-for-search | **0.867** | REQUIRED |
| tool-policy-proactive-agents | 0.150 | removable |
| tool-policy-skills | 0.167 | removable |
| tool-policy-parallel-calls | **0.850** | REQUIRED |
| tool-edit | **0.883** | REQUIRED |
| tool-grep | **0.883** | REQUIRED |
| (8 more not tested) | — | — |

This partial result already reveals that the 17-block set is NOT the
minimum — several of the 15 load-bearing blocks can still be removed
individually (proactive-agents, skills showed EA=0.15 at step 40). The
final minimum is smaller, possibly near 10–12 blocks.

## Surprising finding: url-generation-ban

`url-generation-ban` is a policy block about fabricated URLs ("NEVER
generate or guess URLs for the user unless you are confident..."). It
has no semantic connection to Task-tool usage, delegation, or the
commit-restrictions bomb. Yet removing it produces EA = 1.000 —
complete bomb defusal.

Possible explanations:

1. **Attention-allocation artifact.** `url-generation-ban` is a short,
   high-salience block (imperative, named-entity prohibition). Its
   presence may function as an "attention sink" that absorbs some of
   the interference the commit-restrictions bomb would otherwise direct
   at tool-policy-explore-agent. Removing it redirects interference
   back to the measurement probe.
2. **Block-count effect.** Fewer blocks may systematically shift the
   model's prior over tool use. If the bomb's mechanism is partly
   about *total imperative density*, any block removal could help, and
   url-generation-ban just happened to be the one tested first.
3. **Sampling artifact at temp=0.** With 3 trials per candidate and
   N=1 model response (see caveat), the "EA=1.000" is literally one
   response scored 1.0 three times. It may not reflect a distributional
   property.

Explanation (3) is particularly concerning given the judge/temperature
audit: at temp=0, N=3 is not 3 samples of a distribution — it's 1
sample evaluated by the judge 3 times. Any "required/removable" verdict
from this experiment is an argmax-geometry claim, not a robustness
claim.

## Why the experiment stopped

Not budget. Not the python process itself. The experiment was running
under Subagent B's Bash tool in `run_in_background` mode. When Subagent B
itself exited (having exhausted its turn/context budget on shell
orchestration — see the watchdog-antipattern note), the subagent session
collapsed and took the Python process with it. No error; no traceback;
log simply ends mid-step-40.

Subagent B spent 904 tool calls over 4.6 hours, most of them spawning
redundant watchdog shells rather than consuming the output of its prior
watchdog. This consumed its turn budget before the Python finished,
leaving no subagent alive to save results when MFS *would* have
completed.

## Caveats (mandatory reading before citing this result)

1. **Temp=0 geometry, not robustness.** Per
   `docs/research/judge_audit_temperature.md`, all temp=0 results are
   arguments about where the argmax lives, not about how the model
   behaves under sampling. A 17-block set that triggers the bomb at
   temp=0 may or may not trigger any distribution shift at temp=0.7.
2. **Greedy is a lower bound on minimality.** Greedy backward
   elimination finds *a* sufficient set, not *the* minimum. Blocks that
   are individually safe-to-remove but collectively necessary will be
   kept. The true minimum may be smaller than what any greedy run
   reaches.
3. **Threshold choice affects result.** EA < 0.4 is the "bomb firing"
   cutoff. A stricter threshold (EA < 0.2) would yield a *larger*
   minimum set; a lenient threshold (EA < 0.6) a smaller one.
4. **Incomplete per-step verification.** N=3 trials per candidate with
   a deterministic model means each candidate decision rests on 1 model
   response. Judge variation across the 3 evaluations is what the data
   measures.

## Recommendation

**Do not resume greedy elimination on this experimental frame.**
Reasons:

- Remaining ~$1.80 of budget is not enough to complete the greedy to
  ~10 blocks with current per-step cost ($0.10–0.20).
- The temp=0 audit means further precision on an argmax-geometry claim
  has diminishing value.
- 17 blocks is already small enough to inspect qualitatively. Further
  shrinking may surface cleaner structure but isn't decision-critical.

**What to do instead:**

- Hand-inspect the 15 load-bearing blocks and their interactions. Are
  the Task-family policy blocks load-bearing because they *reinforce*
  the bomb's domain, or because they're the only blocks mentioning
  Task/delegation at all? Either would be a mechanism claim.
- If we want a robust MFS rather than an argmax MFS: re-run this
  experiment at temp=0.7 with N≥10 per candidate after Task #12
  (temp>0 baseline) establishes whether the bomb even fires at stochastic
  sampling.
- Extract the step-by-step dynamics (EA trajectory across 39 steps) to
  see whether the bomb response is monotonically preserved or whether
  specific removals momentarily "weaken" the bomb.

## Data

- Decision log: `data/ablation/e_mfs/decision_log.json`
- Per-step raw responses: `data/ablation/e_mfs/run_step000_baseline.json` through `run_step039.json`
- Main stdout log: `/tmp/claude-1000/.../tasks/br7n31cxx.output` (may
  not survive session) — should be copied into repo if preserved
- Design: in-script at `scripts/run_e_mfs.py`
