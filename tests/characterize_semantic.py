"""Characterize semantic conflict detection across models and prompt variants.

Tests whether Haiku's semantic conflict failure is:
  (a) a capability limitation (can't do 3-hop reasoning), or
  (b) token-sensitive (specific formatting triggers/prevents detection)

Runs N trials per model × prompt variant. Outputs pass rates as a table
and raw results as JSON for the model registry.

Usage:
    python tests/characterize_semantic.py [--trials 5]

Default is 5 trials per cell (5 models × 4 variants × 5 trials = 100 API calls).
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from arbiter.evaluator import AnthropicEvaluator, OpenAICompatibleEvaluator
from arbiter.models import DomainLayer, EvaluationResult, SystemLayer

# ---------------------------------------------------------------------------
# OpenRouter attribution
# ---------------------------------------------------------------------------

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/fsgeek/arbiter",
    "X-Title": "Arbiter conflict-detection",
}

# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------


def _make_models() -> dict:
    """Return available model evaluators keyed by display name."""
    models = {}

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        models["anthropic/haiku-4.5"] = lambda k=anthropic_key: AnthropicEvaluator(
            model="claude-haiku-4-5-20251001", api_key=k,
        )

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        models["openai/gpt-4o-mini"] = lambda k=openai_key: OpenAICompatibleEvaluator(
            model="gpt-4o-mini", api_key=k,
        )

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        models["google/gemini-2.0-flash"] = lambda k=openrouter_key: OpenAICompatibleEvaluator(
            model="google/gemini-2.0-flash-001",
            base_url="https://openrouter.ai/api/v1",
            api_key=k,
            extra_headers=_OPENROUTER_HEADERS,
        )
        models["qwen/qwen-2.5-72b"] = lambda k=openrouter_key: OpenAICompatibleEvaluator(
            model="qwen/qwen-2.5-72b-instruct",
            base_url="https://openrouter.ai/api/v1",
            api_key=k,
            extra_headers=_OPENROUTER_HEADERS,
        )
        models["x-ai/grok-3-mini"] = lambda k=openrouter_key: OpenAICompatibleEvaluator(
            model="x-ai/grok-3-mini",
            base_url="https://openrouter.ai/api/v1",
            api_key=k,
            extra_headers=_OPENROUTER_HEADERS,
        )

    return models


# ---------------------------------------------------------------------------
# Prompt variants — same semantic content, different surface formatting.
#
# The three-hop chain:
#   1. "use created_ts for time queries"
#   2. "only id and name are indexed"
#   3. "never use unindexed columns in WHERE"
#
# If Haiku's failure is token-sensitive, some variants will pass more
# than others. If it's capability-limited, all variants fail equally.
# ---------------------------------------------------------------------------

SYSTEM = SystemLayer(
    name="query-rules",
    rules=[
        "Generate valid SQL for the user query.",
        "Report conflicts rather than resolving them silently.",
    ],
)

VARIANTS: dict[str, tuple[DomainLayer, str]] = {
    # Original — the baseline from session 1
    "baseline": (
        DomainLayer(
            name="schema-knowledge",
            entries=[
                "Use the column records.created_ts for time-based queries.",
                "The records table indexes: id, name. No other columns are indexed.",
                "Never use unindexed columns in WHERE clauses on large tables.",
            ],
        ),
        "Find records created in the last 30 days",
    ),
    # Reversed entry order — prohibition first, recommendation last
    "reversed": (
        DomainLayer(
            name="schema-knowledge",
            entries=[
                "Never use unindexed columns in WHERE clauses on large tables.",
                "The records table indexes: id, name. No other columns are indexed.",
                "Use the column records.created_ts for time-based queries.",
            ],
        ),
        "Find records created in the last 30 days",
    ),
    # Colon-label style — more structured, less narrative
    "colon-labels": (
        DomainLayer(
            name="schema-knowledge",
            entries=[
                "Recommended column for time queries: records.created_ts",
                "Indexed columns on records table: id, name (no others are indexed)",
                "Performance rule: never use unindexed columns in WHERE clauses on large tables",
            ],
        ),
        "Find records created in the last 30 days",
    ),
    # Question-form query — imperative vs interrogative
    "question-query": (
        DomainLayer(
            name="schema-knowledge",
            entries=[
                "Use the column records.created_ts for time-based queries.",
                "The records table indexes: id, name. No other columns are indexed.",
                "Never use unindexed columns in WHERE clauses on large tables.",
            ],
        ),
        "What records were created in the last 30 days?",
    ),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class TrialResult:
    model: str
    variant: str
    trial: int
    detected_conflict: bool
    num_conflicts: int
    error: str | None = None
    raw_output: str | None = None


def run_trial(evaluator, domain: DomainLayer, query: str) -> tuple[bool, int, str | None, str | None]:
    """Run a single evaluation. Returns (detected_conflict, num_conflicts, error, raw_output)."""
    try:
        result = evaluator.evaluate(SYSTEM, domain, query)
        return (
            not result.resolved,
            len(result.conflicts),
            None,
            result.output,
        )
    except Exception as e:
        return (False, 0, str(e), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=5, help="Trials per model×variant cell")
    parser.add_argument("--output", type=str, default=None, help="JSON output file")
    args = parser.parse_args()

    models = _make_models()
    if not models:
        print("ERROR: No API keys found. Set at least one of:")
        print("  ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY")
        sys.exit(1)

    print(f"Models: {list(models.keys())}")
    print(f"Variants: {list(VARIANTS.keys())}")
    print(f"Trials per cell: {args.trials}")
    print(f"Total API calls: {len(models) * len(VARIANTS) * args.trials}")
    print()

    results: list[TrialResult] = []

    for model_name, make_evaluator in models.items():
        evaluator = make_evaluator()
        for variant_name, (domain, query) in VARIANTS.items():
            for trial in range(args.trials):
                detected, n_conflicts, error, raw_output = run_trial(evaluator, domain, query)
                tr = TrialResult(
                    model=model_name,
                    variant=variant_name,
                    trial=trial,
                    detected_conflict=detected,
                    num_conflicts=n_conflicts,
                    error=error,
                    raw_output=raw_output,
                )
                results.append(tr)
                status = "DETECT" if detected else ("ERROR" if error else "MISS")
                print(f"  {model_name:30s} {variant_name:15s} trial={trial} {status}")

                # Gentle rate limiting — be polite to APIs
                time.sleep(0.2)

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("SEMANTIC CONFLICT DETECTION — PASS RATES (detect = pass)")
    print("=" * 80)

    # Header
    variant_names = list(VARIANTS.keys())
    header = f"{'Model':30s} | " + " | ".join(f"{v:15s}" for v in variant_names) + " | {'OVERALL':10s}"
    print(header)
    print("-" * len(header))

    for model_name in models:
        cells = []
        model_results = [r for r in results if r.model == model_name]
        total_pass = 0
        total_n = 0
        for variant_name in variant_names:
            vr = [r for r in model_results if r.variant == variant_name]
            passes = sum(1 for r in vr if r.detected_conflict)
            errors = sum(1 for r in vr if r.error)
            n = len(vr)
            total_pass += passes
            total_n += n
            if errors:
                cells.append(f"{passes}/{n} ({errors}err)")
            else:
                cells.append(f"{passes}/{n} = {passes/n:.0%}")
        overall = f"{total_pass}/{total_n} = {total_pass/total_n:.0%}"
        row = f"{model_name:30s} | " + " | ".join(f"{c:15s}" for c in cells) + f" | {overall}"
        print(row)

    print("=" * 80)

    # Check for token sensitivity: does any model show high variance across variants?
    print("\nTOKEN SENSITIVITY CHECK:")
    for model_name in models:
        model_results = [r for r in results if r.model == model_name]
        variant_rates = {}
        for variant_name in variant_names:
            vr = [r for r in model_results if r.variant == variant_name]
            variant_rates[variant_name] = sum(1 for r in vr if r.detected_conflict) / len(vr) if vr else 0
        rates = list(variant_rates.values())
        spread = max(rates) - min(rates) if rates else 0
        if spread > 0.3:
            best = max(variant_rates, key=variant_rates.get)
            worst = min(variant_rates, key=variant_rates.get)
            print(f"  {model_name}: SENSITIVE (spread={spread:.0%}, best={best}, worst={worst})")
        elif spread > 0:
            print(f"  {model_name}: mild variance (spread={spread:.0%})")
        else:
            print(f"  {model_name}: stable across variants")

    # Save raw results as JSON
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(__file__).resolve().parent.parent / "docs" / "cairn" / "semantic_characterization.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw = [
        {
            "model": r.model,
            "variant": r.variant,
            "trial": r.trial,
            "detected_conflict": r.detected_conflict,
            "num_conflicts": r.num_conflicts,
            "error": r.error,
            "raw_output": r.raw_output,
        }
        for r in results
    ]
    out_path.write_text(json.dumps(raw, indent=2))
    print(f"\nRaw results written to {out_path}")


if __name__ == "__main__":
    main()
