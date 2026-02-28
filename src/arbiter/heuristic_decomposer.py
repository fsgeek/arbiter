"""Heuristic prompt decomposer — splits raw prompt text into blocks without LLM calls.

This is the free/instant fallback for offline use, CI pipelines, and quick
first-pass analysis. The LLM decomposer (via LLMCaller) is the real decomposer;
this is intentionally rough.

Splitting heuristics (ordered by priority):
1. Markdown headings (# ## ###) start new blocks
2. Code fences (``` blocks) kept as single units
3. Blank-line-delimited paragraphs
4. Root-level list items (- or * bullets)

Classification heuristics (regex, best-effort):
- MUST/NEVER/ALWAYS → mandate/prohibition
- tool/function/command → tool-usage category
- IMPORTANT/CRITICAL → system tier
- Default: application tier, behavioral category, descriptive modality
"""

from __future__ import annotations

import re

from .prompt_blocks import (
    BlockCategory,
    Modality,
    PromptBlock,
    Tier,
)


def _classify_modality(text: str) -> Modality:
    """Best-effort modality from keyword patterns."""
    upper = text.upper()
    has_prohibition = bool(re.search(r"\b(NEVER|MUST NOT|DO NOT|REFUSE|FORBIDDEN)\b", upper))
    has_mandate = bool(re.search(r"\b(MUST(?!\s+NOT)|ALWAYS|REQUIRED|SHALL)\b", upper))

    if has_prohibition and has_mandate:
        return Modality.mixed
    if has_prohibition:
        return Modality.prohibition
    if has_mandate:
        return Modality.mandate
    if re.search(r"\b(MAY|CAN|ALLOWED|OPTIONAL)\b", upper):
        return Modality.permission
    return Modality.definition


def _classify_category(text: str) -> BlockCategory:
    """Best-effort category from keyword patterns."""
    lower = text.lower()
    # Identity checked first — "You are a" is a strong signal
    if re.search(r"\b(identity|who you are|you are a)\b", lower):
        return BlockCategory.identity
    if re.search(r"\b(security|policy|safety|content.?policy|owasp)\b", lower):
        return BlockCategory.policy
    if re.search(r"\b(tool|function|command|bash|glob|grep|read|write|edit)\b", lower):
        return BlockCategory.tool_definition
    if re.search(r"\b(workflow|step|process|procedure|when .* follow)\b", lower):
        return BlockCategory.workflow
    if re.search(r"\b(context|environment|platform|directory|working dir)\b", lower):
        return BlockCategory.context
    if re.search(r"\b(meta|formatting|output|markdown|rendering)\b", lower):
        return BlockCategory.meta
    return BlockCategory.behavioral_constraint


def _classify_tier(text: str) -> Tier:
    """Best-effort tier from keyword patterns."""
    upper = text.upper()
    if re.search(r"\b(IMPORTANT|CRITICAL|NEVER|INVARIANT|CONSTITUTION)\b", upper):
        return Tier.system
    if re.search(r"\b(CONTEXT|ENVIRONMENT|PLATFORM|WORKING DIR|SESSION)\b", upper):
        return Tier.application
    return Tier.domain


def _extract_scope(text: str) -> list[str]:
    """Extract scope keywords from block text."""
    keywords = set()
    patterns = {
        "security": r"\b(security|safety|auth|credential|vulnerability)\b",
        "git": r"\b(git|commit|branch|push|pull|merge|rebase)\b",
        "tool-usage": r"\b(tool|function|bash|glob|grep|read|write|edit)\b",
        "file-operations": r"\b(file|directory|path|create|delete|read|write)\b",
        "communication": r"\b(output|respond|display|message|user|communicate)\b",
        "task-management": r"\b(todo|task|plan|progress|tracking)\b",
        "code-quality": r"\b(over.?engineer|refactor|abstract|helper|utility)\b",
        "content-policy": r"\b(url|emoji|praise|validation|superlative)\b",
    }
    lower = text.lower()
    for scope, pattern in patterns.items():
        if re.search(pattern, lower):
            keywords.add(scope)
    return sorted(keywords) if keywords else ["general"]


def _split_into_raw_chunks(text: str) -> list[tuple[str, int, int]]:
    """Split text into raw chunks with line numbers.

    Returns list of (chunk_text, line_start, line_end) tuples.
    Line numbers are 1-indexed.
    """
    lines = text.split("\n")
    chunks: list[tuple[str, int, int]] = []
    current_lines: list[str] = []
    chunk_start = 1
    in_code_fence = False

    for i, line in enumerate(lines):
        line_num = i + 1

        # Track code fences
        if line.strip().startswith("```"):
            if in_code_fence:
                # Closing fence — end the code block
                current_lines.append(line)
                chunks.append(("\n".join(current_lines), chunk_start, line_num))
                current_lines = []
                chunk_start = line_num + 1
                in_code_fence = False
                continue
            else:
                # Opening fence — flush current chunk first
                if current_lines and any(l.strip() for l in current_lines):
                    chunks.append(("\n".join(current_lines), chunk_start, line_num - 1))
                current_lines = [line]
                chunk_start = line_num
                in_code_fence = True
                continue

        if in_code_fence:
            current_lines.append(line)
            continue

        # Markdown heading starts a new block
        if re.match(r"^#{1,3}\s+", line):
            if current_lines and any(l.strip() for l in current_lines):
                chunks.append(("\n".join(current_lines), chunk_start, line_num - 1))
            current_lines = [line]
            chunk_start = line_num
            continue

        # Blank line: end current chunk if non-empty
        if not line.strip():
            if current_lines and any(l.strip() for l in current_lines):
                chunks.append(("\n".join(current_lines), chunk_start, line_num - 1))
                current_lines = []
                chunk_start = line_num + 1
            else:
                chunk_start = line_num + 1
            continue

        current_lines.append(line)

    # Flush remaining
    if current_lines and any(l.strip() for l in current_lines):
        chunks.append(("\n".join(current_lines), chunk_start, len(lines)))

    return chunks


def heuristic_decompose(text: str, source: str = "unknown") -> list[PromptBlock]:
    """Split prompt text into PromptBlocks using structural heuristics.

    This is intentionally rough — it exists so `arbiter prompt.md` does
    something useful without an API key. The LLM decomposer is the real
    decomposer; this is the fallback.

    Args:
        text: Raw prompt text.
        source: Corpus identifier (e.g. 'claude-code/v2.1.50').

    Returns:
        List of PromptBlock instances with best-effort classification.
    """
    raw_chunks = _split_into_raw_chunks(text)
    blocks: list[PromptBlock] = []

    for i, (chunk_text, line_start, line_end) in enumerate(raw_chunks):
        stripped = chunk_text.strip()
        if not stripped:
            continue

        blocks.append(
            PromptBlock(
                id=f"{source}:block_{i:03d}",
                source=source,
                tier=_classify_tier(stripped),
                category=_classify_category(stripped),
                text=stripped,
                modality=_classify_modality(stripped),
                scope=_extract_scope(stripped),
                exports=[],
                imports=[],
                line_start=line_start,
                line_end=line_end,
            )
        )

    return blocks
