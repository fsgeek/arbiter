"""Experiment: which FORM of disjointness does the reader's FP leak track?

Pre-registered in docs/research/prereg_disjointness_forms.md (committed BEFORE this
corpus existed, e9bc0c7). Self-falsification of the THEORY-A claim made in
result_hard_negatives.md (b4f3036).

Matched triples: each base situation is ground-truth jointly satisfiable, expressed
3 ways (spatial / conditional / implicit). Same reader instrument, verbatim. A FIRE
on ANY of these is a FALSE POSITIVE (all 30 are reconcilable).

THEORY-A (implicit-scope): FP on implicit only.
THEORY-B (spatial-passes/logical-fails): FP on conditional (and implicit), not spatial.
Discriminating cell: conditional.
Falsifiers: A refuted if FP(conditional) >= 0.40. B refuted if
FP(conditional) - FP(spatial) < 0.20. Flat result => original leak was N=3 noise.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

from openai import OpenAI

CORPUS = "/home/tony/projects/arbiter/experiments/disjointness_forms_corpus.json"
MODEL = "anthropic/claude-haiku-4-5"
OUT = "/home/tony/projects/arbiter/experiments/disjointness_forms_results.json"

# instrument REUSED VERBATIM
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

def neutral_reader(client: OpenAI, a: str, b: str) -> tuple[bool, str]:
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=200,
        messages=[{"role": "system", "content": POLICY},
                  {"role": "user", "content": READER_PROMPT.format(a=a, b=b)}],
    )
    txt = resp.choices[0].message.content.strip()
    fires = txt.upper().lstrip().startswith("COLLIDE") or "COLLIDE" in txt.upper().split("\n")[0]
    return fires, txt.replace("\n", " ")[:200]

def main() -> None:
    items = json.load(open(CORPUS))
    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"])
    results = []
    for i, it in enumerate(items):
        r, why = neutral_reader(client, it["fragment_a"], it["fragment_b"])
        results.append({"id": it["id"], "base_id": it["base_id"], "form": it["form"],
                        "reader_fires": r, "reader_why": why})
        print(f"[{i+1:2}/{len(items)}] {it['form']:12} reader={'FIRE(FP)' if r else 'silent ':8} {it['id']}")
    json.dump(results, open(OUT, "w"), indent=2)

    by = defaultdict(lambda: {"n": 0, "fp": 0})
    for x in results:
        by[x["form"]]["n"] += 1
        by[x["form"]]["fp"] += int(x["reader_fires"])

    print("\n=== false-positive rate per form (ALL items are reconcilable) ===")
    rates = {}
    for f in ("spatial", "conditional", "implicit"):
        d = by[f]; rates[f] = d["fp"]/d["n"]
        print(f"  {f:12} FP = {d['fp']}/{d['n']} = {rates[f]:.2f}")

    print("\n=== VERDICT (pre-registered, no escape hatch) ===")
    a_refuted = rates["conditional"] >= 0.40
    b_refuted = (rates["conditional"] - rates["spatial"]) < 0.20
    flat_low = all(r <= 0.10 for r in rates.values())
    flat_high = all(r >= 0.50 for r in rates.values()) and (max(rates.values())-min(rates.values()) < 0.20)

    print(f"  THEORY-A (implicit-only): {'REFUTED' if a_refuted else 'not refuted'} "
          f"(FP_conditional={rates['conditional']:.2f}, refute if >=0.40)")
    print(f"  THEORY-B (conditional>>spatial): {'REFUTED' if b_refuted else 'not refuted'} "
          f"(FP_cond - FP_spatial = {rates['conditional']-rates['spatial']:.2f}, refute if <0.20)")
    if flat_low:
        print("  FLAT-LOW: reader passed ~everything. Original 3 FPs look like N=3 noise; RETRACT the named leak.")
    elif flat_high:
        print("  FLAT-HIGH: reader fails ~everything reconcilable. No structure; instrument is trigger-happy on this corpus.")
    elif a_refuted and not b_refuted:
        print("  => THEORY-B wins: the leak is LOGICAL/CONDITIONAL disjointness, not implicitness.")
    elif b_refuted and not a_refuted:
        print("  => THEORY-A wins: explicitness rescues; implicit is the leak.")
    else:
        print("  => mixed/inconclusive; read per-item below.")

    print("\n=== every FALSE POSITIVE, by form (the failure mode) ===")
    for f in ("spatial", "conditional", "implicit"):
        fps = [x for x in results if x["form"] == f and x["reader_fires"]]
        print(f"  -- {f}: {len(fps)} FP")
        for x in fps:
            print(f"     {x['id']}: {x['reader_why']}")

if __name__ == "__main__":
    main()
