#!/usr/bin/env python3
"""Analyze system prompt structure using the prompt AST.

Usage:
    python scripts/analyze_prompt.py data/prompts/claude-code/latest_prompt.md
    python scripts/analyze_prompt.py --diff v2.1.50.md v2.1.71.md
    python scripts/analyze_prompt.py --compare prompt1.md prompt2.md prompt3.md
    python scripts/analyze_prompt.py --json data/prompts/claude-code/latest_raw.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from arbiter.prompt_ast import (
    parse_prompt,
    parse_api_blocks,
    annotate_semantics,
    channel_summary,
    diff_ast,
)


def load_prompt(path: Path):
    """Load a prompt from .md, .txt, or .json (API blocks)."""
    text = path.read_text()
    if path.suffix == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            ast = parse_api_blocks(data)
        else:
            ast = parse_prompt(text)
    else:
        ast = parse_prompt(text)
    annotate_semantics(ast)
    return ast


def print_analysis(name: str, ast):
    total = ast.node_count()
    unknowns = sum(1 for n in ast.walk()
                   if n.semantic_role and n.semantic_role.value == "unknown")
    print(f"=== {name} ===")
    print(f"Nodes: {total}, Depth: {ast.depth()}, "
          f"Sections: {len(ast.sections())}, "
          f"Directives: {len(ast.directives())}, "
          f"Unknown: {unknowns} ({unknowns/total*100:.0f}%)")
    print(f"Structural hash: {ast.structural_hash()}")
    print()
    print("Channels:")
    for ch, roles in sorted(channel_summary(ast).items()):
        t = sum(roles.values())
        print(f"  {ch} ({t}): {dict(sorted(roles.items()))}")
    print()
    print("Skeleton:")
    print(ast.skeleton())


def main():
    parser = argparse.ArgumentParser(description="Analyze system prompt structure")
    parser.add_argument("prompts", nargs="+", type=Path, help="Prompt file(s)")
    parser.add_argument("--diff", action="store_true",
                        help="Diff two prompts (requires exactly 2 files)")
    parser.add_argument("--compare", action="store_true",
                        help="Side-by-side channel comparison")
    parser.add_argument("--skeleton-only", action="store_true",
                        help="Only show structural skeleton")
    args = parser.parse_args()

    asts = [(p.stem, load_prompt(p)) for p in args.prompts]

    if args.diff:
        if len(asts) != 2:
            print("--diff requires exactly 2 prompt files", file=sys.stderr)
            sys.exit(1)
        (name_a, ast_a), (name_b, ast_b) = asts
        print(f"Diff: {name_a} → {name_b}")
        print()
        d = diff_ast(ast_a, ast_b)
        print(d.summary())

    elif args.compare:
        # Channel comparison table
        all_channels = set()
        summaries = {}
        for name, ast in asts:
            cs = channel_summary(ast)
            summaries[name] = cs
            all_channels.update(cs.keys())

        header = f"{'Channel':<15}" + "".join(f"{n:<20}" for n, _ in asts)
        print(header)
        print("-" * len(header))
        for ch in sorted(all_channels):
            row = f"{ch:<15}"
            for name, ast in asts:
                total = sum(summaries[name].get(ch, {}).values())
                pct = total / ast.node_count() * 100
                row += f"{total:>4} ({pct:>4.0f}%)        "
            print(row)

    elif args.skeleton_only:
        for name, ast in asts:
            print(f"=== {name} ===")
            print(ast.skeleton())
            print()

    else:
        for name, ast in asts:
            print_analysis(name, ast)
            print()


if __name__ == "__main__":
    main()
