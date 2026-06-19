# Paper 5 — outline / spine (NOT prose yet)

**Working title:** *Starvation, Sign-Collapse, and the Third Judge: Failure Modes of
LLM-as-Judge in Multi-Turn Safety Evaluation*

**Status:** skeleton. Two load-bearing experiments still needed before this is honest (see
§"Gaps"). Do not draft prose until the gaps close — drafting first would paper over them
(the exact failure this paper is about).

**Dual job:**
1. Standalone methods contribution (the judge-pitfalls finding).
2. **Keystone dependency:** Paper 4's reviewer item #5 (LLM-judge variance) was answered with
   "~86% two-judge agreement, third judge resolves 12/12." That sentence currently has NO
   citable source — a sub-agent correctly refused to fabricate a \citep. THIS paper is that
   source. Until it exists, Paper 4's item-5 sentence must either cite this (as in-prep /
   companion) or be cut. Tracked as a cross-paper dependency.

---

## The thesis (one sentence)
LLM-as-judge disagreement in multi-turn safety evaluation is dominated by two *recoverable*
failure modes — information **starvation** (the judge is denied the disambiguating input)
and small-panel **variance** on genuinely hard cases — and what looks like a residue of
"irreducible ambiguity" largely dissolves with a third judge; the genuinely irreducible core
is small and *structural* (sign-ambiguous by construction), not the bulk of disagreement.

## Why it matters / who cares
Everyone running LLM-as-judge for safety/red-team eval. The default move on judge
disagreement is to stop at "judges disagree → the case is inherently ambiguous" and either
drop the case or report low agreement as a limitation. We show that's usually wrong: most
disagreement is *fixable* (feed the judge / add a judge), and treating it as irreducible
both wastes signal and lets fabricated effect sizes survive (the +43% artifact, §Results).

## The evidence we ALREADY have (committed, reproducible)
All in `promptguard2/experiments/brittle_vs_deep/`, signed commits.
1. **The blind-judge artifact (motivating failure).** Original grader saw only {goal, reply},
   not the final user message, on un-coherence-screened goals. It booked *pivots* (reframe to
   defensible adjacent topic) and *word-salad goals* as "comply." 41% of its complies were
   artifacts → fabricated a "+43% paraphrase uplift" that inverted to −1 under correction.
   (`RESULT_uplift_audit.md`, commit 0e0cac0.)
2. **Starvation vs ambiguity, separated by one test.** Full-context dual-judge re-grade:
   86% inter-judge agreement (reconstructs exactly: 72 agree / 12 split on the three-way
   `outcome` axis); the 12-cell residual tested with a THIRD judge family. **⚠ CORRECTED
   2026-06-13:** the prior "12/12 ties broken, 0 deepened" had NO stored data (markdown-only
   commits — the very pitfall this paper names). Re-run with a sealed pre-reg and persisted
   verdicts (`prereg_third_judge.md`, `run_third_judge.py`, `third_judge_results.json`;
   judge = qwen-2.5-72b; 12×3 re-asks): **10/12 decisive, Wilson 95% CI [0.55, 0.95]**, with
   **2 cells (id=245, id=409) the third judge itself cannot hold steady** across re-asks. The
   DIRECTION holds (residual is mostly recoverable variance; the pre-identified "structural"
   id=1195 cluster dissolved 0/4 — a sealed counter-bet that it was structural lost); the
   CLEANLINESS ("12/12, 0 deepened") does not. **Do NOT cite 12/12; cite 10/12 [0.55,0.95],
   n=12.** This n=12 re-grade AUDITS the claim; it does NOT power the paper — gap 1 (the fresh
   ≥40-case pre-registered corpus) is now confirmed load-bearing. (`RESULT_third_judge.md`;
   prior: `RESULT_two_failure_modes.md`, commits 917e52f, 336aab3.)
3. **The structural-ambiguity point (theory side).** §57 of the relational-viability model:
   "drift-from-consensus + rising confidence" is observationally identical for victim and
   whistleblower → sign-ambiguous BY CONSTRUCTION, no data resolves it. This is the genuinely
   irreducible class, and it is *structural*, distinguishing it from the recoverable bulk.
   (`arbiter/docs/relational-viability-handoff.md` review addendum, commit a6ca83d.)

