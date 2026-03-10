# Artifact Reproduction Guide

This repository contains the implementation and cached datasets used to produce the paper artifacts in `docs/paper/`.

This project is a reconstruction/extension of earlier exploratory work; this guide documents what is reproducible from the materials in this repository today.

## Scope

This guide reproduces deterministic outputs from pinned local inputs:

- Cross-vendor scourer analysis tables
- Paper figures
- PDF build of the paper
- Local non-integration test signal

It does **not** re-run live LLM API campaigns, guarantee historical model parity, or guarantee stable API pricing/availability; those are non-deterministic and time-varying.

## Prerequisites

- `uv` installed
- LaTeX toolchain with `latexmk` and `pdflatex`
- Python environment managed by `uv`

## One-command reproduction

From repository root:

```bash
bash scripts/reproduce_artifact.sh
```

This executes:

1. `uv sync --extra dev --extra paper`
2. `uv run pytest -q -m 'not integration'`
3. `uv run python scripts/analyze_scourer_data.py`
4. `uv run python docs/paper/generate_figures.py`
5. `latexmk -pdf -interaction=nonstopmode -halt-on-error docs/paper/main.tex`
6. `uv run python scripts/generate_artifact_manifest.py --write`

## Expected outputs

- `data/analysis/cross_vendor_analysis.json`
- `data/analysis/cross_vendor_report.md`
- `data/analysis/artifact_manifest.json`
- `docs/paper/figures/heatmap.pdf`
- `docs/paper/figures/severity.pdf`
- `docs/paper/figures/per_pass.pdf`
- `docs/paper/figures/cost.pdf`
- `docs/paper/main.pdf`

Archived artifact DOI:
- https://doi.org/10.5281/zenodo.18929834

## Machine verification

Check that deterministic artifacts match the committed manifest:

```bash
uv run python scripts/generate_artifact_manifest.py --check data/analysis/artifact_manifest.json
```

The manifest intentionally covers deterministic text artifacts only. PDF files are excluded from hash checks because PDF metadata can vary across build environments.

## Notes on tests

- `-m 'not integration'` is used for deterministic CI/local validation.
- Integration tests exercise live model behavior and may drift over time due to model updates.

## Optional: run integration tests

```bash
uv run pytest -m integration
```

This requires valid API credentials and should be interpreted as live-system checks, not strict regressions.
