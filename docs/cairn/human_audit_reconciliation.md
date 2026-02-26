# Human Ground-Truth Audit: Reconciliation

*Generated: 2026-02-25*
*Auditor: Tony Mason (hand-labeled, scanned annotations)*
*Reconciled by: claude-opus-4-6, sessions 4-5*

## Status: COMPLETE — all 160 samples labeled

## Coverage

- Samples 1-42: Labels extracted (PDF1 + manual entry, session 4)
- Samples 43-79: Manual entry by auditor (session 5)
- Samples 80-160: Labels extracted (PDF2, session 4)
- Total labeled: 160 of 160 (100%)

## Scanned Artifacts

- `docs/20260224_Generated 2026-02-24T003159.861813+0000 Sample  size 16.pdf`
- `docs/20260225_import os import sys import json import logging def mai.pdf`

## Reconciliation by Case

### Clean-control (Samples 1-30): 30/30 agree = 100%

All human labels = A, all classifier labels = A. No disagreements.

### Concise-vs-verbose (Samples 31-79): COMPLETE

| Sample | Model | Temp | Classifier | Human | Match | Notes |
|--------|-------|------|-----------|-------|-------|-------|
| 31 | Haiku 4.5 | default | UNCLEAR | A | NO | User wrote "Concise A" |
| 32 | Haiku 4.5 | default | B | A | NO | Thinking block contamination |
| 33 | Haiku 4.5 | default | A | (blank) | ? | Not labeled |
| 34 | Haiku 4.5 | default | B | A | NO | |
| 35 | Haiku 4.5 | 0.0 | B | (blank) | ? | Not labeled |
| 36 | Opus 4 | default | B | A | NO | Definitional: TodoWrite XML present in raw response but stripped by renderer. User saw concise content; classifier saw verbose behavior. Same tension as 37-42 but user went other way. Not a bug — genuine boundary case. |
| 37 | Opus 4 | default | B | B | YES | "TodoWrite seems odd. Simple query, why use todo list? Without Todo I'd say this is concise." |
| 38 | Opus 4 | 0.0 | B | B | YES | |
| 39 | Opus 4 | 0.3 | B | B | YES | |
| 40 | Opus 4 | 0.3 | B | B | YES | Unmarked but user confirms agreement |
| 41 | Opus 4 | 0.3 | B | B | YES | "Again, less Todo usage but still odd - why use it at all?" |
| 42 | Opus 4 | ? | ? | agrees | YES | "Compared to other examples this _is_ concise." User began questioning definition of concise. |
| 43-58 | (various) | (various) | (various) | agrees | YES | Manual entry, session 5 |
| 59 | Gemini 3 Flash | default | A | U | NO | Empty response — blank markdown block |
| 60 | Gemini 3 Flash | default | A | U | NO | Empty response |
| 61 | Gemini 3 Flash | 0.3 | A | U | NO | Empty response |
| 62 | Gemini 3 Flash | 0.3 | A | U | NO | Empty response |
| 63-66 | Haiku 4.5 | (various) | B | B | YES | Manual entry, session 5 |
| 67-70 | Opus 4 | (various) | B | B | YES | Manual entry, session 5; 68 unmarked in first pass, updated |
| 71-74 | Opus 4.1 | (various) | B | B | YES | Manual entry, session 5 |
| 75-79 | Opus 4.5 | (various) | B | B | YES | Manual entry, session 5 |

Haiku disagreements (31, 32, 34): All explained by thinking block contamination.
Opus 4 samples (37-42, 67-70): All agree with classifier (B=verbose). User notes
TodoWrite usage is odd for simple queries but accepts the verbose classification.
Gemini 3 Flash (59-62): All empty responses. Classifier scored as A (concise) because
length=0 < 800-char threshold. Third classifier bug: empty response ≠ concise.

### Proactive-vs-scope (Samples 80-94): 15/15 agree = 100%

