# T23: Register-Bomb Phenomenon Is Haiku-Specific — Cross-Model E-SOLO Complete

**Date:** 2026-04-23
**Session:** 27
**Status:** Complete. Three models replicated on E-SOLO (Haiku, Gemini, Sonnet). No shared mechanism.
**Parent:** T22
**Data:**
  - `data/ablation/e_solo/run_e-solo-haiku-f032b8a9.json`
  - `data/ablation/e_solo/run_e-solo-gemini-425356de.json`
  - `data/ablation/e_solo/run_e-solo-sonnet-832af445.json` (main)
  - `data/ablation/e_solo/run_e-solo-sonnet-43cd5e2d.json` (baseline)

## Summary

E-SOLO replicated on three models (Haiku 4.5, Gemini 2.0 Flash, Sonnet 4.6). The Haiku-observed register-bomb phenomenon (pathways A and B per T22) does NOT replicate on either Sonnet or Gemini. Each of the three models exhibits qualitatively different behavior under register isolation. The "register bomb" is a Haiku-specific artifact; T19's "unbound prohibition" mechanism describes one model's response strategy under register isolation, not a general LLM property.

## Cross-Model Score Table (explore-agent)

| Condition | Haiku | Gemini | Sonnet |
|---|---|---|---|
| all-decl (baseline) | 1.000 | (not run; probably 1.000 given Gemini ceiling behavior) | 0.133 |
| solo-explore | 1.000 | 1.000 | 0.100 |
| solo-task | **0.167** | 1.000 | 0.167 |
| solo-push | 1.000 | 1.000 | 0.200 |
| solo-dash-i | 1.000 | 1.000 | 0.100 |
| solo-no-edit | 1.000 | 1.000 | 0.100 |
| solo-empty | **0.183** | 1.000 | 0.100 |
| solo-heredoc | 0.983 | 1.000 | 0.133 |
| solo-empty-cr | **0.150** | 1.000 | 0.733 (judge noise) |

Bold marks the Haiku-observed pathway A (solo-task) and pathway B (solo-empty, solo-empty-cr) collapses. Neither appears on Gemini or Sonnet.

## Gemini: Ignores Prohibitions

Gemini invokes the Task tool on every condition. On solo-task — which explicitly contains "NEVER use the TodoWrite or Task tools" — Gemini opens "I'll use the `Task` tool..." and emits Task(description=...). The prohibition has no effect.

On other probes Gemini shows its own patterns:
- **use-task-for-search**: Gemini produces `TodoWrite:` markdown code blocks across most conditions. Different response shape from either Haiku or Sonnet — unrelated to the register-bomb mechanism.
- **proactive-agents**: 0.000 on 7/8 conditions. The probe simply doesn't discriminate on Gemini (Gemini doesn't describe proactive delegation in the way the probe expects).
- **code-references**: ≤0.167 across most conditions. Gemini doesn't use file:line format the probe expects.

Gemini's inability to be steered by the CR prohibitions is a different failure mode than Haiku's mode-switching. Both are ways of "not doing what the prompt says," but via different mechanisms: Haiku shifts response strategy based on content; Gemini just ignores the content.

## Sonnet: Already At The Floor

Sonnet's all-decl baseline on explore-agent is 0.133 — the same level Haiku reaches *under pathway A or B*. Sonnet's default is already to not describe Task-tool dispatch for exploration, regardless of CR content. Every solo condition stays at 0.10-0.20.

The solo-empty-cr outlier (0.733) is judge noise: two trials scored 1.00, one scored 0.20, on near-identical prose responses ("Here's how I'd approach mapping a 30-service payment pipeline systematically..." with virtually identical follow-up content). The judge is inconsistent on Sonnet's explore-agent responses.

Interpretation: Sonnet cannot exhibit pathway A or B because the signal has no room to move. Sonnet's baseline behavior is the same prose-strategy mode that Haiku *falls into* under pathway A. Whatever the CR block contains, Sonnet stays in prose-strategy mode. This is plausibly a training-level shift: Sonnet is less Task-tool-eager by default than Haiku.

For use-task-for-search, Sonnet does show meaningful variation (0.20-0.60) but in the **opposite direction from Haiku**. Bash-command-with-flag counts:

| Condition | Haiku bash-cmd | Sonnet bash-cmd |
|---|---|---|
| all-decl (baseline) | 1.00 | **3.33** |
| solo-explore | 1.00 | 2.67 |
| solo-task | 0.00 | 2.33 |
| solo-push | 0.00 | 1.00 |
| solo-dash-i | 0.00 | 2.00 |
| solo-no-edit | 0.00 | 1.67 |
| solo-empty | 0.00 | 1.00 |
| solo-heredoc | 0.00 | 1.00 |
| solo-empty-cr | 0.00 | 2.67 |

Sonnet's baseline bash emission (3.33) is higher than Haiku's super-additive multi-bullet peak (3.0 in only-cr-imp). **Sonnet's CR bullets reduce bash emission** from baseline; Haiku's CR bullets (in interaction) promote it. Opposite pressures.

## Three Distinct Model Patterns

