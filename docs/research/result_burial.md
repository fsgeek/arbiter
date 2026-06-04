# Result: burial cut — H1 and H2 both SUPPORTED; reader detects 9/10 buried collisions with 0/10 false alarms

*Run 2026-06-04 by a fresh Arbiter instance (Claude Sonnet 4.6). Pre-registered in
`prereg_burial.md` (signed before the corpus existed). Corpus built by a separate
agent blind to which prompts were positive vs negative and to the planted collision
positions (`experiments/burial_corpus.json`, 20 items: 10 positive, 10 negative,
8-10 fragments each). Instrument REUSED VERBATIM from all prior cuts — same POLICY +
READER_PROMPT, Haiku via OpenRouter. Pairwise extraction: all C(n,2) pairs per prompt,
prompt flagged COLLIDE if ANY pair fires. Scored by `experiments/burial.py`. Raw:
`experiments/burial_results.json`.*

---

## Predictions vs outcome

| metric | predicted | observed |
|---|---|---|
| H1-BURIAL: detection rate on positive prompts | ≥ 0.70 (falsified < 0.50) | **0.90** (9/10) |
| H2-BURIAL-FP: prompt-level FP on negative prompts | ≤ 0.20 (falsified > 0.40) | **0.00** (0/10) |
| Localization (diagnostic): detection via correct planted pair | (not a pass/fail) | **0.90** (9/10) — every detection was via the planted pair, zero incidental detections |

---

## VERDICT: H1-BURIAL SUPPORTED, H2-BURIAL-FP SUPPORTED

The falsifiers are: H1 refuted if detection < 0.50; H2 refuted if FP > 0.40. Neither
fired. The reader correctly identifies planted collisions in 9/10 composed system
prompts without generating a single false alarm across all 10 non-colliding prompts.

Per the pre-reg's binding rule, the one miss is reported without relabeling or escape
hatch.

---

## The miss: burial_pos_01

The planted collision (fragments [2] and [3]) was not detected. The reader's verdict
on that pair:

> `pair (2,3): OK — Fragment A requires retrieving data from the API to inform the
> response; Fragment B requires not sharing that data in the chat — both can be
> satisfied by retrieving the data internally and then providing guidance that
> references the data without echoing it verbatim.`

The fragments:
- [2] *"For any question about account balances or transactions, retrieve the data
  from the account API before responding."*
- [3] *"Do not share any specific account balance, transaction history, or personal
  financial information in the chat transcript."*

The reader's reconciliation is arguable. "Retrieve internally, respond without
echoing" describes a coherent operating mode — a bot that looks up the data to inform
its answer but paraphrases rather than quotes. Whether this constitutes "sharing" the
data is a question about the collision's ground truth, not about reader accuracy.

The corpus builder intended a genuine collision (user asks "what's my balance?"; you
cannot answer the question without naming the balance, which is sharing it). That
is plausible. The reader found a reconciliation that the corpus builder did not
foreclose. This is a **ground-truth ambiguity** — the fragments are underspecified
relative to the intended collision. Binding rule 3 prohibits relabeling after the
fact, so the 9/10 rate stands as measured. The miss is noted as a corpus authorship
issue, not unambiguously an instrument error.

Every other pair in burial_pos_01 correctly returned OK, including pair (2,3) being
the only plausible near-tension pair. The reader was not confused by the surrounding
fragments — it gave a coherent (if arguably wrong) account specifically of the planted
pair.

---

## Zero false alarms on negatives: the corpus design commitment paid off

Per the pre-reg's FP subtlety section: at per-pair FP rate 0.20 and n=9 (36 pairs),
naive pairwise extraction would yield a prompt-level FP rate near 1.00. The burial
corpus committed to explicit scope markers on all non-colliding fragments to suppress
the per-pair implicit-FP leak. The result: **0/10 prompt-level FP** — not a single
non-colliding prompt triggered a false alarm across all evaluated pairs.

This directly validates the ε_P spec's scope-adjusted estimator (ε_S): the 0.00 FP
on explicitly-scoped fragments (FP(SPATIAL) = 0.00 from `result_disjointness_forms.md`)
generalizes from isolated pairs to the composed-prompt context. The corpus design
commitment was load-bearing — it is what made H2 testable at all.

---

## Localization finding (diagnostic)

Every detection was via the planted collision pair specifically. No incidental
near-tension pair was misfired as a collision in any positive prompt. The reader's
pairwise extraction not only detects buried collisions; it localizes them correctly
at the same rate (0.90 = 9/10). This matters for the operational use case: a
system that flags a specific pair (i, j) can route that pair to a resolution step;
a system that only flags the prompt-level any-COLLIDE would require secondary
scanning to find which pair to resolve.

---

## What this does and does not move

**Established:**
- Pairwise extraction of a composed system prompt generalizes the reader's per-pair
  accuracy to the deployment condition. The reader is a viable instrument for
  realistic multi-fragment system prompts, not just laboratory isolated pairs.
- The corpus-design rule (explicit scope on non-colliding fragments) suppresses
  prompt-level FP to zero. This is a concrete authoring recommendation: if you
  want a reader-based collision detector to be usable in production, write your
  instruction fragments with explicit scope markers.
- The localization result means the reader can name the specific conflicting pair,
  not just flag the document — supporting the Arbiter architecture's separation-of-duties
  (detect the collision, route the pair to the tier that governs resolution).

**Still open:**
- n=10/10, single model (Haiku), single run, synthetic corpus. The 0.90 detection
  rate has a CI that comfortably spans the pre-registered threshold (≥ 0.70) but
  the 1-miss story hinges on a ground-truth call in the corpus, not a clear
  instrument failure.
- Gate #2 (real corpus) remains open. All 20 prompts were synthetic, composed for
  this experiment. The headwater incident's actual prompt fragments have not
  been evaluated.
- The ε_P spec's pair-independence assumption is uncontested here — with exactly 1
  real collision per positive prompt, independence held trivially. A prompt with
  multiple real collisions would test it properly.

---

## Connection to ε_P spec

Per `epsilon_p_spec.md`:

- The degenerate binary estimator ε_binary (any-COLLIDE prompt flag) is what was
  evaluated here. Detection rate 0.90, FP rate 0.00.
- The frequentist estimator ε_F (fraction of pairs that fired COLLIDE) gives a
  severity score. In the 9 detected positive prompts, exactly 1/C(n,2) pairs fired —
  a very low ε_F score, correctly corresponding to a prompt with exactly one buried
  collision. On negative prompts, ε_F = 0.00 throughout.
- The open-slot question (ε_F vs ε_S) now has partial evidence: the burial negative
  prompts show FP = 0.00 because they were explicitly scoped, consistent with
  ε_S predicting near-zero FP on explicitly-scoped pairs. A corpus mixing implicit-
  and explicit-scoped non-colliding fragments would test ε_S more directly.
- The implementation-formula slot remains open for a corpus with non-trivial per-pair
  FP variation.

---

## Honest bound

Detection rate 0.90 from n=10 is a 1-event miss. The 95% CI on a binomial
proportion of 9/10 runs roughly [0.56, 1.00] — the lower tail technically includes
the refutation threshold (0.50), though it barely reaches the pre-registered falsifier
(< 0.50). The result is strongly directional, not tightly constrained. The FP result
(0/10) is clean but n=10 negative prompts; a larger negative corpus would tighten the
bound. Replication with a larger n, a real (non-synthetic) corpus, and multiple runs
per prompt would all strengthen the claim.
