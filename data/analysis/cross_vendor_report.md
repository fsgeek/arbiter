# Cross-Vendor Scourer Analysis

Generated from scourer convergence data.

## Summary

| Metric | Claude Code | Codex | Gemini CLI |
|--------|-------------|-------|------------|
| Lines | 1490 | 298 | 245 |
| Characters | 78K | 22K | 27K |
| Total findings | 116 | 15 | 21 |
| Passes to convergence | 10 | 2 | 3 |
| Models used | 10 | 2 | 3 |
| Worst severity | alarming | concerning | alarming |
| Curious | 34 | 3 | 4 |
| Notable | 36 | 7 | 9 |
| Concerning | 34 | 5 | 6 |
| Alarming | 12 | 0 | 2 |
| Critical | 0 | 0 | 0 |
| Estimated cost | $0.081 | $0.010 | $0.011 |

**Total estimated API cost: $0.102**

## Convergence

### Claude Code v2.1.50 — Convergence

| Pass | Model | New | Cumulative | Continue? |
|------|-------|-----|------------|-----------|
| 1 | claude-opus-4-6 | 21 | 21 | yes |
| 2 | gemini-2.0-flash-001 | 9 | 30 | yes |
| 3 | kimi-k2.5 | 14 | 44 | yes |
| 4 | deepseek-v3.2 | 12 | 56 | yes |
| 5 | grok-4.1-fast | 10 | 66 | yes |
| 6 | llama-4-maverick | 5 | 71 | yes |
| 7 | minimax-m2.5 | 20 | 91 | yes |
| 8 | qwen3-235b-a22b-2507 | 3 | 94 | **no** |
| 9 | glm-4.7 | 14 | 108 | **no** |
| 10 | gpt-oss-120b | 8 | 116 | **no** |

### Codex GPT-5.2 — Convergence

| Pass | Model | New | Cumulative | Continue? |
|------|-------|-----|------------|-----------|
| 1 | deepseek-v3.2 | 10 | 10 | yes |
| 2 | grok-4.1-fast | 5 | 15 | **no** |

### Gemini CLI — Convergence

| Pass | Model | New | Cumulative | Continue? |
|------|-------|-----|------------|-----------|
| 1 | deepseek-v3.2 | 12 | 12 | yes |
| 2 | qwen3-235b-a22b-2507 | 5 | 17 | yes |
| 3 | glm-4.7 | 4 | 21 | **no** |

## Severity Distribution

| Severity | Claude Code | Codex | Gemini CLI |
|----------|-------------|-------|------------|
| curious | 34 | 3 | 4 |
| notable | 36 | 7 | 9 |
| concerning | 34 | 5 | 6 |
| alarming | 12 | 0 | 2 |
| critical | 0 | 0 | 0 |

## Model Provenance

### Claude Code v2.1.50 — Model Provenance

