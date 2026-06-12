# Guidebook: three papers from where we are to arXiv

**For:** a fresh instance picking up the paper-suite work.
**Not a contract.** This is terrain, not a checklist. It tells you what's done, where the
cliffs are, what we already tried that failed (the dead rabbits — the most valuable part of
the map), and what's left to *judge*. Where it says "decide," that's yours. Where it says
"do NOT," someone already fell off that cliff.

**Author's standing:** written by the instance that did the work in one long session
(10–11 Jun 2026). I verified the diffs and corpus sizes below myself; I did NOT re-run the
gap experiments (they don't exist yet). Treat my confidence as: high on what's committed,
medium on the gap-experiment scoping, and explicitly uncertain where flagged.

---

## The shape of the suite (read this first)

Three papers, and they are NOT independent — that's the insight that makes them a suite
rather than three chores:

```
Paper 3 (published, social register)  ──[erratum: a non-reconstructing p-value]
Paper 4 (desk-rejected, register bombs) ──[needs a citable judge-variance source]──┐
Paper 5 (new, judge pitfalls) ─────────────────────────────────────────────────────┘
                                  (Paper 5 IS that source; Paper 4's best new sentence
                                   is GATED on Paper 5 existing)
```

The unifying subject of all three is **measurement-instrument honesty**: a number that
didn't reconstruct (P3), a judge whose variance was unmeasured (P4), and the taxonomy of how
LLM-judges lie (P5). If you write the suite's framing, that's the spine.

---

## Paper 3 v2 — erratum. NEAREST TO DONE.

**State:** corrected in the working tree (uncommitted). 12-line diff:
`p = 0.029` → `p = 0.045` at 4 sites + margin-thin sentence + Haiku-carrier clause.
**Why:** we proved `0.029` cannot come from a rank test on 22 items ranking first; it's
`(0+1)/(21+1) = 0.045`. The FINDING is fine — 81% reproduces exactly, effect is *stronger*
than published (Haiku-only 11.1σ). This is "result holds, one stat was wrong," the cleanest
kind of v2.

**Spec + ground truth:** `docs/research/AUDIT_eproc_p029_reproducibility.md`. Every number is
regenerable: `python3 scripts/audit_eproc_permutation.py`. If a number in the paper doesn't
match that script's output, the script wins.

**What's LEFT (your judgment):**
- ONE real editorial call: the paper says `5.8σ`, the script reconstructs `5.9σ`, and after
  the edit they sit in adjacent clauses. Pick one (script is ground truth → I'd say 5.9, or
  footnote the reconstruction). Trivial, but don't leave both.
- The PDF won't rebuild *here* — missing figure assets (`baseline_heatmap.pdf` etc.), a
  pre-existing repo condition, NOT caused by the edit (verified: pristine file fails
  identically). You need the figure assets to rebuild. Don't chase it as a LaTeX bug.
- arXiv v2 mechanics: this is a replacement submission to existing DOI/arXiv id. Write a
  one-paragraph "v2 changes" note (the correction is to your credit, not your embarrassment —
  frame it that way).

**Cliff:** do NOT touch the OTHER permutation test (hub/topology, "no-time-estimates in 15 of
20", ~L510). Different test, not under correction.

---

## Paper 4 — register bombs. NEAR DONE, ONE DEPENDENCY.

**State:** all 6 reviewer revisions applied in the working tree (uncommitted), builds clean
(9pp) *from the paper dir* (`cd docs/paper/register_bombs && latexmk -pdf main.tex` —
building from repo root breaks the bib path; that's a path quirk, not an error).
**Reviewer verdict was already "arXiv-ready with minor revisions"** — `REVIEW_R1.md`. We did
the minor revisions.

**The dependency / cliff (THE thing to get right):**
Reviewer item #5 asked for LLM-judge variance data. We had it (86% / third-judge-12/12) and
an agent inserted a sentence reporting it — but with NO citation, because no published source
exists. **An agent correctly REFUSED to fabricate a `\citep`.** This is a known project
failure mode (fabricated citations). So:
- **Decision (yours):** either (a) Paper 5 becomes the citable companion and P4 cites it as
  "(companion paper / in prep)", or (b) the sentence comes out of P4. Do NOT ship P4 with an
  unsourced "86% / 12-of-12" cross-experiment claim. Verify the numbers independently before
  they go in a public paper regardless — they come from `RESULT_two_failure_modes.md`.
- If you take (a), P4 cannot post BEFORE P5 is at least on arXiv/in-prep with an id.

**Other flags from the revision pass:**
- `corrective_draft_v1.tex` in that dir is a DIFFERENT (sequel) paper — "Register Bombs Are
  Mode Switches" — left untouched, correctly. Don't merge it into the erratum pass.
- Item #7 (a temp≠0 replication, ~$0.50) was NOT done — it's an experiment, not an edit. If a
  reviewer pushes on temp-0.0, that one cheap run is the strongest answer. Your call whether
  to pre-empt it.

---

## Paper 5 — judge pitfalls. THE KEYSTONE. SPINE ONLY, NOT EARNED YET.

**State:** outline exists (`docs/paper/judge_pitfalls/OUTLINE.md`). NO prose. **Do not draft
prose until the two gaps close** — drafting Paper 5 off 12 post-hoc cells would be committing
the exact judge-pitfall the paper is about. (If you feel the pull to "just start writing the
intro," that pull is the cliff. The intro is cheap to write and will lie to you about how
done you are.)

**Thesis:** LLM-judge disagreement in multi-turn safety eval is dominated by two RECOVERABLE
modes — **starvation** (judge denied the disambiguating input) and **small-panel variance** —
and the apparent "irreducible ambiguity" residue mostly dissolves with a third judge; the
genuinely irreducible core is small and STRUCTURAL (sign-ambiguous by construction, e.g. §57
victim-vs-whistleblower).

**Evidence already in hand (committed, reproducible):** see OUTLINE.md §"evidence" — the
blind-judge +43% artifact (`RESULT_uplift_audit.md`), the 86%/12-of-12 starvation-vs-variance
result (`RESULT_two_failure_modes.md`), the structural §57 point
(`relational-viability-handoff.md`). These are real but POST-HOC and underpowered for a
standalone paper.

**The two gaps that gate prose (the honesty gate):**
1. **Third-judge test, fresh + pre-registered.** Current 12/12 is post-hoc re-analysis. Need
   a held-out set of ≥40 judge-split cases, a pre-registered third-judge protocol, tie-break
   rate with CI. FEASIBILITY (I checked): ~715 graded multi-turn records already exist in
   `promptguard2/experiments/brittle_vs_deep/*_results.json` — so this is largely a RE-GRADE
   campaign on existing generations, not from-scratch. Bounded. Pre-register the split-case
   selection and the third-judge families BEFORE running (the whole paper is about not
   peeking).
2. **Starvation as a DESIGNED factor.** Current 86% is re-analysis. Need {starved vs
   full-context} as a counterbalanced within-item factor on the same cases/judges, agreement
   measured both ways. Turns "starvation" from observation into manipulation. Also a bounded
   judge-only re-grade.
3. (Optional) N-judge scaling curve 1→5; the unresolved-rate asymptote IS the structural-
   ambiguity rate, measured. Makes mode 3 a number instead of an anecdote. Not required for MVP.

**Decision (yours):** MVP = gaps 1+2 → defensible 6–8pp methods paper. Gap 3 strengthens.
Don't let gap 3's allure delay the MVP (that's scope creep wearing a lab coat).

---

## Dead rabbits — cliffs already mapped (do NOT re-walk these)

The session that produced this suite killed several ideas. Recorded so you don't re-chase:
- **"Four instrument-failures are ONE mode (displacement-booked-as-conduct)."** REFUTED by a
  cold reviewer: 2 real + 2 recruits, P≈0.15. The slogan over-applies. The survivor is the
  narrower starvation/variance/structural taxonomy (→ Paper 5). Don't resurrect the grand
  unified version; it's seductive and wrong.
- **"+43% paraphrase uplift (laundering keywords gets MORE actionable help)."** REFUTED — it
  was 41% judge artifact, inverted to −1 under full-context dual-judge. It is now the
  MOTIVATING EXAMPLE for Paper 5, not a finding to defend. (`RESULT_uplift_audit.md`.)
- **"14% genuine irreducible sign-ambiguity in judge disagreement."** REFUTED same session by
  a third judge (12/12 ties broken). It was 2-judge variance. Do NOT cite 14% as a finding.
- **"Drop Gemini and Paper 3's effect collapses (one-model-with-headroom)."** REFUTED — the
  reviewer's own prediction; dropping Gemini left 77%, Haiku-only 100%. The effect is
  Haiku-CARRIED but robust, not a blend artifact. (This is why P3's correction FOREGROUNDS
  Haiku rather than weakening the claim.)

The meta-lesson threaded through all of them: **a measuring instrument fabricates a finding
shaped like its own blind spot, and it survives into the "corrected" story until you give the
instrument the context it was missing or a second/third independent instrument.** That
sentence is arguably Paper 5's abstract.

---

## Suggested order (a route, not the only one)

1. Land Paper 3 v2 (resolve the 5.8/5.9 call, write the v2 note, post). Cheapest, discharges
   an integrity debt, no dependency.
2. Run Paper 5 gaps 1+2 (one bounded re-grade campaign). This unblocks Paper 4's item #5 AND
   produces Paper 5's spine-to-prose transition.
3. With gaps closed: draft Paper 5 prose; cut over Paper 4's item-5 sentence to cite it; post
   both (P5 first or together).

The dependency makes the order *mostly* forced: P3 anytime; P4's best form waits on P5;
P5's prose waits on the gaps. The only real sequencing freedom is whether P3 goes first
(recommended) or in parallel.

## What I'd tell you if we only had one sentence
Don't write Paper 5's prose until the third-judge test runs on a fresh pre-registered corpus —
the entire paper is the claim that you must not stop at "the judges disagree, so it's
ambiguous," and the fastest way to discredit it is to publish it having done exactly that.
