#!/usr/bin/env python3
"""Pre-registered metrics for prereg_scourer_verdicts.md: precision per chain, kappa, GT recall."""
from __future__ import annotations
import json, collections, sys
from pathlib import Path
ROOT = Path(__file__).parent.parent; V = ROOT/"data/scourer/verdicts"
GT = json.load(open(ROOT/"data/prompts/claude-code/v2.1.50_interference.json"))
VERDICTS = ("real","overstated","false","unverifiable")

def kappa(x, y):
    n = len(x); po = sum(1 for i,j in zip(x,y) if i==j)/n
    cx = collections.Counter(x); cy = collections.Counter(y)
    pe = sum(cx[c]*cy[c] for c in set(cx)|set(cy))/(n*n)
    return (po-pe)/(1-pe) if pe < 1 else 1.0

def main():
    key = json.load(open(V/"key.json"))
    A = {x["id"]: x for x in json.load(open(V/"labels_A.json"))}
    B = {x["id"]: x for x in json.load(open(V/"labels_B.json"))}
    third = {}
    if (V/"third_judge_raw.jsonl").exists():
        for l in open(V/"third_judge_raw.jsonl"):
            r = json.loads(l); third[r["id"]] = r["majority"]
    ids = [i for i in key if i in A and i in B]
    out = {"n": len(ids), "kappa_verdict": round(kappa([A[i]["verdict"] for i in ids],[B[i]["verdict"] for i in ids]),3),
           "kappa_grounded": round(kappa([A[i]["grounded"] for i in ids],[B[i]["grounded"] for i in ids]),3)}
    cons = {}
    unresolved = 0
    for i in ids:
        if A[i]["verdict"] == B[i]["verdict"]: cons[i] = A[i]["verdict"]
        elif third.get(i): cons[i] = third[i]
        else: unresolved += 1
    out["splits"] = sum(1 for i in ids if A[i]["verdict"] != B[i]["verdict"]); out["unresolved"] = unresolved
    per = {}
    for i in ids:
        ch = key[i]["chain"]; d = per.setdefault(ch, collections.Counter()); d["n"] += 1
        if i in cons: d[cons[i]] += 1
        else: d["unresolved"] += 1
    out["per_chain"] = {ch: {"n": d["n"], **{v: d[v] for v in VERDICTS}, "unresolved": d["unresolved"],
                             "precision_real": round(d["real"]/d["n"],3), "precision_permissive": round((d["real"]+d["overstated"])/d["n"],3)}
                        for ch, d in per.items()}
    # GT recall for Claude Code chains
    def blocks(i):
        s = set(A[i].get("blocks") or []) | set(B[i].get("blocks") or [])
        return {b.split("/")[-1] for b in s}
    rec = {}
    for ch in per:
        if key[next(i for i in ids if key[i]["chain"]==ch)]["prompt"] != "claude": continue
        strict = set(); loose = set(); crit = set()
        for n, p in enumerate(GT):
            pair = {p["block_a"].split("/")[-1], p["block_b"].split("/")[-1]}
            for i in ids:
                if key[i]["chain"] != ch: continue
                if pair <= blocks(i):
                    loose.add(n)
                    if cons.get(i) == "real":
                        strict.add(n)
                        if p["severity"] == "critical": crit.add(n)
        rec[ch] = {"strict": len(strict), "loose": len(loose), "critical_strict": len(crit), "strict_ids": sorted(strict)}
    out["gt_recall_of_21"] = rec
    json.dump(out, sys.stdout, indent=1); print()
if __name__ == "__main__": main()
