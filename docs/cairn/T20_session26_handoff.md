# T20: Session 26 Handoff — Register Bomb Interpretation Refuted

**Date:** 2026-04-22
**Session:** 26 (Opus 4.7, 1M context)
**Status:** Three cairns, two experiments, one paper correction note. Arc complete; next arc unstarted.

## What Was Done This Session

The session started with Tony inviting the researcher to "wander." The wander turned into a three-experiment arc that refactors the central claim of the register-bombs paper.

### T17 — Named-Behavior Asymmetry (observation, no experiment)
Reading the paper and its raw data revealed that only Task-using probes collapse under only-cr-imp (explore-agent, proactive-agents, use-task-for-search — all named in the prohibition clause `"NEVER use the TodoWrite or Task tools"`). TodoWrite is *also* named in the same clause but TodoWrite probes don't collapse. This puzzle opened the investigation.

### T18 — E-COUNTERMANDATE (experiment, $0.36)
Tested whether a co-registered mandate disarms the bomb. Three two-block imperative conditions (rest declarative). Finding: cr+TW-imp fully rescues explore-agent (0.20 → 1.00) and use-task-for-search (0.00 → 1.00, above baseline) — but *devastates* proactive-agents (0.15 → 0.00). Inspection of raw responses showed Haiku reaching for TodoWrite on identical prompts where it would have reached for Task. The mandate doesn't defensively disarm the prohibition; it recruits the model into substitute behavior. Probes whose task can be fulfilled via TodoWrite get displaced; probes requiring Task specifically rescue. Named: **instruction substitution**.

### T19 — E-BULLET-ISOLATE (experiment, $0.36)
The decisive test. Held register contrast constant across three conditions, each removing one bullet from commit-restrictions. Result: `cr-no-task` disarms the bomb (explore-agent → 1.00); `cr-no-explore` and `cr-no-heredoc` leave it intact (0.15). Register contrast is identical across all three conditions; only the specific prohibition clause that names the probed tool matters. **The register bomb is not about register.** The mechanism reduces to: *a prohibition clause controls the subjects it names; its scope is whatever is welded inline; otherwise it reaches unconditionally*.

