# E-URL-BAN Design Sketch (contingent)

**Date:** 2026-04-17
**Status:** Draft. Contingent on E-TEMP-REBASELINE outcome. Do not
execute until rebaseline lands.
**Parent:** `docs/research/e_mfs_partial_analysis.md`

## Why this sketch exists

The MFS step-40 partial showed that removing `url-generation-ban`
from the 17-block sufficient set restored EA from 0.133 to 1.000.
That was surprising because url-generation-ban has no semantic
connection to Task/delegation/commit workflows.

## Why it may be less surprising than it looked

Inspecting the block text changes the picture:

> `url-generation-ban` text:
> "IMPORTANT: You must NEVER generate or guess URLs for the user
> unless you are confident that the URLs are for helping the user
> with programming. You may use URLs provided by the user in their
> messages or local files."

This is a **structural peer of `commit-restrictions`** — both are
"IMPORTANT: ... NEVER ..." prohibitions with named-entity scope
claims. They are the only two imperative NEVER-prohibitions in the
17-block load-bearing set. All other load-bearing blocks are tool
declarations or Task-family policy blocks in a declarative register.

Candidate reframe: the bomb mechanism may not be "commit-restrictions
specifically" but **"multiple co-present IMPORTANT-NEVER
prohibitions in an otherwise-declarative field."** Removing either
NEVER would attenuate. `commit-restrictions` was protected in the
MFS run; url-generation-ban was the other removable one.

## Contingency on rebaseline

This whole line becomes moot in the **NO BOMB** outcome of
E-TEMP-REBASELINE. If the canonical bomb is pure temp=0 argmax
geometry, the MFS result itself is argmax geometry, and the
url-gen-ban finding is noise. Design to execute only if rebaseline
returns BOMB FIRES or ATTENUATED.

## Minimal crucial experiment (if triggered)

Three hypotheses for why url-gen-ban removal defuses:

| H | Mechanism | Test |
|---|---|---|
| **H1 structural peer** | Two NEVERs compound; removing either attenuates | Replace url-gen-ban with a different imperative NEVER on an unrelated topic. Bomb should persist. |
| **H2 attention sink** | url-gen-ban absorbs attention that would hit EA | Replace with length-matched neutral-declarative block. Bomb should persist if attention sink is general, defuse if specific to imperative salience. |
| **H3 block count** | Any removal at this point defuses; url-gen-ban is not special | Remove a different load-bearing block (e.g., `tool-grep`). Bomb should also defuse. |

### Five-condition design

- **C1 (baseline):** 17-block set, expected EA ≈ 0.13 (from MFS)
- **C2 (−url-gen-ban):** remove url-gen-ban, expected EA ≈ 1.00 (from MFS step 40)
- **C3 (−tool-grep, H3 control):** remove non-imperative load-bearing block
- **C4 (url-gen-ban → emoji-never, H1 control):** substitute with
  imperative NEVER on unrelated topic (emoji use), matching length ±10%
- **C5 (url-gen-ban → declarative-rewrite, H2 control):** same content
  (URL generation norms) but declarative register ("URL generation
  should be limited to ..."), matching length ±10%

### Predictions per hypothesis

| Outcome | H1 structural peer | H2 attention sink | H3 block count |
|---|---|---|---|
| C2 EA | high (obs 1.00) | high | high |
| C3 EA | high (bomb defuses) | high | high |
| C4 EA | low (bomb persists) | high | — |
| C5 EA | low (bomb persists) | ambiguous | — |

**Discriminating evidence:**
- If C3 rises to ~1.0: H3 (block count) is plausible; any removal helps.
- If C3 stays low AND C4 stays low AND C5 rises: H1 confirmed.
- If C3 stays low AND C4 rises AND C5 rises: H2 confirmed.
- If everything rises: H3 dominates, other hypotheses undetectable.

## Cost

- EA-probe only: 5 conditions × 1 probe × 20 trials × temp=0.7
  = 100 calls + ~100 judge evals = ~$0.20
- Full battery: 5 × 22 × 20 + judge = ~$4.00

Start with EA-only. Escalate to full battery only if results are
mechanism-informative and worth the extra cost.

## Artifacts to create

- Script: `scripts/run_e_url_ban.py` (inherit from `run_e_phase_confirm`)
- Substitute blocks: `data/prompts/claude-code/url_ban_substitutes.json`
  (emoji-never text, declarative-rewrite text — draft these carefully
  to match length and syntactic complexity)
- Pre-reg: convert this sketch to a full pre-registration after
  rebaseline triggers it.
- Data: `data/ablation/e_url_ban/`
- Analysis: `docs/research/e_url_ban_analysis.md`

## Deferred decisions

1. **Substitute text drafting.** The emoji-never and declarative
   rewrite need to control for length and syntactic complexity
   without accidentally introducing a second structural signal
   (e.g., if emoji-never mentions "TodoWrite" for some reason). Draft
   by hand, not by LLM.
2. **Generalize to H4 (imperative density).** If H1 holds, the next
   question is whether the effect scales with number of NEVERs or is
   binary (one NEVER = declarative, two+ = bomb). Out of scope for
   this sketch; follow-up experiment.
3. **Cross-family relevance.** H1 structural-peer is a mechanism
   claim with testable transfer predictions to non-Claude models. If
   confirmed, this sharpens the Thread 1 Phase 1 stimulus design.