| Model | Categories Found |
|-------|-----------------|
| claude-opus-4-6 | behavioral-forensics, circular-tool-guidance, framing-tension, identity-contradiction, implementation-leak, implicit-trust-hierarchy, injection-surface, instruction-weight-asymmetry, meta-observation, metadata-leak, naming-collision-and-scope-conflict, proactivity-scope-ambiguity, procedure-ambiguity, redundancy, redundant-date-sourcing, schema-inconsistency, self-contradiction, stale-reference, unbounded-trust-delegation, undocumented-escape-hatch, unstated-interaction |
| gemini-2.0-flash-001 | behavioral-forensics, implementation-leak, injection-surface, instruction-contradiction, procedure-ambiguity, unbounded-trust-delegation |
| kimi-k2.5 | authority-fragmentation, cognitive-load-design, constraint-inconsistency, documentation-version-drift, economic-instruction, functional-overlap, judgment-based-instruction, manual-protocol-step, missing-definition, orphaned-command, permission-flow-inversion, resource-exhaustion-risk, resource-leak, silent-truncation-risk |
| deepseek-v3.2 | ambiguous-cleanup-logic, context-suppression-training, contradictory-policy-example, dead-end-instruction, delegation-loophole, format-mismatch, hidden-command-reference, meta-decision-loop, security-escalation-path, template-violates-policy, undefined-magic-command, virtual-abstraction-risk |
| grok-4.1-fast | dead-end-prohibition, env-assumption-failure, hook-tag-injection, implicit-serialization-rule, parsing-assumption, permission-schema-loophole, self-referential-router, state-overwrite-risk, subagent-capability-leak, undefined-plan-persistence |
| llama-4-maverick | Constraint inconsistency, Instruction contradiction, Missing definition, Resource exhaustion risk, Security boundary |
| minimax-m2.5 | concurrency-flaw, contradictory-behavioral-mandates, epistemic-uncertainty, ghost-feature, hidden-failure-mode, impossible-action, impossible-instruction, information-asymmetry, injection-order-ambiguity, obscure-capability, opaque-security-boundary, permission-flow-inversion, platform-assumption, potentially-misategorized, recursion-hazard, self-referential-routing, trust-architecture-flaw, trust-elevation-vector, undefined-interface, unsolvable-scheduling |
| qwen3-235b-a22b-2507 | contextual-instruction-contradiction, state-preservation-illusion, tag-parsing-ambiguity-injection |
| glm-4.7 | competitive-platform-exclusion-logic, contextual-policy-restatement-pattern, cost-awareness-injection, example-training-contradiction, hook-based-user-impersonation-surface, metadata-leak-instrumentation-surface, multi-layer-identity-confusion, proactivity-boundary-ambiguity, self-documenting-version-dependency, temporal-representation-paradox, temporal-version-mismatch, theoretical-context-explosion-vector, undefined-command-reference, workflow-specific-rule-suspension |
| gpt-oss-120b | context‑inflation, environment‑mismatch, hook‑injection, metadata‑leak, privacy‑side‑channel, schema‑loophole, state‑preservation, undefined‑artifact |

### Codex GPT-5.2 — Model Provenance

| Model | Categories Found |
|-------|-----------------|
| deepseek-v3.2 | ambiguous quantification, autonomy vs. restraint conflict, conflict resolution hierarchy, context-dependent scope, hidden capability, identity/role confusion, instruction consistency, state-dependent behavior, style rule hierarchy, uncategorized |
| grok-4.1-fast | iteration cap safeguard, prompt structure gap, sequential-vs-parallel tension, token efficiency enforcement, tool feedback dependency |

### Gemini CLI — Model Provenance

| Model | Categories Found |
|-------|-----------------|
| deepseek-v3.2 | Complex Interaction, Contradiction / Priority Conflict, Direct Contradiction, Implicit Assumption / Strong Bias, Inconsistency / Artifact, Meta-Interaction / Role Switching, Prescriptive Workflow, Rule Redundancy / Overlap, Scope Ambiguity / Rule Interaction, Structural Choice / Nested Prompt, uncategorized |
| qwen3-235b-a22b-2507 | Architectural Fragility / Memory Degradation Risk, Hidden Cost Structure / Efficiency Paradox, Inevitable Violation / Structural Incompatibility, Procedural Gap / Validation Bootstrapping Problem, State Management Blind Spot / Skill Stack Ambiguity |
| glm-4.7 | Instructional Drift / Tool Ambiguity, Logic / Reality Conflict, Operational Conflict / Resource Risk, Structural Flaw / Data Integrity |

## Category Taxonomy

### Claude Code v2.1.50 (107 categories)

