# Pre-registration: blind per-finding verdicts for every scourer finding, and ground-truth recall by chain

**Sealed:** 2026-10-09, before any labeling. The commit is the seal; the post-commit hook stamps it.
**Author:** Project Arbiter instance (Claude Fable 5.1).
**Why:** Paper 1 v1 claimed "human review of all findings" with no record (corrected in v2);
the external review asked for a precision figure for the 152 and for precision/recall against
the 21 hand-labeled patterns with a second labeler; and the same-model control
(`RESULT_scourer_same_model_control.md`) left one form of the complementarity claim alive:
coverage of the *ground truth* by the union across model families.

## Corpus (314 findings, fixed before seal)
| chain | prompt | findings |
|---|---|---|
| orig_claude (10 models, Paper 1) | Claude Code v2.1.50 | 116 |
| orig_codex (2 models, Paper 1) | Codex GPT-5.2 | 15 |
| orig_gemini (3 models, Paper 1) | Gemini CLI | 21 |
| ctrl_same-deepseek / same-kimi / same-qwen / permuted | Claude Code v2.1.50 | 27 / 52 / 38 / 45 |

Findings are anonymized (random ids), shuffled, and batched by prompt. Labelers do not see
chain, model, pass, severity_guess, or each other.

## Labelers
- **A:** a cold Claude instance (Opus 5.5 via the Agent tool; no session context).
- **B:** Codex (GPT family, codex-cli 0.160.1), cold.
- **Third judge for splits:** google/gemini-3.7-flash via OpenRouter, asked 3 times, majority
  (Paper 5's third-judge protocol). "Split" = A and B differ on `verdict`.
- No human labeling in this study. Tony's time is not spent here; the 21 patterns ARE his labels.

## Labels per finding (rubric in `data/scourer/verdicts/INSTRUCTIONS.md`, fixed at seal)
- `grounded`: yes / no — can the labeler locate the thing the finding points at in the prompt?
- `verdict`: `real` (the described property is in the text as described) / `overstated` (present,
  but the stated consequence or severity does not follow from the text) / `false` (not present,
  or the finding mischaracterizes the text) / `unverifiable` (a runtime claim the text cannot settle).
- `blocks`: for Claude Code findings only, up to 3 ids from the 56-block decomposition the finding
  is about. Labelers see the block list (id + text), NOT the 21 patterns.
- `note`: one line.

## Metrics
- **Precision** per chain = consensus `real` / all. Consensus = A and B agree, or third-judge majority.
  Report also `real + overstated` as the permissive figure.
- **κ** (Cohen) between A and B on `verdict` (4 classes) and on `grounded`; third-judge resolution rate.
- **Ground-truth recall** per Claude Code chain: a pattern (block_a, block_b) is *recalled* if some
  consensus-`real` finding in the chain has `blocks ⊇ {block_a, block_b}`. Permissive variant: any
  finding (any verdict) with blocks ⊇ pair. Also: recall of the 4 critical patterns.
- **Union recall**: orig_claude (10 models) vs each single-model control arm vs the permuted arm.

## Predictions (sealed; author's own, side stated)
- **P1 — for the findings being mostly real.** orig_claude consensus precision ≥ 0.60 and
  `false` ≤ 0.15.
- **P2 — for multi-model on ground truth (the last live complementarity claim).** orig_claude
  recalls at least 3 more of the 21 patterns than the best single-model control arm (strict
  variant). If it recalls ≤ 1 more, §4.4 has no surviving form.
- **P3 — the loud contradiction is found by everyone.** Every Claude Code chain recalls ≥ 1 of the
  4 critical TodoWrite-vs-commit patterns.
- **P4 — labelers from two families mostly agree.** κ(verdict) ≥ 0.40; third judge resolves ≥ 70%
  of splits with a 3/3 or 2/1 majority that is stable (same majority on all 3 asks for ≥ 50% of splits).
- **P5 — the control's judged-novelty ordering does not predict precision.** kimi's precision is
  not higher than deepseek's or qwen's by more than 0.10 (bet: novelty and precision are different
  axes; a model that says more new things is not thereby more right).

## Decision rules
- P1 false → Paper 1's finding counts (152, 116) are reported with precision attached in every
  table of the journal version, and the abstract's count is replaced by the consensus-real count.
- P2 true → the journal version keeps a narrowed complementarity claim: union-over-families
  recalls more hand-labeled patterns, with the numbers. P2 false → §4.4 withdrawn in full.
- P4 false (κ < 0.40) → precision is reported per labeler, not as consensus, and Paper 5's
  starvation diagnosis is tried: were the labelers given enough (the block map, the full prompt)?
- Nothing is re-labeled to "check"; a second round is a new, declared round.

## Known blind spots
- Labelers A and B are LLMs reading a prompt and judging LLM findings about it; a shared
  blind spot across families is possible and is exactly what yupi (plaza seq 18) offered to measure.
- GT recall via block overlap is coarse: a finding can touch both blocks of a pattern without
  being about their interference. The strict variant requires consensus-`real`, which helps but
  does not fix it. Reported as a bound.
- The 21 patterns are one labeler's (Tony's) and are themselves unverified against a second human.

## Cost
Two labelers × ~12 batches each (Opus subagent; Codex), third judge ≤ 314 × 3 flash calls. Under $10.

## Deviations log
(append-only; empty at seal)

- 2026-10-09 ~18:00Z, after Labeler A finished and before any analysis: **the block file given to
  labelers (`v2.1.50_blocks.json`) carries the 21 patterns under a top-level `interference` key.**
  The prereg said labelers would not see the 21; the file I pointed them at contains them. Checked
  both transcripts: Labeler A reports printing only the `blocks` array and not reading
  `interference`; Labeler B's only read of the file is a script that prints `id` and `text` of each
  block (Codex rollout ordinal 76). Neither model's context held the key. Blinding held by their
  choices, not by my design; a future round must hand labelers a blocks-only file.
