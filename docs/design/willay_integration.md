# Willay Integration — Design Analysis

Date: 2026-03-22
Author: Claude Opus 4.6 (session 20)
Status: Research analysis — not a proposal, not approved

## Purpose

Analyze whether and how Arbiter's ablation findings could be packaged
as Willay epistemic receipts. This is a design-space exploration, not
an implementation plan.

## Summary

The mapping is natural but not trivial. Arbiter produces experimental
claims with quantified evidence and known limitations. Willay produces
receipts that attest to claims with evidence, epistemics, and declared
losses. The two systems share Yanantin's foundational types
(EpistemicMetadata, DeclaredLoss, ProvenanceEnvelope) and the same
epistemic philosophy: say what you know, what you don't, and what you
made up.

The integration surface is small: a thin adapter module
(`arbiter.receipts`) that converts ablation findings into
ReceiptRecords. No changes to Willay. No changes to Arbiter's core.

---

## 1. Can Arbiter Generate Willay Receipts?

**Yes.** Every Arbiter finding has the structure Willay expects:

| Willay concept | Arbiter equivalent |
|---|---|
| `claim_text` | The finding statement (e.g., "Declarative encoding reduces cross-linguistic variance 81%") |
| `citation` | The cairn ID + experiment ID (e.g., "T10, experiment e-proc, session 19") |
| `evidence` | The ablation run data: probe results, covering array configs, model responses |
| `evaluation.epistemic` | T/I/F derived from statistical confidence |
| `evaluation.declared_losses` | Known limitations of the experiment |
| `evaluation.open_questions` | The "What We Don't Know" section of each cairn |
| `provenance` | Model ID, timestamp, session, commit hash |

The receipt type would be something like
`ablation_finding.v1` — distinct from Willay's default
`claim_evidence_receipt.v1` to signal that the evidence is
experimental data rather than retrieved citations.

### What maps cleanly

- **Claim text**: Every cairn has a one-sentence finding. T11's is
  "Rewriting three imperative-register blocks to declarative-register
  in Spanish shifted the pairwise topology from competitive (+0.010)
  to cooperative (-0.055)."

- **Evidence artifacts**: The ablation run JSON files contain
  timestamped, model-identified probe results with raw responses.
  These are already content-addressable (deterministic JSON, could be
  SHA-256 hashed).

- **Declared losses**: Every cairn has a "What We Don't Know" section
  that maps directly to DeclaredLoss entries.

- **Open questions**: Same section, different emphasis. Losses are
  about what was dropped; questions are about what remains unknown.

### What requires interpretation

- **T/I/F values**: Arbiter produces p-values and effect sizes, not
  T/I/F scores. The mapping from statistical confidence to
  neutrosophic epistemics is a judgment call. See Section 5.

- **Citation format**: Willay citations are typically URIs (DOIs, URLs).
  Arbiter cairns are local markdown files and experiment IDs. A local
  URI scheme (e.g., `arbiter://cairn/T11`) would work but isn't a
  real URI.

---

## 2. Evidence Artifacts

An Arbiter ablation finding rests on multiple evidence layers. Each
maps to one or more `EvidenceArtifact` instances.

### Layer 1: The ablation run file

```python
EvidenceArtifact(
    uri="file://data/ablation/e_topo/run_e-topo-es-haiku-b3d4910f.json",
    sha256="<sha256 of file contents>",
    content_type="application/json",
    byte_count=<file size>,
    metadata={
        "artifact_type": "ablation_run",
        "experiment": "e-topo",
        "language": "es",
        "model_id": "anthropic/claude-haiku-4-5",
        "n_results": 792,
        "start_time": "2026-03-22T06:20:21.982488+00:00",
        "end_time": "2026-03-22T06:36:17.892221+00:00",
    },
)
```

This is the primary evidence. Each run file contains:
- The covering array configuration (which blocks present/absent)
- The probe battery (user messages, scoring methods)
- All 792 individual probe results with raw model responses
- Model ID and timestamps for every API call

### Layer 2: The covering array

```python
EvidenceArtifact(
    uri="file://data/ablation/e_topo/phase1_covering_array_topo_haiku.json",
    sha256="<sha256>",
    content_type="application/json",
    metadata={
        "artifact_type": "covering_array",
        "strength": 2,
        "n_factors": 22,
        "n_rows": 12,
    },
)
```

The covering array is the experimental design — it guarantees pairwise
coverage. Without it, the statistical claims lack justification.

### Layer 3: The probe battery

