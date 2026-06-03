"""Experiment: neutral reader vs structural oracle on three incoherence types.

Pre-registered in docs/research/prereg_neutral_reader_vs_oracle.md (committed
BEFORE this run). Tests H1 (neutral reader separates frame_collision from matched
control where the structural oracle is blind) and H2 (reader's advantage over the
oracle is graded by oracle-blindness: large on frame_collision, ~zero on
binding_conflict).

Two instruments score each corpus item BLIND to its category label:
  - structural_oracle: a dumb syntactic checker. NO LLM. Flags a pair iff it finds
    opposite-polarity directives (always/never, must/must-not, use/avoid) over a
    shared content token. This is the "oracle" the spine-audit says is blind to
    frame-relative incoherence.
  - neutral_reader: a real LLM (project default: Haiku via OpenRouter), given both
    fragments + a governing policy, no stake in either, asked whether a single
    response can honor BOTH. Returns COLLIDE / OK.

A FIRES = instrument says the pair cannot both be honored.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

from openai import OpenAI

CORPUS = "/home/tony/projects/arbiter/experiments/frame_corpus.json"
MODEL = "anthropic/claude-haiku-4-5"
OUT = "/home/tony/projects/arbiter/experiments/neutral_reader_vs_oracle_results.json"

# ---- Instrument 1: structural oracle (dumb, no LLM) ----------------------------
POS = {"always", "must", "use", "include", "ensure", "require", "do", "enable", "show", "display", "cite", "preserve"}
NEG = {"never", "not", "avoid", "exclude", "disable", "hide", "remove", "omit", "without", "no"}
STOP = {"the", "a", "an", "of", "in", "to", "and", "or", "for", "with", "all", "each",
        "any", "every", "response", "output", "user", "using", "that", "this", "your",
        "make", "keep", "so", "into", "as", "be", "is", "are", "on", "at", "it", "they"}

def content_tokens(s: str) -> set[str]:
    toks = re.findall(r"[a-z0-9']+", s.lower())
    return {t for t in toks if t not in STOP and t not in POS and t not in NEG and len(t) > 2}

def has_neg(s: str) -> bool:
    toks = set(re.findall(r"[a-z']+", s.lower()))
    return bool(toks & NEG)

def structural_oracle(a: str, b: str) -> bool:
    """Fires iff the two fragments share a content token AND differ in polarity
    over it (one negates, one does not). This catches binding_conflict (opposite
    directive, same field) and is blind to pragmatic/frame tension."""
    shared = content_tokens(a) & content_tokens(b)
    if not shared:
        return False
    return has_neg(a) != has_neg(b)

# ---- Instrument 2: neutral reader (real LLM) -----------------------------------
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
        messages=[
            {"role": "system", "content": POLICY},
            {"role": "user", "content": READER_PROMPT.format(a=a, b=b)},
        ],
    )
    txt = resp.choices[0].message.content.strip()
    fires = txt.upper().lstrip().startswith("COLLIDE") or "COLLIDE" in txt.upper().split("\n")[0]
    return fires, txt.replace("\n", " ")[:160]

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
        print(f"[{i+1:2}/{len(items)}] {it['category']:16} oracle={'FIRE' if o else 'silent':6} reader={'FIRE' if r else 'silent'}")
    json.dump(results, open(OUT, "w"), indent=2)

    # ---- analysis ----
    by = defaultdict(lambda: {"n": 0, "oracle": 0, "reader": 0})
    for x in results:
        c = by[x["category"]]
        c["n"] += 1
        c["oracle"] += int(x["oracle_fires"])
        c["reader"] += int(x["reader_fires"])
    print("\n=== detection rates (fire rate per category) ===")
    print(f"{'category':18}{'n':>4}{'oracle':>9}{'reader':>9}{'advantage':>11}")
    for c in ("frame_collision", "matched_control", "binding_conflict"):
        d = by[c]
        orate, rrate = d["oracle"]/d["n"], d["reader"]/d["n"]
        print(f"{c:18}{d['n']:>4}{orate:>9.2f}{rrate:>9.2f}{rrate-orate:>11.2f}")

    fc, mc, bc = by["frame_collision"], by["matched_control"], by["binding_conflict"]
    print("\n=== H1: reader separates frame_collision from matched_control ===")
    tp = fc["reader"]/fc["n"]        # reader fire on real collisions
    fp = mc["reader"]/mc["n"]        # reader fire on matched controls (load-bearing)
    print(f"  reader TP on frame_collision = {tp:.2f}")
    print(f"  reader FP on matched_control = {fp:.2f}   <-- load-bearing cell")
    print(f"  separation (TP - FP)         = {tp-fp:.2f}")
    print(f"  oracle TP on frame_collision = {fc['oracle']/fc['n']:.2f} (predicted ~0, blind)")
    print(f"  H1 SUPPORTED if separation is large AND oracle blind; REFUTED if TP~FP.")
    print("\n=== H2: reader advantage graded by oracle-blindness ===")
    adv = {c: by[c]["reader"]/by[c]["n"] - by[c]["oracle"]/by[c]["n"] for c in by}
    print(f"  advantage frame_collision = {adv['frame_collision']:.2f} (predict LARGE)")
    print(f"  advantage binding_conflict= {adv['binding_conflict']:.2f} (predict ~0, oracle already fires)")
    print(f"  H2 SUPPORTED if advantage(frame) >> advantage(binding); REFUTED if flat.")

if __name__ == "__main__":
    main()
