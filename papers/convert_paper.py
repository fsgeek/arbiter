#!/usr/bin/env python3
"""Convert the Arbiter paper from markdown to decomposed LaTeX sections.

Handles tables properly for acmart (two-column) by using table* with tabular
instead of pandoc's longtable.
"""

import re
from pathlib import Path

PAPER_MD = Path(__file__).parent.parent / "docs" / "paper.md"
OUT_DIR = Path(__file__).parent


def md_table_to_latex(table_text: str) -> str:
    """Convert a markdown table to LaTeX tabular inside table*."""
    lines = [ln.strip() for ln in table_text.strip().split("\n") if ln.strip()]
    if len(lines) < 2:
        return table_text

    # Parse header
    header_cells = [c.strip() for c in lines[0].split("|") if c.strip()]
    ncols = len(header_cells)

    # Parse separator (line 1) — skip it
    # Parse data rows
    data_rows = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.split("|") if c.strip()]
        data_rows.append(cells)

    # Build LaTeX
    col_spec = "@{}" + "l" * ncols + "@{}"
    out = []
    out.append("\\begin{table*}[t]")
    out.append("\\small")
    out.append(f"\\begin{{tabular}}{{{col_spec}}}")
    out.append("\\toprule")

    # Header row with bold
    header = " & ".join(f"\\textbf{{{c}}}" for c in header_cells) + " \\\\"
    out.append(header)
    out.append("\\midrule")

    # Data rows
    for cells in data_rows:
        # Pad or truncate to match header column count
        while len(cells) < ncols:
            cells.append("")
        row_cells = []
        for c in cells[:ncols]:
            # Convert markdown bold
            c = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", c)
            # Convert markdown italic
            c = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", c)
            # Convert markdown code
            c = re.sub(r"`([^`]+)`", r"\\texttt{\1}", c)
            # Escape special chars
            c = c.replace("$", "\\$")
            c = c.replace("%", "\\%")
            c = c.replace("#", "\\#")
            c = c.replace("_", "\\_")
            c = c.replace("~", "\\textasciitilde{}")
            c = c.replace("—", "---")
            c = c.replace("–", "--")
            c = c.replace("↔", "$\\leftrightarrow$")
            # Handle strikethrough
            c = re.sub(r"~~([^~]+)~~", r"\\sout{\1}", c)
            row_cells.append(c)
        out.append(" & ".join(row_cells) + " \\\\")

    out.append("\\bottomrule")
    out.append("\\end{tabular}")
    out.append("\\end{table*}")

    return "\n".join(out)


def md_to_latex_body(text: str) -> str:
    """Convert markdown body text to LaTeX, handling inline formatting."""
    # Extract tables and code blocks FIRST, replace with placeholders
    # to protect them from inline formatting
    placeholders = {}
    counter = [0]

    def stash(content):
        key = f"%%PLACEHOLDER_{counter[0]}%%"
        counter[0] += 1
        placeholders[key] = content
        return key

    # Code blocks → stash
    def stash_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        if lang:
            latex = f"\\begin{{lstlisting}}[language={lang}]\n{code}\\end{{lstlisting}}"
        else:
            latex = f"\\begin{{lstlisting}}\n{code}\\end{{lstlisting}}"
        return stash(latex)

    text = re.sub(r"```(\w*)\n(.*?)```", stash_code_block, text, flags=re.DOTALL)

    # Tables → stash
    def stash_table(match):
        return stash(md_table_to_latex(match.group(0)))

    text = re.sub(
        r"(?:^\|.+\|$\n?)+",
        stash_table,
        text,
        flags=re.MULTILINE,
    )

    # NOW safe to do inline formatting (tables and code are placeholders)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", text)
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)

    # Block quotes → quotation
    lines = text.split("\n")
    result = []
    in_quote = False
    for line in lines:
        if line.startswith("> "):
            if not in_quote:
                result.append("\\begin{quotation}")
                in_quote = True
            result.append(line[2:])
        else:
            if in_quote:
                result.append("\\end{quotation}")
                in_quote = False
            result.append(line)
    if in_quote:
        result.append("\\end{quotation}")
    text = "\n".join(result)

    # Bullet lists → itemize
    text = re.sub(r"^- ", r"\\item ", text, flags=re.MULTILINE)

    # Add \begin{itemize}/\end{itemize} around consecutive \item lines
    lines = text.split("\n")
    result = []
    in_list = False
    for line in lines:
        if line.strip().startswith("\\item "):
            if not in_list:
                result.append("\\begin{itemize}")
                in_list = True
            result.append(line)
        else:
            if in_list:
                result.append("\\end{itemize}")
                in_list = False
            result.append(line)
    if in_list:
        result.append("\\end{itemize}")
    text = "\n".join(result)

    # Numbered lists
    text = re.sub(r"^\d+\. ", r"\\item ", text, flags=re.MULTILINE)

    # Special characters
    text = text.replace("—", "---")
    text = text.replace("–", "--")
    text = text.replace("↔", "$\\leftrightarrow$")
    text = text.replace("【", "[")
    text = text.replace("】", "]")
    text = text.replace("−", "-")

    # Escape $ in body text (but not in LaTeX commands or math)
    # Only escape bare $ that aren't already part of \$ or math delimiters
    text = re.sub(r"(?<!\\)\$(?!\$|\\)", r"\\$", text)

    # URLs → \url{}
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r"\\href{\2}{\1}",
        text,
    )

    # Restore stashed tables and code blocks
    for key, val in placeholders.items():
        text = text.replace(key, val)

    return text


