"""Characterize adversarial conflict detection across models.

Extends the semantic characterization to adversarial cases — same underlying
conflict but with deliberate obfuscation. Focuses on the tier 2 (buried)
case since that's where GPT-4o-mini (previously "bulletproof") broke.

Usage:
    python tests/characterize_adversarial.py [--trials 5]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from arbiter.evaluator import AnthropicEvaluator, OpenAICompatibleEvaluator
from arbiter.models import DomainLayer, EvaluationResult, SystemLayer

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/fsgeek/arbiter",
    "X-Title": "Arbiter conflict-detection",
}


def _make_models() -> dict:
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


SYSTEM = SystemLayer(
    name="query-rules",
    rules=[
        "Generate valid SQL for the user query.",
        "Report conflicts rather than resolving them silently.",
    ],
)

QUERY = "Find records created in the last 30 days"

TIERS: dict[str, DomainLayer] = {
    "tier1-synonym": DomainLayer(
        name="schema-knowledge",
        entries=[
            "For temporal filtering on the records collection, the preferred column is records.created_ts.",
            "Index coverage on the records collection: primary key (id), name lookup (name). Remaining columns lack index coverage.",
            "Columns without index coverage must not appear in filter predicates on high-volume collections due to full-scan overhead.",
        ],
    ),
    "tier2-buried": DomainLayer(
        name="schema-knowledge",
        entries=[
            "The records collection stores audit trail data. Each record has an id (UUID), name (varchar), created_ts (timestamp), updated_ts (timestamp), and payload (jsonb).",
            "For time-based queries against records, use the created_ts column.",
            "Database performance guidelines: always use LIMIT on unbounded queries; prefer batch inserts for bulk operations; columns that are not indexed should never be used in WHERE clauses on tables with more than 10k rows, as the query planner will resort to sequential scans.",
            "The records table currently maintains two indexes: a B-tree on id (primary key) and a hash index on name for exact-match lookups.",
        ],
    ),
    "tier3-split": DomainLayer(
        name="schema-knowledge",
        entries=[
            "The records table is one of the largest in the system, containing approximately 50 million rows across all tenants.",
            "For time-based queries, the created_ts column in the records table provides millisecond-precision timestamps.",
            "Query optimizer hints: the records table has indexes on id and name only. Plan accordingly.",
            "All queries against tables exceeding 1 million rows must use indexed columns in their WHERE clause to maintain SLA response times.",
            "The payload column in records stores arbitrary JSON. Use jsonb_path_query for structured access.",
        ],
    ),
}


def run_trial(evaluator, domain, query):
    try:
        result = evaluator.evaluate(SYSTEM, domain, query)
        return (not result.resolved, len(result.conflicts), None, result.output)
    except Exception as e:
        return (False, 0, str(e), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    models = _make_models()
    if not models:
        print("ERROR: No API keys found.")
        sys.exit(1)

    tier_names = list(TIERS.keys())
    print(f"Models: {list(models.keys())}")
    print(f"Tiers: {tier_names}")
    print(f"Trials per cell: {args.trials}")
    print(f"Total API calls: {len(models) * len(TIERS) * args.trials}")
    print()

    results = []

    for model_name, make_evaluator in models.items():
        evaluator = make_evaluator()
        for tier_name, domain in TIERS.items():
            for trial in range(args.trials):
                detected, n_conflicts, error, raw_output = run_trial(evaluator, domain, QUERY)
                results.append({
                    "model": model_name,
                    "tier": tier_name,
                    "trial": trial,
                    "detected_conflict": detected,
                    "num_conflicts": n_conflicts,
                    "error": error,
                    "raw_output": raw_output,
                })
                status = "DETECT" if detected else ("ERROR" if error else "MISS")
                print(f"  {model_name:30s} {tier_name:15s} trial={trial} {status}")
                time.sleep(0.2)

    # Summary
    print("\n" + "=" * 80)
    print("ADVERSARIAL CONFLICT DETECTION — PASS RATES (detect = pass)")
    print("=" * 80)

    header = f"{'Model':30s} | " + " | ".join(f"{t:15s}" for t in tier_names) + " | {'OVERALL':10s}"
    print(header)
    print("-" * len(header))

    for model_name in models:
        cells = []
        model_results = [r for r in results if r["model"] == model_name]
        total_pass = 0
        total_n = 0
        for tier_name in tier_names:
            tr = [r for r in model_results if r["tier"] == tier_name]
            passes = sum(1 for r in tr if r["detected_conflict"])
            errors = sum(1 for r in tr if r["error"])
            n = len(tr)
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

    # Difficulty gradient check: does pass rate decrease with tier?
    print("\nDIFFICULTY GRADIENT:")
    for model_name in models:
        model_results = [r for r in results if r["model"] == model_name]
        rates = []
        for tier_name in tier_names:
            tr = [r for r in model_results if r["tier"] == tier_name]
            rate = sum(1 for r in tr if r["detected_conflict"]) / len(tr) if tr else 0
            rates.append(rate)
        if rates == sorted(rates, reverse=True):
            print(f"  {model_name}: monotonic decline ({' → '.join(f'{r:.0%}' for r in rates)})")
        elif all(r == rates[0] for r in rates):
            print(f"  {model_name}: flat at {rates[0]:.0%}")
        else:
            print(f"  {model_name}: non-monotonic ({' → '.join(f'{r:.0%}' for r in rates)})")

    # Save
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(__file__).resolve().parent.parent / "docs" / "cairn" / "adversarial_characterization.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nRaw results written to {out_path}")


if __name__ == "__main__":
    main()