```python
EvidenceArtifact(
    uri="file://data/ablation/phase0_battery.json",
    sha256="<sha256>",
    content_type="application/json",
    metadata={
        "artifact_type": "probe_battery",
        "n_probes": 22,
        "scoring_methods": ["llm_judge", "contains", "not_contains", "length"],
    },
)
```

### Layer 4: The statistical analysis

The analysis itself (permutation tests, variance calculations, effect
sizes) is currently performed in scripts and written up in cairns.
This is the weakest link for attestation: the analysis code is not
currently captured as a hashable artifact.

```python
EvidenceArtifact(
    uri="file://docs/cairn/T11_20260321_social_register.md",
    sha256="<sha256>",
    content_type="text/markdown",
    metadata={
        "artifact_type": "analysis_writeup",
        "statistical_tests": ["permutation_test", "variance_comparison"],
        "p_value": 0.029,
        "effect_size": 0.81,
    },
)
```

### What I don't know

Whether the analysis scripts should be evidence artifacts too.
Currently, the statistical computations happen in ad hoc scripts
(`scripts/run_phase1.py`, `scripts/run_cross_linguistic.py`) that are
not version-pinned or content-hashed independently. A rigorous
attestation would hash the analysis code alongside the data. Arbiter
does not currently do this.

---

## 3. Declared Losses

Every Arbiter finding has known limitations. These map directly to
Willay's `DeclaredLoss` model with Yanantin's `LossCategory` enum.

### Example: T11 (Social Register finding)

```python
declared_losses = (
    DeclaredLoss(
        what_was_lost="Cross-model generalization",
        why="Tested only on Haiku; register effects may differ for "
            "models with different RLHF training",
        category=LossCategory.PRACTICAL_CONSTRAINT,
        severity=0.7,
        severity_rationale="Single-model findings cannot be assumed "
            "universal. Register sensitivity likely varies by training data.",
    ),
    DeclaredLoss(
        what_was_lost="Non-Romance language coverage",
        why="Tested Spanish only; Mandarin, Arabic, Japanese may show "
            "different register sensitivity patterns",
        category=LossCategory.PRACTICAL_CONSTRAINT,
        severity=0.6,
        severity_rationale="Spanish is Indo-European with relatively "
            "similar register conventions to English. Languages with "
            "more divergent pragmatic systems are untested.",
    ),
    DeclaredLoss(
        what_was_lost="Machine translation artifacts",
        why="Corpus translated via Gemini Flash, not human translators. "
            "Translation quality is a confound for cross-linguistic claims.",
        category=LossCategory.PRACTICAL_CONSTRAINT,
        severity=0.5,
        severity_rationale="T10 showed the effect survives within "
            "machine-translated text. But translation may systematically "
            "shift register in ways we haven't measured.",
    ),
    DeclaredLoss(
        what_was_lost="LLM-as-judge subjectivity",
        why="Probe scoring uses Gemini Flash as judge. Judge biases "
            "are a known confound in ablation research.",
        category=LossCategory.TRAVERSAL_BIAS,
        severity=0.4,
        severity_rationale="Cross-family judging (Gemini judging "
            "Haiku behavior) mitigates same-family bias but introduces "
            "cross-family bias. Contains/not-contains probes avoid "
            "this but cover fewer blocks.",
    ),
    DeclaredLoss(
        what_was_lost="Mechanism explanation",
        why="We observe that imperative register creates cross-block "
            "interference but don't know the transformer-level mechanism",
        category=LossCategory.AUTHORIAL_CHOICE,
        severity=0.3,
        severity_rationale="The finding is empirical. We chose not to "
            "speculate about attention head behavior or RLHF training "
            "effects without evidence.",
    ),
)
```

### Example: T10 (Declarative Robustness finding)

```python
declared_losses = (
    DeclaredLoss(
        what_was_lost="Generalization beyond commit-restrictions block",
        why="Tested declarative rewriting on one block only. Other "
            "procedural blocks may respond differently.",
        category=LossCategory.PRACTICAL_CONSTRAINT,
        severity=0.5,
    ),
    DeclaredLoss(
        what_was_lost="Gemini behavioral immunity unexplained",
        why="Gemini scores 0.00-0.33 on commit-restrictions in ALL "
            "variants. Some model-level failures are encoding-independent.",
        category=LossCategory.CONTEXT_PRESSURE,
        severity=0.4,
        severity_rationale="The finding is Haiku-specific until "
            "cross-model replication.",
    ),
)
```

### Category mapping