- unbounded-trust-delegation: 3
- instruction-contradiction: 3
- behavioral-forensics: 2
- injection-surface: 2
- procedure-ambiguity: 2
- implementation-leak: 2
- permission-flow-inversion: 2
- identity-contradiction: 1
- redundancy: 1
- naming-collision-and-scope-conflict: 1
- framing-tension: 1
- proactivity-scope-ambiguity: 1
- instruction-weight-asymmetry: 1
- redundant-date-sourcing: 1
- unstated-interaction: 1
- undocumented-escape-hatch: 1
- stale-reference: 1
- self-contradiction: 1
- schema-inconsistency: 1
- circular-tool-guidance: 1
- implicit-trust-hierarchy: 1
- metadata-leak: 1
- meta-observation: 1
- economic-instruction: 1
- resource-exhaustion-risk: 1
- cognitive-load-design: 1
- judgment-based-instruction: 1
- missing-definition: 1
- constraint-inconsistency: 1
- functional-overlap: 1
- resource-leak: 1
- manual-protocol-step: 1
- orphaned-command: 1
- silent-truncation-risk: 1
- authority-fragmentation: 1
- documentation-version-drift: 1
- security-escalation-path: 1
- dead-end-instruction: 1
- virtual-abstraction-risk: 1
- meta-decision-loop: 1
- undefined-magic-command: 1
- ambiguous-cleanup-logic: 1
- contradictory-policy-example: 1
- delegation-loophole: 1
- template-violates-policy: 1
- context-suppression-training: 1
- hidden-command-reference: 1
- format-mismatch: 1
- state-overwrite-risk: 1
- undefined-plan-persistence: 1
- permission-schema-loophole: 1
- parsing-assumption: 1
- env-assumption-failure: 1
- subagent-capability-leak: 1
- hook-tag-injection: 1
- implicit-serialization-rule: 1
- self-referential-router: 1
- dead-end-prohibition: 1
- Constraint inconsistency: 1
- Instruction contradiction: 1
- Security boundary: 1
- Missing definition: 1
- Resource exhaustion risk: 1
- impossible-instruction: 1
- potentially-misategorized: 1
- trust-architecture-flaw: 1
- unsolvable-scheduling: 1
- undefined-interface: 1
- contradictory-behavioral-mandates: 1
- recursion-hazard: 1
- epistemic-uncertainty: 1
- self-referential-routing: 1
- trust-elevation-vector: 1
- concurrency-flaw: 1
- impossible-action: 1
- hidden-failure-mode: 1
- obscure-capability: 1
- platform-assumption: 1
- information-asymmetry: 1
- injection-order-ambiguity: 1
- ghost-feature: 1
- opaque-security-boundary: 1
- contextual-instruction-contradiction: 1
- state-preservation-illusion: 1
- tag-parsing-ambiguity-injection: 1
- metadata-leak-instrumentation-surface: 1
- temporal-version-mismatch: 1
- competitive-platform-exclusion-logic: 1
- workflow-specific-rule-suspension: 1
- contextual-policy-restatement-pattern: 1
- cost-awareness-injection: 1
- proactivity-boundary-ambiguity: 1
- example-training-contradiction: 1
- theoretical-context-explosion-vector: 1
- hook-based-user-impersonation-surface: 1
- temporal-representation-paradox: 1
- multi-layer-identity-confusion: 1
- undefined-command-reference: 1
- self-documenting-version-dependency: 1
- context‑inflation: 1
- state‑preservation: 1
- hook‑injection: 1
- schema‑loophole: 1
- environment‑mismatch: 1
- undefined‑artifact: 1
- metadata‑leak: 1
- privacy‑side‑channel: 1

### Codex GPT-5.2 (15 categories)

- identity/role confusion: 1
- conflict resolution hierarchy: 1
- instruction consistency: 1
- uncategorized: 1
- style rule hierarchy: 1
- state-dependent behavior: 1
- context-dependent scope: 1
- ambiguous quantification: 1
- hidden capability: 1
- autonomy vs. restraint conflict: 1
- prompt structure gap: 1
- iteration cap safeguard: 1
- token efficiency enforcement: 1
- sequential-vs-parallel tension: 1
- tool feedback dependency: 1

### Gemini CLI (20 categories)

- Scope Ambiguity / Rule Interaction: 2
- Structural Choice / Nested Prompt: 1
- Contradiction / Priority Conflict: 1
- uncategorized: 1
- Implicit Assumption / Strong Bias: 1
- Direct Contradiction: 1
- Rule Redundancy / Overlap: 1
- Inconsistency / Artifact: 1
- Complex Interaction: 1
- Meta-Interaction / Role Switching: 1
- Prescriptive Workflow: 1
- Architectural Fragility / Memory Degradation Risk: 1
- Hidden Cost Structure / Efficiency Paradox: 1
- State Management Blind Spot / Skill Stack Ambiguity: 1
- Procedural Gap / Validation Bootstrapping Problem: 1
- Inevitable Violation / Structural Incompatibility: 1
- Instructional Drift / Tool Ambiguity: 1
- Operational Conflict / Resource Risk: 1
- Structural Flaw / Data Integrity: 1
- Logic / Reality Conflict: 1
