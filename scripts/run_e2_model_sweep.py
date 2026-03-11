#!/usr/bin/env python3
"""Run bounded E2 semantic ablation across a model list and summarize results."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
E2_SCRIPT = REPO_ROOT / "scripts" / "run_e2_semantic_ablation.py"
OUT_JSON = REPO_ROOT / "data" / "analysis" / "e2_model_sweep_summary.json"
OUT_MD = REPO_ROOT / "data" / "analysis" / "e2_model_sweep_summary.md"


def _load_models(path: Path) -> list[str]:
    tokens = path.read_text().split()
    return [t.strip() for t in tokens if "/" in t]


def _slug(model: str) -> str:
    return model.replace("/", "_").replace(".", "").replace("-", "")


def _run_one(
    model: str,
    max_cases: int,
    timeout_seconds: float,
    model_timeout_seconds: float,
) -> tuple[bool, str]:
    tag = f"sweep_{_slug(model)}_{max_cases}"
    cmd = [
        "uv", "run", "python", str(E2_SCRIPT),
        "--model", model,
        "--max-cases", str(max_cases),
        "--timeout-seconds", str(timeout_seconds),
        "--run-tag", tag,
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=model_timeout_seconds,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).strip().splitlines()
        return False, msg[-1] if msg else f"exit {proc.returncode}"
    return True, tag


def _read_report(tag: str) -> dict:
    p = REPO_ROOT / "data" / "analysis" / f"e2_semantic_ablation_report_{tag}.json"
    return json.loads(p.read_text())


def _render_md(summary: dict) -> str:
    lines = []
    lines.append("# E2 Model Sweep Summary")
    lines.append("")
    lines.append(f"Case budget per model: {summary['max_cases']}")
    lines.append("")
    lines.append("| Model | Compared | Discrimination | Declared-Loss Presence | JSON Fail Rate |")
    lines.append("|---|---:|---:|---:|---:|")
    for row in summary["results"]:
        if row["status"] != "ok":
            lines.append(f"| `{row['model']}` | - | ERROR | - | - |")
            continue
        lines.append(
            f"| `{row['model']}` | {row['compared']} | {row['discrimination_rate']:.2%} | "
            f"{row['declared_losses_rate']:.2%} | {row['json_parse_fail_rate']:.2%} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Higher discrimination with low parse-failure is preferred for follow-up high-budget runs.")
    lines.append("- This sweep is bounded and intended for triage, not final promotion decisions.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-file", default="models.txt")
    parser.add_argument("--max-cases", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--model-timeout-seconds", type=float, default=300.0)
    parser.add_argument("--resume", action="store_true", help="Skip models with existing sweep artifacts")
    args = parser.parse_args()

    models = _load_models(REPO_ROOT / args.models_file)
    results = []

    for model in models:
        tag = f"sweep_{_slug(model)}_{args.max_cases}"
        existing = REPO_ROOT / "data" / "analysis" / f"e2_semantic_ablation_report_{tag}.json"
        if args.resume and existing.exists():
            report = _read_report(tag)
            results.append(
                {
                    "model": model,
                    "status": "ok",
                    "tag": tag,
                    "compared": report["discrimination"]["compared"],
                    "discrimination_rate": report["discrimination"]["discrimination_rate"],
                    "declared_losses_rate": report["parseability"]["optional_declared_losses_rate"],
                    "json_parse_fail_rate": report["parseability"]["json_parse_fail_rate"],
                    "resumed": True,
                }
            )
            continue
        try:
            ok, data = _run_one(
                model,
                args.max_cases,
                args.timeout_seconds,
                args.model_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            results.append(
                {
                    "model": model,
                    "status": "error",
                    "error": f"timeout after {args.model_timeout_seconds}s",
                }
            )
            continue
        if not ok:
            results.append({"model": model, "status": "error", "error": data})
            continue
        report = _read_report(data)
        results.append(
            {
                "model": model,
                "status": "ok",
                "tag": data,
                "compared": report["discrimination"]["compared"],
                "discrimination_rate": report["discrimination"]["discrimination_rate"],
                "declared_losses_rate": report["parseability"]["optional_declared_losses_rate"],
                "json_parse_fail_rate": report["parseability"]["json_parse_fail_rate"],
            }
        )

    # Sort successful rows by discrimination desc, then parsefail asc.
    results.sort(
        key=lambda r: (
            0 if r["status"] == "ok" else 1,
            -(r.get("discrimination_rate", -1.0)),
            r.get("json_parse_fail_rate", 1.0),
        )
    )

    summary = {
        "max_cases": args.max_cases,
        "models_total": len(models),
        "results": results,
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2))
    OUT_MD.write_text(_render_md(summary))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