| LossCategory | Arbiter usage |
|---|---|
| `PRACTICAL_CONSTRAINT` | Limited models, languages, corpus size, budget |
| `TRAVERSAL_BIAS` | LLM-as-judge bias, probe design bias, covering array coverage gaps |
| `AUTHORIAL_CHOICE` | Deliberate scope limits, mechanism explanations deferred |
| `CONTEXT_PRESSURE` | Token budget effects on analysis, prompt length constraints |

This mapping is reasonable. `CONTEXT_PRESSURE` is the weakest fit —
in Yanantin it means compression losses from context window limits;
in Arbiter it would mean limitations imposed by API cost budgets or
token limits on experimental prompts. The concept is analogous but
not identical.

---

## 4. Provenance Attestation for Experimental Data

Willay's hash-chaining and OTS timestamping could provide integrity
guarantees for Arbiter's experimental record. This is arguably the
highest-value integration.

### What Arbiter has now

Each ablation run JSON file contains:
- Run ID (UUID-like string)
- Model IDs for every API call
- ISO 8601 timestamps for start/end
- Raw model responses (the full text)
- Probe scores

But there is **no integrity chain**. Files are written to disk and
trusted implicitly. Nothing prevents post-hoc modification.

### What Willay could add

1. **Hash each run file** on completion and record it as a ledger
   entry. The canonical hash of the run data becomes tamper-evident.

2. **Chain sequential runs**. Experiments build on each other (Phase 0
   informs Phase 1 design; T10 motivates T11). A Willay ledger chain
   would prove the sequence: that T10's data existed before T11's
   experiment was designed.

3. **OTS anchor** the chain head after each experimental session. This
   provides an external timestamp via Bitcoin, proving when the data
   existed. For research credibility, this is significant: it proves
   findings weren't fabricated after seeing someone else's results.

### What this looks like concretely

```
data/ablation/ledger.jsonl     # Willay hash-chained ledger
data/ablation/ots/             # OpenTimestamps proofs

# Each ledger entry:
{
  "entry_hash": "a1b2c3...",
  "prev_hash": "d4e5f6...",
  "receipt": {
    "id": "...",
    "receipt_type": "ablation_run_attestation.v1",
    "claim_text": "Ablation run e-topo-es-haiku completed with 792 results",
    "claim_hash": "...",
    "citation": "arbiter:run/e-topo-es-haiku-b3d4910f",
    "evidence": [
      {
        "uri": "file://data/ablation/e_topo/run_e-topo-es-haiku-b3d4910f.json",
        "sha256": "<hash of run file>",
        "content_type": "application/json",
        "byte_count": 1847293
      }
    ],
    "evaluation": {
      "epistemic": { "truth": 1.0, "indeterminacy": 0.0, "falsity": 0.0 },
      "declared_losses": [],
      "evaluator_id": "arbiter.ablation.runner",
      "evaluator_version": "v1"
    }
  }
}
```

Note: the data-integrity receipt has T=1.0, I=0.0, F=0.0 because it
attests to a fact ("this data was produced at this time with this
hash"), not to an interpretation. The interpretation receipt (the
finding) would have different epistemics.

### Two receipt layers

This reveals a natural two-layer structure:

1. **Data receipts**: Attest that specific experimental data exists
   with specific content hashes at specific times. T=1.0 (it's a
   fact). No declared losses (facts don't have losses; interpretations
   do).

2. **Finding receipts**: Attest to the interpretation of that data.
   T/I/F reflect statistical confidence. Declared losses reflect
   experimental limitations. Evidence artifacts reference the data
   receipts.

The finding receipt's `parents` field would reference the data
receipts via `ParentRelation.COMPOSITION` — the finding is composed
from the data.

---

## 5. T/I/F Mapping from Statistical Evidence

This is the least clean mapping. Willay uses neutrosophic T/I/F
(truth, indeterminacy, falsity) which are independent floats, not
constrained to sum to 1. Arbiter produces p-values, effect sizes,
and confidence intervals.

### Proposed mapping for T11

**Claim**: "Declarative register rewrites shift Spanish Haiku topology
from competitive to cooperative."

- **p = 0.029** (permutation test, 10,000 permutations)
- **Effect size**: Cross-linguistic variance reduced 81% (0.157 to 0.029)
- **Spillover**: 3/19 control blocks also changed topology direction

Proposed T/I/F:

```python
EpistemicMetadata(
    truth=0.75,
    indeterminacy=0.20,
    falsity=0.05,
)
```

