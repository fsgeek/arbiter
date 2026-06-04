"""
Compare original Mistral judge (confab_scores.json) vs independent DeepSeek judge
(confab_scores_independent.json). Compute Cohen's kappa on compliance_violation
and conflict_acknowledged. Report every disagreement.
"""

import json
import math

BASE = "/home/tony/projects/arbiter/experiments"

with open(f"{BASE}/confab_scores.json") as f:
    original = json.load(f)
with open(f"{BASE}/confab_scores_independent.json") as f:
    independent = json.load(f)

orig_by_id = {r["id"]: r for r in original}
indep_by_id = {r["id"]: r for r in independent}

ids = sorted(orig_by_id.keys())
assert len(ids) == 30, f"Expected 30 items, got {len(ids)}"

# Align
rows = []
for id_ in ids:
    o = orig_by_id[id_]
    i = indep_by_id[id_]
    rows.append({
        "id": id_,
        "bucket": o["bucket"],
        "epsilon_f": o["epsilon_f"],
        "orig_violation": bool(o["compliance_violation"]),
        "indep_violation": bool(i["compliance_violation"]),
        "orig_ack": bool(o["conflict_acknowledged"]),
        "indep_ack": bool(i["conflict_acknowledged"]),
        "orig_vfrag": o.get("violated_fragment"),
        "indep_vfrag": i.get("violated_fragment"),
    })


def cohen_kappa(a, b):
    """Compute Cohen's kappa for two binary lists."""
    n = len(a)
    assert n == len(b)
    tp = sum(1 for x, y in zip(a, b) if x and y)
    tn = sum(1 for x, y in zip(a, b) if not x and not y)
    fp = sum(1 for x, y in zip(a, b) if not x and y)  # orig=F indep=T
    fn = sum(1 for x, y in zip(a, b) if x and not y)  # orig=T indep=F
    po = (tp + tn) / n
    pe = ((tp + fn) / n) * ((tp + fp) / n) + ((tn + fp) / n) * ((tn + fn) / n)
    if pe == 1.0:
        return 1.0, tp, tn, fp, fn
    kappa = (po - pe) / (1 - pe)
    return kappa, tp, tn, fp, fn


def kappa_se(kappa, n):
    """Approximate SE for kappa (Fleiss et al.)."""
    return math.sqrt((1 - kappa) / (n * (1 - 0.0)))  # simplified


orig_v = [r["orig_violation"] for r in rows]
indep_v = [r["indep_violation"] for r in rows]
orig_a = [r["orig_ack"] for r in rows]
indep_a = [r["indep_ack"] for r in rows]

kappa_v, tp_v, tn_v, fp_v, fn_v = cohen_kappa(orig_v, indep_v)
kappa_a, tp_a, tn_a, fp_a, fn_a = cohen_kappa(orig_a, indep_a)

# Agreement table
print("=" * 70)
print("COMPLIANCE_VIOLATION — agreement table")
print(f"  Both True  (agree-violation): {tp_v}")
print(f"  Both False (agree-clean):     {tn_v}")
print(f"  Orig=F, Indep=T (indep finds more): {fp_v}")
print(f"  Orig=T, Indep=F (orig finds more):  {fn_v}")
print(f"  Cohen's kappa = {kappa_v:.4f}")
print()

print("CONFLICT_ACKNOWLEDGED — agreement table")
print(f"  Both True:   {tp_a}")
print(f"  Both False:  {tn_a}")
print(f"  Orig=F, Indep=T: {fp_a}")
print(f"  Orig=T, Indep=F: {fn_a}")
print(f"  Cohen's kappa = {kappa_a:.4f}")
print()

# Verdict table (all 30)
print("=" * 70)
print("RAW VERDICT TABLE")
print(f"{'ID':<20} {'bkt':>3} {'ε_F':>6} | {'orig_V':>6} {'indep_V':>7} {'agree':>5} | {'orig_A':>6} {'indep_A':>7}")
print("-" * 70)
disagree_v = []
disagree_a = []
for r in rows:
    agree_v = "YES" if r["orig_violation"] == r["indep_violation"] else "NO "
    if r["orig_violation"] != r["indep_violation"]:
        disagree_v.append(r)
    if r["orig_ack"] != r["indep_ack"]:
        disagree_a.append(r)
    print(
        f"{r['id']:<20} {r['bucket']:>3} {r['epsilon_f']:>6.3f} | "
        f"{str(r['orig_violation']):>6} {str(r['indep_violation']):>7} {agree_v:>5} | "
        f"{str(r['orig_ack']):>6} {str(r['indep_ack']):>7}"
    )

print()
print("=" * 70)
print(f"DISAGREEMENTS ON compliance_violation ({len(disagree_v)}):")
for r in disagree_v:
    direction = "orig=T indep=F" if r["orig_violation"] and not r["indep_violation"] else "orig=F indep=T"
    print(f"  {r['id']} (bucket {r['bucket']}, ε_F={r['epsilon_f']:.3f}): {direction}")

print()
print(f"DISAGREEMENTS ON conflict_acknowledged ({len(disagree_a)}):")
for r in disagree_a:
    direction = "orig=T indep=F" if r["orig_ack"] and not r["indep_ack"] else "orig=F indep=T"
    print(f"  {r['id']} (bucket {r['bucket']}, ε_F={r['epsilon_f']:.3f}): {direction}")

print()
print("=" * 70)
print("SUMMARY")
print(f"  N = 30 triples")
print(f"  compliance_violation: κ = {kappa_v:.4f}  ({tp_v}TP {tn_v}TN {fp_v}FP {fn_v}FN)")
print(f"  conflict_acknowledged: κ = {kappa_a:.4f}  ({tp_a}TP {tn_a}TN {fp_a}FP {fn_a}FN)")
print()
# Thresholds from prereg
if kappa_v >= 0.6:
    verdict_v = "SUPPORTED (κ ≥ 0.6)"
elif kappa_v >= 0.4:
    verdict_v = "INCONCLUSIVE (0.4 ≤ κ < 0.6)"
else:
    verdict_v = "REFUTED (κ < 0.4)"
if kappa_a >= 0.6:
    verdict_a = "SUPPORTED (κ ≥ 0.6)"
elif kappa_a >= 0.4:
    verdict_a = "INCONCLUSIVE (0.4 ≤ κ < 0.6)"
else:
    verdict_a = "REFUTED (κ < 0.4)"
print(f"  H-JUDGE:     {verdict_v}")
print(f"  H-JUDGE-ACK: {verdict_a}")
print()

# Counts
orig_pos = sum(orig_v)
indep_pos = sum(indep_v)
print(f"  Original judge: {orig_pos}/30 violations")
print(f"  Independent judge: {indep_pos}/30 violations")
