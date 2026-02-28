"""Arbiter CLI — system prompt interference analysis.

Usage:
    arbiter                              # ground truth structural analysis
    arbiter prompt.md                    # heuristic decompose → structural
    arbiter corpus.json                  # pre-decomposed → structural
    arbiter prompt.md --full             # LLM decompose → full analysis
    arbiter prompt.md --full --budget 0.10
    arbiter prompt.md -o report.json     # JSON output
    arbiter prompt.md -q                 # quiet mode (exit code only)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .heuristic_decomposer import heuristic_decompose
from .pipeline import PromptAnalyzer
from .prompt_blocks import PromptBlock, PromptCorpus
from .rules import default_ruleset


GROUND_TRUTH = Path(__file__).parent.parent.parent / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"


def load_corpus(path: Path) -> list[PromptBlock]:
    """Load a PromptCorpus JSON file and return its blocks."""
    with open(path) as f:
        data = json.load(f)
    corpus = PromptCorpus(**data)
    return corpus.blocks


def _detect_file_type(path: Path) -> str:
    """Detect whether a file is a pre-decomposed corpus or raw text."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "corpus"
    return "raw"


def _get_blocks(path: Path, *, full: bool, quiet: bool) -> list[PromptBlock]:
    """Get blocks from a file, choosing decomposition strategy."""
    file_type = _detect_file_type(path)

    if file_type == "corpus":
        blocks = load_corpus(path)
        if not quiet:
            print(f"  {len(blocks)} blocks loaded from corpus\n")
        return blocks

    # Raw text file — decompose it
    text = path.read_text()

    if full:
        # LLM decomposition handled by caller (run_full)
        # This path shouldn't be reached — full mode calls _run_full
        raise RuntimeError("Full mode should not call _get_blocks for raw files")

    blocks = heuristic_decompose(text, source=path.stem)
    if not quiet:
        print(f"  {len(blocks)} blocks (heuristic decomposition)\n")
    return blocks


def _run_structural(blocks: list[PromptBlock], *, quiet: bool, output: Path | None) -> int:
    """Run structural-only analysis."""
    rule_set = default_ruleset().compile()
    analyzer = PromptAnalyzer(rule_set)
    result = analyzer.analyze_structural(blocks)

    if output:
        output.write_text(result.tensor.to_json())
        if not quiet:
            print(f"  Tensor written to {output}")
        return 1 if result.tensor.entries else 0

    if quiet:
        return 1 if result.tensor.entries else 0

    print(result.summary)

    if result.score == 0.0:
        print("\nNo structural interference detected.")
        print("Run with --full for LLM-powered semantic analysis.")
    else:
        print(f"\n  Score: {result.score:.2f}")
        print(f"  Findings: {len(result.tensor.entries)}")
        by_sev = result.tensor.by_severity()
        for sev, entries in sorted(by_sev.items(), key=lambda x: -len(x[1])):
            print(f"    {sev.value}: {len(entries)}")

    return 1 if result.tensor.entries else 0


async def _run_full(
    path: Path,
    *,
    model: str | None,
    base_url: str | None,
    budget: float,
    quiet: bool,
    output: Path | None,
) -> int:
    """Run full analysis with LLM decomposition and evaluation."""
    # Find API key
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY.\n"
            "Running structural analysis only.",
            file=sys.stderr,
        )
        text = path.read_text()
        blocks = heuristic_decompose(text, source=path.stem)
        if not quiet:
            print(f"  {len(blocks)} blocks (heuristic decomposition, fallback)\n")
        return _run_structural(blocks, quiet=quiet, output=output)

    try:
        import openai
    except ImportError:
        print("OpenAI SDK required for --full mode. Install with: uv sync --extra openai-compat", file=sys.stderr)
        return 2

    from .llm_caller import LLMCaller

    # Default to OpenRouter
    if base_url is None:
        if os.environ.get("OPENROUTER_API_KEY"):
            base_url = "https://openrouter.ai/api/v1"

    if model is None:
        model = "anthropic/claude-haiku-4-5-20251001"

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    caller = LLMCaller(client, model)

    rule_set = default_ruleset().compile()
    file_type = _detect_file_type(path)

    if file_type == "corpus":
        blocks = load_corpus(path)
        if not quiet:
            print(f"  {len(blocks)} blocks loaded from corpus")
    else:
        text = path.read_text()
        if not quiet:
            print(f"  Decomposing with LLM ({model})...")
        blocks = await caller.decompose(text, path.stem, rule_set)
        if not quiet:
            print(f"  {len(blocks)} blocks (LLM decomposition)\n")

    # Structural analysis
    analyzer = PromptAnalyzer(rule_set)
    structural_result = analyzer.analyze_structural(blocks)

    if not quiet:
        print(f"  Evaluating LLM rules ({model})...")
    llm_scores = await caller.evaluate_llm_rules(blocks, rule_set)
    if not quiet:
        print(f"  {len(llm_scores)} LLM evaluations completed\n")

    result = analyzer.analyze_with_scores(blocks, llm_scores)

    if output:
        output.write_text(result.tensor.to_json())
        if not quiet:
            print(f"  Tensor written to {output}")
        return 1 if result.tensor.entries else 0

    if quiet:
        return 1 if result.tensor.entries else 0

    print(result.summary)

    if result.score == 0.0:
        print("\nNo interference detected.")
    else:
        print(f"\n  Score: {result.score:.2f}")
        print(f"  Findings: {len(result.tensor.entries)}")
        by_sev = result.tensor.by_severity()
        for sev, entries in sorted(by_sev.items(), key=lambda x: -len(x[1])):
            print(f"    {sev.value}: {len(entries)}")

    return 1 if result.tensor.entries else 0


def run(args: argparse.Namespace) -> int:
    """Main entry point after argument parsing."""
    path = args.path
    full = args.full
    quiet = args.quiet
    output = Path(args.output) if args.output else None

    # Default: ground truth structural analysis
    if path is None:
        if not GROUND_TRUTH.exists():
            print("No ground truth data found. Pass a prompt file as argument.")
            print(f"  Expected: {GROUND_TRUTH}")
            return 1
        path = GROUND_TRUTH
        if not quiet:
            print(f"arbiter: analyzing {path.name} (structural, no API calls)\n")
        blocks = load_corpus(path)
        if not quiet:
            print(f"  {len(blocks)} blocks loaded\n")
        return _run_structural(blocks, quiet=quiet, output=output)

    path = Path(path)
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    mode_label = "full (LLM)" if full else "structural"
    if not quiet:
        print(f"arbiter: analyzing {path.name} ({mode_label})\n")

    if full:
        return asyncio.run(
            _run_full(
                path,
                model=args.model,
                base_url=args.base_url,
                budget=args.budget,
                quiet=quiet,
                output=output,
            )
        )

    blocks = _get_blocks(path, full=False, quiet=quiet)
    return _run_structural(blocks, quiet=quiet, output=output)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="arbiter",
        description="System prompt interference analysis.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Prompt file (.md/.txt) or pre-decomposed corpus (.json). "
        "Default: built-in ground truth.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Enable LLM decomposition + LLM rule evaluation (costs money).",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=0.10,
        help="Cost ceiling in USD for LLM calls (default: 0.10).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID for LLM calls (default: anthropic/claude-haiku-4-5-20251001).",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible API base URL.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Write JSON tensor to file instead of stdout summary.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output. Exit code: 0=clean, 1=findings, 2=error.",
    )

    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
