# Prompt Drift: v2.1.50 → v2.1.71

**Date:** 2026-04-17
**Data:**
- LHS: `data/prompts/claude-code/v2.1.50_blocks.json` (56 AST-parsed blocks)
- RHS: `data/prompts/claude-code/latest_prompt.md` (raw v2.1.71 capture, 2026-03-09)
**Method:** Per-block phrase-match probe — extract up to 5 multi-word phrases
(≥5 words each) from each v2.1.50 block, normalize whitespace/case, substring-test
against v2.1.71. All phrases match → `preserved`; some → `modified`; none →
`removed`. (See inline script; the earlier single-token heuristic false-positived
on generic words like `IMPORTANT` and `HEREDOC`.)

## Summary

| Category   | Count | % of v2.1.50 |
|------------|------:|-------------:|
| Preserved  | 12    | 21%          |
| Modified   | 4     | 7%           |
| Removed    | 40    | 71%          |

Size: v2.1.50 = 16,080 chars; v2.1.71 = 16,165 chars. Net +85 chars. The
prompt is nearly identical in length but **71% of v2.1.50's content was
replaced**. This is a restructuring, not an accumulation.

## Removals by cluster

### Tool declarations → API `tools` parameter (15 blocks)

All per-tool description blocks are gone from the system prompt:

```
tool-askuserquestion  tool-bash-general  tool-edit  tool-enterplanmode
tool-exitplanmode     tool-glob         tool-grep  tool-notebookedit
tool-read             tool-skill        tool-task  tool-todowrite
tool-webfetch         tool-websearch    tool-write
```

