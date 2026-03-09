#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/6] Syncing dependencies (including paper extras)..."
uv sync --extra dev --extra paper

echo "[2/6] Running deterministic test suite (excluding integration)..."
uv run pytest -q -m 'not integration'

echo "[3/6] Rebuilding cross-vendor analysis artifacts..."
uv run python scripts/analyze_scourer_data.py

echo "[4/6] Regenerating paper figures..."
uv run python docs/paper/generate_figures.py

echo "[5/6] Building paper PDF..."
cd docs/paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex >/dev/null
cd "$ROOT_DIR"

echo "[6/6] Writing deterministic artifact manifest..."
uv run python scripts/generate_artifact_manifest.py --write

echo
echo "Artifact reproduction complete."
echo "Generated outputs:"
echo "  - data/analysis/cross_vendor_analysis.json"
echo "  - data/analysis/cross_vendor_report.md"
echo "  - data/analysis/artifact_manifest.json"
echo "  - docs/paper/figures/{heatmap,severity,per_pass,cost}.pdf"
echo "  - docs/paper/main.pdf"