def split_sections(md_text: str):
    """Split markdown into sections based on ## headers."""
    # Remove title and subtitle (# and ## at very start)
    md_text = re.sub(r"^# [^\n]+\n## [^\n]+\n", "", md_text)

    # Split on ## headers (main sections)
    parts = re.split(r"(?=^## )", md_text, flags=re.MULTILINE)

    sections = {}
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract section header
        header_match = re.match(r"^## (\d+\.)?\s*(.+)", part)
        if not header_match:
            # Could be the abstract (no ## header)
            if part.startswith("**Abstract.**"):
                sections["abstract"] = part.replace("**Abstract.**", "").strip()
            continue

        num = header_match.group(1) or ""
        title = header_match.group(2).strip()

        # Remove the header line from the body
        body = re.sub(r"^## [^\n]+\n", "", part).strip()

        # Map to filenames
        title_lower = title.lower()
        if "introduction" in title_lower:
            key = "intro"
        elif "background" in title_lower:
            key = "background"
        elif "methodology" in title_lower:
            key = "methodology"
        elif "result" in title_lower:
            key = "results"
        elif "discussion" in title_lower:
            key = "discussion"
        elif "conclusion" in title_lower:
            key = "conclusion"
        elif "appendix" in title_lower:
            key = f"appendix_{title}"
        else:
            key = title_lower.replace(" ", "_")

        sections[key] = (title, body)

    return sections


def convert_subsections(text: str) -> str:
    """Convert ### and #### headers to \\subsection and \\subsubsection."""
    # #### N.N.N Title → \subsubsection{Title}
    text = re.sub(
        r"^#### (\d+\.\d+\.\d+\s+)?(.+)",
        r"\\subsubsection{\2}",
        text,
        flags=re.MULTILINE,
    )
    # ### N.N Title → \subsection{Title}
    text = re.sub(
        r"^### (\d+\.\d+\s+)?(.+)",
        r"\\subsection{\2}",
        text,
        flags=re.MULTILINE,
    )
    return text


def main():
    md = PAPER_MD.read_text()

    # Extract abstract (between Abstract. and first ##)
    abs_match = re.search(
        r"\*\*Abstract\.\*\*\s*\n(.*?)(?=\n## )", md, re.DOTALL
    )
    abstract_text = abs_match.group(1).strip() if abs_match else ""

    # Split into sections
    # Find all ## headers and their positions
    section_pattern = re.compile(r"^## (\d+\.\s+)?(.+)$", re.MULTILINE)
    matches = list(section_pattern.finditer(md))

    file_map = {
        "Introduction": "intro",
        "Background and Related Work": "background",
        "Methodology": "methodology",
        "Results": "results",
        "Discussion": "discussion",
        "Conclusion": "conclusion",
    }

    appendix_parts = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        title = match.group(2).strip()
        body = md[match.end() : end].strip()

        # Convert subsections first (before general inline processing)
        body = convert_subsections(body)

        # Convert body to LaTeX
        body = md_to_latex_body(body)

        # Determine filename
        fname = None
        for key, val in file_map.items():
            if key in title:
                fname = val
                break

        if title.startswith("Appendix"):
            appendix_parts.append(f"\\section{{{title}}}\n\n{body}")
            continue

        if fname:
            section_cmd = f"\\section{{{title}}}\n\n{body}\n"
            OUT_DIR.joinpath(f"{fname}.tex").write_text(section_cmd)
            print(f"  {fname}.tex: {len(body.splitlines())} lines")
        else:
            print(f"  UNMAPPED: {title}")

    # Write abstract
    abstract_latex = md_to_latex_body(abstract_text)
    OUT_DIR.joinpath("abstract.tex").write_text(abstract_latex + "\n")
    print(f"  abstract.tex: {len(abstract_latex.splitlines())} lines")

    # Write appendices
    if appendix_parts:
        appendix_content = "\n\n".join(appendix_parts)
        OUT_DIR.joinpath("appendix.tex").write_text(appendix_content + "\n")
        print(f"  appendix.tex: {len(appendix_content.splitlines())} lines")

    print("\nDone. Run: cd papers && pdflatex main.tex")


if __name__ == "__main__":
    main()
