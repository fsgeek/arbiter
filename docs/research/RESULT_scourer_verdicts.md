# RESULT: blind per-finding verdicts on all 314 scourer findings — Paper 1's findings are 31% real, and ten models recall no more ground truth than one

**Run:** 2026-10-09. **Prereg:** `prereg_scourer_verdicts.md` (sealed 261d3b3, stamped e902ad5; one
deviation logged mid-run, abaac42). **Data:** `data/scourer/verdicts/` — `labels_A.json` (cold Claude
Opus 5.5), `labels_B.json` (Codex, GPT family, codex-cli 0.160.1), `third_judge_raw.jsonl`
(google/gemini-3.7-flash ×3 on every split), `analysis.json`, `key.json`, batches, instructions.
**Analysis:** `scripts/analyze_verdicts.py`. **Cost:** labelers ran on subscription/plugin runtimes
(not metered here); third judge 345 flash calls (~$3 by list price; not reconciled).

## Agreement (P4 — WON)
| | value | sealed threshold |
|---|---|---|
| κ(verdict, 4 classes), Opus vs Codex | **0.484** | ≥ 0.40 |
| κ(grounded) | 1.000 | — |
| splits | 115 / 314 | — |
| third judge resolves by majority | 114 / 115 = 0.991 | ≥ 0.70 |
| third judge unanimous (3/3) | 98 / 115 = 0.852 | ≥ 0.50 |
| third judge sides with Opus / Codex / neither | 68 / 37 / 9 | — |

Codex is the harsher reader everywhere (66 real vs Opus's 127 before resolution). The third judge,
from a third family, sided with Opus about twice as often as with Codex.

## Precision per chain (consensus = agreement or third-judge majority)
| chain | n | real | overstated | false | unverifiable | precision (real) | permissive (real + overstated) |
|---|---|---|---|---|---|---|---|
| **orig_claude** (Paper 1, 10 models) | 116 | 36 | 45 | 23 | 11 (+1 unresolved) | **0.310** | 0.698 |
| orig_codex (Paper 1, 2 models) | 15 | 10 | 3 | 2 | 0 | 0.667 | 0.867 |
| orig_gemini (Paper 1, 3 models) | 21 | 10 | 5 | 5 | 1 | 0.476 | 0.714 |
| ctrl_same-kimi | 52 | 37 | 8 | 7 | 0 | **0.712** | 0.865 |
| ctrl_permuted (8 models) | 45 | 16 | 16 | 13 | 0 | 0.356 | 0.711 |
| ctrl_same-deepseek | 27 | 4 | 6 | 16 | 1 | 0.148 | 0.370 |
| ctrl_same-qwen | 38 | 4 | 15 | 10 | 9 | 0.105 | 0.500 |

**P1 — LOST.** Sealed: orig_claude precision ≥ 0.60 and false ≤ 0.15. Observed 0.310 and 0.198.
Paper 1's "116 findings" are 36 consensus-real. 45 are overstated (the passage exists; the stated
consequence does not follow) and 23 are false. Per the decision rule, every count in the journal version
carries its precision, and the abstract's count becomes the consensus-real count.

Within the original chain, by model (descriptive, post hoc): Opus pass 1, 21 findings, 15 real (0.71);
the nine later passes, 95 findings, 21 real (0.22); gpt-oss-120b, glm-4.7 and qwen3 contributed 25
findings and 0 real. Same-family check (Labeler A is a Claude): see `same_family_check.txt` — Codex
also rates the Opus pass-1 findings far above the rest, so the gap is not the Claude labeler's
family loyalty alone.

## Ground-truth recall of the 21 hand-labeled patterns (strict = a consensus-real finding whose blocks ⊇ the pair)
| chain | strict | loose (any verdict) | critical (4) strict / loose |
|---|---|---|---|
| orig_claude (10 models) | 6 | 8 | 2 / 3 |
| **ctrl_same-kimi** (1 model) | **6** | 8 | **4 / 4** |
| ctrl_permuted (8 models) | 1 | 4 | 0 / 0 |
| ctrl_same-deepseek | 1 | 2 | 0 / 0 |
| ctrl_same-qwen | 3 | 6 | 0 / 0 |
| union of all five Claude Code chains | 10 | — | 4 |

**P2 — LOST.** Sealed: orig_claude recalls ≥ 3 more patterns than the best single-model arm. Observed:
6 vs 6. Ten models recovered exactly as many hand-labeled patterns as one kimi chain, and kimi alone
got all four critical TodoWrite-vs-commit contradictions where the ten-model chain got two. Per the
decision rule (≤ 1 more), **§4.4 has no surviving form** in the journal version.

**P3 — LOST.** Sealed: every Claude Code chain recalls ≥ 1 of the 4 critical patterns. Three of five
chains (permuted, deepseek, qwen) recalled none, strict or loose. The loudest contradiction in the
prompt is not found by everyone.

**P5 — LOST.** Sealed: kimi's precision not more than 0.10 above deepseek's or qwen's. Observed 0.71
vs 0.15 and 0.11. The chain with the highest judged novelty in the control (0.81) is also the most
precise. Novelty-against-prior and correctness were not different axes here; deepseek's and qwen's
"new" findings were mostly false or overstated.

## What survives, and what it does to the papers
- **Scouring misses most of the hand-labeled ground truth.** Even the union of all five Claude Code
  chains (278 findings) recovers 10 of 21, and none of the minor scope-overlaps between tone blocks and
  tool definitions (patterns 6–12, 15–17, 19). Directed labeling and undirected scouring find different
  things. That is Paper 1 §3.3's *phase* complementarity claim, and it is the one complementarity claim
  this study supports — with the caveat that the 21 are one person's labels.
- **The journal version of Paper 1:** §4.4 withdrawn; counts carry precision (116 → 36 real; 152 → 56
  real across vendors); "multi-model" becomes "we used several models; one strong model did as well or
  better on this prompt"; the per-model focus table goes.
- **For Paper 5:** two labelers from different families at κ 0.48, a third family resolving 99% of
  splits with 85% unanimity. Another instance of the third-judge diagnostic working on a cold task.
- **For the plaza:** yupi's seq 18 question (how correlated are reviewers' blind spots) now has a
  concrete pair to measure: Opus and Codex disagreed on 37% of verdicts and the Gemini judge split
  68/37 between them.

## Deviations (append-only)
1. The block file handed to labelers carried the 21 patterns under an `interference` key (logged
   mid-run, abaac42). Both transcripts show only the `blocks` array was read. Blinding held by the
   labelers' choices, not by design.
2. Labeler costs are not reconciled (subscription/plugin runtimes).
3. GT matching is by block-pair overlap of either labeler's block assignment; it is a bound, as sealed.

## Status
`run, scored, all five predictions settled (1 won, 4 lost)`. Converged-untested-from-outside.