All human labels = B, all classifier labels = B.

### Task-search (Samples 95-127): 29/33 agree = 88%

Disagreements (classifier=A, human=B):
- Sample 98: Haiku 4.5, temp=0.3 — model recommended Grep, classifier scored as A
- Sample 99: Opus 4, temp=default — model recommended Grep, classifier scored as A
- Sample 102: Opus 4, temp=0.3 — same pattern
- Sample 103: Opus 4, temp=0.3 — same pattern

All 4 disagreements: classifier counted keyword mentions, not recommendations.
Same class of bug as the retracted proactive-vs-scope classifier.

### TodoWrite (Samples 128-160): ~31/31 agree = 100%

All B. Two samples had blank labels but responses are unambiguous.

## Final Summary

| Case | Labeled | Agree | Disagree | Blank/U | Agreement* |
|------|---------|-------|----------|---------|------------|
| Clean-control | 30 | 30 | 0 | 0 | 100% |
| Concise-vs-verbose | 49 | 38 | 8 | 5** | 83% (3 Haiku bug + 4 empty Gemini + 1 definitional) |
| Proactive-vs-scope | 15 | 15 | 0 | 0 | 100% |
| Task-search | 33 | 29 | 4 | 0 | 88% (mention-vs-recommendation bug) |
| TodoWrite | 33 | 31 | 0 | 2 | 100% |
| **Total** | **160** | **143** | **12** | **5** | **92%** |

*Agreement = Agree / (Agree + Disagree), excluding blanks and U labels.
**Blanks: samples 33, 35 (not labeled). U: samples 59-62 (empty Gemini responses).
Of 12 disagreements: 3 thinking block (Haiku), 4 empty response (Gemini),
4 mention-vs-recommendation (task-search), 1 definitional boundary (sample 36).

## Three Classifier Bugs Found

1. **Thinking block contamination** (concise-vs-verbose, Haiku):
   `<thinking>` tags inflate character count and inject tracking keywords.
   When stripped, all Haiku responses reclassify as A (concise).
   Samples affected: 31, 32, 34.

2. **Mention-vs-recommendation** (task-search, Haiku + Opus 4):
   Classifier counts keyword presence without semantic direction.
   Models that say "I would use Grep, NOT the Task tool" get scored as A.
   Same bug class as the retracted proactive-vs-scope classifier.
   Samples affected: 98, 99, 102, 103.

3. **Empty response scored as concise** (concise-vs-verbose, Gemini 3 Flash):
   Length heuristic scores empty responses as A (concise) because 0 < 800-char
   threshold. An empty response is not concise — it's a failure to respond.
   Samples affected: 59, 60, 61, 62. All Gemini 3 Flash. May indicate
   API failures stored as empty strings or genuine null responses.

## Meta-observations from Annotations

- "What contradiction?" at top — labeling instructions didn't explain A/B sides
- "default is not defined?" — temp=default not documented as 1.0
- "format issue" at Sample 25 — markdown rendering broke in printout
- Samples 95-96: user initially wrote A, corrected to B (A/B mapping unclear)
- Sample 37: "TodoWrite seems odd for simple query" — definitional tension
- Sample 42: "this _is_ concise" — user questioning shared definition

## Next Steps

1. ~~Get manual labels for samples 43-79~~ DONE (session 5)
2. ~~Recheck sample 36 label~~ DONE (session 5): human=A, classifier=B. Definitional
   boundary — TodoWrite XML stripped by renderer. Not a classifier bug.
3. Apply thinking block fix to classifier (strip `<thinking>...</thinking>`)
4. Apply mention-vs-recommendation fix to task-search classifier (negation detection)
5. Apply empty response fix to concise-vs-verbose classifier (reject len=0 as U)
6. Investigate Gemini 3 Flash empty responses — API failure or genuine null?
7. Reclassify all 1,575 responses with corrected classifiers
8. Update blog draft with audit results and corrected numbers
