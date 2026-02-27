"""Arbiter CLI — system prompt interference analysis.

Run with no arguments to see what Arbiter does:

    python -m arbiter

Or point it at a prompt corpus JSON file:

    python -m arbiter path/to/corpus.json

Structural analysis only — no API calls, no cost, milliseconds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

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


def run(path: Path | None = None) -> int:
    """Run structural analysis and print the result."""
    if path is None:
        if not GROUND_TRUTH.exists():
            print("No ground truth data found. Pass a corpus JSON file as argument.")
            print(f"  Expected: {GROUND_TRUTH}")
            return 1
        path = GROUND_TRUTH
        print(f"arbiter: analyzing {path.name} (structural, no API calls)\n")
    else:
        if not path.exists():
            print(f"File not found: {path}")
            return 1
        print(f"arbiter: analyzing {path.name} (structural, no API calls)\n")

    blocks = load_corpus(path)
    print(f"  {len(blocks)} blocks loaded\n")

    rule_set = default_ruleset().compile()
    analyzer = PromptAnalyzer(rule_set)
    result = analyzer.analyze_structural(blocks)

    print(result.summary)

    if result.score == 0.0:
        print("\nNo structural interference detected.")
        print("Run with LLM evaluation to check for semantic interference.")
    else:
        print(f"\n  Score: {result.score:.2f}")
        print(f"  Findings: {len(result.tensor.entries)}")
        by_sev = result.tensor.by_severity()
        for sev, entries in sorted(by_sev.items(), key=lambda x: -len(x[1])):
            print(f"    {sev.value}: {len(entries)}")

    return 0


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    path = Path(args[0]) if args else None
    sys.exit(run(path))


if __name__ == "__main__":
    main()
