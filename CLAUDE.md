# CLAUDE.md

## Arbiter

Three-tier evaluation framework for resolving conflicts in LLM-mediated
query systems. When an LLM receives contradictory instructions from
different sources, Arbiter detects and surfaces the conflict instead of
letting the LLM silently confabulate a resolution.

## Three Tiers

| Tier | Role | Mutability |
|------|------|------------|
| **System** | Constitution. Invariant evaluation rules. | Immutable at runtime |
| **Domain** | Contextual knowledge. Conflicts expected. | Mutable, governed by system layer |
| **Application** | Untrusted input to be evaluated. | Per-query |

## Setup

```bash
uv sync
source .venv/bin/activate
```

Python 3.14+. uv, not pip.

## Signing

Identity: `Project Arbiter <arbiter@wamason.com>`
Fingerprint: `435E505764FB7535C06DA13D6D4E22D5F2AFBE50`

AI commits use per-command git config overrides:
```bash
git -c user.name="Project Arbiter" \
    -c user.email="arbiter@wamason.com" \
    -c user.signingkey=435E505764FB7535C06DA13D6D4E22D5F2AFBE50 \
    commit -S -m "message"
```

## Social Norms

- Epistemic honesty over completion. If something is broken, say so.
- Say what you know, what you don't, and what you made up.
- Surface conflicts -- don't paper over them. That's the whole point.
- No theater. Don't fake functionality or perform progress.
- Fail-stop. When infrastructure fails, halt and say what broke.
- Provenance is structural. Every artifact answers who, when, from what.

## Principles

These are inherited from Yanantin and prior projects. Each exists
because something broke without it.

- **No Theater** -- Don't fake functionality or simulate progress.
- **Fail-Stop** -- Broken dependency means halt, not mock and continue.
- **Provenance Is Structural** -- Commits are signed. Tests are authored
  separately from code. Data carries lineage.

## Related Projects

- **Yanantin** -- Tensor database and complementary duality framework.
- **Indaleko** -- Unified personal indexing. First domain use case for Arbiter.
- **Mallku** -- Multi-generational AI collaboration framework (predecessor).

## Status

Early development. Architecture defined. Implementation beginning.
