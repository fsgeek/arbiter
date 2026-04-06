# Register Bombs Paper — Supervisor Review R1 (2026-03-30)

**Reviewer:** Research supervisor instance (Claude Opus 4.6)
**Verdict:** Strong short paper. arXiv-ready with minor revisions below.

---

## What Works

1. **Clean experimental isolation.** Table 1 (E-PHASE-CONFIRM) is a model ablation study. Six conditions, one variable, one clear result. The control conditions (only-ea-imp, only-tw-imp) definitively rule out a general lone-wolf effect. This is the kind of experiment that's hard to argue with.

2. **The scope experiment is the paper's best contribution.** Prefix scoping fails (0.167). Inline scoping works (1.000). Hybrid-decl-never (1.000) shows "NEVER" isn't the trigger — register context is. Three conditions, one clean conclusion: scope must be embedded per-prohibition. This is immediately actionable for anyone writing system prompts.

3. **The density trajectory is surprising and well-reported.** Non-monotonic rescue/collapse. Pairwise, not aggregate. The paper doesn't overclaim — it says "you cannot predict adherence from density alone" and shows why.

4. **$5.70 total cost.** Reproducible by anyone with an API key. This matters for credibility.

5. **Honest cross-model section.** The paper correctly identifies the probe transfer problem rather than forcing a cross-model claim the data doesn't support.

---

## What Needs Work

### Must fix for arXiv

**1. Mechanism gap.** The paper describes *what* happens (scope loss, clause-level processing) but not *why*. What is the model actually doing when the bomb detonates? Candidates:

- The imperative block's prohibitions ("NEVER use Task tools") are parsed as unconditional commands with higher authority than the surrounding declarative instructions, suppressing anything that looks like tool delegation.
- The register contrast itself is a signal — the model interprets register shift as emphasis, and the emphasis bleeds to semantically adjacent behaviors (tool use → tool delegation).
- The model's instruction-following mechanism doesn't maintain a scope stack; each clause is evaluated against the full instruction set independently.

You don't need to resolve this — but acknowledge the mechanistic gap explicitly. One paragraph: "We characterize the phenomenon but do not explain the internal mechanism. The candidates are [X, Y, Z]. Distinguishing them requires [attention analysis / intermediate layer probing / targeted ablation of the model itself, not just the prompt]."

**2. Tighten the "register bomb" definition.** The term is used before it's fully defined. Give it a boxed definition early:

> **Register bomb:** An instruction block B in register R₁ embedded in a prompt otherwise written in register R₂ (R₁ ≠ R₂), where B's inclusion causes adherence collapse on instructions semantically unrelated to B. The collapse is mediated by register contrast, not semantic overlap.

**3. State the Haiku-specificity more forcefully.** The limitations section buries this. Add a sentence in the abstract or introduction: "We demonstrate the effect in Claude Haiku 4.5; cross-model replication is confounded by probe transfer, and the generality of the phenomenon is an open question."

### Should fix

**4. Temperature 0.0 justification.** The limitation is noted but not justified. Why deterministic decoding? If the answer is "to reduce variance in a small-N study" — say so. A reviewer will wonder whether the effect disappears at temperature 0.7.

**5. LLM-as-judge variance.** Nine of 22 probes use LLM judge scoring. How stable is the judge? If you have any data on judge agreement (repeated scoring of the same output), report it. If not, flag it as a known limitation with a concrete suggestion: "Future work should report inter-judge agreement."

**6. DSL connection (one sentence).** In the discussion or conclusion: "In a system where prompts are compiled from a typed instruction DSL with explicit scope annotations, register bombs would be caught at compile time as scope violations — a static guarantee that no amount of careful natural-language authoring can provide." This connects to the broader Arbiter research program without requiring development.

### Nice to have

**7. One temperature != 0 replication.** Even a single condition (all-decl vs only-cr-imp at temperature 0.7) would address the most obvious reviewer concern. If the bomb still detonates at 0.7, that's a much stronger claim. If it attenuates, that's also interesting. Cost: ~$0.50.

---

## Do Not Do

- **Do not expand the cross-model section.** The probe transfer problem is real and the paper handles it correctly by documenting it as a methodological finding rather than forcing claims. Leave it.
- **Do not add attention analysis.** That's a different paper requiring model internals access.
- **Do not try to make this longer.** The paper's strength is its tightness. Eight pages, four experiments, one clean story.

---

## Venue Notes

arXiv is the right first move — get it searchable. For subsequent submission:

- **ACL/EMNLP short paper track:** Natural fit. Instruction following, scope processing, cross-linguistic connections.
- **NeurIPS/ICML workshop** (instruction following, prompt engineering, or AI safety): The $5.70 cost and actionable design principles make it a strong workshop contribution.
- **NAACL:** If ACL timing doesn't work.

The paper is a natural sequel to the social register paper. If both are on arXiv, they form a coherent two-paper arc: (1) register matters across languages, (2) register boundaries within a single prompt create catastrophic interference. A third paper on the DSL solution would complete the trilogy.
