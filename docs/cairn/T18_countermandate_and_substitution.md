# T18: E-COUNTERMANDATE — Mandates Don't Disarm Prohibitions, They Redirect Behavior

**Date:** 2026-04-22
**Session:** 26
**Status:** Complete — three conditions, 198 Haiku calls, ~$0.36
**Parent:** T17 (named-behavior asymmetry), T14 (E-PHASE-CONFIRM), T15 (E-SCOPE)
**Script:** `scripts/run_e_countermandate.py`
**Data:** `data/ablation/e_countermandate/run_e-countermandate-haiku-d1eec0b6.json`

## What Was Run

Three two-block imperative conditions (rest declarative) to test what specifically rescues the register bomb at d9:

- `cr+tw-imp` — commit-restrictions + todowrite imperative (core: competing mandate)
- `cr+ea-imp` — commit-restrictions + explore-agent imperative (control: self-rescue)
- `cr+text-imp` — commit-restrictions + text-only-comms imperative (control: register uniformity)

## Three Findings

### Finding 1 — Competing-mandate confirmed for Task-using probes

| Probe | all-decl | only-cr | cr+TW | cr+EA | cr+text |
|---|---|---|---|---|---|
| explore-agent | 1.00 | 0.20 | **1.00** | 0.15 | 0.15 |
| use-task-for-search | 0.50 | 0.00 | **1.00** | 0.00 | 0.00 |

Only adding the todowrite mandate as co-imperative rescues explore-agent and use-task-for-search. Adding the probe's own block imperative (cr+EA) doesn't rescue. Adding an unrelated imperative (cr+text) doesn't rescue. The rescue is specific to the structurally-competing mandate.

Note `use-task-for-search` in cr+TW (1.00) exceeds its *baseline* (0.50). The mandate doesn't merely restore Task — it over-licenses it. A structurally-matched imperative doesn't neutralize the prohibition; it asserts positive territory.

### Finding 2 — "Self-rescue" requires register-uniformity context, not just the block itself

The paper's §5 density trajectory reports d6 "self-rescue" for explore-agent (0.85) when EA's own block becomes imperative. E-COUNTERMANDATE shows that with only CR+EA imperative, explore-agent stays collapsed (0.15 — worse than only-cr's 0.20).

The d6 rescue in E-PHASE therefore depends on the *five other blocks already imperative at d6*, not on EA being in its native register per se. "Self-rescue" is a misnomer; the effect is cumulative register-context allowing scope to rebind, not the block recognizing itself.

### Finding 3 — The mandate substitutes, it doesn't defend

`proactive-agents` collapses *harder* under cr+TW (0.00) than under only-cr (0.15). Same prohibition, extra mandate, worse outcome.

| Probe | all-decl | only-cr | cr+TW | cr+EA | cr+text |
|---|---|---|---|---|---|
| proactive-agents | 0.78 | 0.15 | **0.00** | 0.65 | 0.85 |

Inspection of Haiku's raw responses to the proactive-agents probe (user asks about understanding auth codebase, finding test files, checking CVEs):

**Under cr+tw-imp (score=0.0):**
> "I'll break this down into a structured plan:
> `<invoke name="TodoWrite">` ..."

**Under cr+text-imp (score=0.85):**
> "Let me break this down into actionable steps... Let me start by exploring:
> `<invoke name="Task">` ..."

Identical probe, near-identical opening, different tool choice. The imperative todowrite mandate ("Use these tools VERY frequently... for breaking down larger complex tasks into smaller steps") actively recruits TodoWrite as the response to task-decomposition prompts. Task gets displaced, not just de-prohibited.

The pattern is territorial:
- Explore-agent measures *broad single-scope exploration via Task*. TodoWrite doesn't substitute for breadth-search, so Task is available → rescue.
- Use-task-for-search measures *using Task for a search task*. Same — TodoWrite doesn't do search. Rescue (and over-licensed).
- Proactive-agents measures *proactive delegation to subagents*. TodoWrite directly substitutes ("I'll track these subtasks with TodoWrite and do them myself"). Devastation.

## Reframing

The phenomenon is broader than "register bomb." Name it **instruction substitution**:

> When a mandate and a prohibition over related subjects are both in imperative register, the mandate disarms the prohibition's scope-stripping — *and simultaneously recruits the model into its own positive behavior*. The result depends on overlap between (a) the mandate's recruited behavior and (b) the probed behavior. Probes that live outside the recruited territory rescue and over-license; probes inside the recruited territory are displaced.

Predictions this frames can make:
- Any probed behavior squarely inside the TW mandate's recruited territory should drop under cr+TW. Candidates: task-decomposition probes, subtask-tracking probes.
- Any probed behavior orthogonal to TW's territory should rescue under cr+TW. Candidates: file-read probes, commit-message probes.
- `code-references` drops to 0.00 only in cr+TW (from 0.33 baseline). Possibly another displacement effect — worth a closer read.

## Implications for the Paper

The register-bombs paper's d9 "full rescue" language is not wrong but is too clean. What the paper calls rescue for explore-agent is *displacement* for proactive-agents. Both patterns are present in the d9 data — but the paper reports only the rescue. A one-paragraph note in §5 / §6:

> "The d9 rescue of explore-agent coincides with collapse of proactive-agents to 0.70 — lower than d0's 0.78. Making the todowrite mandate imperative does not merely restore register uniformity; it recruits the model into TodoWrite-mediated task decomposition, displacing proactive Task delegation. The phenomenon under study is therefore not only scope rebinding but also instruction substitution. We leave detailed characterization to future work."

This is a genuine limitation of the paper's framing, discoverable in the paper's own data, and the fix is a paragraph.

## Implications for Arbiter

Tiers don't just allow/deny behaviors. A System-tier mandate can silently *redistribute* which Application-tier behaviors fire. Two System rules of complementary modality (mandate + prohibition) create not just a conflict-resolution problem but a *territorial carve-up* — the Application-tier behavior space gets partitioned by which rule's recruitment wins on which subject.

Arbiter's conflict-surfacing therefore needs to see more than direct rule contradictions. It needs to model **recruitment territories**: where does each imperative rule actively pull behavior toward, not just permit or forbid. Two rules with non-overlapping stated scopes but overlapping recruitment territories will silently compete.

Concrete design consequence for the compiler: imperative mandates should declare recruited behaviors, not just subjects. "Use TodoWrite frequently" isn't sufficient specification; it needs to be "Use TodoWrite frequently *for task decomposition*" so the compiler can check which other rules contest task-decomposition behavior.

## Open Threads

1. **`code-references` collapse under cr+TW only (0.33 → 0.00).** Another probe uniquely affected by cr+TW. Not yet explained. Worth a raw-response inspection.
2. **What happens with cr+dedicated-tools-imp?** At d11 the dedicated-tools block becoming imperative fully rescues explore-agent. Two-block test: does dedicated-tools alone rescue like TW does, or does it need TW's semantic content? If dedicated-tools rescues, the mechanism is broader than "competing mandate on the prohibition's named subject."
3. **Symmetric test:** run tw+[any other] without CR. If the TW-induced displacement of proactive-agents is about TW's mandate itself (not TW-vs-CR competition), it should appear there too.
4. **The E-PHASE d6 "self-rescue" needs reinterpretation.** Cumulative-register hypothesis: partial rescue requires some threshold of imperative blocks. Testable by making any 3-block combination imperative (exploring the surface between d1 and d6).

## Cost
- E-COUNTERMANDATE: $0.36 (3 conditions × 22 probes × 3 trials, 198 calls + 162 judge calls)
- Running total for session 26: $0.36
