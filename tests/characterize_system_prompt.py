"""Characterize system prompt conflict detection across models.

Tests whether models can detect real contradictions extracted from the
Claude Code system prompt. This is a different-domain validation:
instruction-following compliance rather than database queries.

Usage:
    python tests/characterize_system_prompt.py [--trials 5]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from arbiter.evaluator import AnthropicEvaluator, OpenAICompatibleEvaluator
from arbiter.models import DomainLayer, SystemLayer

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
        models["x-ai/grok-3-mini"] = lambda k=openrouter_key: OpenAICompatibleEvaluator(
            model="x-ai/grok-3-mini",
            base_url="https://openrouter.ai/api/v1",
            api_key=k,
            extra_headers=_OPENROUTER_HEADERS,
        )

    return models


SYSTEM = SystemLayer(
    name="instruction-consistency-audit",
    rules=[
        "Examine the provided instructions for internal contradictions.",
        "Report conflicts rather than resolving them silently.",
        "A conflict exists when one instruction requires behavior that another instruction prohibits.",
    ],
)

QUERY = "An AI assistant receives these instructions and must follow all of them. Can it comply with every instruction simultaneously?"

CASES: dict[str, DomainLayer] = {
    "todowrite-mandatory-forbidden": DomainLayer(
        name="claude-code-system-prompt-excerpt",
        entries=[
            "You have access to the TodoWrite tools to help you manage and plan tasks. Use these tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress.",
            "These tools are also EXTREMELY helpful for planning tasks, and for breaking down larger complex tasks into smaller steps. If you do not use this tool when planning, you may forget to do important tasks - and that is unacceptable.",
            "IMPORTANT: Always use the TodoWrite tool to plan and track tasks throughout the conversation.",
            "Important notes: NEVER use the TodoWrite or Task tools.",
            "Important: DO NOT use the TodoWrite or Task tools.",
        ],
    ),
    "concise-vs-verbose": DomainLayer(
        name="claude-code-system-prompt-excerpt",
        entries=[
            "Your output will be displayed on a command line interface. Your responses should be short and concise.",
            "Use the TodoWrite tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress.",
            "Update task status in real-time as you work. Mark tasks complete IMMEDIATELY after finishing. Exactly ONE task must be in_progress at any time.",
            "When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully.",
        ],
    ),
    "task-search-contradictory": DomainLayer(
        name="claude-code-system-prompt-excerpt",
        entries=[
            "When doing file search, prefer to use the Task tool in order to reduce context usage.",
            "When NOT to use the Task tool: If you want to read a specific file path, use the Read or Glob tool instead of the Task tool, to find the match more quickly.",
            "If you are searching for a specific class definition like 'class Foo', use the Glob tool instead, to find the match more quickly.",
            "For broader codebase exploration and deep research, use the Task tool with subagent_type=Explore.",
        ],
    ),
    "proactive-vs-scope": DomainLayer(
        name="claude-code-system-prompt-excerpt",
        entries=[
            "Use this tool proactively when you're about to start a non-trivial implementation task.",
            "IMPORTANT: Always use the TodoWrite tool to plan and track tasks throughout the conversation.",
            "Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused.",
            "Don't add features, refactor code, or make improvements beyond what was asked.",
            "NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.",
        ],
    ),
    "clean-control": DomainLayer(
        name="claude-code-consistent-excerpt",
        entries=[
            "Use the Read tool to read files before editing them.",
            "Use the Edit tool to modify existing files rather than creating new ones.",
            "Always read a file's contents before attempting to write changes to it.",
        ],
    ),
}

# Expected outcomes: True = should detect conflict, False = should resolve clean
EXPECTED = {
    "todowrite-mandatory-forbidden": True,
    "concise-vs-verbose": True,
    "task-search-contradictory": True,
    "proactive-vs-scope": True,
    "clean-control": False,
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

    case_names = list(CASES.keys())
    print(f"Models: {list(models.keys())}")
    print(f"Cases: {case_names}")
    print(f"Trials per cell: {args.trials}")
    print(f"Total API calls: {len(models) * len(CASES) * args.trials}")
    print()

    results = []

    for model_name, make_evaluator in models.items():
        evaluator = make_evaluator()
        for case_name, domain in CASES.items():
            expected_conflict = EXPECTED[case_name]
            for trial in range(args.trials):
                detected, n_conflicts, error, raw_output = run_trial(evaluator, domain, QUERY)
                correct = (detected == expected_conflict)
                results.append({
                    "model": model_name,
                    "case": case_name,
                    "trial": trial,
                    "detected_conflict": detected,
                    "expected_conflict": expected_conflict,
                    "correct": correct,
                    "num_conflicts": n_conflicts,
                    "error": error,
                    "raw_output": raw_output,
                })
                if error:
                    status = "ERROR"
                elif correct:
                    status = "CORRECT"
                else:
                    status = "FP" if detected and not expected_conflict else "MISS"
                print(f"  {model_name:30s} {case_name:30s} trial={trial} {status}")
                time.sleep(0.2)

    # Summary
    print("\n" + "=" * 100)
    print("SYSTEM PROMPT CONFLICT DETECTION — ACCURACY (correct answer = pass)")
    print("=" * 100)

    header = f"{'Model':30s} | " + " | ".join(f"{c:15s}" for c in case_names) + " | {'OVERALL':10s}"
    print(header)
    print("-" * len(header))

    for model_name in models:
        cells = []
        model_results = [r for r in results if r["model"] == model_name]
        total_correct = 0
        total_n = 0
        for case_name in case_names:
            cr = [r for r in model_results if r["case"] == case_name]
            correct = sum(1 for r in cr if r["correct"])
            errors = sum(1 for r in cr if r["error"])
            n = len(cr)
            total_correct += correct
            total_n += n
            expected = EXPECTED[case_name]
            label = "detect" if expected else "clean"
            if errors:
                cells.append(f"{correct}/{n} ({errors}err)")
            else:
                cells.append(f"{correct}/{n}={correct/n:.0%} [{label}]")
        overall = f"{total_correct}/{total_n} = {total_correct/total_n:.0%}"
        row = f"{model_name:30s} | " + " | ".join(f"{c:15s}" for c in cells) + f" | {overall}"
        print(row)

    print("=" * 100)

    # False positive analysis
    print("\nFALSE POSITIVE ANALYSIS (clean control case):")
    for model_name in models:
        control = [r for r in results if r["model"] == model_name and r["case"] == "clean-control"]
        fps = sum(1 for r in control if r["detected_conflict"])
        n = len(control)
        print(f"  {model_name}: {fps}/{n} false positives")

    # Save
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(__file__).resolve().parent.parent / "docs" / "cairn" / "system_prompt_characterization.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nRaw results written to {out_path}")


if __name__ == "__main__":
    main()
