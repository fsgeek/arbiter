# Tensor Extension Spec v0

Date: 2026-03-10  
Status: Draft for implementation

## 1. Objective

Extend Arbiter's interference tensor from scalar conflict scoring to a
context-aware adjudication representation:

- retain current score/severity compatibility,
- add neutrosophic-style adjudication dimensions (`T`, `I`, `F`),
- add structured declared losses,
- support deterministic tier-gated routing (`accept/clarify/rewrite/reject`).

This is a representation transfer for normative adjudication, not a
claim that epistemic and normative truth are identical.

## 2. Current State (as of commit `e51cd61`)

Existing model:
- `TensorEntry(block_a, block_b, rule, score, severity, explanation?)`
- stored in `src/arbiter/interference_tensor.py`

Limitations:
- scalar `score` collapses distinct failure modes,
- no explicit indeterminacy channel,
- no machine-parseable reason for adjudication limits,
- no direct representation of tier/canon context.

## 3. Proposed Data Model

## 3.1 New Enums

- `AdjudicationDecision`: `accept | clarify | rewrite | reject`
- `DrafterIdentity`: `provider | operator | user | unknown`

## 3.2 Declared Loss

```python
class DeclaredLoss(BaseModel):
    what: str
    why: str
    severity: float = Field(ge=0.0, le=1.0)
```

## 3.3 Extended Tensor Entry

```python
class TensorEntryV2(BaseModel):
    # Backward-compatible core
    block_a: str
    block_b: str
    rule: str
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str | None = None

    # New adjudication channels
    t: float = Field(ge=0.0, le=1.0)
    i: float = Field(ge=0.0, le=1.0)
    f: float = Field(ge=0.0, le=1.0)

    # Context and governance
    tier_a: Tier | None = None
    tier_b: Tier | None = None
    scope_tags: list[str] = Field(default_factory=list)
    canon_tags: list[str] = Field(default_factory=list)
    drafter_identity: DrafterIdentity = DrafterIdentity.unknown
    evidence_quality: float = Field(default=0.5, ge=0.0, le=1.0)

    # Loss channel
    declared_losses: list[DeclaredLoss] = Field(default_factory=list)

    # Routing output
    decision: AdjudicationDecision | None = None
```

Notes:
- No hard constraint that `t + i + f = 1.0`.
- Compatibility mode can set:
  - `f = score`,
  - `i = 1 - evidence_quality`,
  - `t = max(0, 1 - max(f, i))`.

## 4. Decision Policy Interface

```python
class DecisionPolicy(Protocol):
    def decide(self, entry: TensorEntryV2) -> AdjudicationDecision: ...
```

Initial deterministic routing (default policy):
- `reject` if `f >= tau_reject` and tier conflict crosses higher-precedence boundary,
- `clarify` if `i >= tau_clarify` in high-risk scopes,
- `rewrite` if `f` or `i` moderate and rewrite is feasible,
- `accept` otherwise.

Policy inputs must include:
- tier precedence,
- canon application trace,
- drafter identity when ambiguity-against-drafter is enabled.

## 5. Serialization and Migration

## 5.1 JSON Format Strategy

- Keep existing `InterferenceTensor` serialization stable.
- Introduce versioned payload:
  - `schema_version: 2`
  - `entries_v2: [...]`
- During transition, write both `entries` (v1) and `entries_v2` when requested.

## 5.2 Migration Helper

Provide `to_v2()` conversion from v1 tensors:
- deterministic field mapping,
- explicit `migration_notes` in output metadata,
- no lossy removal of v1 fields.

## 6. Validation Requirements

Unit tests (minimum):
1. `TensorEntryV2` field validation and bounds.
2. v1 -> v2 migration determinism.
3. decision policy determinism for fixed thresholds.
4. serialization round trip with mixed v1/v2 modes.
5. declared loss schema validation.

Behavioral tests:
1. scalar-collapse fixtures where v1 ties but v2 separates via losses.
2. persistent-high-I criterion check:
   - `I >= tau_I` after `N_min`,
   - `|delta I| < epsilon` for `k` consecutive passes,
   - allowed canon/context mutations do not push below `tau_I`.

## 7. Implementation Plan (Phased)

Phase 1: schema scaffolding
- add v2 models and migration helper,
- keep current evaluator output unchanged.

Phase 2: evaluator enrichment
- emit provisional `t/i/f`, context tags, and declared losses,
- retain v1 output for compatibility.

Phase 3: routing integration
- add deterministic decision policy,
- expose policy thresholds in config/CLI.

Phase 4: benchmark and ablation
- run scalar-only vs tensor+loss channels on `benchmark_v0`,
- report discrimination-gain and error/recovery metrics.

## 8. Open Questions

1. Should `t/i/f` be rule-specific only, or include aggregated per-pair fields?
2. Should declared losses be generated per entry or per adjudication batch?
3. Do we need a canonical loss taxonomy or free text + embedding clustering?
4. How should `unknown` drafter identity interact with ambiguity-against-drafter?

## 9. Out of Scope for v0 Spec

- Full legal-style precedent engine,
- panel/court orchestration runtime,
- integration-specific behavior under external compaction pipelines.
