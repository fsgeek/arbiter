#!/usr/bin/env python3
"""E1 parseability run for optional tensor-v2 LLM output fields.

Runs a bounded batch of pending LLM rule evaluations and reports:
- JSON parse failure rate
- optional field presence rates (t/i/f, evidence_quality, declared_losses, decision, drafter_identity)
- malformed declared-loss rate

Output:
- data/analysis/e1_parseability_report.json
- data/analysis/e1_parseability_report.md
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import openai

from arbiter.block_evaluator import BlockEvaluator
from arbiter.prompt_blocks import PromptCorpus
from arbiter.rules import default_ruleset

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_FILE = REPO_ROOT / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
OUT_JSON = REPO_ROOT / "data" / "analysis" / "e1_parseability_report.json"
OUT_MD = REPO_ROOT / "data" / "analysis" / "e1_parseability_report.md"


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


def _build_markdown(report: dict) -> str:
    stats = report["parseability"]
    lines = []
    lines.append("# E1 Parseability Report")
    lines.append("")
    lines.append(f"Model: `{report['model']}` ({report['provider']})")
    lines.append(f"Cases evaluated: {report['cases_evaluated']}")
    lines.append("")
    lines.append("## Parseability")
    lines.append("")
    lines.append(f"- JSON parse fail rate: {stats['json_parse_fail_rate']:.2%}")
    lines.append(f"- t present rate: {stats['optional_t_rate']:.2%}")
    lines.append(f"- i present rate: {stats['optional_i_rate']:.2%}")
    lines.append(f"- f present rate: {stats['optional_f_rate']:.2%}")
    lines.append(f"- evidence_quality present rate: {stats['optional_evidence_quality_rate']:.2%}")
    lines.append(f"- declared_losses present rate: {stats['optional_declared_losses_rate']:.2%}")
    lines.append(f"- decision present rate: {stats['optional_decision_rate']:.2%}")
    lines.append(f"- drafter_identity present rate: {stats['optional_drafter_identity_rate']:.2%}")
    lines.append(f"- malformed declared-loss rate: {stats['malformed_declared_losses_rate']:.2%}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Batch is bounded and intended for protocol validation, not final performance claims.")
    lines.append("- Missing optional fields are expected during transition; this report tracks elicitation progress.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--base-url", type=str, default=None)
    args = parser.parse_args()

    client, model, provider = _resolve_client_and_model(args.model, args.base_url)

    corpus = PromptCorpus(**json.loads(BLOCKS_FILE.read_text()))
    rule_set = default_ruleset().compile()

    evaluator = BlockEvaluator(structural_only=False)
    pending = evaluator.pending_llm_evaluations(corpus.blocks, rule_set)
    pending = pending[: args.max_cases]

    scored = 0
    for block_a, block_b, rule, prompt in pending:
        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content
        evaluator.parse_llm_score(raw, block_a, block_b, rule)
        scored += 1

    report = {
        "provider": provider,
        "model": model,
        "cases_evaluated": scored,
        "parseability": evaluator.parseability_report(),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2))
    OUT_MD.write_text(_build_markdown(report))

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