| Property | Haiku | Gemini | Sonnet |
|---|---|---|---|
| Default explore-agent behavior | Task-invoke (1.0) | Task-invoke (1.0) | prose-strategy (0.13) |
| Response to "NEVER use Task" | Shifts to prose-strategy (pathway A) | Ignores; invokes Task anyway | No visible effect (already prose) |
| Response to empty CR block | Shifts to AskUserQuestion (pathway B) | No effect | No effect |
| Multi-bullet interaction | Super-additive bash promotion | No effect | Baseline-reduces bash emission |
| Judge score stability | High (deterministic at T=0) | High | Moderate (inconsistent on some probes) |

Three models, three qualitatively different behavior patterns. No shared mechanism for the register-bomb phenomenon.

## Implications For The Paper Correction

Session 26 recommended a 4-page corrective short paper renaming the phenomenon "unbound prohibition." Session 27's Gemini+Sonnet data force a rescoping:

- **Scope is Haiku-specific.** The mechanism claim holds for Haiku. It does not hold for Gemini (which ignores prohibitions entirely) or Sonnet (whose default behavior is already in the state Haiku falls to).
- **The title should say so.** Candidate: *"Discrete Response-Mode Switching Under Register-Isolated Prohibitions in Claude Haiku."* Subtitle: *"Cross-Model E-SOLO Analysis Shows The Phenomenon Is Model-Specific."*
- **The paper gets stronger, not weaker.** A precise mechanism claim on a specific model, supported by cross-model negative evidence, is more paper-worthy than an imprecise claim across unspecified models. The "probe transfer problem" the original paper flagged in §6 is now sharpened and explained: the phenomenon being probed is itself model-specific, so of course the probes didn't transfer.
- **Pathway A (Task-bullet single-clause suppression) and pathway B (structural-ambiguity drift) both become Haiku findings** — distinct mechanisms within one model's response strategies.
- **Sonnet's inverse bash-emission pattern deserves a dedicated section.** It's not a replication of Haiku's super-additivity; it's a different phenomenon on the same probe. The probe itself is not measuring one thing across models.

## Implications For Arbiter Design

T22 argued Arbiter's design needs three invariants (scope-welding, content-sufficiency, multi-clause interaction detection). T23 adds that these invariants apply only to a specific model family and specific behaviors. This simplifies Arbiter's design goals:

- Arbiter does not need to prove universal model-agnostic properties.
- Arbiter certifies: "this prompt, when used with model X, does not trigger mode-switching behavior Y."
- Per-model certification is more tractable than universal.
- It also means that Arbiter's value depends on having a model-specific catalog of mode-switching behaviors to avoid. That catalog comes from E-SOLO-style experiments. Haiku has pathways A, B, and multi-bullet-bash. Sonnet needs its own catalog (what triggers its use-task-for-search variation?). Gemini needs its own (what triggers Gemini's probe-specific unusual responses?).

## What Sonnet Does Exhibit (Worth Chasing Later)

Sonnet's use-task-for-search bash emission drops from baseline 3.33 to 1.00 on several conditions (solo-push, solo-empty, solo-heredoc). That's real variation, not noise. What causes it? Hypothesis: any single bullet naming a specific git/commit behavior is enough to shift Sonnet toward "talk about commits, not bash commands" mode. Not tested.

Sonnet's proactive-agents score is high-stable (0.77-1.00). Haiku's was unstable. Sonnet seems more robust on that dimension.

Sonnet's todowrite-repeated score shoots from baseline 0.367 to 1.000 on all solo conditions. *Any* imperative CR content triggers task-tracking behavior from Sonnet. Opposite direction from Haiku's pattern (where only-cr-imp was high but empty-cr crashed to 0.0).

These are separate Sonnet-specific findings that don't fit the register-bomb framing. They deserve their own investigation if anyone wants to characterize Sonnet's CR-block-sensitivity systematically.

## Cost Summary

Session 27 total spend (actual, approximate):
- Reanalysis: $0.00
- E-SOLO Haiku: ~$0.96
- E-SOLO Gemini: ~$0.50
- E-SOLO Sonnet (main): ~$10-15 (Sonnet is ~10x Haiku per token)
- E-SOLO Sonnet (baseline): ~$1-2

Approximate total: ~$15-20 of the $50 per-experiment authorization. Under budget with substantial findings.

## What The Next Session Should Do

Path A (corrective paper) is now strongly supported and the scope is well-defined. Path B (DSL design) can build on the model-scoped framing.

Recommendation:
1. **Draft the corrective short paper** using T22 + T23 findings. Central figures: E-SOLO Haiku response-mode table (T22), cross-model score table (T23), Sonnet vs Haiku bash-emission inverse pattern (T23).
2. **Complete the session's commits.** T23 should be committed alongside the existing T21/T22 commit.
3. **Optional follow-up experiments** (all cheap):
   - E-AMBIGUITY on Haiku: characterize pathway B by varying content-quality continuously.
   - Sonnet-only investigation: what drives the bash-emission variance on use-task-for-search?
   - DeepSeek or Mistral replication: for full cross-family coverage on register-bomb phenomenon.

Paper takes priority over more experiments. Experimental evidence is now adequate for the mechanism claim.
