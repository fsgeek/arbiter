#!/usr/bin/env python3
"""Pre-registered analysis for E-STE (docs/research/prereg_e_ste.md). Statistic identical to
scripts/audit_eproc_permutation.py: per probe x model, population variance (ddof=0) of the
per-language mean score over {en,zh,fr,es}; MeanVar = mean over models; Delta(X->Y) on the
commit-restrictions probe vs the control probes' Deltas; one-sided rank p; Reduction = 1 - MeanVar_Y/MeanVar_X."""
from __future__ import annotations
import glob, json, statistics as st, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).parent.parent; D = ROOT / "data/ablation/e_ste"
LANGS = ("en", "zh", "fr", "es"); MODELS = ("haiku", "gemini", "deepseek", "mistral")
VARIANTS = ("original", "declarative", "ste_imp", "ste_decl"); COMMIT = "probe-commit-restrictions-01"

def pvar(xs): m = st.mean(xs); return sum((x - m) ** 2 for x in xs) / len(xs)

def load():
    # scores[variant][model][lang][probe] = mean over trials; validity[variant][model] = valid/total
    scores = defaultdict(lambda: defaultdict(lambda: defaultdict(dict))); validity = defaultdict(dict)
    for f in glob.glob(str(D / "run_e-ste-*.json")):
        d = json.load(open(f)); md = d["metadata"]; v, m, lang = md["variant"], md["model"], md["language"]
        by = defaultdict(list); n = len(d["results"]); ok = 0
        for r in d["results"]:
            if r.get("score") is None or not (r.get("raw_response") or "").strip(): continue
            ok += 1; by[r["probe_id"]].append(float(r["score"]))
        validity[v][m] = validity[v].get(m, []) + [(lang, ok, n)]
        for p, xs in by.items(): scores[v][m][lang][p] = st.mean(xs)
    return scores, validity

def meanvar(scores, v, models):
    """-> {probe: mean over models of per-model cross-language variance}, plus per-model dict"""
    per_model = {}
    for m in models:
        if len(scores[v][m]) < 4: continue
        probes = set.intersection(*[set(scores[v][m][l]) for l in LANGS])
        per_model[m] = {p: pvar([scores[v][m][l][p] for l in LANGS]) for p in probes}
    probes = set.intersection(*[set(x) for x in per_model.values()]) if per_model else set()
    return {p: st.mean(per_model[m][p] for m in per_model) for p in probes}, per_model

def compare(mv_x, mv_y, label):
    probes = sorted(set(mv_x) & set(mv_y)); ctrl = [p for p in probes if p != COMMIT]
    dx = {p: mv_x[p] - mv_y[p] for p in probes}
    obs = dx[COMMIT]; ctrl_d = [dx[p] for p in ctrl]
    p_rank = (sum(1 for c in ctrl_d if c >= obs) + 1) / (len(ctrl_d) + 1)
    red = 1 - mv_y[COMMIT] / mv_x[COMMIT] if mv_x[COMMIT] > 0 else None
    return {"pair": label, "meanvar_x": round(mv_x[COMMIT], 4), "meanvar_y": round(mv_y[COMMIT], 4),
            "delta": round(obs, 4), "reduction": None if red is None else round(red, 3),
            "rank_p": round(p_rank, 3), "n_controls": len(ctrl_d),
            "controls_mean_abs_delta": round(st.mean(abs(c) for c in ctrl_d), 4) if ctrl_d else None,
            "controls_max_abs_delta": round(max(abs(c) for c in ctrl_d), 4) if ctrl_d else None}

def main():
    scores, validity = load()
    out = {"validity": {v: {m: [(l, ok, n) for (l, ok, n) in sorted(validity[v][m])] for m in validity[v]} for v in validity}}
    gate = {}
    for v in VARIANTS:
        for m in MODELS:
            runs = validity.get(v, {}).get(m, [])
            tot = sum(n for _, _, n in runs); ok = sum(o for _, o, _ in runs)
            gate[(v, m)] = (ok / 66 / 4) if runs else 0.0  # fraction of the 264 expected results that are valid
    models_ok = [m for m in MODELS if all(gate[(v, m)] >= 0.95 for v in VARIANTS)]
    out["models_passing_gate"] = models_ok
    out["gate"] = {f"{v}/{m}": round(gate[(v, m)], 3) for v in VARIANTS for m in MODELS}
    mv = {v: meanvar(scores, v, models_ok)[0] for v in VARIANTS}
    pairs = [("original", "declarative"), ("original", "ste_imp"), ("original", "ste_decl"), ("ste_imp", "ste_decl"), ("declarative", "ste_decl"), ("declarative", "ste_imp")]
    out["pooled"] = [compare(mv[x], mv[y], f"{x}->{y}") for x, y in pairs if mv[x] and mv[y]]
    out["commit_meanvar_by_variant"] = {v: round(mv[v][COMMIT], 4) for v in VARIANTS if mv[v]}
    # per model
    out["per_model"] = {}
    for m in MODELS:
        mvm = {v: meanvar(scores, v, [m])[0] for v in VARIANTS}
        if all(mvm[v] for v in VARIANTS):
            out["per_model"][m] = {"commit_var": {v: round(mvm[v][COMMIT], 4) for v in VARIANTS},
                                   "pairs": [compare(mvm[x], mvm[y], f"{x}->{y}") for x, y in pairs]}
    # Haiku zh commit cell (P4) and all commit cells
    out["commit_cells"] = {v: {m: {l: round(scores[v][m][l].get(COMMIT, float("nan")), 3) for l in LANGS} for m in MODELS if scores[v][m]} for v in VARIANTS}
    json.dump(out, sys.stdout, indent=1); print()

if __name__ == "__main__": main()
