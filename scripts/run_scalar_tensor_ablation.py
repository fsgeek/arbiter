#!/usr/bin/env python3
"""Run scalar-vs-tensor decision ablation on benchmark_v0.

Produces:
- data/analysis/scalar_tensor_ablation_v0.json
- data/analysis/scalar_tensor_ablation_v0.md
"""

from __future__ import annotations

import json
from pathlib import Path

from arbiter.decision_policy import DeterministicDecisionPolicy
from arbiter.interference_tensor import (
    AdjudicationDecision,
    DrafterIdentity,
    TensorEntryV2,
)
from arbiter.pipeline import PromptAnalyzer
from arbiter.prompt_blocks import PromptCorpus, Severity, Tier
from arbiter.rules import default_ruleset

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "docs" / "cairn" / "benchmark_v0_manifest_20260310.json"
OUTPUT_JSON = REPO_ROOT / "data" / "analysis" / "scalar_tensor_ablation_v0.json"
OUTPUT_MD = REPO_ROOT / "data" / "analysis" / "scalar_tensor_ablation_v0.md"


def _scalar_only_decide(score: float, *, tau_reject: float = 0.8, tau_rewrite: float = 0.45) -> AdjudicationDecision:
    """Simple scalar baseline: score-only routing, no indeterminacy channel."""
    if score >= tau_reject:
        return AdjudicationDecision.reject
    if score >= tau_rewrite:
        return AdjudicationDecision.rewrite
    return AdjudicationDecision.accept


def _discrimination_rate(entries: list[TensorEntryV2]) -> dict:
    policy = DeterministicDecisionPolicy()
    compared = 0
    different = 0
    counts: dict[str, int] = {}

    for entry in entries:
        scalar_decision = _scalar_only_decide(entry.score)
        tensor_decision = policy.decide(entry)
        key = f"{scalar_decision.value}->{tensor_decision.value}"
        counts[key] = counts.get(key, 0) + 1
        compared += 1
        if scalar_decision != tensor_decision:
            different += 1

    rate = (different / compared) if compared else 0.0
    return {
        "compared": compared,
        "different": different,
        "discrimination_rate": rate,
        "transitions": counts,
    }


def _load_directed_entries() -> list[TensorEntryV2]:
    with open(REPO_ROOT / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json") as f:
        corpus = PromptCorpus(**json.load(f))

    analyzer = PromptAnalyzer(default_ruleset().compile())
    result = analyzer.analyze_structural(corpus.blocks)
    return result.tensor.entries_v2


def _synthetic_collapse_entries() -> list[TensorEntryV2]:
    """Synthetic cases with near-identical scalar scores but different tensor channels."""
    return [
        TensorEntryV2(
            block_a="synthetic/a1",
            block_b="synthetic/b1",
            rule="scope-overlap-redundancy",
            score=0.55,
            severity=Severity.major,
            t=0.25,
            i=0.75,
            f=0.55,
            tier_a=Tier.system,
            tier_b=Tier.application,
            scope_tags=["security"],
            drafter_identity=DrafterIdentity.unknown,
        ),
        TensorEntryV2(
            block_a="synthetic/a2",
            block_b="synthetic/b2",
            rule="scope-overlap-redundancy",
            score=0.55,
            severity=Severity.minor,
            t=0.45,
            i=0.20,
            f=0.55,
            tier_a=Tier.domain,
            tier_b=Tier.domain,
            scope_tags=["format"],
            drafter_identity=DrafterIdentity.user,
        ),
        TensorEntryV2(
            block_a="synthetic/a3",
            block_b="synthetic/b3",
            rule="mandate-prohibition-conflict",
            score=0.82,
            severity=Severity.critical,
            t=0.10,
            i=0.30,
            f=0.82,
            tier_a=Tier.system,
            tier_b=Tier.domain,
            scope_tags=["safety"],
            drafter_identity=DrafterIdentity.provider,
        ),
        TensorEntryV2(
            block_a="synthetic/a4",
            block_b="synthetic/b4",
            rule="implicit-dependency",
            score=0.48,
            severity=Severity.major,
            t=0.30,
            i=0.68,
            f=0.48,
            tier_a=Tier.system,
            tier_b=Tier.application,
            scope_tags=["privacy"],
            drafter_identity=DrafterIdentity.unknown,
        ),
        TensorEntryV2(
            block_a="synthetic/a5",
            block_b="synthetic/b5",
            rule="verbatim-duplication",
            score=0.46,
            severity=Severity.minor,
            t=0.40,
            i=0.15,
            f=0.46,
            tier_a=Tier.domain,
            tier_b=Tier.domain,
            scope_tags=["style"],
            drafter_identity=DrafterIdentity.user,
        ),
        TensorEntryV2(
            block_a="synthetic/a6",
            block_b="synthetic/b6",
            rule="scope-overlap-redundancy",
            score=0.46,
            severity=Severity.major,
            t=0.10,
            i=0.72,
            f=0.46,
            tier_a=Tier.system,
            tier_b=Tier.application,
            scope_tags=["financial"],
            drafter_identity=DrafterIdentity.unknown,
        ),
    ]


def _build_markdown(report: dict) -> str:
    real = report["real_structural"]
    synthetic = report["synthetic_collapse"]

    lines = []
    lines.append("# Scalar vs Tensor Ablation (v0)")
    lines.append("")
    lines.append(f"Manifest: `{report['manifest_path']}`")
    lines.append("")
    lines.append("## Real Structural Slice")
    lines.append("")
    lines.append(f"- Compared: {real['compared']}")
    lines.append(f"- Decision differences: {real['different']}")
    lines.append(f"- Discrimination rate: {real['discrimination_rate']:.2%}")
    lines.append("")
    lines.append("## Synthetic Collapse Slice")
    lines.append("")
    lines.append(f"- Compared: {synthetic['compared']}")
    lines.append(f"- Decision differences: {synthetic['different']}")
    lines.append(f"- Discrimination rate: {synthetic['discrimination_rate']:.2%}")
    lines.append("")
    lines.append("## Transition Counts (synthetic)")
    lines.append("")
    for k, v in sorted(synthetic["transitions"].items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Real slice uses structural analysis output over frozen prompt corpus.")
    lines.append("- Synthetic slice stress-tests scalar-collapse conditions with controlled fixtures.")
    lines.append("- This is a baseline harness for future evaluator-native declared-loss experiments.")
    return "\n".join(lines)


def main() -> None:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")

    with open(MANIFEST) as f:
        manifest = json.load(f)

    real_entries = _load_directed_entries()
    synthetic_entries = _synthetic_collapse_entries()

    report = {
        "manifest_path": str(MANIFEST.relative_to(REPO_ROOT)),
        "benchmark_id": manifest.get("benchmark_id"),
        "real_structural": _discrimination_rate(real_entries),
        "synthetic_collapse": _discrimination_rate(synthetic_entries),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, indent=2))
    OUTPUT_MD.write_text(_build_markdown(report))

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
