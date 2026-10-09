#!/usr/bin/env python3
"""Third judge (google/gemini-3.7-flash, 3 asks, majority) for findings where labelers A and B split on verdict."""
from __future__ import annotations
import json, os, sys, collections
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).parent.parent; V = ROOT/"data/scourer/verdicts"
PROMPTS = {"claude": ROOT/"docs/claude-code-system-prompt.md", "codex": ROOT/"data/prompts/codex/gpt5.2_system_prompt.md",
           "gemini": ROOT/"data/prompts/gemini-cli/gemini_cli_system_prompt.txt"}
INSTR = (V/"INSTRUCTIONS.md").read_text()
JUDGE = "google/gemini-3.7-flash"

def call(prompt):
    import openai
    c = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"],
                      default_headers={"X-Title": "arbiter-verdicts-third-judge"}, timeout=900)
    r = c.chat.completions.create(model=JUDGE, messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content or ""

def parse(t):
    t = t.strip()
    if t.startswith("```"): t = t.strip("`").split("\n",1)[-1].rsplit("```",1)[0]
    try:
        d = json.loads(t); d = d[0] if isinstance(d, list) else d
        v = str(d.get("verdict","")).lower()
        return v if v in ("real","overstated","false","unverifiable") else None
    except Exception:
        return None

def main():
    a = {x["id"]: x for x in json.load(open(V/"labels_A.json"))}
    b = {x["id"]: x for x in json.load(open(V/"labels_B.json"))}
    key = json.load(open(V/"key.json"))
    batches = {}
    for p in (V/"batches").glob("*.json"):
        for f in json.load(open(p)): batches[f["id"]] = f
    splits = [i for i in a if i in b and a[i].get("verdict") != b[i].get("verdict")]
    print(len(splits), "splits", flush=True)
    def run(i):
        f = batches[i]; ptxt = PROMPTS[key[i]["prompt"]].read_text()
        prompt = (INSTR + "\n\n## The system prompt\n\n" + ptxt + "\n\n## The finding (label this one only)\n\n" +
                  json.dumps({k: f[k] for k in ("id","description","location","category")}, indent=1) +
                  "\n\nOutput a JSON list with one object.")
        asks = [call(prompt) for _ in range(3)]
        labs = [parse(x) for x in asks]
        maj = collections.Counter(l for l in labs if l).most_common(1)
        return {"id": i, "A": a[i].get("verdict"), "B": b[i].get("verdict"), "third": labs,
                "majority": maj[0][0] if maj and maj[0][1] >= 2 else None, "raw": asks}
    with open(V/"third_judge_raw.jsonl", "w") as fh, ThreadPoolExecutor(max_workers=6) as ex:
        for rec in ex.map(run, splits):
            fh.write(json.dumps(rec)+"\n"); fh.flush()
    print("done")
if __name__ == "__main__": main()
