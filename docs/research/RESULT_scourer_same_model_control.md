# RESULT: same-model scourer chains — the "complementarity" of Paper 1 §4.4 is mostly the instruction

**Run:** 2026-10-09, 13:13–13:48Z. **Prereg:** `prereg_scourer_same_model_control.md`
(sealed at c187b27, stamped 81b85d0). **Data:** `data/scourer/control/` — per-arm stack
JSON, every raw response with OpenRouter generation id and usage, logs; judge raw in
`m4_judge_raw.jsonl`. **Cost:** $0.46 total, from the generation records (kimi $0.18,
permuted $0.23 of which the Opus pass $0.17, qwen $0.04, deepseek $0.02).
**Analysis:** `scripts/analyze_scourer_control.py` (M1–M3, M5), `scripts/judge_scourer_control.py` (M4).

## Sealed predictions vs. observed

| arm | passes | first "no" | 3× "no" | findings | M2 uniq-cat | M3 new-cat |
|---|---|---|---|---|---|---|
| baseline (orig. 10-model chain, hand-resumed past "no") | 10 | 8 | 10 | 116 | 0.879 | 0.897 |
| same-deepseek | 4 | 2 | 4 | 27 | 0.889 | 0.889 |
| same-kimi | 5 | 3 | 5 | 52 | **0.308** | **0.500** |
| same-qwen | 10 (cap) | 6 | never | 38 | 0.974 | 0.974 |
| permuted (8 models, code-enforced stop) | 5 | 3 | 5 | 45 | 0.756 | 1.000 |

- **P1 (bet against the paper: all three same-model arms M2 ≥ 0.75 and M3 ≥ 0.75) — LOST,
  on one arm.** deepseek and qwen reproduce the "category explosion" at or above the
  original chain's level on their own. kimi does not (0.308 / 0.500). The prereg's P1-false
  rule fires (an arm with M2 < 0.6 and M3 < 0.6), so the category-divergence claim gets
  its first real support — from one arm of three, and see the caveat below.
- **P2 (bet for the paper: ≥ 2 of 3 same-model arms reach 3× "no" by pass ≤ 7 with ≤ 81
  findings) — WON, and it means less than it was sealed to mean.** deepseek (4, 27) and
  kimi (5, 52) qualify; qwen never produced three consecutive "no" and ran to the cap at 38.
  But the **permuted cross-model chain under the same code-enforced stop rule also stopped
  at pass 5 with 45 findings**, inside the same-model range (27–52). The original's 116
  findings over 10 passes came from a chain that was resumed by hand after each "no"
  (the runner stops at the first "no"; the three-consecutive rule was applied manually).
  Under a matched stop rule, eight models gave no more coverage than one.
- **P3 (bet against model-specific focus: same-model cross-position Jaccard not > different-
  model same-position by > 0.05) — WON.** 0.157 vs 0.150, difference 0.007, n = 5 and 4.
  Weak by construction (two original models unavailable, permuted arm 5 passes), and it
  says what it says: nothing in a model's findings marks it as that model.

## The kimi caveat (post hoc, flagged as such)
kimi's low uniqueness is a labelling style, visible in its category list: 9 ×
`surprising_structure`, 8 × `scope_ambiguity`, 6 × `contradiction`, 6 ×
`implicit_assumption` — the first-pass prompt's own bullet list of what might be
interesting, reused as a fixed taxonomy across all five passes. In the original chain the
same model id at pass 3 produced 14 hyphenated one-off labels ("economic-instruction",
"permission-flow-inversion"). So M2/M3 on kimi measure label reuse, not substance, which is
exactly the blind spot the prereg named and sent M4 to check.

## M4 — judged novelty (secondary; judge google/gemini-3.7-flash, asked twice, agreed-only)
209 findings from passes ≥ 2 across all five chains; two-ask agreement 0.947. "novel" means
*no earlier finding in the same chain addressed it*, as judged — not true, and not
ground-truth-matched. Pass-1 findings are novel by construction and are added in the last
column.

