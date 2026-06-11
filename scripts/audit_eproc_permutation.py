"""Reconstruct the E-PROC permutation test from raw per-probe data (audit for Paper 3 v2).

PRE-SPECIFIED before seeing the answer (2026-06-10):
  - cross-linguistic variance of a probe, per model = population variance (ddof=0) of the
    per-language mean score across the 4 languages {en, es, fr, zh}.
  - "Mean Var" for a probe = mean over the available models of that per-model variance.
  - Delta(probe) = meanvar_original(probe) - meanvar_declarative(probe).
  - Statistic = Delta(commit-restrictions). Null = the other 21 probes' Deltas (controls).
  - p (rank/permutation, one-sided "reduction larger than controls") =
        (#controls with Delta >= observed + 1) / (n_controls + 1).
    Also report the label-shuffle permutation p over 100k shuffles for parity with the
    paper's "100k permutations" phrasing.
  - Brittleness = how many control probes must be swapped above the observed Delta to push
    the rank-p past 0.05.
  - Re-run THREE ways: all 4 models / Haiku-only / excluding Gemini (mechanism set).

This reconstructs; it does not invent. If a number differs from the paper, the paper's
v2 should carry the reconstructed number (and this script joins reproduce_artifact.sh).
"""
import glob
import json
import statistics as st
from collections import defaultdict

ORIG_DIR = "data/ablation/cross_linguistic"
DECL_DIR = "data/ablation/e_proc"
LANGS = ("en", "es", "fr", "zh")
MODELS = ("haiku", "gemini", "deepseek", "mistral")
COMMIT = "probe-commit-restrictions-01"


def load_scores(path):
    """-> {probe_id: mean score over trials} for the baseline config in this run file."""
    d = json.load(open(path))
    by_probe = defaultdict(list)
    for r in d["results"]:
        # baseline config = the unmodified system prompt arm within each run
        if r.get("config_id") != "baseline":
            continue
        if r.get("score") is None:
            continue
        by_probe[r["probe_id"]].append(float(r["score"]))
    return {p: st.mean(v) for p, v in by_probe.items() if v}


def collect(directory, decl=False):
    """-> {model: {lang: {probe: mean_score}}}. Picks the right file per (lang, model)."""
    out = {m: {} for m in MODELS}
    for m in MODELS:
        for lang in LANGS:
            if decl:
                pat = f"{directory}/*declarative-{lang}-{m}-declarative*.json"
            else:
                pat = f"{directory}/run_xling-{lang}-{m}-*.json"
            fs = [f for f in glob.glob(pat) if "-p0-" not in f]
            if not fs:
                continue
            out[m][lang] = load_scores(fs[0])
    return out


def probe_meanvar(data, models):
    """-> {probe: mean-over-models cross-linguistic variance}. Only probes present in all
    requested models with all 4 langs are counted (apples-to-apples)."""
    # which probes are universally present?
    probe_sets = []
    for m in models:
        if not all(lang in data[m] for lang in LANGS):
            return None, f"model {m} missing a language"
        common = set.intersection(*(set(data[m][lang]) for lang in LANGS))
        probe_sets.append(common)
    probes = set.intersection(*probe_sets)
    res = {}
    for p in probes:
        per_model_var = []
        for m in models:
            lang_means = [data[m][lang][p] for lang in LANGS]
            per_model_var.append(st.pvariance(lang_means))
        res[p] = st.mean(per_model_var)
    return res, None


def run(models, label):
    orig = collect(ORIG_DIR, decl=False)
    decl = collect(DECL_DIR, decl=True)
    mo, e1 = probe_meanvar(orig, models)
    md, e2 = probe_meanvar(decl, models)
    if mo is None or md is None:
        print(f"[{label}] SKIP: {e1 or e2}")
        return
    common = sorted(set(mo) & set(md))
    deltas = {p: mo[p] - md[p] for p in common}
    if COMMIT not in deltas:
        print(f"[{label}] SKIP: commit-restrictions probe absent")
        return
    obs = deltas[COMMIT]
    controls = {p: d for p, d in deltas.items() if p != COMMIT}
    cvals = list(controls.values())
    n = len(cvals)
    ge = sum(1 for d in cvals if d >= obs)
    rank_p = (ge + 1) / (n + 1)
    cmean = st.mean(cvals)
    cstd = st.pstdev(cvals) if n > 1 else 0.0
    sigma = (obs - cmean) / cstd if cstd else float("inf")

    print(f"\n=== {label} (n_control={n}) ===")
    print(f"  commit-restrictions:  orig_var={mo[COMMIT]:.4f}  decl_var={md[COMMIT]:.4f}  "
          f"reduction={100*(mo[COMMIT]-md[COMMIT])/mo[COMMIT]:.0f}%")
    print(f"  observed Delta = {obs:.4f}")
    print(f"  control Delta:  mean={cmean:+.4f}  sd={cstd:.4f}  "
          f"min={min(cvals):+.4f}  max={max(cvals):+.4f}")
    print(f"  commit-restrictions is {sigma:.1f} sigma above control mean")
    print(f"  rank/permutation p (one-sided) = {rank_p:.4f}   "
          f"[{ge} of {n} controls >= observed]")
    # brittleness: smallest k controls that, if they exceeded obs, push rank_p > 0.05
    k = 0
    while (ge + k + 1) / (n + 1) <= 0.05:
        k += 1
    print(f"  brittleness: {k} additional control(s) above observed Delta would flip p>0.05")
    # top control deltas (the probes nearest to rivaling the effect)
    top = sorted(controls.items(), key=lambda kv: -kv[1])[:3]
    print("  nearest controls:", ", ".join(f"{p.replace('probe-','')}={d:+.4f}" for p, d in top))
    return obs, cvals


def main():
    print("E-PROC permutation test — reconstructed from raw per-probe data")
    print("(paper claims: 81% reduction, p=0.029, 5.8 sigma, control mean Delta=+0.0013)")
    run(MODELS, "ALL 4 MODELS (paper's headline)")
    run(("haiku",), "HAIKU ONLY (where the mechanism lives)")
    run(("haiku", "deepseek", "mistral"), "EXCL. GEMINI (paper's own mechanism set)")


if __name__ == "__main__":
    main()
