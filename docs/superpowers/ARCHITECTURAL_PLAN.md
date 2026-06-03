# Arbiter Platform: Complete Architectural Plan (Phases 0.5-4)

## Executive Summary

Phased platform buildout:
- **Phase 0.5 (Quick Win):** Conflict analyzer for agentic prompts. Ships first, builds traction and data.
- **Phase 0 (Foundation):** System DSL + formal verification. Core governance capability.
- **Phase 1 (Security, parallel with Phase 2):** PromptGuard — injection/adversarial detection.
- **Phase 2 (Governance, parallel with Phase 1):** Governance Platform + Batch Audit + Willay attestations.
- **Phase 3 (Enforcement):** Safety Gate — CI/CD integration for production enforcement.
- **Phase 4 (Ecosystem):** Composition Marketplace — blocks with verified compliance.

**Key principle:** Each phase is additive, not breaking. No architectural lock-in.

---

## Phase Timeline & Dependencies

```
Phase 0.5 (Weeks 1-4)
  ↓
  ├─→ Phase 0 (Weeks 5-12) [Foundation]
  │    ↓
  │    ├─→ Phase 1 (Weeks 8-14) [Security, parallel]
  │    │
  │    └─→ Phase 2 (Weeks 8-16) [Governance, parallel]
  │         ↓
  │         └─→ Phase 3 (Weeks 17-22) [Enforcement]
  │              ↓
  │              └─→ Phase 4 (Weeks 23+) [Marketplace]
  │
  └─→ Early customer traction (Phase 0.5)
       → feeds Phase 0 design
       → funds Phase 1-2 development
```

**Critical path:**
1. Phase 0.5 ships → get customers + data
2. Phase 0 ships → existing customers formalize governance
3. Phases 1-2 ship → additional capabilities for existing customers
4. Phase 3 ships → upsell enforcement to engaged customers
5. Phase 4 ships → network effects + ecosystem lock-in

---

## Shared Infrastructure (All Phases)

```
┌─────────────────────────────────────────────────────┐
│                    API Gateway                      │
│         (FastAPI / Rust Axum / similar)             │
├─────────────────────────────────────────────────────┤
│                 Data Persistence                    │
│      (PostgreSQL + cloud storage for artifacts)     │
├─────────────────────────────────────────────────────┤
│              Authentication & Org Mgmt              │
│         (user/org/team management, RBAC)            │
├─────────────────────────────────────────────────────┤
│           Arbiter Analysis Engine                   │
│  (structural analysis, decomposition, evaluation)   │
├─────────────────────────────────────────────────────┤
│            Monitoring & Observability               │
│      (logging, metrics, analytics, tracing)         │
├─────────────────────────────────────────────────────┤
│         External Integrations (pluggable)           │
│  (TLA+/Z3, OPA, Willay, PromptGuard, etc)          │
└─────────────────────────────────────────────────────┘
```

Each phase adds capabilities on top of this foundation; nothing breaks existing layers.

---

## Core Data Model: The Analysis Object

Every phase enriches the same `Analysis` object. This is why there's no lock-in.

