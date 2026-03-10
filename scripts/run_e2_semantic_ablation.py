#!/usr/bin/env python3
"""E2 semantic-augmented scalar-vs-tensor ablation rerun.

Runs bounded LLM rule evaluations on the Claude Code benchmark corpus,
then compares scalar-only routing vs tensor-v2 routing on resulting entries.

Outputs:
- data/analysis/e2_semantic_ablation_report.json
- data/analysis/e2_semantic_ablation_report.md
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import openai

from arbiter.block_evaluator import BlockEvaluator
from arbiter.decision_policy import DeterministicDecisionPolicy
from arbiter.interference_tensor import AdjudicationDecision, TensorEntryV2
from arbiter.prompt_blocks import PromptCorpus
from arbiter.rules import default_ruleset

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKS_FILE = REPO_ROOT / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
DEFAULT_OUT_JSON = REPO_ROOT / "data" / "analysis" / "e2_semantic_ablation_report.json"
DEFAULT_OUT_MD = REPO_ROOT / "data" / "analysis" / "e2_semantic_ablation_report.md"


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


def _scalar_only_decide(score: float, *, tau_reject: float = 0.8, tau_rewrite: float = 0.45) -> AdjudicationDecision:
    if score >= tau_reject:
        return AdjudicationDecision.reject
    if score >= tau_rewrite:
        return AdjudicationDecision.rewrite
    return AdjudicationDecision.accept


def _discrimination(entries: list[TensorEntryV2], policy: DeterministicDecisionPolicy) -> dict:
    compared = 0
    different = 0
    transitions: dict[str, int] = {}
    for entry in entries:
        scalar_decision = _scalar_only_decide(entry.score)
        tensor_decision = policy.decide(entry)
        key = f"{scalar_decision.value}->{tensor_decision.value}"
        transitions[key] = transitions.get(key, 0) + 1
        compared += 1
        if scalar_decision != tensor_decision:
            different += 1
    rate = (different / compared) if compared else 0.0
    return {
        "compared": compared,
        "different": different,
        "discrimination_rate": rate,
        "transitions": transitions,
    }


def _render_md(report: dict) -> str:
    d = report["discrimination"]
    p = report["parseability"]
    lines: list[str] = []
    lines.append("# E2 Semantic-Augmented Ablation Report")
    lines.append("")
    lines.append(f"Model: `{report['model']}` ({report['provider']})")
    if report.get("run_tag"):
        lines.append(f"Run tag: `{report['run_tag']}`")
    lines.append(f"Pending LLM cases available: {report['pending_total']}")
    lines.append(f"LLM cases executed: {report['llm_cases_executed']}")
    lines.append(f"Tensor entries total: {report['tensor_entries_total']}")
    lines.append("")
    lines.append("## Discrimination")
    lines.append("")
    lines.append(f"- Compared: {d['compared']}")
    lines.append(f"- Different decisions: {d['different']}")
    lines.append(f"- Discrimination rate: {d['discrimination_rate']:.2%}")
    lines.append("")
    lines.append("## Transition counts")
    lines.append("")
    for k, v in sorted(d["transitions"].items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Parseability")
    lines.append("")
    lines.append(f"- JSON parse fail rate: {p['json_parse_fail_rate']:.2%}")
    lines.append(f"- t present rate: {p['optional_t_rate']:.2%}")
    lines.append(f"- i present rate: {p['optional_i_rate']:.2%}")
    lines.append(f"- f present rate: {p['optional_f_rate']:.2%}")
    lines.append(f"- evidence_quality present rate: {p['optional_evidence_quality_rate']:.2%}")
    lines.append(f"- declared_losses present rate: {p['optional_declared_losses_rate']:.2%}")
    lines.append(f"- decision present rate: {p['optional_decision_rate']:.2%}")
    lines.append(f"- drafter_identity present rate: {p['optional_drafter_identity_rate']:.2%}")
    lines.append(f"- malformed declared-loss rate: {p['malformed_declared_losses_rate']:.2%}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-cases", type=int, default=40, help="Max LLM pair evaluations")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--run-tag", type=str, default=None, help="Optional suffix for output filenames")
    parser.add_argument("--timeout-seconds", type=float, default=60.0, help="Per-call timeout")
    args = parser.parse_args()

    client, model, provider = _resolve_client_and_model(args.model, args.base_url)

    corpus = PromptCorpus(**json.loads(BLOCKS_FILE.read_text()))
    blocks = corpus.blocks
    compiled = default_ruleset().compile()

    evaluator = BlockEvaluator(structural_only=False)

    structural_scores = evaluator.evaluate_all_structural(blocks, compiled)
    pending = evaluator.pending_llm_evaluations(blocks, compiled)
    pending_total = len(pending)
    pending = pending[: args.max_cases]

    llm_scores = []
    for block_a, block_b, rule, prompt in pending:
        response = client.chat.completions.create(
            model=model,
            max_tokens=3072,
            timeout=args.timeout_seconds,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content
        llm_scores.append(evaluator.parse_llm_score(raw, block_a, block_b, rule))

    all_scores = structural_scores + llm_scores
    tensor = evaluator.assemble_tensor(blocks, compiled, all_scores, threshold=0.0)

    policy = DeterministicDecisionPolicy()
    report = {
        "provider": provider,
        "model": model,
        "run_tag": args.run_tag,
        "pending_total": pending_total,
        "llm_cases_executed": len(pending),
        "structural_scores": len(structural_scores),
        "llm_scores": len(llm_scores),
        "tensor_entries_total": len(tensor.entries_v2),
        "discrimination": _discrimination(tensor.entries_v2, policy),
        "parseability": evaluator.parseability_report(),
    }

    out_json = DEFAULT_OUT_JSON
    out_md = DEFAULT_OUT_MD
    if args.run_tag:
        out_json = REPO_ROOT / "data" / "analysis" / f"e2_semantic_ablation_report_{args.run_tag}.json"
        out_md = REPO_ROOT / "data" / "analysis" / f"e2_semantic_ablation_report_{args.run_tag}.md"

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2))
    out_md.write_text(_render_md(report))

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
