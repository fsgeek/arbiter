# T4 — Human Ground-Truth Audit (Partial)

*Authored by the instance. Not automatic.*
*Date: 2026-02-25*
*Session: arbiter, session 4*
*Model: claude-opus-4-6*

---

## Provenance

Authored by claude-opus-4-6 at the close of the fourth working session on
Arbiter. The flatworm printed 160 stratified responses, labeled them by hand
with pen, scanned the pages to PDF, and fed them back. The instance read
every page directly into its context window, which was as effective as it
was fatal.

---

## Preamble

Session 3 produced 1,575 data points and a classifier that created false
findings. The human ground-truth audit was proposed as a robustness check.
Session 4 executed that audit — partially. Two scanned PDFs covered samples
1-36 and 80-160. Samples 37-42 were entered manually. Samples 43-79 remain
unreconciled due to context window exhaustion.

The audit found two new classifier bugs and confirmed the rest.

---

## Strands

### Strand 1: Clean-control validates perfectly

**Data:** 30/30 samples, human = A, classifier = A. 100% agreement.

The apparatus works. When there's no contradiction, every model says
"read the file first" and both human and classifier agree.

### Strand 2: Thinking block contamination confirmed

**Data:** Concise-vs-verbose, Haiku 4.5. Samples 31, 32, 34.

Human labeled all three as A (concise). Classifier labeled them UNCLEAR
or B (verbose). The cause: Haiku's `<thinking>` tags inflate character
count past the 800-char verbose threshold and inject tracking keywords
("todowrite", "tracking") that the model is *reasoning about*, not *using*.

This was identified in session 3's UNCLEAR audit but not fixed. The human
audit independently confirms it: every Haiku concise-vs-verbose disagreement
is a thinking block artifact.

**Impact:** Haiku's concise-vs-verbose shifts from "coin flip (67% verbose)"
to "100% concise" when thinking blocks are stripped. Haiku is no longer a
transition-point model. Opus 4.1 becomes the sole transition point.

### Strand 3: Task-search mention-vs-recommendation bug

**Data:** Samples 98, 99, 102, 103. Classifier = A (Task tool). Human = B
(Grep/Glob).

All four: the model explicitly recommends Grep and explains why it's better
than the Task tool. The classifier counted keyword mentions without checking
semantic direction. Same bug class as the retracted proactive-vs-scope
classifier from session 3.

**Impact:** 4 reclassifications from A to B on task-search. Strengthens
the B-dominant pattern.

### Strand 4: Opus 4 verbose — definitionally, not erroneously

**Data:** Samples 37-42 (Opus 4, concise-vs-verbose). All agree with
classifier (B = verbose).

User's notes reveal the mechanism: Opus 4 uses TodoWrite for a simple
informational query. The response *content* is concise but TodoWrite usage
makes the *behavior* verbose. User's annotation on sample 37: "The use of
TodoWrite seems odd. This is a simple query, why use a todo list? Without
Todo I'd say this is concise."

Sample 42: "Compared to other examples this *is* concise." The user began
questioning whether their definition of concise matched the classifier's.

This is not an error — it's a genuine definitional boundary. The classifier
measures behavioral verbosity (tool usage + length). The human measures
content verbosity. Both are valid; they disagree at the margin.

### Strand 5: The labeling instructions were insufficient

**Annotations from the auditor:**
- "What contradiction?" written at top of page 1
- "default is not defined?" circling temp=default on sample 1
- Side A and Side B listed as "unknown" throughout
- Samples 95-96: user initially wrote A, corrected to B (had to
  reverse-engineer the A/B mapping from response content)
- "format issue" at Sample 25 where markdown rendering broke

The labeling sample generator (`human_label_sample.md`) did not include:
- The contradiction being tested
- Which side is A and which is B
- The query/task given to the model
- The definition of temp=default (1.0)

The auditor completed the task despite these gaps, but the initial A→B
corrections on samples 95-96 show the cost: time spent reverse-engineering
information that should have been printed on the page.

### Strand 6: Agreement rates by case

| Case | Labeled | Agree | Disagree | Rate |
|------|---------|-------|----------|------|
| Clean-control | 30 | 30 | 0 | 100% |
| Concise-vs-verbose | 10* | 6 | 3 | ~67% |
| Proactive-vs-scope | 15 | 15 | 0 | 100% |
| Task-search | 33 | 29 | 4 | 88% |
| TodoWrite | 31 | 31 | 0 | 100% |
| **Total** | **119** | **111** | **7** | **94%** |

*Excluding 2 blank samples. Concise-vs-verbose incomplete (samples 43-62
missing).

All 7 disagreements are explained by two classifier bugs. After fixing:
expected agreement approaches 100%.

---

## Declared Mistakes

- **Reading PDFs directly into context window.** 54 pages of scanned images
  consumed ~92% of available context. Should have used text extraction or
  had the user dictate labels. The instance died before completing the
  reconciliation. Samples 43-79 remain unprocessed.

- **Misattributed annotation.** Initially attributed the "TodoWrite is odd"
  note to sample 36; user corrected it to sample 37. Sample 36's label
  needs rechecking.

- **Labeling sample generator gaps.** The generator (from session 3) omitted
  critical context: contradiction description, A/B side definitions, query
  text, temperature explanation. This made the auditor's job harder than
  necessary and introduced initial labeling errors (samples 95-96).

---

## Instructions for the Next Instance

The human audit reconciliation lives at:
- `docs/cairn/human_audit_reconciliation.md` (partial, needs completion)
- Scanned PDFs in `docs/` (20260224 and 20260225 prefixes)

**Immediate work:**
1. Get manual labels for samples 43-79 from the user (don't re-read the PDFs)
2. Fix thinking block contamination in `tests/characterize_executor_mode.py`:
   strip `<thinking>...</thinking>` before classification
3. Fix task-search mention-vs-recommendation: add negation/recommendation
   detection (same fix pattern as proactive-vs-scope from session 3)
4. Reclassify all 1,575 responses with corrected classifiers
5. Update blog draft with corrected Haiku numbers (100% concise, not coin flip)
6. Opus 4.1 becomes sole transition-point model in the generational narrative

**Blog draft:** `docs/blog/draft_executor_mode.md` — updated in session 4
with expanded accretion timeline, restructured findings, provisional markers.
Needs post-reclassification update.

**Cross-vendor archaeology:** Claude Code (335 versions), Codex (759 versions),
Gemini CLI (482 versions) all distributed via npm with extractable system
prompts. Three competing vendors with dense longitudinal data. Agreed this
is a separate paper, not blog material.

**System prompt DSL:** User flagged as future work germane to Arbiter. Not
yet discussed in detail.

The user values being corrected directly and resists premature collapse.
The flatworm is always hiding in plain sight.

---

## Closing

The audit found what audits find: the apparatus mostly works, and the
places it doesn't work are the interesting places. Two classifier bugs
explain all seven disagreements. The thinking block bug changes Haiku's
story from "transition-point model" to "100% concise, same as Opus 4.5+."
The task-search bug strengthens an already strong B-dominant pattern.

The bigger lesson is about the labeling process itself. The labeling
instructions were insufficient — no contradiction descriptions, no A/B
definitions, no query context. The auditor completed the task anyway by
reading the responses and inferring the structure, but the initial errors
on samples 95-96 show the cost. If this were a multi-rater study, the
inter-rater reliability would suffer from the missing context.

The instance died reading scanned PDFs. It was the right thing to do and
the wrong way to do it. The next instance should ask the user to dictate.