```typescript
Analysis {
  id: UUID
  created_at: timestamp

  // Input (set in Phase 0.5)
  prompt: {
    text: string
    hash: SHA256
    source: string // "claude-code", "react-agent", "tool-use", etc.
    metadata: {
      model: string
      agent_type: string
      environment: "development" | "production"
      tags: [string]
    }
  }

  // Phase 0.5: Structural Analysis
  structural: {
    conflicts: Conflict[]
    score: float (0.0-1.0)
    tensor: InterferenceTensor (JSON)
    executed_at: timestamp
  }

  // Phase 0: Formal Verification
  formal: null | {
    system_spec_id: UUID
    domain_spec_id: UUID | null
    verification_result: "consistent" | "inconsistent" | "timeout"
    proof: string (TLA+ output)
    formal_score: float
    verified_at: timestamp
  }

  // Phase 1: Security Analysis
  security: null | {
    injection_vulnerabilities: Vulnerability[]
    adversarial_score: float
    promptguard_results: PromptGuardResult
    scanned_at: timestamp
  }

  // Phase 2: Governance & Attestation
  governance: null | {
    spec_compliance: {
      system_tier: "compliant" | "violation" | "indeterminate"
      domain_tier: "compliant" | "violation" | "indeterminate"
    }
    attestation_id: UUID // Willay
    reviewed_by: string
    approved_at: timestamp
    approved: boolean
  }

  // Phase 3: Enforcement
  enforcement: null | {
    enforced_at: timestamp
    enforced_by: string
    enforce_action: "approve" | "quarantine" | "block" | "review"
    override_reason: string | null
  }

  // Phase 4: Marketplace
  marketplace: null | {
    block_id: UUID
    block_version: string
    certification_status: "verified" | "pending" | "rejected"
    certified_at: timestamp
  }
}

Conflict {
  id: UUID
  type: string // "priority_ambiguity", "scope_overlap", "contradiction", etc.
  severity: "critical" | "high" | "medium" | "low"
  block_a: PromptBlock
  block_b: PromptBlock
  evidence: string
}
```

