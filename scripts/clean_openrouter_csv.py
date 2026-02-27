#!/usr/bin/env python3
"""Clean OpenRouter activity CSV for public inclusion.

Keeps only Arbiter-related rows. Strips generation_id and api_key_name.
Retains: timestamps, costs, tokens, model, provider, timing, finish reason.
"""

import csv
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT = DATA_DIR / "openrouter_activity_2026-02-27.csv"
OUTPUT = DATA_DIR / "openrouter_arbiter_costs.csv"

ARBITER_APPS = {"arbiter-scourer", "Arbiter conflict-detection"}

DROP_COLUMNS = {"generation_id", "api_key_name", "user"}

def main():
    with open(INPUT) as f:
        reader = csv.DictReader(f)
        fieldnames = [c for c in reader.fieldnames if c not in DROP_COLUMNS]

        rows = []
        for row in reader:
            if row.get("app_name") in ARBITER_APPS:
                cleaned = {k: v for k, v in row.items() if k not in DROP_COLUMNS}
                rows.append(cleaned)

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} Arbiter rows to {OUTPUT.name}")
    print(f"Dropped columns: {', '.join(sorted(DROP_COLUMNS))}")
    print(f"Dropped {363 - 1 - len(rows)} non-Arbiter rows")


if __name__ == "__main__":
    main()
