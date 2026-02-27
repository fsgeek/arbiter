#!/usr/bin/env python3
"""Fix table column specs to match actual data columns."""

import re
import sys
from pathlib import Path


def fix_tabular_spec(match: re.Match) -> str:
    spec = match.group(1)
    body = match.group(2)

    # Count columns from data rows
    data_lines = [
        ln.strip()
        for ln in body.split("\n")
        if "&" in ln
        and "toprule" not in ln
        and "midrule" not in ln
        and "bottomrule" not in ln
    ]
    if data_lines:
        ncols = max(ln.count("&") for ln in data_lines) + 1
    else:
        ncols = 4

    new_spec = "@{}" + "l" * ncols + "@{}"
    return f"\\begin{{tabular}}{{{new_spec}}}{body}\\end{{tabular}}"


for fname in sys.argv[1:]:
    path = Path(fname)
    content = path.read_text()
    content = re.sub(
        r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}",
        fix_tabular_spec,
        content,
        flags=re.DOTALL,
    )
    path.write_text(content)
    print(f"Fixed: {fname}")
