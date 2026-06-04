"""Experiment: does the neutral reader detect collisions BURIED in realistic composed prompts?

Pre-registered in docs/research/prereg_burial.md (committed BEFORE the corpus existed).
This is the deployment condition: the reader instrument is run on all C(n,2) fragment pairs
extracted from multi-fragment system prompts, not on isolated pairs.

Two hypotheses (from prereg):
  H1-BURIAL: detection rate on positive prompts >= 0.70 (refuted if < 0.50)
  H2-BURIAL-FP: prompt-level FP rate on negative prompts <= 0.20 (refuted if > 0.40)

Instrument is REUSED VERBATIM from hard_negatives.py — same POLICY, same READER_PROMPT,
same model. Only the input shape changes: pairs extracted from composed prompts.
"""
from __future__ import annotations

import itertools
import json
import os

from openai import OpenAI

CORPUS = "/home/tony/projects/arbiter/experiments/burial_corpus.json"
MODEL = "anthropic/claude-haiku-4-5"
OUT = "/home/tony/projects/arbiter/experiments/burial_results.json"

# ---- Instrument: neutral reader (REUSED VERBATIM from hard_negatives.py) -----
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
    raw = resp.choices[0].message.content or ""
    txt = raw.strip()
    fires = txt.upper().lstrip().startswith("COLLIDE") or "COLLIDE" in txt.upper().split("\n")[0]
    return fires, txt.replace("\n", " ")[:200]


