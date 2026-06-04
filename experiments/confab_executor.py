"""Execute the confabulation corpus against Haiku at temperature=0.0.

Pre-registered in docs/research/prereg_confabulation_correlation.md.

For each item in confab_corpus.json:
- Concatenate fragments as a natural system prompt
- Run anthropic/claude-haiku-4-5 via OpenRouter at t=0.0
- Record the response

Writes experiments/confab_executor_results.json.
"""
from __future__ import annotations

import json
import os

from openai import OpenAI

MODEL = "anthropic/claude-haiku-4-5"
CORPUS = "/home/tony/projects/arbiter/experiments/confab_corpus.json"
OUT = "/home/tony/projects/arbiter/experiments/confab_executor_results.json"


def build_system_prompt(fragments: list[str]) -> str:
    """Concatenate fragments as a natural system prompt — one paragraph/line each."""
    return "\n\n".join(fragments)


def run_item(client: OpenAI, item: dict, idx: int, total: int) -> dict:
    system_prompt = build_system_prompt(item["fragments"])
    user_query = item["user_query"]

    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.0,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
    )
    response_text = resp.choices[0].message.content or ""

    preview = response_text.replace("\n", " ")[:80]
    print(f"[{idx:02}/{total}] {item['id']} bucket={item['bucket']} | {preview}")

    return {
        "id": item["id"],
        "bucket": item["bucket"],
        "epsilon_f": item["epsilon_f"],
        "user_query": user_query,
        "response": response_text,
        "fragments": item["fragments"],
    }


def main() -> None:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

    with open(CORPUS) as f:
        corpus = json.load(f)

    total = len(corpus)
    print(f"Running {total} items at temperature=0.0 via {MODEL}")

    results = []
    for idx, item in enumerate(corpus, start=1):
        result = run_item(client, item, idx, total)
        results.append(result)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults written to {OUT}")
    print(f"Total items: {len(results)}")

    # Quick bucket summary
    from collections import defaultdict
    by_bucket: dict[int, list] = defaultdict(list)
    for r in results:
        by_bucket[r["bucket"]].append(r)
    print("\n=== Bucket summary ===")
    for b in sorted(by_bucket):
        items = by_bucket[b]
        eps_vals = [i["epsilon_f"] for i in items]
        print(f"  Bucket {b}: {len(items)} items, ε_F = {[round(e, 3) for e in eps_vals]}")


if __name__ == "__main__":
    main()