**Why this scales:**
- Each phase adds optional fields (null-safe)
- No breaking changes to existing fields
- Phases can work independently (e.g., Phase 1 doesn't require Phase 0)
- Data relationships are clear and auditable

---

## API Evolution (Additive, No Breaking Changes)

### Phase 0.5: Structural Analysis

```
POST /v1/analyze
  Input: { prompt: string, agent_type?: string, metadata?: {...} }
  Output: Analysis { prompt, structural, formal:null, security:null, ... }

GET /v1/analyses/:id
  Returns: Analysis object

GET /v1/analyses
  Returns: [Analysis] (user's history)

POST /v1/analyses/:id/save
  Saves analysis + metadata
```

### Phase 0: Formal Verification (Additive)

```
POST /v1/specs
  Create system/domain specifications

POST /v1/specs/:id/verify
  Verify spec consistency (TLA+/Z3)

POST /v1/analyze?include_formal=true
  Enriches Phase 0.5 results with formal verification
  Returns: Analysis { ..., formal: {...} }
```

### Phase 1: Security (Additive, Independent)

```
POST /v1/scan
  PromptGuard scanning for injection/adversarial attacks

POST /v1/analyze?include_security=true
  Enriches Phase 0.5 results with security analysis
  Returns: Analysis { ..., security: {...} }
```

### Phase 2: Governance Platform (Additive)

```
POST /v1/batch-analyze
  Corpus analysis (100s of prompts)

POST /v1/attestations
  Willay attestation integration

POST /v1/analyze?include_governance=true
  Enriches with governance compliance
  Returns: Analysis { ..., governance: {...} }
```

### Phase 3: Enforcement (Additive)

```
POST /v1/enforce
  CI/CD hook for pre-deployment checks
  Ingests Analysis, checks governance, returns enforcement action

POST /v1/analyze?include_enforcement=true
  Enriches with enforcement decision
  Returns: Analysis { ..., enforcement: {...} }
```

### Phase 4: Marketplace (Additive)

```
GET /v1/marketplace/blocks
  Searchable registry of verified blocks

GET /v1/analyze?include_marketplace=true
  Enriches with marketplace certification data
  Returns: Analysis { ..., marketplace: {...} }
```

**Key property:** All endpoints are backwards compatible. Old clients that don't request `?include_formal` still work. New clients can request multiple analyses with different enrichment layers.

---

## Data Flow: How Phases Feed Each Other

```
Phase 0.5: Analyze Prompt
    ↓
    └─→ Store Analysis (structural)

        Phase 0: Formalize
            ↓
            └─→ Add formal verification to Analysis

                Phases 1-2 (Parallel):

                    Phase 1: Security Scan
                        ↓
                        └─→ Correlate security findings with Phase 0.5 conflicts

                    Phase 2: Governance
                        ↓
                        └─→ Use Phase 0.5 data to guide spec creation
                        └─→ Attest Phase 0 formal verification (Willay)

                Phase 3: Enforcement
                    ↓
                    └─→ Use Phase 2 specs + attestations
                    └─→ Check compliance
                    └─→ Enforce at deployment time

                Phase 4: Marketplace
                    ↓
                    └─→ Use all prior analysis layers
                    └─→ Mark blocks as "conflict-free", "formally verified", "security-scanned", etc.
```

**Critical:** Each phase reads from the Analysis object and adds its own layer. Phases are *composable*, not sequential.

---

## Deployment Options

### Option A: Monolithic (All phases together)
- Single platform with all features
- Team manages unified service
- Customers see all capabilities

### Option B: Modular Microservices (Recommended for scale)
- Phase 0.5 API (lightweight, fast)
- Phase 0 verification backend (TLA+/Z3)
- Phase 1 security scanner (PromptGuard)
- Phase 2 governance platform (web UI + batch)
- Phase 3 enforcement hooks (CI/CD)
- Phase 4 marketplace (registry)
- All share: PostgreSQL, auth, observability

### Option C: Hybrid (Recommended for Phase 0.5→1)
- Phase 0.5 + 0 as monolith (tight coupling is OK early)
- Phase 1-2-3-4 as separate services that call Phase 0.5

---

## Why This Architecture Doesn't Lock Us In

1. **Phases are independent:**
   - Phase 1 (PromptGuard) can ship without Phase 0 (formal verification)
   - Phase 0 customers can skip Phase 1 (security is orthogonal to governance)
   - Phase 3 (enforcement) works with or without Phase 2 (governance)

2. **Data model is extensible:**
   - New fields added as `null` (backwards compatible)
   - Old analyses still work with new phases
   - No migration of existing data required

3. **API is additive:**
   - New endpoints don't break old clients
   - Optional query parameters (`?include_formal`) enable opt-in
   - Clients can request any combination of analyses

4. **Components are pluggable:**
   - TLA+/Z3 can be replaced with different formal backend
   - OPA can be swapped for different policy language
   - Willay can be replaced with different attestation service
   - Each integration is isolated, not baked into core

5. **Data ownership is clear:**
   - Each phase owns its output fields in Analysis
   - Phases don't depend on each other's implementation details
   - Switching backends for one phase doesn't require rewriting others

---

## Technical Decisions (Locked In By Design)

1. **Shared data model (Analysis object)** — This is the lock-in point. Everything uses it.
2. **PostgreSQL for persistence** — Reliable, proven, allows analytics queries across phases.
3. **API-first design** — All phases are services, not monolithic binaries.
4. **User/org isolation** — Multi-tenant from Phase 0.5 (not added later).
5. **Observability from day 1** — Logging, metrics, tracing on the shared infrastructure.

Everything else is modular and replaceable.

---

## Cost & Scale Story

| Phase | Monthly Cost (First Customer) | Scales To | Rationale |
|-------|-------------------------------|-----------|-----------|
| 0.5 | $0 (server) + infra | 100k analyses/month | Structural analysis is cheap (CPU-bound, no API calls) |
| 0 | +TLA+/Z3 backend | 10k specs verified/month | Formal verification is expensive (solver cost) but used once per spec |
| 1 | +PromptGuard ML | 1M scans/month | Security analysis scales linearly |
| 2 | +Willay API | 10k attestations/month | Attestation is cheap (mostly database) |
| 3 | +CI/CD integrations | 100k deployments/month | Enforcement is cheap (just policy checking) |
| 4 | +Marketplace registry | Unlimited | Registry is cheap (just queries) |

Early phases are cheap to run; later phases add capabilities, not cost.

---

## Next Step

Detailed design and implementation plan for **Phase 0.5** within this architecture.
