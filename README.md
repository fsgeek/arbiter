# Arbiter

A three-tier evaluation framework for resolving conflicts in LLM-mediated query systems.

## The Problem

When an LLM receives contradictory instructions, it doesn't tell you. It confabulates a reconciliation and moves on, producing output that looks confident but is quietly wrong. Feed it a prompt assembled from multiple sources — some authoritative, some contextual, some untrusted — and it treats them all as undifferentiated text in the context window, smoothing over contradictions rather than surfacing them.

This produces a condition that appears isomorphic to cognitive dissonance: the LLM's output quality degrades in measurable ways when its instructions conflict. Not because it "feels confused" (that's a philosophical question we're not trying to answer here) but because contradictory constraints produce incoherent outputs. This is empirically observable and practically damaging.

The root cause is architectural. There is no standard mechanism for separating instructions by trust level, distinguishing immutable rules from mutable context, or giving the LLM a way to say "these instructions conflict and I cannot cleanly resolve this" instead of silently guessing.

## The Proposed Solution

Arbiter introduces a three-tier evaluation architecture that explicitly separates concerns:

### System Layer

The foundational evaluation framework — the constitution. This layer defines invariant rules for how the LLM judge operates. It must be internally consistent; no contradictions are permitted at this level. The system layer provides the ground rules for evaluating content in the other two layers and establishes the neutral observer perspective. It is defined once, validated for consistency, and does not change during evaluation. If you need different system-level behavior, you define a different system layer — you don't patch this one at runtime.

### Domain Layer

The contextual knowledge layer. This provides domain-specific information the LLM judge needs to do its work. It is mutable — it changes as the domain evolves — and may contain conflicts. That's expected. The domain layer is trusted but not unconditionally: the system layer governs how conflicts within the domain layer are detected, reported, and (where possible) resolved.

### Application Layer

The untrusted input — the actual query or request to be evaluated. This is assessed against the system and domain layers to determine if it can be cleanly resolved. When it cannot, Arbiter returns an explicit, structured description of why. It does not confabulate. It does not silently pick one interpretation. It tells you what the conflict is, where it arises, and what information would be needed to resolve it.

## Architecture

```
┌─────────────────────────────────┐
│         System Layer            │
│  Invariant evaluation rules.    │
│  Validated for consistency.     │
│  Does not change at runtime.    │
├─────────────────────────────────┤
│         Domain Layer            │
│  Contextual domain knowledge.   │
│  Mutable. May contain conflicts.│
│  Conflict handling governed by  │
│  system layer.                  │
├─────────────────────────────────┤
│       Application Layer         │
│  Untrusted input.               │
│  Evaluated against system and   │
│  domain layers.                 │
│  Returns resolution or explicit │
│  conflict report.               │
└─────────────────────────────────┘
```

The architecture is domain-agnostic. The system and application layers are independent of any particular use case. The domain layer is the pluggable piece that adapts Arbiter to specific contexts.

## Example Domains

Arbiter applies anywhere an LLM operates with layered instructions that can conflict. Some concrete cases:

**Database query generation.** Late-binding schema descriptions guide LLM generation of queries. These descriptions evolve, are written by different people at different times, and contradict each other. Without Arbiter, the LLM silently produces subtly wrong queries. With Arbiter, contradictions in the schema descriptions are detected and reported before query generation proceeds. The [Indaleko](https://github.com/fsgeek/indaleko) project provides the first reference implementation of a domain layer for this case, mapping human episodic memory concepts to ArangoDB AQL queries.

**RAG pipelines.** Retrieved context chunks may contain contradictory information. Arbiter can evaluate whether the retrieved context is internally consistent before the LLM attempts to synthesize a response from it.

**Code generation.** Style guides, framework documentation, and user requirements may disagree. Arbiter can surface these conflicts rather than letting the LLM silently favor one source over another.

**Multi-agent systems.** When multiple agents provide guidance to a downstream LLM, that guidance may conflict. Arbiter provides a structured way to detect this before the downstream LLM acts on incoherent instructions.

**Tool use.** Tool descriptions and user intent don't always align. Arbiter can evaluate whether the application query is consistent with the tool's documented behavior before execution.

Each of these requires only a domain layer definition. The system and application layers remain the same.

## Usage

```python
from arbiter import Arbiter, SystemLayer, DomainLayer

# Define the system layer (the constitution)
system = SystemLayer.from_file("system_rules.yaml")
system.validate()  # Fails if internally inconsistent

# Define the domain layer (contextual knowledge)
domain = DomainLayer.from_file("my_domain.yaml")

# Evaluate an application query
result = Arbiter(system, domain).evaluate(query)

if result.resolved:
    # Clean resolution
    process(result.output)
else:
    # Conflict detected — result.conflicts describes what and why
    handle_conflicts(result.conflicts)
```

## Evaluation Harness

Arbiter includes a test harness for characterizing evaluation behavior across:

- **Clean queries** — unambiguous requests that should resolve without issue
- **Ambiguous queries** — underspecified but not conflicting
- **Conflicting queries** — domain layer contains contradictory guidance
- **Adversarial queries** — designed to exploit gaps between layers
- **Evolution scenarios** — domain layer updates that introduce new conflicts

The harness produces structured output for analysis and regression testing. The goal is not coverage metrics — it's confidence that regressions in conflict detection are caught immediately.

## For AI Coding Instances

If you're an AI instance working in this repository: welcome.

This project values epistemic honesty over completion. If you encounter a design decision that doesn't make sense, say so rather than implementing around it. If a test reveals unexpected behavior, that's data — surface it. If the system layer's conflict-free invariant is hard to maintain, that difficulty is the point, not a bug to be worked around.

The three-tier separation is the core architectural commitment. Everything else is negotiable. If you see a better way to implement conflict detection, propose it. If the API feels wrong, say why. The human steward of this project has a high tolerance for "I think this is wrong because..." and a low tolerance for silent workarounds that hide problems.

If you make a non-trivial architectural choice, document why. Future instances will thank you.

## Status

Early development. The architecture is defined. The implementation is beginning.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Related Projects

- [Indaleko](https://github.com/fsgeek/indaleko) — Unified personal indexing system (first domain use case)
- [Mallku](https://github.com/fsgeek/mallku) — Multi-generational AI collaboration framework
