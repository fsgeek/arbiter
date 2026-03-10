#!/usr/bin/env python3
"""E3 persistent-high-I pilot mapping.

Runs repeated LLM evaluations on a fixed pending-case subset and flags
entries that satisfy a simplified persistent-high-I condition:
- I >= tau_i on all passes
- max(I) - min(I) < epsilon

Outputs:
- data/analysis/e3_persistent_high_i_report.json
- data/analysis/e3_persistent_high_i_report.md
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import openai

from arbiter.block_evaluator import BlockEvaluator
from arbiter.prompt_blocks import PromptCorpus
from arbiter.rules import default_ruleset

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_FILE = REPO_ROOT / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
OUT_JSON = REPO_ROOT / "data" / "analysis" / "e3_persistent_high_i_report.json"
OUT_MD = REPO_ROOT / "data" / "analysis" / "e3_persistent_high_i_report.md"


def _resolve_client_and_model(model: str | None, base_url: str | None) -> tuple[openai.OpenAI, str, str]:
    if base_url:
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("No API key found for specified base URL")
        resolved_model = model or "openai/gpt-4o-mini"
        return openai.OpenAI(api_key=api_key, base_url=base_url), resolved_model, "custom"

    if os.environ.get("OPENROUTER_API_KEY"):
        resolved_model = model or "openai/gpt-4o-mini"
        return (
            openai.OpenAI(
                api_key=os.environ["OPENROUTER_API_KEY"],
                base_url="https://openrouter.ai/api/v1",
            ),
            resolved_model,
            "openrouter",
        )

    if os.environ.get("OPENAI_API_KEY"):
        resolved_model = model or "gpt-4o-mini"
        return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"]), resolved_model, "openai"

    raise RuntimeError("No OPENROUTER_API_KEY or OPENAI_API_KEY found")


def _render_md(report: dict) -> str:
    lines: list[str] = []
    lines.append("# E3 Persistent-High-I Pilot")
    lines.append("")
    lines.append(f"Model: `{report['model']}` ({report['provider']})")
    lines.append(f"Passes: {report['passes']}")
    lines.append(f"Cases per pass: {report['cases_per_pass']}")
    lines.append("")
    lines.append("## Criterion")
    lines.append("")
    lines.append(f"- tau_i: {report['criterion']['tau_i']}")
    lines.append(f"- epsilon: {report['criterion']['epsilon']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(f"- keys evaluated on all passes: {report['evaluated_keys']}")
    lines.append(f"- persistent high-I keys: {report['persistent_count']}")
    lines.append(f"- persistent ratio: {report['persistent_ratio']:.2%}")
    lines.append("")
    lines.append("## Rule/Tier Map")
    lines.append("")
    for row in report["rule_tier_map"]:
        lines.append(f"- {row['rule']} | {row['tier_pair']}: {row['count']}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This pilot does not yet include canon/context mutation sweeps.")
    lines.append("- Use this map to prioritize full persistent-high-I runs in next iteration.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-cases", type=int, default=40)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--tau-i", type=float, default=0.60)
    parser.add_argument("--epsilon", type=float, default=0.03)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    args = parser.parse_args()

    client, model, provider = _resolve_client_and_model(args.model, args.base_url)

    corpus = PromptCorpus(**json.loads(BLOCKS_FILE.read_text()))
    blocks = corpus.blocks
    block_by_id = {b.id: b for b in blocks}

    compiled = default_ruleset().compile()
    evaluator = BlockEvaluator(structural_only=False)
    pending = evaluator.pending_llm_evaluations(blocks, compiled)[: args.max_cases]

    i_values: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for _ in range(args.passes):
        for block_a, block_b, rule, prompt in pending:
            response = client.chat.completions.create(
                model=model,
                max_tokens=3072,
                timeout=args.timeout_seconds,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content
            score = evaluator.parse_llm_score(raw, block_a, block_b, rule)
            i_val = score.i if score.i is not None else 0.0
            key = (score.block_a, score.block_b, score.rule)
            i_values[key].append(i_val)

    persistent = {}
    for key, vals in i_values.items():
        if len(vals) != args.passes:
            continue
        if min(vals) >= args.tau_i and (max(vals) - min(vals)) < args.epsilon:
            persistent[key] = vals

    rule_tier_counter: dict[tuple[str, str], int] = defaultdict(int)
    for (a, b, rule), _vals in persistent.items():
        ta = getattr(block_by_id.get(a), "tier", None)
        tb = getattr(block_by_id.get(b), "tier", None)
        tier_pair = f"{ta}->{tb}"
        rule_tier_counter[(rule, tier_pair)] += 1

    rule_tier_map = [
        {"rule": r, "tier_pair": t, "count": c}
        for (r, t), c in sorted(rule_tier_counter.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))
    ]

    evaluated_keys = sum(1 for v in i_values.values() if len(v) == args.passes)
    persistent_count = len(persistent)
    persistent_ratio = (persistent_count / evaluated_keys) if evaluated_keys else 0.0

    report = {
        "provider": provider,
        "model": model,
        "passes": args.passes,
        "cases_per_pass": len(pending),
        "criterion": {"tau_i": args.tau_i, "epsilon": args.epsilon},
        "evaluated_keys": evaluated_keys,
        "persistent_count": persistent_count,
        "persistent_ratio": persistent_ratio,
        "rule_tier_map": rule_tier_map,
        "parseability": evaluator.parseability_report(),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2))
    OUT_MD.write_text(_render_md(report))

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