| chain | judged | agreed | novel | refinement | duplicate | novel / agreed | novel incl. pass 1, of total |
|---|---|---|---|---|---|---|---|
| baseline (10 models, hand-resumed) | 95 | 86 | 30 | 24 | 32 | 0.349 | ~51 / 116 |
| same-deepseek | 17 | 17 | 9 | 6 | 2 | 0.529 | 19 / 27 |
| same-kimi | 38 | 37 | 30 | 7 | 0 | **0.811** | **44 / 52** |
| same-qwen | 29 | 28 | 7 | 15 | 6 | 0.250 | 16 / 38 |
| permuted (8 models) | 30 | 30 | 24 | 6 | 0 | 0.800 | 39 / 45 |

Three things the primary metrics could not see:
1. **M2/M3 measured label style, and in the wrong direction.** kimi had the lowest
   category uniqueness (0.308) and the highest judged novelty (0.811); qwen the highest
   uniqueness (0.974) and the lowest novelty (0.250): qwen renamed while restating. The
   P1-false rule that fired on kimi is therefore reversed by its own pre-registered check:
   the category-divergence claim gets **no** support from any arm. Paper 1's "102 unique
   categories for 116 findings" was a statistic about label inventiveness, not findings.
2. **The original chain's 116 findings are ~51 novel.** After pass 5 the baseline is mostly
   refinement and duplicate (passes 6–10: 5 novel of 45 agreed). The hand-resumed passes
   8–10 added 22 findings, 2 of them novel.
3. **One model, five passes, out-found eight models in five passes.** kimi alone: 44
   judged-novel of 52; the permuted cross-model chain: 39 of 45. One chain each; the
   ordering kimi > permuted > deepseek > qwen is a description of four runs, not a ranking
   of models.

Judge caveats (Paper 5's own list): one judge family; "novel" is relative to the chain's
prior findings, so a fabricated finding is "novel"; refinement/duplicate boundaries are
the judge's convention. Reliability is reported (0.947) and is not validity.

## Deviations (append-only)
1. **Comparator flaw in P2, found after the runs.** P2 was sealed against the baseline's
   10 passes / 116 findings. That baseline was produced by hand-resuming past "no" votes,
   so it is not comparable under a code-enforced stop rule. The permuted arm is the right
   comparator and was run, but the prereg did not name it as P2's comparator. The
   interpretation above uses it; the sealed P2 is reported as sealed and then set aside.
2. **M5 model-id normalisation added to the analysis script after the runs.** The original
   chain logged Opus as `claude-opus-4-6`, OpenRouter as `anthropic/claude-opus-4.6`; the
   first M5 computation silently dropped Opus (n = 4). Normalised ids give n = 5; the
   number moved from −0.004 to +0.007 and the conclusion did not.
3. qwen pass 2, attempt 1: unparseable JSON; re-asked once per protocol, both raw
   responses kept.
4. Models: `gemini-2.0-flash-001` and `grok-4.1-fast` no longer served; the permuted arm
   used the 8 survivors, no substitutes (declared at seal).

## What this does to Paper 1
§4.4 cannot be stated as in v1 or v2's hypothesis form without qualification:
- "Each model invents its own taxonomy; the categories don't converge" — a single model,
  told not to repeat itself, does this too (two of three arms at ≥ the original's rate).
  The explosion is the instruction's. The one exception is a labelling style, not evidence
  of convergence.
- "The coverage does [converge]" — not shown. Under a matched stop rule, a cross-model
  chain and three single-model chains all exhaust at 4–10 passes with 27–52 findings.
  The original's 116 is a product of hand-resumption and ten passes, not of ten models.
- Per-model "characteristic focus" (Table in §4.4) — no model signature detectable
  (P3), on weak n.
For the journal version: multi-model scouring is reported as a robustness/cost choice,
not a methodological requirement; the per-model focus table is dropped or relabelled as
a description of one chain; the "102 unique categories" statistic is dropped (it measures
labels). With M4 in hand, the decision-rule outcome is **"P1 true and P2 false" in
substance**: §4.4 is withdrawn in the journal version. The one thing this does NOT test is whether the *union* of
findings across model families covers more of the ground truth than one model's — that
needs the per-finding verdicts (queue item 4), and the 21-pattern ground truth.

## Status
`run, scored, M4 complete`. Converged-untested-from-outside: no second
instance has reconstructed these numbers from the raw files.
