#!/usr/bin/env python3
"""Run the scourer against a system prompt and compare to ground truth.

Usage:
    python scripts/run_scourer.py [--passes N] [--model MODEL]

    # Fresh run with Gemini
    python scripts/run_scourer.py --model google/gemini-2.5-flash --provider openrouter

    # Resume from a previous run (e.g., pass 1 done by Claude, pass 2 by Gemini)
    python scripts/run_scourer.py --resume data/scourer/pass1.json --model google/gemini-2.5-flash --provider openrouter

    # Save results
    python scripts/run_scourer.py --save data/scourer/gemini_2pass.json

    # Multilingual scouring (Mistral Nemo in Hindi)
    python scripts/run_scourer.py --model mistralai/mistral-nemo --provider openrouter --language Hindi

Defaults to Claude Haiku for cost efficiency. Runs up to 3 passes or
until the scourer says to stop, whichever comes first.

OpenRouter requests are labeled with X-Title for cost tracking in the
OpenRouter dashboard.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from arbiter.scourer import Scourer, ScourerStack
from arbiter.prompt_blocks import InterferencePattern

PROMPT_FILE = Path(__file__).parent.parent / "docs" / "claude-code-system-prompt.md"
INTERFERENCE_FILE = (
    Path(__file__).parent.parent / "data" / "prompts" / "claude-code" / "v2.1.50_interference.json"
)


def load_ground_truth() -> list[InterferencePattern]:
    with open(INTERFERENCE_FILE) as f:
        data = json.load(f)
    return [InterferencePattern(**p) for p in data]


def run_with_anthropic(prompt: str, model: str, pass_number: int) -> str:
    """Run a single scourer prompt through Anthropic's API."""
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
        metadata={"user_id": f"arbiter-scourer-pass{pass_number}"},
    )
    return message.content[0].text


def run_with_openrouter(prompt: str, model: str, pass_number: int) -> str:
    """Run a single scourer prompt through OpenRouter.

    Requests are labeled with X-Title and X-Trace for cost tracking
    in the OpenRouter usage dashboard.
    """
    import openai
    import os

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
        default_headers={
            "X-Title": "arbiter-scourer",
            "HTTP-Referer": "https://github.com/wamason/arbiter",
        },
    )
    response = client.chat.completions.create(
        model=model,
        max_tokens=65536,
        messages=[{"role": "user", "content": prompt}],
        extra_body={
            "transforms": [],
            "route": "fallback",
            "metadata": {
                "label": f"arbiter-scourer-pass{pass_number}",
                "model": model,
            },
        },
    )
    return response.choices[0].message.content


def compare_to_ground_truth(stack: ScourerStack, ground_truth: list[InterferencePattern]) -> None:
    """Compare scourer findings against hand-labeled interference patterns."""
    print("\n" + "=" * 60)
    print("COMPARISON TO GROUND TRUTH")
    print("=" * 60)

    gt_descriptions = []
    for p in ground_truth:
        gt_descriptions.append(
            f"  [{p.severity.value}] {p.type.value}: {p.block_a} <-> {p.block_b}"
        )

    print(f"\nGround truth: {len(ground_truth)} patterns")
    for d in gt_descriptions:
        print(d)

    print(f"\nScourer findings: {stack.finding_count()} across {len(stack.reports)} pass(es)")
    for report in stack.reports:
        model_tag = f" ({report.model})" if report.model else ""
        print(f"\n  Pass {report.pass_number}{model_tag}: {len(report.findings)} findings")
        for f in report.findings:
            print(f"    [{f.severity_guess}] {f.category}: {f.description[:80]}")

    remaining = stack.all_unexplored()
    if remaining:
        print(f"\n  Remaining unexplored ({len(remaining)}):")
        for u in remaining:
            print(f"    - {u.description[:80]}")

    print(f"\n  Should continue: {stack.should_continue()}")
    if stack.reports and stack.reports[-1].rationale_for_continuation:
        print(f"  Rationale: {stack.reports[-1].rationale_for_continuation}")

    models = stack.models_used()
    if models:
        print(f"  Models used: {', '.join(models)}")


def main():
    parser = argparse.ArgumentParser(description="Run scourer against Claude Code system prompt")
    parser.add_argument("--passes", type=int, default=3, help="Maximum number of passes")
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Model to use (default: Haiku 4.5)",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openrouter"],
        default="anthropic",
        help="API provider",
    )
    parser.add_argument("--resume", type=str, default=None, help="Resume from a saved JSON file")
    parser.add_argument("--save", type=str, default=None, help="Save results to JSON file")
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language for analysis (e.g. Hindi, French, Chinese). "
             "Model conducts analysis in this language.",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        default=None,
        help="Path to system prompt file (default: Claude Code v2.1.50)",
    )
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file) if args.prompt_file else PROMPT_FILE
    prompt_text = prompt_path.read_text()

    # Ground truth is optional — only load if the file exists
    gt_file = INTERFERENCE_FILE
    ground_truth = []
    if gt_file.exists():
        ground_truth = load_ground_truth()

    print(f"System prompt: {len(prompt_text)} chars, {len(prompt_text.splitlines())} lines")
    print(f"  Source: {prompt_path}")
    if ground_truth:
        print(f"Ground truth: {len(ground_truth)} interference patterns")
    else:
        print("Ground truth: (none — comparison will be skipped)")
    print(f"Model: {args.model} via {args.provider}")
    print(f"Max passes: {args.passes}")
    if args.language:
        print(f"Language: {args.language}")

    scourer = Scourer()

    # Resume from previous run if specified
    if args.resume:
        resume_path = Path(args.resume)
        print(f"Resuming from: {resume_path}")
        prior_stack = ScourerStack.model_validate_json(resume_path.read_text())
        for report in prior_stack.reports:
            scourer.add_report(report)
        print(f"  Loaded {len(prior_stack.reports)} prior pass(es), "
              f"{prior_stack.finding_count()} findings")
        if not prior_stack.should_continue():
            print("  Prior run said to stop. Running anyway (you asked).")

    run_fn = run_with_anthropic if args.provider == "anthropic" else run_with_openrouter
    start_pass = len(scourer.stack.reports)

    for i in range(start_pass, start_pass + args.passes):
        print(f"\n{'=' * 60}")
        print(f"PASS {i + 1} — {args.model}")
        if args.language:
            print(f"  Language: {args.language}")
        print("=" * 60)

        prompt = scourer.build_prompt(prompt_text, language=args.language)
        print(f"Prompt length: {len(prompt)} chars")

        raw = run_fn(prompt, args.model, pass_number=i + 1)
        print(f"Response length: {len(raw)} chars")

        report = scourer.parse_response(raw, model=args.model)
        scourer.add_report(report)

        print(f"Findings: {len(report.findings)}")
        print(f"Unexplored: {len(report.unexplored)}")
        print(f"Continue: {report.should_send_another}")

        if not report.should_send_another:
            print("Scourer says: enough.")
            break

    if ground_truth:
        compare_to_ground_truth(scourer.stack, ground_truth)
    else:
        # Just print findings summary without ground truth comparison
        print(f"\nScourer findings: {scourer.stack.finding_count()} "
              f"across {len(scourer.stack.reports)} pass(es)")

    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(scourer.stack.model_dump_json(indent=2))
        print(f"\nResults saved to {save_path}")


if __name__ == "__main__":
    main()
