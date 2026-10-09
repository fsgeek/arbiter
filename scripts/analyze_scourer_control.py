#!/usr/bin/env python3
"""Compute the pre-registered metrics M1-M3 (and M5 for the permuted arm) for the
scourer control arms against the original chain. No judgment calls; see
docs/research/prereg_scourer_same_model_control.md for definitions."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = ROOT / "data" / "scourer" / "10pass_gptoss.json"
CTRL = ROOT / "data" / "scourer" / "control"
STOP = set("a an the of to in on for and or is are be with that this as by from at it its into "
           "not no vs via than when which what who how where".split())


def norm(c: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", c.lower()).strip()


def bow(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2}


def metrics(reports: list[dict]) -> dict:
    seen: set[str] = set()
    total = new = 0
    cats: list[str] = []
    first_no = None
    three_no = None
    run = 0
    for r in reports:
        pc = [norm(f.get("category", "")) for f in r["findings"]]
        new += sum(1 for c in pc if c not in seen)
        seen.update(pc)
        cats += pc
        total += len(pc)
        if not r["should_send_another"]:
            run += 1
            first_no = first_no or r["pass_number"]
            if run >= 3 and three_no is None:
                three_no = r["pass_number"]
        else:
            run = 0
    return {
        "passes": len(reports),
        "M1a_first_no": first_no,
        "M1b_three_consecutive_no": three_no,
        "M1c_findings": total,
        "M2_unique_category_ratio": round(len(set(cats)) / total, 3) if total else None,
        "M3_new_category_fraction": round(new / total, 3) if total else None,
        "per_pass": [(r["pass_number"], r.get("model"), len(r["findings"]), r["should_send_another"])
                     for r in reports],
    }


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def m5(base: list[dict], perm: list[dict]) -> dict:
    def text(r: dict) -> set[str]:
        return bow(" ".join(f.get("category", "") + " " + f.get("description", "") for f in r["findings"]))
    base_by_model = {r["model"]: (r["pass_number"], text(r)) for r in base}
    perm_by_model = {r["model"]: (r["pass_number"], text(r)) for r in perm}
    perm_by_pos = {r["pass_number"]: (r["model"], text(r)) for r in perm}
    same_model, diff_model = [], []
    for m, (pos, bt) in base_by_model.items():
        if m in perm_by_model:
            same_model.append(jaccard(bt, perm_by_model[m][1]))
        if pos in perm_by_pos and perm_by_pos[pos][0] != m:
            diff_model.append(jaccard(bt, perm_by_pos[pos][1]))
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None  # noqa: E731
    return {"same_model_cross_position": mean(same_model), "n_same": len(same_model),
            "diff_model_same_position": mean(diff_model), "n_diff": len(diff_model),
            "difference": round((mean(same_model) or 0) - (mean(diff_model) or 0), 3)}


def main() -> None:
    base = json.load(open(BASE))["reports"]
    out = {"baseline": metrics(base)}
    for p in sorted(CTRL.glob("*.json")):
        reps = json.load(open(p))["reports"]
        out[p.stem] = metrics(reps)
        if p.stem == "permuted":
            out[p.stem]["M5"] = m5(base, reps)
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
