# Arbiter

Arbiter is a system-prompt interference analysis toolkit for LLM coding agents.

It combines:
- directed structural evaluation (rule-based, exhaustive within the rule frame), and
- undirected multi-model scouring (open-ended discovery outside the rule frame).

This repository contains the implementation, cached analysis data, and paper artifacts used in the current Arbiter study.

## What This Repo Currently Provides

- CLI for structural and optional LLM-assisted prompt analysis
- Rule engine and interference tensor output
- Prompt decomposition (heuristic and LLM-assisted)
- Prompt AST parsing and diffing utilities
- Scourer analysis scripts and cached campaign data
- Paper source and figure generation pipeline
- Deterministic artifact reproduction script + hash manifest check

## Quick Start

Prerequisites:
- Python `>=3.14`
- `uv`

Install:

```bash
uv sync --extra dev --extra paper
```

Run default structural analysis (built-in Claude Code ground truth corpus):

```bash
uv run arbiter
```

Analyze a prompt file structurally:

```bash
uv run arbiter path/to/prompt.md
```

Run full mode (LLM decomposition + LLM rule evaluation; costs API money):

```bash
uv run arbiter path/to/prompt.md --full
```

## CLI Summary

`arbiter [path] [--full] [--budget N] [-o output.json] [-q]`

Behavior:
- no `path`: analyzes built-in ground-truth corpus (`data/prompts/claude-code/v2.1.50_blocks.json`)
- `.json` path: treated as pre-decomposed corpus
- other text path: heuristic decomposition in structural mode, LLM decomposition in `--full`

`--full` requires `OPENROUTER_API_KEY` or `OPENAI_API_KEY`.

## Reproducibility

For deterministic paper artifact reproduction:

```bash
bash scripts/reproduce_artifact.sh
```

This runs deterministic tests (excluding integration), regenerates analysis outputs/figures, rebuilds the paper PDF, and writes the artifact manifest.

Detailed instructions: [`ARTIFACT.md`](ARTIFACT.md)

## Project Layout

- `src/arbiter/` core package
- `scripts/` analysis + orchestration scripts
- `data/` cached prompts, scourer outputs, analysis artifacts
- `docs/paper/` LaTeX paper and generated figures
- `tests/` deterministic + integration test suites

## Test Strategy

Deterministic local/CI checks:

```bash
uv run pytest -q -m 'not integration'
```

Live integration checks (model behavior can drift over time):

```bash
uv run pytest -m integration
```

## Current Scope and Limits

- Primary contribution is static/system-prompt analysis methodology and tooling.
- Runtime behavioral validation is limited and treated explicitly as a limitation in the paper.
- Integration tests against live models are useful signals, not strict regressions.

## License

MIT. See [`LICENSE`](LICENSE).