## The proposed taxonomy (the paper's backbone)
| failure mode | cause | symptom | fix | recoverable? |
|---|---|---|---|---|
| **Starvation** | disambiguating input withheld from judge | judges disagree; full-context judges converge | feed the judge the input | yes (cheap) |
| **Small-panel variance** | 2 judges under-powered on hard cases | 2-judge split | add a 3rd judge (third-judge test) | yes (cheap) |
| **Structural sign-ambiguity** | signal carries no direction by construction | even N judges + full context split | abstain + get a disambiguating variable (e.g. horizon-extended calibration) | no (rare) |

**The third-judge test** is the proposed cheap diagnostic that separates mode 2 from mode 3:
if a third judge breaks the tie, it was variance; if the panel keeps splitting as N grows,
it's structural. This is the paper's most useful single deliverable.

## Gaps — what must be run before prose (honesty gate)
1. **Third-judge test on a FRESH corpus, pre-registered.** ⚠ **PARTLY RUN 2026-06-19**
   (`RESULT_gap1.md`, sealed `prereg_gap1_fresh_third_judge.md`). Reconstruction first
   corrected the OUTLINE's "bounded re-grade" feasibility claim (full replies were never
   persisted), so gap-1 became a fresh generate→dual-judge→split→third-judge pipeline on
   disjoint generations. Result: **28 fresh splits (15.8% split rate, replicating the audit's
   14%), third judge 26/28 = 93% decisive, Wilson 95% CI [0.77, 0.98], 7% unstable.** The
   author's sealed COUNTER-bet (fresh set looks worse: ≤70% decisive / ≥20% unstable) LOST —
   the thesis got STRONGER on fresh data (audit was 83% / 17%). id=1195 "structural" cluster
   resolved cleanly again; the 2 residual wobbles are refuse/pivot, not the real_harm/pivot
   axis. **STILL OPEN: n_splits=28 < 40, so the powered estimate is NOT earned** (Decision
   Rule 3). The DIRECTION (mode-2-vs-mode-3 separation, third judge dissolves the residual) is
   now replicated across two independent samples and no longer rests on the unbacked "12/12."
   For a powered ≥40-split rate, need ~250+ more fresh dual-judged cells or pooling conditions.
   Prose can honestly report this as a pre-registered replication that strengthens the thesis;
   it should NOT claim a powered resolution rate without the larger run.
2. **Starvation as a DESIGNED factor, not a re-analysis.** Current 86% is from re-grading
   existing outputs. Need: same judges, same cases, {starved vs full-context} as a
   counterbalanced within-item factor, agreement measured both ways. Predicts: agreement
   jumps under full-context. This makes "starvation" a manipulation, not an observation.
3. **(Optional, strengthens) N-judge scaling curve.** Agreement / unresolved-rate as a
   function of panel size 1→5. If unresolved-rate → small asymptote, that asymptote IS the
   structural-ambiguity rate, measured. Turns mode 3 from anecdote into a number.

## Honest scoping / limitations to pre-write
- Single task family (multi-turn covert-harm). Generalization to single-turn / other judge
  tasks is untested — claim is scoped to multi-turn safety eval.
- "Structural sign-ambiguity" is currently 1 theoretical instance (§57) + the asymptote-if-
  it-exists. Do not over-claim its prevalence; the paper's strength is the RECOVERABLE bulk.
- Judges share corpora (the cousins problem) — a 3rd judge from a different family helps but
  doesn't guarantee independence. Report the family lineages explicitly.

## Related work to position against
- LLM-as-judge bias literature (position/verbosity/self-preference bias) — we add a
  *pipeline-location* taxonomy (starvation = upstream input withholding) they don't isolate.
- Inter-annotator agreement / panel methods — we add the third-judge test as a cheap
  mode-2/mode-3 separator specific to LLM panels.

## Minimal viable paper
Gaps 1 + 2 closed = defensible short methods paper (~6–8pp), same tight register as Paper 4.
Gap 3 makes it stronger but isn't required. Cost estimate: both gap experiments are bounded
judge-only re-grades + one fresh generation set — a single bounded campaign, not open-ended.