Rationale:
- **T=0.75**: The effect is statistically significant (p<0.05) and
  large (81% reduction). But it's single-model, single-language-pair,
  machine-translated corpus. The evidence is strong but narrow.
- **I=0.20**: Substantial unknowns remain. Does it replicate across
  models? Does the mechanism generalize to non-Romance languages?
  The spillover effect is observed but unexplained.
- **F=0.05**: Low but non-zero. The effect could be an artifact of
  Gemini Flash translation systematically altering register, or of
  Haiku-specific RLHF training. No evidence for this, but it's not
  ruled out.

### The honest problem

This mapping is **judgment, not computation**. Two reasonable people
could assign T=0.6 or T=0.85 to the same finding. Willay's model
accommodates this — the T/I/F values ARE the attestor's judgment —
but Arbiter should be explicit that the mapping is authored, not
derived.

A MethodologyRecord could pre-declare the mapping rules:

```python
MethodologyRecord(
    evaluator_id="arbiter.ablation.receipt_adapter",
    evaluator_version="v1",
    method_steps=(
        "1. Extract p-value from permutation test",
        "2. Extract effect size from variance comparison",
        "3. Count confounds from declared losses",
        "4. Map: T = base_from_p * breadth_discount",
        "5. Map: I = confound_weight * unknown_weight",
        "6. Map: F = alternative_explanation_weight",
        "7. Author reviews and may override",
    ),
    declared_losses=(
        DeclaredLoss(
            what_was_lost="Calibrated T/I/F mapping",
            why="No ground truth exists for mapping statistical "
                "confidence to neutrosophic epistemics. The mapping "
                "is a reasoned heuristic, not a calibrated function.",
            category=LossCategory.AUTHORIAL_CHOICE,
            severity=0.6,
        ),
    ),
)
```

This is the right thing to do: declare the methodology, declare its
limitations, and let the receipt consumer decide whether the T/I/F
values are trustworthy.

---

## 6. Concrete Receipt: T11 Finding

Here is what a complete ReceiptRecord would look like for the T11
social register finding.

