#!/usr/bin/env python3
"""Pre-registered analysis for E-STE-S (docs/research/prereg_e_ste_sampled.md): trial-level bootstrap of
Spread differences and Level differences between variants, pooled over gated models; control probes."""
from __future__ import annotations
import glob, json, random, statistics as st, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).parent.parent; D = ROOT / "data/ablation/e_ste_sampled"
LANGS = ("en", "zh", "fr", "es"); MODELS = ("haiku", "gemini", "deepseek", "mistral")
VARIANTS = ("original", "declarative", "ste_imp", "ste_decl"); COMMIT = "probe-commit-restrictions-01"
PAIRS = [("original", "declarative"), ("ste_imp", "ste_decl"), ("original", "ste_imp"), ("declarative", "ste_decl"), ("original", "ste_decl")]
B = 10_000; rng = random.Random(20261013)

def pvar(xs): m = st.mean(xs); return sum((x - m) ** 2 for x in xs) / len(xs)

def load():
    trials = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))  # [probe][variant][model][lang] -> [scores]
    failures = defaultdict(list); expected = defaultdict(int)
    for f in glob.glob(str(D / "run_*.json")):
        d = json.load(open(f)); md = d["metadata"]; v, m, lang = md["variant"], md["model"], md["language"]
        for r in d["results"]:
            if r.get("score") is not None: trials[r["probe_id"]][v][m][lang].append(float(r["score"]))
        for fl in md.get("failures", []): failures[m].append({"variant": v, "lang": lang, **fl})
        expected[(v, m, lang)] = d.get("trials_per_probe", 10)
    return trials, failures

def spread(cells):  # cells: {lang: [scores]} -> variance of the 4 means
    return pvar([st.mean(cells[l]) for l in LANGS])

def boot_stat(trials_probe, x, y, models, fn):
    """fn(cells_x_by_model, cells_y_by_model) -> number; bootstrap by resampling trials within cells."""
    def draw(cells): return {l: [rng.choice(cells[l]) for _ in cells[l]] for l in LANGS}
    point = fn({m: trials_probe[x][m] for m in models}, {m: trials_probe[y][m] for m in models})
    vals = []
    for _ in range(B):
        vals.append(fn({m: draw(trials_probe[x][m]) for m in models}, {m: draw(trials_probe[y][m]) for m in models}))
    vals.sort(); lo, hi = vals[int(0.025 * B)], vals[int(0.975 * B) - 1]
    return {"point": round(point, 4), "ci95": [round(lo, 4), round(hi, 4)], "excludes_0": lo > 0 or hi < 0}

def d_spread(cx, cy): return st.mean(spread(cx[m]) - spread(cy[m]) for m in cx)
def d_level(cx, cy): return st.mean(st.mean(st.mean(cx[m][l]) for l in LANGS) - st.mean(st.mean(cy[m][l]) for l in LANGS) for m in cx)

def main():
    trials, failures = load()
    out = {"failures_per_model": {m: len(failures[m]) for m in MODELS}}
    # gate on the target probe: valid/expected >= 0.95 (expected 10 trials x 4 variants x 4 langs = 160)
    gate = {m: sum(len(trials[COMMIT][v][m][l]) for v in VARIANTS for l in LANGS) / 160 for m in MODELS}
    models = [m for m in MODELS if gate[m] >= 0.95 and all(len(trials[COMMIT][v][m][l]) > 0 for v in VARIANTS for l in LANGS)]
    out["gate_target"] = {m: round(g, 3) for m, g in gate.items()}; out["models_gated_in"] = models
    out["cells_commit"] = {v: {m: {l: round(st.mean(trials[COMMIT][v][m][l]), 2) for l in LANGS if trials[COMMIT][v][m][l]} for m in MODELS} for v in VARIANTS}
    out["spread_commit"] = {v: {m: round(spread(trials[COMMIT][v][m]), 4) for m in models} for v in VARIANTS}
    out["spread_commit_pooled"] = {v: round(st.mean(spread(trials[COMMIT][v][m]) for m in models), 4) for v in VARIANTS}
    out["pairs"] = {}
    for x, y in PAIRS:
        out["pairs"][f"{x}->{y}"] = {"D_spread": boot_stat(trials[COMMIT], x, y, models, d_spread),
                                     "D_level": boot_stat(trials[COMMIT], x, y, models, lambda a, b: -d_level(a, b))}  # level gain of y over x
    # controls: |D_spread| per control probe per pair, point + CI (bootstrap with fewer draws)
    global B; Bsave = B; B = 2000
    ctrl = {}
    for p in trials:
        if p == COMMIT: continue
        ctrl[p] = {}
        for x, y in PAIRS:
            ms = [m for m in models if all(trials[p][v][m][l] for v in (x, y) for l in LANGS)]
            if not ms: continue
            ctrl[p][f"{x}->{y}"] = boot_stat(trials[p], x, y, ms, lambda a, b: abs(d_spread(a, b)))
    B = Bsave
    out["controls"] = ctrl
    out["controls_max_point_by_pair"] = {pr: round(max((ctrl[p][pr]["point"] for p in ctrl if pr in ctrl[p]), default=0), 4) for pr in [f"{x}->{y}" for x, y in PAIRS]}
    json.dump(out, sys.stdout, indent=1); print()
if __name__ == "__main__": main()
