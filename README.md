# Arbiter

Arbiter is a system-prompt interference analysis toolkit for LLM coding agents.

It combines:
- directed structural evaluation (rule-based, exhaustive within the defined rule frame), and
- undirected multi-model scouring (open-ended discovery outside the rule frame).

## Provenance and Reproducibility

This project is a reconstruction and extension of earlier exploratory work whose published materials were not fully reproducible as-is.

This repository is intended to be reproducible for the deterministic parts of the pipeline:
- prompt parsing/decomposition utilities,
- directed rule checks and interference tensor generation,
- cached cross-vendor scourer analysis outputs used in the paper,
- figure generation and LaTeX paper build,
- deterministic test suite and artifact manifest verification.

What is intentionally *not* claimed as deterministic/reproducible:
- live LLM API behavior,
- re-running historical multi-model campaigns with identical outputs,
- pricing/model availability stability over time.

## Quick Start

Prerequisites:
- Python `>=3.14`
- `uv`

Install dependencies:

```bash
uv sync --extra dev --extra paper
```

Run default structural analysis (built-in ground truth corpus):

```bash
uv run arbiter
```

Analyze a prompt file structurally:

```bash
uv run arbiter path/to/prompt.md
```

Run full mode (LLM decomposition + LLM rule evaluation; uses paid APIs):

```bash
uv run arbiter path/to/prompt.md --full
```

`--full` requires `OPENROUTER_API_KEY` or `OPENAI_API_KEY`.

## CLI

`arbiter [path] [--full] [--budget N] [--model MODEL] [--base-url URL] [-o output.json] [-q]`

Behavior:
- no `path`: analyzes built-in corpus `data/prompts/claude-code/v2.1.50_blocks.json`
- `.json` path: treated as a pre-decomposed prompt corpus
- other text path: heuristic decomposition in structural mode; LLM decomposition in `--full`

Exit codes:
- `0`: no findings
- `1`: findings detected
- `2`: error

## Reproduce Paper Artifacts

One-command deterministic reproduction:

```bash
bash scripts/reproduce_artifact.sh
```

This runs deterministic tests (excluding integration), regenerates analysis outputs/figures, rebuilds `docs/paper/main.pdf`, and writes `data/analysis/artifact_manifest.json`.

For details and verification commands, see [`ARTIFACT.md`](ARTIFACT.md).

## Repository Layout

- `src/arbiter/`: core package and CLI
- `scripts/`: orchestration and analysis scripts
- `data/`: prompts, cached scourer outputs, and analysis artifacts
- `docs/paper/`: LaTeX source, figures, and built paper outputs
- `tests/`: deterministic and integration test suites

## Testing

Deterministic checks:

```bash
uv run pytest -q -m 'not integration'
```

Integration checks against live models (non-deterministic):

```bash
uv run pytest -m integration
```

## Paper and Artifact

The paper source lives in `docs/paper/`.

Archived artifact DOI:
- https://doi.org/10.5281/zenodo.18929834

## License

MIT. See [`LICENSE`](LICENSE).