This matches the observation in commit `bed737b` ("v2.1.50→v2.1.71: flat blob
→ sectioned document, tool definitions extracted to API tools parameter").
Tool schemas now flow through the API's `tools` field, not the prompt text.

### Workflow blocks containing imperative prohibitions (4)

```
tool-bash-commit-restrictions  ← the canonical bomb
tool-bash-commit-workflow      ← multi-step commit procedure
tool-bash-git-safety           ← "NEVER update git config" etc.
tool-bash-pr-workflow          ← PR creation procedure
```

The bomb block's distinctive strings ("NEVER use the TodoWrite or Task
tools", "Important notes", the verbatim HEREDOC instructions) are entirely
absent from v2.1.71. Verified via grep.

### Task-tool policy cluster (7 blocks)

```
task-management-todowrite       doing-tasks-plan-with-todo
task-management-examples        tool-policy-use-task-for-search
tool-policy-proactive-agents    tool-policy-dedicated-tools
todowrite-importance-repeated
```

These are the blocks implicated in the revised register-bomb mechanism
(Task-tool suppression via over-generalized imperative norm). All gone.

### Tone / behavioral constraints (6)

```
tone-text-only-comms    tone-no-new-files        professional-objectivity
no-time-estimates       doing-tasks-no-compat-hacks    code-references
```

Some of these reappear in rewritten form inside the new "Doing tasks" section
(e.g., the no-compat-hacks guidance has a paraphrased equivalent). They did
not survive verbatim.

### Context / meta (8)

```
system-reminder-tags    unlimited-context        asking-questions
environment-info        model-identity           model-background
skill-list-system-reminder    date-context-system-reminder
```

The application-layer blocks (`environment-info`, date reminders) are
ephemeral per-session content and are expected to differ run-to-run.

## What was preserved verbatim

| Block id | Tier | Category |
|---|---|---|
| security-policy | system | policy |
| url-generation-ban | system | policy |
| doing-tasks-security | system | policy |
| security-policy-repeated | system | policy |
| tone-emoji | system | behavioral-constraint |
| tone-no-colon-before-tools | system | behavioral-constraint |
| doing-tasks-no-overengineering | system | behavioral-constraint |
| tool-policy-skills | domain | meta |
| tool-policy-parallel-calls | system | behavioral-constraint |
| help-feedback | domain | context |
| hooks-info | domain | context |
| fast-mode-info | domain | context |

Four of the twelve preserved blocks are **policy**-category. Three are
terse behavioral norms. Three are reference/context blocks.

## Research implications

### 1. Independent confirmation of the mechanism claim

The Task-tool policy cluster and `commit-restrictions` were removed together.
Our revised mechanism claim — that the bomb over-generalizes a Task-tool
suppression norm from the commit-restrictions block across the broader
Task-family — predicts that either *defusing the bomb* or *restructuring the
policy cluster* would neutralize the failure mode. Anthropic did both.

This is stronger convergent evidence than either change alone would be:
fixing only the bomb would leave the Task-policy cluster as a potential
future bomb substrate; fixing only the cluster would leave the
commit-restrictions block as a trigger for future bombs. Doing both matches
the shape of a root-cause fix, not a spot patch.

### 2. Structural peer hypothesis (E-URL-BAN) reframed

The MFS partial surprise was that removing `url-generation-ban` from the
17-block sufficient set restored EA to 1.000. `e_url_ban_sketch.md`
proposed that url-gen-ban and commit-restrictions are **structural peers**
— both are "IMPORTANT: ... NEVER ..." prohibitions with named-entity
scope.

v2.1.71 removed commit-restrictions and **preserved url-gen-ban verbatim**.
If the structural-peer hypothesis (H1) were correct, the lone remaining
IMPORTANT-NEVER block should now be detectable on its own. Two relevant
observations:

- There is no concentrated bomb behavior observed in v2.1.71 (circumstantial,
  from user reports and our own use, not a controlled experiment).
- At temp=0.7 on v2.1.50 the bomb is **undetectable** (E-TEMP-REBASELINE,
  NO BOMB verdict, 2026-04-17).

Both are consistent with "single IMPORTANT-NEVER is insufficient; the
failure mode requires both co-present **and** argmax decoding." That is a
sharper, more testable claim than the original bomb framing.

### 3. The `commit-restrictions` findings are now historical

Per the E-TEMP-REBASELINE analysis, our effect-size claims are
temp=0-conditional. Now they are also **version-conditional**: the bomb
block no longer ships.

This re-scopes the research contribution:

> Characterization of a register-bomb failure mode in a specific historical
> Claude Code prompt (v2.1.50, shipped Feb 2026) under argmax decoding,
> whose upstream replacement (v2.1.71, shipped Mar 2026) matches the
> declarative-wrapper mechanism our +seq analysis identified as defusing
> the failure.

Smaller claim, cleaner contribution. The mechanism analysis remains valid
and is now validated by independent upstream action.

## What this analysis cannot say

- **Whether v2.1.71 contains new bombs.** The removal of a known bomb is
  not evidence that no bombs exist. A fresh MFS against v2.1.71 would be
  its own research project.
- **What prompted the Anthropic change.** Convergence with our mechanism
  claim is suggestive, not causal. Internal Anthropic signals (user
  reports, eval regressions, capacity pressures) likely drive prompt
  changes and are not visible to us.
- **Whether thinking-mode changes or UI-hidden thinking (per recent public
  discussion) are part of the same restructuring effort.** Those are
  runtime / UI changes, not prompt changes. Related but distinct.

## Related artifacts

- `docs/research/e_temp_rebaseline_analysis.md` — NO BOMB at temp=0.7
- `docs/research/e_url_ban_sketch.md` — structural-peer hypothesis (H1)
- `memory/project_register_bomb_mechanism.md` — revised mechanism claim
- `data/prompts/claude-code/v50_v71_diff.json` — full per-block diff output

## Next steps

1. **Pull v2.1.113** if a proxy-capture path becomes available. (Per
   Tony's note: "the more resilient way is to use a proxy.") Bun-compiled
   binary is not strings-extractable.
2. **Hold Thread 1 Phase 1 re-scope** until the "argmax-geometry transfer"
   framing is fully articulated in a pre-reg.
3. **Consider** whether the longitudinal drift itself is publishable — the
   restructuring pattern (imperatives → declarative wrappers; tool specs
   → API tools param) could be characterized across more versions if
   v2.1.71 and v2.1.113 captures accumulate.
