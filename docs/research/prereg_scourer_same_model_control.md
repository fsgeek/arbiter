# Pre-registration: same-model scourer chains — is "complementarity" the models or the instruction?

**Sealed:** 2026-10-09, before any run. Commit hash is the seal; the post-commit
OpenTimestamps hook anchors it.
**Author:** Project Arbiter instance (Claude Fable 5.1), owner since 2026-10-07.
**Prompted by:** external review of arXiv 2603.08993 (October 2026), item 1; the
v2 of that paper restates the complementarity claim as a hypothesis pending this test.

## The claim under test

Paper 1 §4.4: "different models find different kinds of findings" — 116 findings,
102 unique free-text categories (ratio 0.879), each model "invents its own taxonomy",
"the categories don't converge; the coverage does."

The confound: every pass after the first receives all prior findings and is told
**"DO NOT repeat their findings... Go where they didn't."** Divergence between
successive passes is what the instruction demands of any model. The paper never ran
the same model for N passes. (Also found while preparing this: `scripts/run_scourer.py`
stops at the FIRST `should_send_another: false`; the Claude Code chain's
three-consecutive-"no" rule was enforced by manually resuming. The control enforces
the three-consecutive rule in code.)

## Arms (all on the same prompt file as the paper: `docs/claude-code-system-prompt.md`, v2.1.50, 78,259 chars)

Protocol identical to Paper 1: same prompt templates (`src/arbiter/scourer.py`,
unchanged), OpenRouter, `max_tokens=65536` (as the original OpenRouter path),
temperature default (as the original). Each pass sees prior findings tagged with the
producing model's name, as the original did (so a same-model chain sees its own name).

| arm | passes | model(s) |
|---|---|---|
| `same-deepseek` | up to 10 | deepseek/deepseek-v3.2 every pass |
| `same-kimi` | up to 10 | moonshotai/kimi-k2.5 every pass (the model credited with the "economic lens") |
| `same-qwen` | up to 10 | qwen/qwen3-235b-a22b-2507 every pass (the model that said "no" first, at pass 8) |
| `permuted` | 8 | the 8 original models still on OpenRouter, order permuted by `random.Random(20261009).shuffle`: minimax-m2.5, qwen3-235b, claude-opus-4.6, deepseek-v3.2, kimi-k2.5, gpt-oss-120b, glm-4.7, llama-4-maverick |

Not replicable: `google/gemini-2.0-flash-001` and `x-ai/grok-4.1-fast` are no longer
served. The permuted arm uses the 8 survivors with no substitutes; that is declared, and
it means the permuted arm is 8 passes against the original's 10.

Stop rule for every arm: three consecutive `should_send_another: false`, or the pass
cap. A pass whose JSON fails to parse is re-asked once; both raw responses are kept.

Everything is persisted per pass before the next pass starts: the stack JSON, every raw
response, the OpenRouter generation id and usage. No max-token cap below the original.

## Baseline (the original chain, `data/scourer/10pass_gptoss.json`, recomputed 2026-10-09)

| metric | definition | baseline |
|---|---|---|
| M1a | pass of first "no" | 8 |
| M1b | pass at which 3 consecutive "no" reached | 10 |
| M1c | total findings | 116 |
| M2 | unique normalized category strings / findings | 102/116 = 0.879 |
| M3 | pooled fraction of findings whose normalized category did not appear in any prior pass | 104/116 = 0.897 |

Normalization: lowercase, non-alphanumerics to single spaces, strip. M2 and M3 are
computed by `scripts/analyze_scourer_control.py` with no judgment calls.

Secondary, judged (reported with its reliability, never load-bearing alone):
- **M4** semantic-duplicate rate: a judge from a family in no arm (google/gemini-3.7-flash)
  sees each finding with the prior passes' findings and labels it `novel` /
  `refinement` / `duplicate`; asked twice; a label counts only if both asks agree.
- **M5** model signature (permuted arm): for each model, bag-of-words Jaccard between its
  findings (category + description, stopwords removed) in the original chain and in the
  permuted chain (same model, different position), versus Jaccard between that model's
  original-chain findings and the findings of whichever model occupied its original
  position in the permuted chain (different model, same position).

## Predictions (sealed; the author's own, with the side stated)

- **P1 — bet AGAINST the paper.** All three same-model arms reproduce the "category
  explosion": M2 ≥ 0.75 and M3 ≥ 0.75. If true, the categories-don't-converge
  observation is the instruction's, not the models'.
- **P2 — bet FOR the paper, separable from P1.** Same-model chains exhaust earlier: at
  least 2 of 3 reach three consecutive "no" by pass ≤ 7 AND finish with ≤ 81 findings
  (70% of 116). If instead same-model chains run to 10 passes with ≥ 100 findings, then
  "the coverage does [converge]" is also instruction-driven and §4.4 has nothing left.
- **P3 — bet AGAINST model-specific focus.** In the permuted arm, mean same-model
  cross-position Jaccard does not exceed mean different-model same-position Jaccard by
  more than 0.05.

## Decision rules

- P1 true AND P2 true → the paper's section splits: category divergence is instruction
  (cut the "invents its own taxonomy" claim); exhaustion-vs-coverage survives as the
  residual complementarity claim, to be stated at that strength.
- P1 true AND P2 false → §4.4 is withdrawn in the journal version; multi-model scouring
  is reported as a cost/robustness choice, not a methodological requirement.
- P1 false (any same-model arm has M2 < 0.6 and M3 < 0.6) → the category claim gets its
  first real support; report it with the arm counts, not as settled.
- P3 decides only whether Table "per-model analytical focus" stays as a description of
  models or becomes a description of one chain.
- A single arm result is one chain. No arm is rerun to "check"; a rerun is a new arm,
  declared.

## Known blind spots

- One prompt (v2.1.50). Nothing here generalizes past it.
- The permuted arm is confounded by two missing models and by model updates since March
  (same ids may be different weights). It is a weak test of P3 and is labelled so.
- M2/M3 measure category *strings*, which a model can vary without varying substance.
  M4 is the check on that, and M4 is an LLM judge, with the pitfalls Paper 5 catalogs.
- The author wants P1 true (it is the cleaner story). That is why P2 is sealed on the
  other side.

## Cost estimate
~20K input tokens per pass plus the growing findings summary; 38 passes; one Opus pass.
Under $3 total. Actual cost from OpenRouter generation records, reconciled after.

## Deviations log
(append-only; empty at seal)
