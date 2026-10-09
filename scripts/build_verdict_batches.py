#!/usr/bin/env python3
"""Anonymize, shuffle, and batch every scourer finding for blind labeling (prereg_scourer_verdicts.md).
Writes data/scourer/verdicts/key.json (id -> chain/pass/model; NOT given to labelers) and
data/scourer/verdicts/batches/<prompt>_<nn>.json."""
from __future__ import annotations
import json, random, glob
from pathlib import Path
ROOT = Path(__file__).parent.parent
V = ROOT / "data/scourer/verdicts"; B = V / "batches"; B.mkdir(parents=True, exist_ok=True)
CHAINS = {"orig_claude": ("claude", ROOT/"data/scourer/10pass_gptoss.json"),
          "orig_codex": ("codex", ROOT/"data/scourer/codex_pass2_grok.json"),
          "orig_gemini": ("gemini", ROOT/"data/scourer/gemini_pass3_glm.json")}
for p in sorted(glob.glob(str(ROOT/"data/scourer/control/*.json"))):
    CHAINS["ctrl_"+Path(p).stem] = ("claude", Path(p))
rng = random.Random(20261009)
items = []
for chain, (prompt, path) in CHAINS.items():
    for r in json.load(open(path))["reports"]:
        for i, f in enumerate(r["findings"]):
            items.append({"chain": chain, "prompt": prompt, "pass": r["pass_number"], "model": r.get("model"),
                          "idx": i, "description": f["description"], "location": f.get("location",""), "category": f.get("category","")})
rng.shuffle(items)
ids = [f"F{n:04d}" for n in rng.sample(range(1000, 9999), len(items))]
key = {}
by_prompt: dict[str, list] = {}
for it, fid in zip(items, ids):
    key[fid] = {k: it[k] for k in ("chain", "prompt", "pass", "model", "idx")}
    by_prompt.setdefault(it["prompt"], []).append({"id": fid, "description": it["description"], "location": it["location"], "category": it["category"]})
json.dump(key, open(V/"key.json", "w"), indent=1)
SIZE = 26
manifest = []
for prompt, lst in by_prompt.items():
    for n, s in enumerate(range(0, len(lst), SIZE)):
        name = f"{prompt}_{n:02d}.json"
        json.dump(lst[s:s+SIZE], open(B/name, "w"), indent=1)
        manifest.append({"batch": name, "prompt": prompt, "n": len(lst[s:s+SIZE])})
json.dump(manifest, open(V/"manifest.json", "w"), indent=1)
print(len(items), "findings;", len(manifest), "batches:", [(m["batch"], m["n"]) for m in manifest])