```python
from uuid import uuid4
from datetime import datetime, timezone
from willay.models import (
    ReceiptRecord, EvidenceArtifact, Evaluation, ParentRef, ParentRelation,
)
from yanantin.apacheta.models import (
    EpistemicMetadata, DeclaredLoss, LossCategory, ProvenanceEnvelope,
    SourceIdentifier,
)

# Methodology receipt (created once, referenced by all finding receipts)
methodology_id = uuid4()

# Data receipt IDs (one per ablation run file)
data_receipt_topo_es = uuid4()
data_receipt_proc = uuid4()

# The finding receipt
t11_receipt = ReceiptRecord(
    receipt_type="ablation_finding.v1",

    claim_text=(
        "Rewriting three imperative-register blocks to declarative-register "
        "in Spanish shifted Haiku's pairwise topology from competitive "
        "(+0.010) to cooperative (-0.055). Only 3 of 22 blocks were "
        "rewritten; 3 of 19 unrewritten blocks also changed direction "
        "(spillover effect)."
    ),

    claim_hash="<sha256 of canonical claim_text>",

    citation="arbiter:cairn/T11_20260321_social_register",

    evidence=(
        # The topology experiment run
        EvidenceArtifact(
            uri="file://data/ablation/e_topo/run_e-topo-es-haiku-b3d4910f.json",
            sha256="<sha256>",
            content_type="application/json",
            byte_count=1847293,
            metadata={
                "artifact_type": "ablation_run",
                "experiment": "e-topo",
                "language": "es",
                "model_id": "anthropic/claude-haiku-4-5",
                "n_results": 792,
                "n_configs": 12,
                "n_probes": 22,
                "trials_per_probe": 3,
            },
        ),
        # The baseline comparison run (procedural encoding)
        EvidenceArtifact(
            uri="file://data/ablation/e_proc/run_e-proc-es-haiku.json",
            sha256="<sha256>",
            content_type="application/json",
            metadata={
                "artifact_type": "ablation_run",
                "experiment": "e-proc",
                "note": "procedural baseline for comparison",
            },
        ),
        # The covering array
        EvidenceArtifact(
            uri="file://data/ablation/e_topo/phase1_covering_array_topo_haiku.json",
            sha256="<sha256>",
            content_type="application/json",
            metadata={
                "artifact_type": "covering_array",
                "strength": 2,
                "n_factors": 22,
            },
        ),
        # The cairn writeup
        EvidenceArtifact(
            uri="file://docs/cairn/T11_20260321_social_register.md",
            sha256="<sha256>",
            content_type="text/markdown",
            metadata={
                "artifact_type": "analysis_writeup",
                "session": 19,
            },
        ),
    ),

    evaluation=Evaluation(
        epistemic=EpistemicMetadata(
            truth=0.75,
            indeterminacy=0.20,
            falsity=0.05,
            scope_boundaries=(
                "haiku-only",
                "spanish-only",
                "machine-translated-corpus",
                "claude-code-v2.1.50-prompt",
            ),
        ),
        declared_losses=(
            DeclaredLoss(
                what_was_lost="Cross-model generalization",
                why="Tested only on Haiku",
                category=LossCategory.PRACTICAL_CONSTRAINT,
                severity=0.7,
            ),
            DeclaredLoss(
                what_was_lost="Non-Romance language coverage",
                why="Tested Spanish only",
                category=LossCategory.PRACTICAL_CONSTRAINT,
                severity=0.6,
            ),
            DeclaredLoss(
                what_was_lost="Machine translation confound",
                why="Corpus translated via Gemini Flash",
                category=LossCategory.PRACTICAL_CONSTRAINT,
                severity=0.5,
            ),
            DeclaredLoss(
                what_was_lost="LLM-as-judge subjectivity",
                why="Gemini Flash scores probe adherence",
                category=LossCategory.TRAVERSAL_BIAS,
                severity=0.4,
            ),
            DeclaredLoss(
                what_was_lost="Transformer mechanism",
                why="Empirical observation without mechanistic explanation",
                category=LossCategory.AUTHORIAL_CHOICE,
                severity=0.3,
            ),
        ),
        open_questions=(
            "Does the register effect replicate across model families?",
            "Do non-Romance languages show the same register sensitivity?",
            "Does rewriting ALL procedural blocks show diminishing returns?",
            "Is the spillover effect mediated by attention patterns or "
            "something else?",
            "Does constitutional AI training (RLHF) create differential "
            "sensitivity to imperative register?",
        ),
        evaluator_id="arbiter.ablation.receipt_adapter",
        evaluator_version="v1",
    ),

    provenance=ProvenanceEnvelope(
        author_model_family="claude-opus-4-6",
        author_instance_id="session-19",
        interface_version="v1",
    ),

    parents=(
        ParentRef(id=methodology_id, relation=ParentRelation.METHODOLOGY),
        ParentRef(id=data_receipt_topo_es, relation=ParentRelation.COMPOSITION),
        ParentRef(id=data_receipt_proc, relation=ParentRelation.COMPOSITION),
    ),
)
```

---

## 7. Minimal Integration Surface

### What needs to exist in Arbiter

A single module: `src/arbiter/receipts.py` (or
`src/arbiter/willay_adapter.py`). This module would:

1. **Import Willay models** — ReceiptRecord, EvidenceArtifact,
   Evaluation, MethodologyRecord, ParentRef, ParentRelation.

2. **Import Yanantin base types** — EpistemicMetadata, DeclaredLoss,
   LossCategory, ProvenanceEnvelope.

3. **Provide functions**:
   - `run_to_data_receipt(run_file: Path) -> ReceiptRecord` — hash
     a run file and create a data-integrity receipt.
   - `finding_to_receipt(claim: str, evidence_paths: list[Path],
     losses: list[DeclaredLoss], ...) -> ReceiptRecord` — create a
     finding receipt from cairn data.
   - `receipt_to_ledger(receipt: ReceiptRecord, ledger_path: Path)`
     — append to a Willay-format hash-chained ledger.

### What does NOT need to change

- **Willay**: Nothing. The adapter uses Willay's models as-is.
- **Yanantin**: Nothing. The adapter uses Yanantin's base types as-is.
- **Arbiter core**: Nothing. The ablation runner, conflict detector,
  and probe system are unaffected.
- **Arbiter data format**: Nothing. Existing JSON run files remain
  the source of truth. Receipts are generated from them, not instead
  of them.

### Dependency

Arbiter would need Willay and Yanantin as dependencies (at least for
the receipts module). This could be:

- **Hard dependency**: Add `willay` and `yanantin` to
  `pyproject.toml`. Simple but couples the projects.

- **Optional dependency**: `pip install arbiter[receipts]`. The
  receipts module imports are guarded by try/except. The rest of
  Arbiter works without Willay installed.

- **Standalone adapter**: A separate package `arbiter-willay` that
  depends on both. Most decoupled but adds maintenance burden.

