#!/usr/bin/env python3
"""Post-process pandoc LaTeX output for acmart compatibility.

Fixes:
1. Section hierarchy (pandoc puts everything one level too deep)
2. longtable → table* + tabular (acmart is two-column)
3. Removes hypertarget cruft
4. Splits into section files
"""

import re
from pathlib import Path

RAW = Path(__file__).parent / "paper_raw.tex"
OUT = Path(__file__).parent


def fix_longtable(block: str) -> str:
    """Convert one longtable to table* + tabular."""
    # First: collapse minipage-wrapped headers into plain text
    # \begin{minipage}[b]{\linewidth}\raggedright\nText\n\end{minipage}
    block = re.sub(
        r"\\begin\{minipage\}[^}]*\{[^}]*\}\\raggedright\s*\n\s*",
        "",
        block,
    )
    block = re.sub(r"\\end\{minipage\}", "", block)

    lines = block.strip().split("\n")

    # Infrastructure patterns to skip
    infra_patterns = [
        "toprule", "midrule", "bottomrule", "endhead",
        "endfirsthead", "endfoot", "endlastfoot",
        "raggedright", "arraybackslash", "begin{longtable}",
        "end{longtable}", "real{",
    ]

    data_lines = []

    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            continue

        is_infra = any(p in stripped for p in infra_patterns)

        if not is_infra:
            data_lines.append(stripped)

    if not data_lines:
        return block

    # Merge continuation lines (lines not ending with \\)
    merged = []
    current = ""
    for dl in data_lines:
        if current:
            current = current + " " + dl
        else:
            current = dl
        if current.rstrip().endswith("\\\\"):
            merged.append(current)
            current = ""
    if current:
        merged.append(current)

    if not merged:
        return block

    # Count columns from first data row
    ncols = merged[0].count("&") + 1
    col_spec = "@{}" + "l" * ncols + "@{}"

    # Reconstruct: header row, then data rows
    out = []
    out.append("\\begin{table*}[t]")
    out.append("\\small")
    out.append(f"\\begin{{tabular}}{{{col_spec}}}")
    out.append("\\toprule")
    out.append(merged[0])  # header
    out.append("\\midrule")
    for row in merged[1:]:
        out.append(row)
    out.append("\\bottomrule")
    out.append("\\end{tabular}")
    out.append("\\end{table*}")

    return "\n".join(out)


def process():
    raw = RAW.read_text()

    # Extract body
    body_match = re.search(
        r"\\begin\{document\}(.*?)\\end\{document\}", raw, re.DOTALL
    )
    body = body_match.group(1).strip()

    # Remove hypertargets
    body = re.sub(r"\\hypertarget\{[^}]*\}\{\s*%?\n?", "", body)

    # Fix multi-line section titles
    body = re.sub(
        r"(\\(?:sub)*section\{[^}]*)\n\s*([^}]*\})",
        r"\1 \2",
        body,
    )

    # Remove stray labels (before title removal so braces don't orphan)
    body = re.sub(r"\\label\{[^}]*\}", "", body)

    # Remove stray closing braces from hypertarget removal
    # Pattern: \section{Title}} → \section{Title}
    body = re.sub(r"(\\(?:sub)*section\{[^}]+)\}\}", r"\1}", body)

    # Clean any remaining orphaned } on lines by themselves
    body = re.sub(r"\n\s*\}\s*\n", "\n", body)

    # Remove title and subtitle
    body = re.sub(r"\\section\{Arbiter: Detecting[^}]*\}\s*", "", body)
    body = re.sub(
        r"\\subsection\{A Cross-Vendor Analysis[^}]*\}\s*", "", body
    )

    # Remove \textbf{Abstract.} marker
    body = re.sub(r"\\textbf\{Abstract\.\}", "", body, count=1)

    # Fix section hierarchy
    # Numbered: \subsection{N. Title} → \section{Title}
    body = re.sub(
        r"\\subsection\{(\d+\.\s+)([^}]+)\}",
        lambda m: f"\\section{{{m.group(2)}}}",
        body,
    )
    # Numbered sub: \subsubsection{N.N Title} → \subsection{Title}
    body = re.sub(
        r"\\subsubsection\{(\d+\.\d+\s+)([^}]+)\}",
        lambda m: f"\\subsection{{{m.group(2)}}}",
        body,
    )
    # Appendix sections
    body = re.sub(
        r"\\subsection\{(Appendix [^}]+)\}",
        r"\\section{\1}",
        body,
    )
    # Remaining subsubsections → \subsection
    body = re.sub(
        r"\\subsubsection\{([^}]+)\}",
        r"\\subsection{\1}",
        body,
    )

    # Fix paragraph-level architecture sections
    # \paragraph{4.3.1 Monolith: Claude Code} → \subsubsection{...}
    body = re.sub(
        r"\\paragraph\{(\d+\.\d+\.\d+\s+)?([^}]+)\}",
        r"\\subsubsection{\2}",
        body,
    )

    # Second pass: fix stray }} on any section-level command
    # (catches \subsubsection from paragraph promotion)
    body = re.sub(
        r"(\\(?:sub)*section\{[^}]+)\}\}", r"\1}", body
    )

    # Leave verbatim blocks as-is (prompt templates are literal text)

    # Convert longtables to table* + tabular
    body = re.sub(
        r"\\begin\{longtable\}.*?\\end\{longtable\}",
        lambda m: fix_longtable(m.group(0)),
        body,
        flags=re.DOTALL,
    )

    # Split into sections
    parts = re.split(r"(?=\\section\{)", body)
    abstract_text = parts[0].strip()

    file_map = {
        "Introduction": "intro.tex",
        "Background and Related Work": "background.tex",
        "Methodology": "methodology.tex",
        "Results": "results.tex",
        "Discussion": "discussion.tex",
        "Conclusion": "conclusion.tex",
    }

    appendix_parts = []

    for part in parts[1:]:
        title_match = re.match(r"\\section\{([^}]+)\}", part)
        if not title_match:
            continue
        title = title_match.group(1).strip()

        matched = False
        for key, fname in file_map.items():
            if key in title:
                OUT.joinpath(fname).write_text(part.strip() + "\n")
                print(f"  {fname}: {len(part.strip().splitlines())} lines")
                matched = True
                break

        if not matched:
            if "Appendix" in title:
                appendix_parts.append(part.strip())
            else:
                print(f"  UNMAPPED: '{title}'")

    OUT.joinpath("abstract.tex").write_text(abstract_text + "\n")
    print(f"  abstract.tex: {len(abstract_text.splitlines())} lines")

    if appendix_parts:
        content = "\n\n".join(appendix_parts)
        OUT.joinpath("appendix.tex").write_text(content + "\n")
        print(
            f"  appendix.tex: {len(content.splitlines())} lines"
            f" — {len(appendix_parts)} appendices"
        )

    print("\nDone.")


if __name__ == "__main__":
    process()
