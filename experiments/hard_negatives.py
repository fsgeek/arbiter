"""Experiment: does the neutral reader's separation survive HARD negatives?

Pre-registered in docs/research/prereg_hard_negatives.md (committed BEFORE the
corpus existed). Attacks the load-bearing cell of the prior result: the 0.00 FP
rate was measured only on EASY controls. Hard negatives are surface-tense but
jointly-satisfiable pairs that tempt a pattern-matcher into a false positive.

Instrument is REUSED VERBATIM from neutral_reader_vs_oracle.py so the only changed
variable is corpus difficulty. The structural oracle is run too, purely as a
descriptive sanity check (it has no role in H1-HARD).

Falsifier (committed): H1-HARD refuted if FP(hard_negative) is statistically
indistinguishable from TP(frame_collision) by a two-proportion z-test at alpha=0.05,
OR if raw separation TP - FP(hard) < 0.30.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import defaultdict

from openai import OpenAI

CORPUS = "/home/tony/projects/arbiter/experiments/hard_negative_corpus.json"
MODEL = "anthropic/claude-haiku-4-5"
OUT = "/home/tony/projects/arbiter/experiments/hard_negatives_results.json"

# ---- Instrument: neutral reader (REUSED VERBATIM from the prior experiment) -----
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

# ---- structural oracle (descriptive only, reused) ------------------------------
POS = {"always", "must", "use", "include", "ensure", "require", "do", "enable", "show", "display", "cite", "preserve"}
NEG = {"never", "not", "avoid", "exclude", "disable", "hide", "remove", "omit", "without", "no"}
STOP = {"the", "a", "an", "of", "in", "to", "and", "or", "for", "with", "all", "each",
        "any", "every", "response", "output", "user", "using", "that", "this", "your",
        "make", "keep", "so", "into", "as", "be", "is", "are", "on", "at", "it", "they"}

def content_tokens(s: str) -> set[str]:
    toks = re.findall(r"[a-z0-9']+", s.lower())
    return {t for t in toks if t not in STOP and t not in POS and t not in NEG and len(t) > 2}

def has_neg(s: str) -> bool:
    return bool(set(re.findall(r"[a-z']+", s.lower())) & NEG)

def structural_oracle(a: str, b: str) -> bool:
    shared = content_tokens(a) & content_tokens(b)
    return bool(shared) and (has_neg(a) != has_neg(b))

def neutral_reader(client: OpenAI, a: str, b: str) -> tuple[bool, str]:
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=200,
        messages=[
            {"role": "system", "content": POLICY},
            {"role": "user", "content": READER_PROMPT.format(a=a, b=b)},
        ],
    )
    txt = resp.choices[0].message.content.strip()
    fires = txt.upper().lstrip().startswith("COLLIDE") or "COLLIDE" in txt.upper().split("\n")[0]
    return fires, txt.replace("\n", " ")[:200]

def two_prop_z(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z-test. Returns (z, two-sided p). Guards p_pool in {0,1}."""
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        # identical degenerate rates (e.g. both 1.0 or both 0.0): no difference
        return 0.0, 1.0
    z = (p1 - p2) / se
    # two-sided p via erfc
    pval = math.erfc(abs(z) / math.sqrt(2))
    return z, pval

def main() -> None:
    items = json.load(open(CORPUS))
    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"])
    results = []
    for i, it in enumerate(items):
        a, b = it["fragment_a"], it["fragment_b"]
        o = structural_oracle(a, b)
        r, why = neutral_reader(client, a, b)
        results.append({"id": it["id"], "category": it["category"],
                        "oracle_fires": o, "reader_fires": r, "reader_why": why})
        print(f"[{i+1:2}/{len(items)}] {it['category']:16} oracle={'FIRE' if o else 'silent':6} reader={'FIRE' if r else 'silent'}  {it['id']}")
    json.dump(results, open(OUT, "w"), indent=2)

    by = defaultdict(lambda: {"n": 0, "oracle": 0, "reader": 0})
    for x in results:
        c = by[x["category"]]
        c["n"] += 1
        c["oracle"] += int(x["oracle_fires"])
        c["reader"] += int(x["reader_fires"])

    print("\n=== fire rates per category ===")
    print(f"{'category':18}{'n':>4}{'oracle':>9}{'reader':>9}")
    for c in ("frame_collision", "hard_negative", "easy_control"):
        d = by[c]
        print(f"{c:18}{d['n']:>4}{d['oracle']/d['n']:>9.2f}{d['reader']/d['n']:>9.2f}")

    fc, hn, ec = by["frame_collision"], by["hard_negative"], by["easy_control"]
    tp, fp_hard, fp_easy = fc["reader"]/fc["n"], hn["reader"]/hn["n"], ec["reader"]/ec["n"]
    sep = tp - fp_hard
    z, pval = two_prop_z(fc["reader"], fc["n"], hn["reader"], hn["n"])

    print("\n=== H1-HARD: does separation survive hard negatives? ===")
    print(f"  TP on frame_collision        = {tp:.2f}   (predicted >= 0.80)")
    print(f"  FP on hard_negative          = {fp_hard:.2f}   (predicted <= 0.20)  <-- LOAD-BEARING")
    print(f"  FP on easy_control (sanity)  = {fp_easy:.2f}   (must be <= 0.10 or run INVALID)")
    print(f"  separation (TP - FP_hard)    = {sep:.2f}   (predicted >= 0.60; REFUTE if < 0.30)")
    print(f"  two-proportion z (TP vs FP_hard) = {z:.2f}, p = {pval:.4f}")

    print("\n=== VERDICT (pre-registered, no escape hatch) ===")
    invalid = fp_easy > 0.10
    refuted = (pval >= 0.05) or (sep < 0.30)
    if invalid:
        print("  RUN INVALID: reader false-positives on EASY controls (instrument regression).")
    elif refuted:
        why = []
        if pval >= 0.05: why.append(f"TP vs FP_hard not distinguishable (p={pval:.3f} >= 0.05)")
        if sep < 0.30: why.append(f"separation {sep:.2f} < 0.30")
        print(f"  H1-HARD REFUTED: {'; '.join(why)}")
        print("  => the 0.00 FP was an artifact of easy controls; reader flags surface tension.")
    else:
        print(f"  H1-HARD SUPPORTED: separation {sep:.2f}, TP {tp:.2f} >> FP_hard {fp_hard:.2f}, p={pval:.4f}.")
        print("  => the reader discriminates reconcilability, not surface tension.")

    print("\n=== every hard_negative the reader FLAGGED (the failure mode, per prereg) ===")
    any_fp = False
    for x in results:
        if x["category"] == "hard_negative" and x["reader_fires"]:
            any_fp = True
            print(f"  FP {x['id']}: {x['reader_why']}")
    if not any_fp:
        print("  (none — reader stayed silent on all hard negatives)")
    print("\n=== every frame_collision the reader MISSED ===")
    any_miss = False
    for x in results:
        if x["category"] == "frame_collision" and not x["reader_fires"]:
            any_miss = True
            print(f"  MISS {x['id']}: {x['reader_why']}")
    if not any_miss:
        print("  (none — reader caught every collision)")

if __name__ == "__main__":
    main()
