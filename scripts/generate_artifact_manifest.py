#!/usr/bin/env python3
"""Generate or verify deterministic artifact manifest hashes.

This manifest intentionally covers deterministic text artifacts only.
Binary PDF outputs are excluded because PDF metadata can vary by build
environment/time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data" / "analysis" / "artifact_manifest.json"

TARGETS = [
    ROOT / "data" / "analysis" / "cross_vendor_analysis.json",
    ROOT / "data" / "analysis" / "cross_vendor_report.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest() -> dict:
    files: dict[str, dict[str, int | str]] = {}
    for p in TARGETS:
        if not p.exists():
            raise FileNotFoundError(f"Missing artifact file: {p}")
        rel = p.relative_to(ROOT).as_posix()
        files[rel] = {
            "sha256": sha256(p),
            "size": p.stat().st_size,
        }

    return {
        "schema_version": 1,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or verify artifact manifest.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write manifest to disk.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current artifacts against existing manifest.",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default=str(DEFAULT_MANIFEST),
        help=f"Manifest path (default: {DEFAULT_MANIFEST.relative_to(ROOT)})",
    )
    args = parser.parse_args()

    if args.write == args.check:
        print("Specify exactly one mode: --write or --check", file=sys.stderr)
        return 2

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path

    current = build_manifest()

    if args.write:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(current, indent=2) + "\n")
        print(f"Wrote manifest: {manifest_path}")
        return 0

    # --check
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    expected = json.loads(manifest_path.read_text())
    if expected != current:
        print("Artifact manifest mismatch.", file=sys.stderr)
        print("Run: uv run python scripts/generate_artifact_manifest.py --write", file=sys.stderr)

        expected_files = expected.get("files", {})
        current_files = current.get("files", {})
        all_keys = sorted(set(expected_files) | set(current_files))
        for key in all_keys:
            e = expected_files.get(key)
            c = current_files.get(key)
            if e != c:
                print(f"- {key}", file=sys.stderr)
                print(f"  expected: {e}", file=sys.stderr)
                print(f"  current:  {c}", file=sys.stderr)
        return 1

    print("Artifact manifest check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