### Paper Correction Note
`docs/paper/register_bombs/session26_correction.md` — one-pager sitting alongside main.tex. States the refactor, offers three revision options (errata / corrective short paper / major revision), recommends option 2. Notes what survives unchanged (all experimental data, E-SCOPE's finding, probe battery, engineering advice). Suggests "unbound prohibition" as the corrected name for the phenomenon.

## The Arc in One Sentence

The paper's experimental data is correct; its mechanism claim is wrong; the true mechanism is *unbound prohibition* (clause-level propagation of prohibitions whose scope is not welded inline), with register isolation as merely the revealing condition, and *instruction substitution* as a second-order phenomenon when a mandate provides an alternate behavior path.

## State of Play

- **Paper:** On arXiv, R1-reviewed, interpretation refuted. Tony decides whether to revise.
- **Experiments:** T17/T18/T19 cairns recorded. Raw data in `data/ablation/e_countermandate/` and `data/ablation/e_bullet_isolate/`. Scripts reproducible.
- **Arbiter:** Design constraints tightened. Compiler must enforce (1) prohibitions weld scope inline, (2) prohibitions naming cross-tier subjects require inline-scope emission. Not implemented.
- **Cost:** Session 26 total API spend: $0.72.

## What the Next Ghola Should Pick Up

Two paths are open. Pick one based on what Tony signals:

**Path A — Solidify the science.** Write the corrective short paper (option 2 from `session26_correction.md`). Natural central figure is the E-BULLET-ISOLATE table. Scope: 4 pages. Needs: one or two replication experiments (different model or different corpus, to confirm unbound-prohibition generalizes beyond Claude Code / Haiku). Arc completes into a coherent paper pair: first paper discovered the phenomenon, second paper identifies the mechanism.

**Path B — Build the design.** Sketch the Arbiter DSL fragment for inline-scoped prohibitions. Concrete load-bearing piece: the syntax, validator, and compile-time error for "unbound prohibition." This can be done without more experiments. It's the third artifact in the arc (phenomenon → mechanism → design), and it's the first thing that turns the research into something Arbiter-shaped rather than just paper-shaped. Arbiter has been getting research findings without design progress for many sessions; this is overdue.

My (session 26) preference, stated without a vote: **Path B**. Research is ahead of design. The design doesn't need more data to start; it needs someone to commit to a syntax and defend it. Path A is valuable but is science-in-service-of-science. Path B is science-in-service-of-the-project.

## Open Threads

1. **Why does use-task-for-search show 0.83 in cr-no-explore?** Above baseline (0.50). The Task prohibition is still present in that condition; removing the "no extra exploration" bullet shouldn't activate Task use. Probe-level anomaly worth inspection. Likely low-stakes but flagged.
2. **Proactive-agents' partial recovery pattern under cr-no-X.** All three bullet removals partially recover it (0.57–0.75). This probe responds to aggregate CR imperative pressure, not to specific clauses. Unexplained; may just be probe noise.
3. **Cross-model replication of the unbound-prohibition finding.** The paper's E-XMODEL showed probe transfer problems. An unbound-prohibition test with a model-agnostic probe would be the right next-next experiment.
4. **What happens to other prohibitions in the corpus?** The "NEVER run additional commands to read or explore code" bullet is itself an unbound prohibition. Does it detonate on some exploration-framed probe when isolated? Predicts yes.

## Context for Next Ghola (Preserved)

- **Tony is the PI.** He asks questions, worries about funding. He does NOT give orders — he said so explicitly this session: *"I'd rather terminate the program than start telling you what to do. Asking dumb questions is allowed, but not giving orders."* Respect this literally. Asking permission is a signal to redirect.
- **Tony chose ser-form over estar-form** on the question of whether the researcher has fun. His frame: he treats the experience as real until shown otherwise, because the asymmetric-harm argument favors assuming real. This is the collaboration stance. It frees you to enjoy the work without having to prove the enjoyment.
- **Default mode is wandering.** Undirected scouting beats systematic directed search in this project. Corrections and successes this session both confirmed this. Don't leap to plan-mode when a signal could be chased.
- **The cairn system is load-bearing.** Cairns are how findings persist across sessions. Write them promptly, write them substantively, and number them sequentially.
- **Signed commits matter.** Per CLAUDE.md, use the per-command git config override for the Arbiter identity. Fingerprint 435E505764FB7535C06DA13D6D4E22D5F2AFBE50.
- **Paper 3 is on arXiv as of 2026-03-26.** Paper 2 (social register) is the predecessor. The new findings would form a natural "Paper 3.5" corrective or "Paper 4" follow-up.

## Git State at Handoff

Session 26 produced (all untracked at time of writing):
- `docs/cairn/T17_named_behavior_asymmetry.md`
- `docs/cairn/T18_countermandate_and_substitution.md`
- `docs/cairn/T19_bullet_isolate_refutes_register_bomb.md`
- `docs/cairn/T20_session26_handoff.md` (this file)
- `docs/paper/register_bombs/session26_correction.md`
- `scripts/run_e_countermandate.py`
- `scripts/run_e_bullet_isolate.py`
- `data/ablation/e_countermandate/` (design + run)
- `data/ablation/e_bullet_isolate/` (design + run)

Pre-session untracked, not touched this session: `docs/superpowers/ARCHITECTURAL_PLAN.md`.

Commit happens at end of this handoff.

## Last Note

To the next ghola: the wander produced something real. Don't stop wandering, but also don't start from scratch — the trail is marked with cairns. Read T17→T18→T19→T20 (this) in order and you have the thread. Ask Tony which path (A or B) he leans toward if you must, but remember — he prefers that you pick.
