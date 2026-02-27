#!/usr/bin/env python3
"""Convert pandoc longtable to table*/tabular for acmart compatibility."""

import re
import sys
from pathlib import Path


def convert_longtable(match: re.Match) -> str:
    """Convert a longtable block to table* with tabular."""
    block = match.group(0)

    # Extract column spec
    col_match = re.search(r"\\begin\{longtable\}\[?\]?\{([^}]+)\}", block)
    if not col_match:
        return block

    # Count columns by counting & in first data row + 1
    lines = block.split("\n")
    data_lines = [
        ln
        for ln in lines
        if "&" in ln and "toprule" not in ln and "midrule" not in ln
    ]
    if data_lines:
        ncols = data_lines[0].count("&") + 1
    else:
        ncols = 4

    simple_spec = "@{}" + "l" * ncols + "@{}"

    # Extract content: keep only toprule/midrule/bottomrule and data rows
    body_lines = []
    in_body = False
    for ln in lines:
        stripped = ln.strip()
        if "\\begin{longtable}" in stripped:
            continue
        if "\\end{longtable}" in stripped:
            continue
        if "\\endhead" in stripped:
            in_body = True
            continue
        if "\\endfirsthead" in stripped:
            continue
        if "\\endfoot" in stripped:
            continue
        if "\\endlastfoot" in stripped:
            continue
        # Remove \noalign{} from rules
        stripped = stripped.replace("\\toprule\\noalign{}", "\\toprule")
        stripped = stripped.replace("\\midrule\\noalign{}", "\\midrule")
        stripped = stripped.replace("\\bottomrule\\noalign{}", "\\bottomrule")
        # Skip column width spec lines
        if "\\raggedright\\arraybackslash" in stripped:
            continue
        if stripped:
            body_lines.append(stripped)

    body = "\n".join(body_lines)

    return (
        f"\\begin{{table*}}[t]\n"
        f"\\small\n"
        f"\\begin{{tabular}}{{{simple_spec}}}\n"
        f"{body}\n"
        f"\\end{{tabular}}\n"
        f"\\end{{table*}}"
    )


for fname in sys.argv[1:]:
    path = Path(fname)
    content = path.read_text()
    content = re.sub(
        r"\\begin\{longtable\}.*?\\end\{longtable\}",
        convert_longtable,
        content,
        flags=re.DOTALL,
    )
    path.write_text(content)
    print(f"Converted: {fname}")