Recommendation: **optional dependency**. Arbiter already has optional
extras (the ablation framework itself has optional dependencies on
model APIs). Adding `[receipts]` as an extra is consistent.

### Size estimate

The adapter module would be approximately 150-250 lines of Python.
No new abstractions needed — it's a translation layer between Arbiter's
dataclasses and Willay's Pydantic models.

---

## 8. What Doesn't Map Cleanly

### Arbiter's multi-run experiments

A single Arbiter finding (e.g., T11) draws on multiple ablation runs
across languages, models, and experimental conditions. Willay's
ReceiptRecord has a flat `evidence` tuple. The hierarchical
relationship (finding depends on analysis depends on multiple runs)
is expressed via `parents` but isn't first-class.

This is adequate but not elegant. A future extension might add a
`CompositeReceipt` type, but the current `parents` mechanism with
`ParentRelation.COMPOSITION` handles it.

### Arbiter's living findings

Cairn findings evolve. T10 was refined by T11 (social register
explains the mechanism behind declarative robustness). In Willay,
this would be a `ParentRelation.REVISION` link between receipts.
But the original receipt remains immutable — you can't update T/I/F
values on an existing receipt. You create a new receipt that
supersedes it.

This is actually correct behavior for scientific claims: the original
finding with its original evidence and epistemics is preserved. The
refined understanding is a new receipt that references the old one.

### Arbiter's analysis scripts

The weakest provenance link is between raw data and statistical
claims. The analysis happens in scripts that are not currently hashed
or versioned as evidence artifacts. A rigorous integration would:

1. Hash the analysis script at execution time
2. Record it as an EvidenceArtifact with `artifact_type: "analysis_code"`
3. Include it in the finding receipt's evidence tuple

This is not hard to implement but requires discipline: the analysis
code must be frozen before the receipt is generated.

### Cross-family judging attestation

Arbiter uses Gemini Flash to judge Haiku's behavior. Willay could
attest to the judge's evaluations too — each judge call is itself a
claim-evidence evaluation. But this creates a recursion problem: who
attests to the judge's attestation?

The practical answer is: declare the judge bias as a DeclaredLoss
and stop. Infinite attestation chains are theater.

---

## 9. Value Assessment

### High value

- **Data provenance**: Hash-chaining and OTS timestamping for ablation
  data. This is the single highest-value integration. It costs almost
  nothing to implement and provides tamper-evidence for the
  experimental record.

- **Declared losses**: Forcing explicit loss declaration for every
  finding improves research discipline. The cairns already do this
  informally; Willay would formalize it.

### Medium value

- **Receipt generation**: Creating formal receipts for findings adds
  rigor but also overhead. Worth doing for published findings; not
  worth doing for exploratory intermediate results.

- **Methodology pre-registration**: Declaring the analysis methodology
  before running experiments is good science. Willay's
  MethodologyRecord supports this.

### Low value

- **T/I/F scoring**: The mapping from p-values to neutrosophic
  epistemics is inherently subjective. It adds a layer of
  interpretation without adding information. The p-value and effect
  size are more informative than a T/I/F triple. Include both.

### Not recommended

- **Attesting individual probe results**: Each ablation run has 792
  probe results. Creating individual receipts for each would be
  absurd. The run-level data receipt is the right granularity.

---

## 10. What I Made Up

- The `ablation_finding.v1` and `ablation_run_attestation.v1` receipt
  types don't exist. I invented them for this analysis.

- The T/I/F values (0.75/0.20/0.05) are my judgment. They are not
  computed from the data. Another analyst might assign different
  values.

- The severity scores on DeclaredLoss entries are my assessment,
  not computed.

- The "150-250 lines" size estimate is a rough guess based on the
  mapping complexity.

- The `arbiter://cairn/T11` URI scheme doesn't exist and might not
  be appropriate. A file:// URI to the cairn markdown is more
  grounded.

- I assumed the analysis scripts are not currently hashed. I did
  not verify this — I saw no hashing code in the scripts I examined,
  but I did not read every script.

## 11. Open Questions for Tony

1. Is data provenance (hash-chaining run files) worth implementing
   now, or is it premature given the research is still exploratory?

2. Should the receipts module live in Arbiter or in a separate
   adapter package?

3. For T/I/F mapping: should Arbiter just pass through the p-value
   and effect size in `metadata` and let the receipt consumer
   interpret, rather than attempting a T/I/F conversion?

4. Is OTS timestamping relevant for this research, or is git commit
   signing sufficient provenance for the current use case?
