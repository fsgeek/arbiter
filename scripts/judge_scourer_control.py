#!/usr/bin/env python3
"""M4 (pre-registered, secondary): a judge from a family in no arm labels every finding
in every chain as novel / refinement / duplicate relative to the PRIOR passes of its
own chain. Asked twice; a label counts only when both asks agree. Persists every raw
judge response. Judge: google/gemini-3.7-flash (prereg). Chains: the original
10-pass baseline plus the four control arms."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAINS = {"baseline": ROOT / "data/scourer/10pass_gptoss.json",
          **{p.stem: p for p in (ROOT / "data/scourer/control").glob("*.json")}}
OUT = ROOT / "data/scourer/control/m4_judge_raw.jsonl"
JUDGE = "google/gemini-3.7-flash"

PROMPT = """You are judging whether a finding from a later pass of a document-exploration \
chain is new relative to the findings of earlier passes.

Earlier passes found:
{prior}

The finding to judge:
[{category}] {description}
(location: {location})

Label it with exactly one word:
- duplicate: the same observation as an earlier finding, possibly reworded
- refinement: builds on, sharpens, or adds a detail to an earlier finding about the same thing
- novel: an observation about something no earlier finding addressed

Respond with JSON only: {{"label": "<duplicate|refinement|novel>", "closest_prior": "<index of the closest earlier finding, or null>"}}"""


def call(prompt: str) -> str:
    import openai
    c = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"],
                      default_headers={"X-Title": "arbiter-scourer-control-judge"}, timeout=600)
    r = c.chat.completions.create(model=JUDGE, messages=[{"role": "user", "content": prompt}],
                                  extra_body={"metadata": {"label": "m4-judge"}})
    return r.choices[0].message.content or ""


def parse(text: str) -> str | None:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        lab = json.loads(t).get("label", "").strip().lower()
        return lab if lab in ("duplicate", "refinement", "novel") else None
    except Exception:
        for w in ("duplicate", "refinement", "novel"):
            if w in t.lower():
                return w
        return None


def jobs():
    for chain, path in CHAINS.items():
        reps = json.load(open(path))["reports"]
        prior: list[str] = []
        for r in reps:
            for i, f in enumerate(r["findings"]):
                if r["pass_number"] > 1:
                    yield (chain, r["pass_number"], i, f, list(prior))
            prior += [f"{len(prior)+j+1}. [{f['category']}] {f['description']}" for j, f in enumerate(r["findings"])]


def run(job):
    chain, pn, i, f, prior = job
    prompt = PROMPT.format(prior="\n".join(prior), category=f["category"], description=f["description"], location=f.get("location", ""))
    labels = []
    raws = []
    for ask in (1, 2):
        raw = call(prompt)
        raws.append(raw)
        labels.append(parse(raw))
    return {"chain": chain, "pass": pn, "idx": i, "labels": labels, "agreed": labels[0] if labels[0] == labels[1] else None, "raw": raws}


def main() -> None:
    js = list(jobs())
    print(f"{len(js)} findings to judge (x2 asks)", flush=True)
    done = 0
    with open(OUT, "w") as fh, ThreadPoolExecutor(max_workers=8) as ex:
        for rec in ex.map(run, js):
            fh.write(json.dumps(rec) + "\n"); fh.flush()
            done += 1
            if done % 25 == 0:
                print(f"{done}/{len(js)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
