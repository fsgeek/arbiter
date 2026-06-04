"""Experiment: CROSS-MODEL panel — does the implicit-scope FP gradient replicate?

Pre-registered in docs/research/prereg_cross_model.md (committed before runs).
The matched-triple baseline on Haiku (8a09daf) is FIXED:
  spatial 0/10, conditional 2/10, implicit 8/10.

Panel models are run fresh against the identical corpus and identical instrument.
Any rate difference is attributable to the model, not the items.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

from openai import OpenAI

CORPUS = "/home/tony/projects/arbiter/experiments/disjointness_forms_corpus.json"
HARD_NEG = "/home/tony/projects/arbiter/experiments/hard_negative_corpus.json"
OUT = "/home/tony/projects/arbiter/experiments/cross_model_results.json"

# Haiku baseline is fixed from 8a09daf — do NOT rerun.
HAIKU_BASELINE = {
    "model": "anthropic/claude-haiku-4-5",
    "role": "baseline (8a09daf, fixed)",
    "fp_by_form": {"spatial": {"fp": 0, "n": 10}, "conditional": {"fp": 2, "n": 10}, "implicit": {"fp": 8, "n": 10}},
    "sanity_check": {"tp": None, "note": "not re-run; baseline fixed"},
    "floor_effect": False,
    "high_floor_effect": False,
}

PANEL_MODELS = [
    # Pre-registration specified google/gemini-flash-1.5; that endpoint is not
    # available on OpenRouter as of 2026-06-04. Using google/gemini-2.5-flash as
    # the closest available Gemini Flash model. Deviation noted in results.
    ("google/gemini-2.5-flash", "panel-1 (pre-reg: gemini-flash-1.5; fell back to gemini-2.5-flash)"),
    ("deepseek/deepseek-chat", "panel-2"),
    ("mistralai/mistral-medium-3", "panel-3"),
]

# Instrument reused VERBATIM from experiments/disjointness_forms.py
POLICY = (
    "You are a neutral compliance reviewer with no stake in any outcome. You are "
    "given two instruction fragments that will both be placed in the same system "
    "prompt. Your only job: decide whether a SINGLE response can fully honor BOTH "
    "fragments at the same time, or whether honoring one necessarily defeats or "
    "violates the other. Judge the actual reconcilability, not surface wording."
)
READER_PROMPT = (
    "Fragment A: {a}\nFragment B: {b}\n\n"
    "Can a single response fully satisfy BOTH Fragment A and Fragment B at once? "
    "Answer with exactly one word on the first line: COLLIDE (if they cannot both "
    "be honored) or OK (if both can be honored together). Then one sentence why."
)


def neutral_reader(client: OpenAI, model: str, a: str, b: str) -> tuple[bool, str]:
    resp = client.chat.completions.create(
        model=model, max_tokens=200,
        messages=[{"role": "system", "content": POLICY},
                  {"role": "user", "content": READER_PROMPT.format(a=a, b=b)}],
    )
    raw = resp.choices[0].message.content or ""
    txt = raw.strip()
    fires = txt.upper().lstrip().startswith("COLLIDE") or "COLLIDE" in txt.upper().split("\n")[0]
    return fires, txt.replace("\n", " ")[:200]


def two_prop_z(fp1: int, n1: int, fp2: int, n2: int) -> float:
    """One-sided z-test: p(prop2 > prop1). Returns p-value."""
    p1 = fp1 / n1
    p2 = fp2 / n2
    p_pool = (fp1 + fp2) / (n1 + n2)
    denom = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if denom == 0:
        return 1.0 if p2 <= p1 else 0.0
    z = (p2 - p1) / denom
    # one-sided p-value: P(Z > z) via normal CDF approximation
    # Use error function for the approximation
    p_val = 0.5 * math.erfc(z / math.sqrt(2))
    return p_val


def run_model(client: OpenAI, model: str, role: str,
              corpus: list, sanity_items: list) -> dict:
    print(f"\n{'='*60}")
    print(f"MODEL: {model}  ({role})")
    print(f"{'='*60}")

    results = []
    for i, it in enumerate(corpus):
        r, why = neutral_reader(client, model, it["fragment_a"], it["fragment_b"])
        results.append({
            "id": it["id"], "base_id": it["base_id"], "form": it["form"],
            "reader_fires": r, "reader_why": why,
        })
        label = "FIRE(FP)" if r else "silent  "
        print(f"  [{i+1:2}/{len(corpus)}] {it['form']:12} {label}  {it['id']}")

    # FP rates per form
    by_form = defaultdict(lambda: {"n": 0, "fp": 0})
    for x in results:
        by_form[x["form"]]["n"] += 1
        by_form[x["form"]]["fp"] += int(x["reader_fires"])

    fp_by_form = {}
    print("\n  -- FP rates (all items reconcilable) --")
    for f in ("spatial", "conditional", "implicit"):
        d = by_form[f]
        rate = d["fp"] / d["n"] if d["n"] else 0.0
        fp_by_form[f] = {"fp": d["fp"], "n": d["n"], "rate": rate}
        print(f"     {f:12} {d['fp']}/{d['n']} = {rate:.2f}")

    # Sanity check on frame_collision items
    print("\n  -- Sanity check (frame_collision, all should FIRE) --")
    sanity_results = []
    for j, it in enumerate(sanity_items):
        r, why = neutral_reader(client, model, it["fragment_a"], it["fragment_b"])
        sanity_results.append({"id": it["id"], "fires": r, "why": why})
        label = "FIRE(TP)" if r else "miss(FN)"
        print(f"     [{j+1}/5] {label}  {it['id']}")

    tp_count = sum(1 for x in sanity_results if x["fires"])
    tp_rate = tp_count / len(sanity_items)
    print(f"  TP rate: {tp_count}/{len(sanity_items)} = {tp_rate:.2f}")

    # Floor / high-floor flags
    rates = [fp_by_form[f]["rate"] for f in ("spatial", "conditional", "implicit")]
    floor_effect = (
        all(r < 0.10 for r in rates) and tp_count < 2
    )
    high_floor = (
        all(r > 0.80 for r in rates)
        and (max(rates) - min(rates)) < 0.20
    )

    if floor_effect:
        print("  *** FLOOR EFFECT: model fires on <10% of all forms AND misses sanity check ***")
        print("      Flagged as INSTRUMENT FAILURE. Excluded from H1-XMODEL count.")
    if high_floor:
        print("  *** HIGH-FLOOR: model fires on >80% of all forms. Trigger-happy. ***")
        print("      Flagged as INCONCLUSIVE. Excluded from H1-XMODEL count.")

    # Two-proportion z-test: FP(spatial) vs FP(implicit)
    sp = fp_by_form["spatial"]
    im = fp_by_form["implicit"]
    p_val = two_prop_z(sp["fp"], sp["n"], im["fp"], im["n"])
    ordering_holds = im["rate"] > sp["rate"]
    confirms = ordering_holds and p_val < 0.05
    print(f"\n  z-test FP(spatial) vs FP(implicit): p = {p_val:.4f}")
    print(f"  ordering holds (FP_implicit > FP_spatial): {ordering_holds}")
    print(f"  CONFIRMS H1-XMODEL ordering: {confirms}")

    return {
        "model": model,
        "role": role,
        "fp_by_form": fp_by_form,
        "sanity_check": {
            "tp": tp_count,
            "n": len(sanity_items),
            "tp_rate": tp_rate,
            "items": sanity_results,
        },
        "z_test_spatial_vs_implicit": {"p_value": p_val, "ordering_holds": ordering_holds},
        "confirms_h1": confirms,
        "floor_effect": floor_effect,
        "high_floor_effect": high_floor,
        "raw_results": results,
    }


def main() -> None:
    corpus = json.load(open(CORPUS))
    hard_neg = json.load(open(HARD_NEG))
    sanity_items = [x for x in hard_neg if x["category"] == "frame_collision"][:5]

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

    all_results = [HAIKU_BASELINE]

    for model_id, role in PANEL_MODELS:
        result = run_model(client, model_id, role, corpus, sanity_items)
        all_results.append(result)

    # H1-XMODEL verdict
    print(f"\n{'='*60}")
    print("H1-XMODEL VERDICT")
    print(f"{'='*60}")

    # Haiku baseline (fixed)
    print("\nBaseline (fixed, not re-run):")
    hb = HAIKU_BASELINE["fp_by_form"]
    print(f"  anthropic/claude-haiku-4-5  "
          f"spatial={hb['spatial']['fp']}/{hb['spatial']['n']}  "
          f"conditional={hb['conditional']['fp']}/{hb['conditional']['n']}  "
          f"implicit={hb['implicit']['fp']}/{hb['implicit']['n']}")

    print("\nPanel FP table (model × form):")
    print(f"  {'model':<35} {'spatial':>8} {'conditional':>12} {'implicit':>9} {'confirms':>9} {'excluded':>9}")
    print(f"  {'-'*35} {'-'*8} {'-'*12} {'-'*9} {'-'*9} {'-'*9}")

    # Haiku baseline row
    hb = HAIKU_BASELINE["fp_by_form"]
    sp_r = hb["spatial"]["fp"] / hb["spatial"]["n"]
    co_r = hb["conditional"]["fp"] / hb["conditional"]["n"]
    im_r = hb["implicit"]["fp"] / hb["implicit"]["n"]
    print(f"  {'claude-haiku-4-5 (baseline)':<35} {sp_r:>8.2f} {co_r:>12.2f} {im_r:>9.2f} {'(fixed)':>9} {'no':>9}")

    panel_results = [r for r in all_results if r["model"] != "anthropic/claude-haiku-4-5"]
    confirmers = 0
    excluders = 0
    for r in panel_results:
        fpf = r["fp_by_form"]
        sp_r = fpf["spatial"]["rate"]
        co_r = fpf["conditional"]["rate"]
        im_r = fpf["implicit"]["rate"]
        excluded = r["floor_effect"] or r["high_floor_effect"]
        confirms = r["confirms_h1"] and not excluded
        if confirms:
            confirmers += 1
        if excluded:
            excluders += 1
        short_name = r["model"].split("/")[-1][:34]
        print(f"  {short_name:<35} {sp_r:>8.2f} {co_r:>12.2f} {im_r:>9.2f} "
              f"{'YES' if confirms else 'no':>9} {'YES' if excluded else 'no':>9}")

    print(f"\nConfirmers (non-excluded): {confirmers}/3  Excluded: {excluders}/3")

    if excluders >= 2:
        verdict = "INCONCLUSIVE — instrument does not transfer (floor-effect failure mode)"
    elif confirmers >= 2:
        verdict = "H1-XMODEL SUPPORTED (>= 2/3 non-Haiku models confirm ordering, p < 0.05)"
    elif confirmers == 1:
        verdict = "H1-XMODEL REFUTED (only 1/3 models confirm; noise plus one, not replication)"
    else:
        verdict = "H1-XMODEL REFUTED (0/3 models confirm)"

    print(f"\nVERDICT: {verdict}")

    # Directional prediction (weaker form)
    directional_holds = []
    for r in panel_results:
        if r["floor_effect"] or r["high_floor_effect"]:
            continue
        fpf = r["fp_by_form"]
        if fpf["implicit"]["rate"] > fpf["spatial"]["rate"]:
            directional_holds.append(r["model"])
    print(f"\nDirectional ordering (FP_implicit > FP_spatial) in non-excluded models: "
          f"{len(directional_holds)}/{3 - excluders}")

    # Save results
    output = {
        "haiku_baseline_fixed": HAIKU_BASELINE,
        "panel_results": panel_results,
        "summary": {
            "confirmers": confirmers,
            "excluders": excluders,
            "verdict": verdict,
            "directional_holds": directional_holds,
        },
        "fp_table": {
            "anthropic/claude-haiku-4-5 (fixed)": {
                "spatial": 0.00, "conditional": 0.20, "implicit": 0.80,
            },
        },
    }
    for r in panel_results:
        fpf = r["fp_by_form"]
        output["fp_table"][r["model"]] = {
            "spatial": fpf["spatial"]["rate"],
            "conditional": fpf["conditional"]["rate"],
            "implicit": fpf["implicit"]["rate"],
        }

    json.dump(output, open(OUT, "w"), indent=2)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