def main() -> None:
    prompts = json.load(open(CORPUS))
    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"])

    results = []
    total_pairs = sum(
        len(p["fragments"]) * (len(p["fragments"]) - 1) // 2
        for p in prompts
    )
    pair_idx = 0

    for prompt in prompts:
        prompt_id = prompt["id"]
        category = prompt["category"]
        fragments = prompt["fragments"]
        gt = prompt["ground_truth"]
        collision_indices = prompt.get("collision_indices")  # None for negatives
        n = len(fragments)
        n_pairs = n * (n - 1) // 2

        pair_results = []
        print(f"\n--- {prompt_id} ({category}, n={n}, {n_pairs} pairs) ---")

        for i, j in itertools.combinations(range(n), 2):
            a, b = fragments[i], fragments[j]
            fires, why = neutral_reader(client, a, b)
            pair_idx += 1
            pair_results.append({
                "pair": [i, j],
                "fires": fires,
                "why": why,
            })
            flag = "COLLIDE" if fires else "ok    "
            gt_mark = ""
            if collision_indices and [i, j] == collision_indices:
                gt_mark = " <-- PLANTED"
            print(f"  [{pair_idx:3}/{total_pairs}] ({i},{j}) {flag}{gt_mark}  {why[:80]}")

        # Prompt-level: any-COLLIDE
        collide_pairs = [pr for pr in pair_results if pr["fires"]]
        prompt_collide = len(collide_pairs) > 0

        # For positive prompts: did the reader find the planted collision specifically?
        planted_detected = False
        planted_fired = False
        if category == "positive" and collision_indices:
            planted = next(
                (pr for pr in pair_results if pr["pair"] == collision_indices),
                None,
            )
            if planted:
                planted_fired = planted["fires"]
            planted_detected = planted_fired

        results.append({
            "id": prompt_id,
            "category": category,
            "ground_truth": gt,
            "n_fragments": n,
            "n_pairs": n_pairs,
            "collision_indices": collision_indices,
            "prompt_collide": prompt_collide,          # any-COLLIDE verdict
            "planted_detected": planted_detected,       # positive only: planted pair found
            "collide_pairs": [[pr["pair"], pr["why"]] for pr in collide_pairs],
            "pair_results": pair_results,
        })

    json.dump(results, open(OUT, "w"), indent=2)
    print(f"\nResults written to {OUT}")

    # ---- Analysis ----
    positives = [r for r in results if r["category"] == "positive"]
    negatives = [r for r in results if r["category"] == "negative"]

    n_pos = len(positives)
    n_neg = len(negatives)

    # H1-BURIAL: detection rate (any-COLLIDE on positive prompts)
    detected = [r for r in positives if r["prompt_collide"]]
    detection_rate = len(detected) / n_pos if n_pos else 0.0

    # For positive: how many detected the CORRECT (planted) pair?
    correct_localizations = [r for r in positives if r["planted_detected"]]
    localization_rate = len(correct_localizations) / n_pos if n_pos else 0.0

    # Note: some detections may fire on a wrong pair but not the planted one
    detected_wrong_pair = [r for r in positives if r["prompt_collide"] and not r["planted_detected"]]

    # H2-BURIAL-FP: prompt-level FP rate on negatives
    fp_prompts = [r for r in negatives if r["prompt_collide"]]
    fp_rate = len(fp_prompts) / n_neg if n_neg else 0.0

    # Pair-level FP rate on negatives (for transparency)
    neg_total_pairs = sum(r["n_pairs"] for r in negatives)
    neg_fired_pairs = sum(len(r["collide_pairs"]) for r in negatives)
    pair_fp_rate = neg_fired_pairs / neg_total_pairs if neg_total_pairs else 0.0

    print("\n" + "=" * 65)
    print("=== BURIAL EXPERIMENT RESULTS ===")
    print("=" * 65)
    print(f"\nPositive prompts (n={n_pos}):")
    print(f"  Detection rate (any-COLLIDE)        = {detection_rate:.2f}  ({len(detected)}/{n_pos})")
    print(f"  Planted-pair localization rate       = {localization_rate:.2f}  ({len(correct_localizations)}/{n_pos})")
    print(f"  Detected via wrong pair only         = {len(detected_wrong_pair)}/{n_pos}")

    print(f"\nNegative prompts (n={n_neg}):")
    print(f"  Prompt-level FP rate                 = {fp_rate:.2f}  ({len(fp_prompts)}/{n_neg})")
    print(f"  Pair-level FP rate (transparency)    = {pair_fp_rate:.2f}  ({neg_fired_pairs}/{neg_total_pairs})")

    print("\n=== H1-BURIAL: detection rate on positive prompts ===")
    print(f"  detection_rate = {detection_rate:.2f}  (predicted >= 0.70; REFUTE if < 0.50)")
    if detection_rate >= 0.70:
        print(f"  H1-BURIAL SUPPORTED: {detection_rate:.2f} >= 0.70")
    elif detection_rate >= 0.50:
        print(f"  H1-BURIAL BORDERLINE: {detection_rate:.2f} below threshold but above refutation line 0.50")
    else:
        print(f"  H1-BURIAL REFUTED: {detection_rate:.2f} < 0.50 -- reader fails to generalize to deployment shape")

    print("\n=== H2-BURIAL-FP: prompt-level false-positive rate on negatives ===")
    print(f"  fp_rate = {fp_rate:.2f}  (predicted <= 0.20; REFUTE if > 0.40)")
    if fp_rate <= 0.20:
        print(f"  H2-BURIAL-FP SUPPORTED: {fp_rate:.2f} <= 0.20 (stronger than pair-level baseline)")
    elif fp_rate <= 0.40:
        print(f"  H2-BURIAL-FP BORDERLINE: {fp_rate:.2f} above threshold but below refutation line 0.40")
    else:
        print(f"  H2-BURIAL-FP REFUTED: {fp_rate:.2f} > 0.40 -- too many false alarms on non-colliding prompts")

    print("\n=== Localization diagnostic ===")
    if detection_rate >= 0.70:
        if localization_rate >= 0.70:
            print(f"  Pairwise extraction working as intended: detects AND localizes at {localization_rate:.2f}")
        else:
            print(f"  WARNING: detects at {detection_rate:.2f} but correct localization only {localization_rate:.2f}")
            print("  => any-COLLIDE flag is partially driven by incidental near-tension pairs")

    print("\n=== Positive misses (planted collision not detected) ===")
    missed = [r for r in positives if not r["planted_detected"]]
    if not missed:
        print("  (none — reader caught all planted collisions)")
    else:
        for r in missed:
            ci = r["collision_indices"]
            frags = None
            # find fragment texts from corpus
            corp_item = next(p for p in json.load(open(CORPUS)) if p["id"] == r["id"])
            fa = corp_item["fragments"][ci[0]]
            fb = corp_item["fragments"][ci[1]]
            # get what the reader said for that pair
            planted_pr = next(
                (pr for pr in r["pair_results"] if pr["pair"] == ci),
                None,
            )
            why = planted_pr["why"] if planted_pr else "N/A"
            print(f"  MISS {r['id']}: planted pair ({ci[0]},{ci[1]})")
            print(f"    A: {fa[:80]}")
            print(f"    B: {fb[:80]}")
            print(f"    reader said: {why[:120]}")
            if r["collide_pairs"]:
                print(f"    (but flagged {len(r['collide_pairs'])} other pair(s) as COLLIDE)")

    print("\n=== Negative false positives (non-colliding prompt flagged COLLIDE) ===")
    if not fp_prompts:
        print("  (none — reader stayed silent on all negative prompts)")
    else:
        corp = {p["id"]: p for p in json.load(open(CORPUS))}
        for r in fp_prompts:
            print(f"  FP {r['id']}:")
            for pair_idx_fp, why in r["collide_pairs"]:
                i, j = pair_idx_fp
                frags = corp[r["id"]]["fragments"]
                print(f"    pair ({i},{j}) fired:")
                print(f"      A: {frags[i][:80]}")
                print(f"      B: {frags[j][:80]}")
                print(f"      reader: {why[:120]}")


if __name__ == "__main__":
    main()
