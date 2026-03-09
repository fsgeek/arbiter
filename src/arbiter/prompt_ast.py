"""Prompt AST — hierarchical parse tree for system prompts.

Turns raw system prompt text into a tree structure that captures:
- Document → ContentBlock → Section → (Paragraph | Directive | List | CodeBlock)
- Heading hierarchy (# > ## > ###) creates nested scopes
- Directives (MUST/NEVER/ALWAYS/IMPORTANT) are first-class nodes
- Metadata (billing headers, env vars) extracted and normalized

The tree enables:
1. Structural diffing across versions (what moved, what's new)
2. MOSS-style similarity detection (hash subtrees, match structures)
3. Scope-aware interference analysis (directives inherit section scope)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Union


class NodeKind(str, Enum):
    document = "document"
    content_block = "content_block"
    section = "section"
    paragraph = "paragraph"
    directive = "directive"
    list_node = "list"
    list_item = "list_item"
    code_block = "code_block"
    metadata = "metadata"


class DirectiveType(str, Enum):
    prohibition = "prohibition"      # NEVER, MUST NOT, DO NOT
    mandate = "mandate"              # MUST, ALWAYS, REQUIRED
    important = "important"          # IMPORTANT:
    critical = "critical"            # CRITICAL:
    permission = "permission"        # MAY, CAN, ALLOWED


class SemanticRole(str, Enum):
    """What a node *means* in the prompt's function.

    The structural layer says "this is a list item under a heading."
    The semantic layer says "this is a file-creation prohibition scoped
    to the tool-usage channel."
    """
    identity = "identity"            # "You are Claude Code"
    policy = "policy"                # Behavioral constraints
    safety = "safety"                # Security, content policy
    tool_usage = "tool_usage"        # How to use tools (not definitions)
    tool_definition = "tool_def"     # Tool schemas (inline or external)
    workflow = "workflow"             # Step-by-step procedures
    format = "format"                # Output formatting rules
    memory_policy = "memory_policy"  # Auto memory instructions
    environment = "environment"      # Runtime context (dir, platform)
    meta = "meta"                    # Billing, version, bookkeeping
    unknown = "unknown"


class Channel(str, Enum):
    """Which communication channel a node belongs to.

    v2.1.50 had everything in one channel (system prompt text).
    v2.1.71 splits into behavior + tool_schema + memory.
    Interference across channels is harder to detect because
    the constraints live in different data structures.
    """
    behavior = "behavior"            # Identity, Policy, Safety, Format, Workflow
    tool_schema = "tool_schema"      # Tool definitions (API tools param or inline)
    memory = "memory"                # Memory policy and config
    environment = "environment"      # Runtime context, meta


@dataclass
class ASTNode:
    """A node in the prompt AST."""
    kind: NodeKind
    text: str = ""                   # Raw text content
    children: list[ASTNode] = field(default_factory=list)
    # Section-specific
    heading_level: int = 0           # 1 for #, 2 for ##, etc.
    heading_text: str = ""           # The heading content
    # Directive-specific
    directive_type: DirectiveType | None = None
    # Metadata-specific
    meta_key: str = ""               # e.g. "cc_version", "model", "platform"
    meta_value: str = ""
    # Code block
    language: str = ""               # Fenced code block language
    # Semantic layer (populated by annotate_semantics)
    semantic_role: SemanticRole | None = None
    channel: Channel | None = None
    # Structural hash (for MOSS-style comparison)
    _struct_hash: str = ""

    def structural_hash(self) -> str:
        """Hash based on structure, not content.

        Two nodes match if they have the same kind, same children structure,
        and (for sections) same heading level. Content is ignored — this is
        how MOSS finds structural plagiarism despite rewording.
        """
        if self._struct_hash:
            return self._struct_hash

        parts = [self.kind.value]
        if self.kind == NodeKind.section:
            parts.append(str(self.heading_level))
        if self.kind == NodeKind.directive:
            parts.append(self.directive_type.value if self.directive_type else "?")
        child_hashes = [c.structural_hash() for c in self.children]
        parts.extend(child_hashes)
        raw = "|".join(parts)
        self._struct_hash = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return self._struct_hash

    def content_hash(self) -> str:
        """Hash based on normalized content (for exact-match detection)."""
        normalized = _normalize_text(self.text)
        child_hashes = [c.content_hash() for c in self.children]
        raw = normalized + "|" + "|".join(child_hashes)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def depth(self) -> int:
        if not self.children:
            return 0
        return 1 + max(c.depth() for c in self.children)

    def node_count(self) -> int:
        return 1 + sum(c.node_count() for c in self.children)

    def directives(self) -> list[ASTNode]:
        """All directive nodes in this subtree."""
        result = []
        if self.kind == NodeKind.directive:
            result.append(self)
        for c in self.children:
            result.extend(c.directives())
        return result

    def sections(self) -> list[ASTNode]:
        """All section nodes in this subtree."""
        result = []
        if self.kind == NodeKind.section:
            result.append(self)
        for c in self.children:
            result.extend(c.sections())
        return result

    def walk(self) -> list[ASTNode]:
        """Pre-order traversal of all nodes."""
        result = [self]
        for c in self.children:
            result.extend(c.walk())
        return result

    def skeleton(self, indent: int = 0) -> str:
        """Human-readable structural outline."""
        prefix = "  " * indent
        label = self.kind.value
        extra = ""
        if self.kind == NodeKind.section:
            extra = f" [h{self.heading_level}] {self.heading_text!r}"
        elif self.kind == NodeKind.directive:
            dtype = self.directive_type.value if self.directive_type else "?"
            preview = self.text[:60].replace("\n", " ")
            extra = f" [{dtype}] {preview!r}"
        elif self.kind == NodeKind.metadata:
            extra = f" {self.meta_key}={self.meta_value!r}"
        elif self.kind == NodeKind.code_block:
            extra = f" lang={self.language!r}" if self.language else ""
        elif self.kind == NodeKind.paragraph:
            preview = self.text[:50].replace("\n", " ")
            extra = f" {preview!r}"

        lines = [f"{prefix}{label}{extra}"]
        for c in self.children:
            lines.append(c.skeleton(indent + 1))
        return "\n".join(lines)


# --- Normalization ---

_VAR_PATTERNS = [
    (re.compile(r"/home/\S+"), "<PATH>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "<DATE>"),
    (re.compile(r"v\d+\.\d+\.\d+\S*"), "<VERSION>"),
    (re.compile(r"[0-9a-f]{7,40}"), "<HASH>"),
    (re.compile(r"claude-\w+-\d+-\d+\S*"), "<MODEL_ID>"),
    (re.compile(r"http\S+"), "<URL>"),
]


def _normalize_text(text: str) -> str:
    """Strip variable content for content comparison."""
    result = text.strip().lower()
    for pattern, replacement in _VAR_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# --- Parsing ---

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"^```(\w*)\s*$", re.MULTILINE)
_DIRECTIVE_RE = re.compile(
    r"(?:^|\n)\s*"
    r"(IMPORTANT|CRITICAL|NEVER|MUST NOT|DO NOT|MUST(?!\s+NOT)|ALWAYS|REQUIRED|MAY|CAN|ALLOWED)"
    r"[:\s]",
    re.MULTILINE,
)
_BULLET_RE = re.compile(r"^\s*[-*]\s+", re.MULTILINE)
_METADATA_RE = re.compile(
    r"^(x-anthropic-\S+|cc_version|cc_entrypoint|cch)[:=]\s*(.+)$",
    re.MULTILINE,
)
_KV_BILLING_RE = re.compile(r"(\w+)=([^;]+);?\s*")


def _classify_directive(keyword: str) -> DirectiveType:
    kw = keyword.upper().strip()
    if kw in ("NEVER", "MUST NOT", "DO NOT"):
        return DirectiveType.prohibition
    if kw in ("MUST", "ALWAYS", "REQUIRED"):
        return DirectiveType.mandate
    if kw == "IMPORTANT":
        return DirectiveType.important
    if kw == "CRITICAL":
        return DirectiveType.critical
    return DirectiveType.permission


def _parse_metadata(text: str) -> list[ASTNode]:
    """Extract metadata nodes from billing headers and env lines."""
    nodes = []
    # x-anthropic-billing-header: key=val; key=val; ...
    if text.startswith("x-anthropic-"):
        colon = text.find(":")
        if colon > 0:
            header_name = text[:colon].strip()
            header_val = text[colon + 1:].strip()
            for m in _KV_BILLING_RE.finditer(header_val):
                nodes.append(ASTNode(
                    kind=NodeKind.metadata,
                    text=m.group(0).strip(),
                    meta_key=m.group(1),
                    meta_value=m.group(2).strip().rstrip(";"),
                ))
            if not nodes:
                nodes.append(ASTNode(
                    kind=NodeKind.metadata,
                    text=text,
                    meta_key=header_name,
                    meta_value=header_val,
                ))
    return nodes


def _split_code_blocks(text: str) -> list[tuple[str, str | None]]:
    """Split text into (text, None) and (code, language) segments."""
    segments: list[tuple[str, str | None]] = []
    pos = 0
    for m in _CODE_FENCE_RE.finditer(text):
        fence_start = m.start()
        lang = m.group(1)
        # Find closing fence
        close = text.find("\n```", m.end())
        if close < 0:
            continue
        close_end = close + 4  # past the closing ```
        # Text before the code block
        if fence_start > pos:
            segments.append((text[pos:fence_start], None))
        # The code block content (between fences)
        code_content = text[m.end():close].strip("\n")
        segments.append((code_content, lang))
        pos = close_end
        # Skip past any trailing newline
        if pos < len(text) and text[pos] == "\n":
            pos += 1
    if pos < len(text):
        segments.append((text[pos:], None))
    return segments


def _is_list_block(text: str) -> bool:
    """Check if text is primarily a bullet list."""
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return False
    bullet_lines = sum(1 for l in lines if _BULLET_RE.match(l))
    return bullet_lines > len(lines) * 0.5


def _parse_list(text: str) -> ASTNode:
    """Parse a bullet list into list + list_item nodes."""
    items: list[ASTNode] = []
    current_lines: list[str] = []
    for line in text.split("\n"):
        if _BULLET_RE.match(line):
            if current_lines:
                items.append(ASTNode(
                    kind=NodeKind.list_item,
                    text="\n".join(current_lines),
                ))
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)
    if current_lines:
        items.append(ASTNode(
            kind=NodeKind.list_item,
            text="\n".join(current_lines),
        ))
    return ASTNode(kind=NodeKind.list_node, text=text, children=items)


def _has_directive(text: str) -> DirectiveType | None:
    """Check if text starts with or prominently contains a directive keyword."""
    m = _DIRECTIVE_RE.match(text.strip())
    if m:
        return _classify_directive(m.group(1))
    # Check first line for directive at start
    first_line = text.strip().split("\n")[0]
    m = re.match(
        r"^\s*(IMPORTANT|CRITICAL|NEVER|MUST NOT|DO NOT|MUST(?!\s+NOT)|ALWAYS)[:\s]",
        first_line,
    )
    if m:
        return _classify_directive(m.group(1))
    return None


def _parse_text_block(text: str) -> ASTNode:
    """Parse a text segment (not code, not heading) into paragraph/directive/list."""
    text = text.strip()
    if not text:
        return ASTNode(kind=NodeKind.paragraph, text="")

    # Check for directive
    dtype = _has_directive(text)
    if dtype:
        return ASTNode(kind=NodeKind.directive, text=text, directive_type=dtype)

    # Check for list
    if _is_list_block(text):
        return _parse_list(text)

    return ASTNode(kind=NodeKind.paragraph, text=text)


def _parse_section_content(text: str) -> list[ASTNode]:
    """Parse the content within a section (between headings) into child nodes."""
    nodes: list[ASTNode] = []
    # First split out code blocks
    segments = _split_code_blocks(text)
    for content, lang in segments:
        if lang is not None:
            nodes.append(ASTNode(
                kind=NodeKind.code_block,
                text=content,
                language=lang,
            ))
        else:
            # Split on double-newlines into paragraphs
            paras = re.split(r"\n\n+", content)
            for para in paras:
                para = para.strip()
                if not para:
                    continue
                # Check for metadata first
                meta = _parse_metadata(para)
                if meta:
                    nodes.extend(meta)
                else:
                    nodes.append(_parse_text_block(para))
    return nodes


def parse_prompt(text: str) -> ASTNode:
    """Parse a system prompt into an AST.

    Handles both raw text prompts and the text extracted from
    API content blocks (join with double-newline before calling).
    """
    root = ASTNode(kind=NodeKind.document)

    # Find all headings to create section structure
    heading_positions: list[tuple[int, int, int, str]] = []  # (start, end, level, text)
    for m in _HEADING_RE.finditer(text):
        heading_positions.append((
            m.start(),
            m.end(),
            len(m.group(1)),
            m.group(2).strip(),
        ))

    if not heading_positions:
        # No headings — flat document
        root.children = _parse_section_content(text)
        return root

    # Content before first heading
    pre_heading = text[:heading_positions[0][0]]
    if pre_heading.strip():
        root.children.extend(_parse_section_content(pre_heading))

    # Build sections with heading hierarchy
    # We use a stack to handle nested sections (## under #)
    section_stack: list[ASTNode] = [root]

    for i, (start, end, level, heading_text) in enumerate(heading_positions):
        # Get content until next heading or end
        if i + 1 < len(heading_positions):
            content_end = heading_positions[i + 1][0]
        else:
            content_end = len(text)
        content = text[end:content_end]

        section = ASTNode(
            kind=NodeKind.section,
            heading_level=level,
            heading_text=heading_text,
        )
        section.children = _parse_section_content(content)

        # Pop stack until we find a parent with lower heading level
        while (len(section_stack) > 1
               and section_stack[-1].kind == NodeKind.section
               and section_stack[-1].heading_level >= level):
            section_stack.pop()

        section_stack[-1].children.append(section)
        section_stack.append(section)

    return root


def parse_api_blocks(blocks: list[dict]) -> ASTNode:
    """Parse from the API content block format (list of {type, text} dicts)."""
    root = ASTNode(kind=NodeKind.document)

    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        text = block.get("text", "")
        if not text:
            continue

        cb = ASTNode(kind=NodeKind.content_block)
        # Parse the text within each content block
        inner = parse_prompt(text)
        cb.children = inner.children
        root.children.append(cb)

    return root


# --- Structural Diffing ---

@dataclass
class ASTDiff:
    """Result of diffing two ASTs."""
    added: list[ASTNode] = field(default_factory=list)      # In B but not A
    removed: list[ASTNode] = field(default_factory=list)     # In A but not B
    moved: list[tuple[ASTNode, ASTNode]] = field(default_factory=list)  # Same content, different position
    modified: list[tuple[ASTNode, ASTNode]] = field(default_factory=list)  # Same structure, different content

    def summary(self) -> str:
        lines = []
        if self.added:
            lines.append(f"Added ({len(self.added)}):")
            for n in self.added:
                lines.append(f"  + {n.kind.value}: {n.heading_text or n.text[:60]}")
        if self.removed:
            lines.append(f"Removed ({len(self.removed)}):")
            for n in self.removed:
                lines.append(f"  - {n.kind.value}: {n.heading_text or n.text[:60]}")
        if self.moved:
            lines.append(f"Moved ({len(self.moved)}):")
            for a, b in self.moved:
                lines.append(f"  ~ {a.heading_text or a.text[:40]} → {b.heading_text or b.text[:40]}")
        if self.modified:
            lines.append(f"Modified ({len(self.modified)}):")
            for a, b in self.modified:
                lines.append(f"  Δ {a.heading_text or a.text[:60]}")
        if not any([self.added, self.removed, self.moved, self.modified]):
            lines.append("No structural differences.")
        return "\n".join(lines)


def diff_ast(a: ASTNode, b: ASTNode) -> ASTDiff:
    """Diff two ASTs by structural and content hashes.

    Strategy:
    1. Collect all section/directive nodes from each tree
    2. Match by content hash (identical content = same node)
    3. Match remaining by structural hash (same shape = modified)
    4. Unmatched in A = removed, unmatched in B = added
    """
    result = ASTDiff()

    # Collect comparable nodes (sections and directives)
    a_nodes = [n for n in a.walk() if n.kind in (NodeKind.section, NodeKind.directive)]
    b_nodes = [n for n in b.walk() if n.kind in (NodeKind.section, NodeKind.directive)]

    # Index by content hash
    a_by_content = {}
    for n in a_nodes:
        h = n.content_hash()
        a_by_content.setdefault(h, []).append(n)

    b_by_content = {}
    for n in b_nodes:
        h = n.content_hash()
        b_by_content.setdefault(h, []).append(n)

    # Exact matches
    matched_a: set[int] = set()
    matched_b: set[int] = set()
    for h in set(a_by_content) & set(b_by_content):
        for i, na in enumerate(a_by_content[h]):
            for j, nb in enumerate(b_by_content[h]):
                if id(na) not in matched_a and id(nb) not in matched_b:
                    matched_a.add(id(na))
                    matched_b.add(id(nb))

    # Structural matches among unmatched
    unmatched_a = [n for n in a_nodes if id(n) not in matched_a]
    unmatched_b = [n for n in b_nodes if id(n) not in matched_b]

    a_by_struct = {}
    for n in unmatched_a:
        h = n.structural_hash()
        a_by_struct.setdefault(h, []).append(n)

    b_by_struct = {}
    for n in unmatched_b:
        h = n.structural_hash()
        b_by_struct.setdefault(h, []).append(n)

    struct_matched_a: set[int] = set()
    struct_matched_b: set[int] = set()
    for h in set(a_by_struct) & set(b_by_struct):
        for na in a_by_struct[h]:
            for nb in b_by_struct[h]:
                if id(na) not in struct_matched_a and id(nb) not in struct_matched_b:
                    result.modified.append((na, nb))
                    struct_matched_a.add(id(na))
                    struct_matched_b.add(id(nb))

    # Remaining unmatched
    for n in unmatched_a:
        if id(n) not in struct_matched_a:
            result.removed.append(n)
    for n in unmatched_b:
        if id(n) not in struct_matched_b:
            result.added.append(n)

    return result


# --- Semantic Annotation ---

# Section heading → semantic role mapping (case-insensitive)
# Vendor-neutral: maps section heading keywords to semantic roles.
# Built from Claude Code, Codex GPT-5.2, and Gemini CLI prompts.
_SECTION_ROLE_MAP = {
    # Policy / behavioral constraints
    "system": SemanticRole.policy,
    "doing tasks": SemanticRole.policy,
    "how you work": SemanticRole.policy,
    "core mandates": SemanticRole.policy,
    "autonomy and persistence": SemanticRole.policy,
    "responsiveness": SemanticRole.policy,
    "ambition vs. precision": SemanticRole.policy,
    "engineering standards": SemanticRole.policy,
    "operational guidelines": SemanticRole.policy,
    "interaction details": SemanticRole.policy,
    "context efficiency": SemanticRole.policy,
    # Identity
    "personality": SemanticRole.identity,
    # Safety
    "executing actions with care": SemanticRole.safety,
    "security & system integrity": SemanticRole.safety,
    "security and safety rules": SemanticRole.safety,
    "critical security rule": SemanticRole.safety,
    # Tools
    "using your tools": SemanticRole.tool_usage,
    "tool guidelines": SemanticRole.tool_usage,
    "tool usage": SemanticRole.tool_usage,
    "shell commands": SemanticRole.tool_usage,
    "apply_patch": SemanticRole.tool_usage,
    "update_plan": SemanticRole.tool_usage,
    # Format / presentation
    "tone and style": SemanticRole.format,
    "output efficiency": SemanticRole.format,
    "presenting your work": SemanticRole.format,
    "final answer structure and style guidelines": SemanticRole.format,
    # Workflow
    "task execution": SemanticRole.workflow,
    "planning": SemanticRole.workflow,
    "validating your work": SemanticRole.workflow,
    "primary workflows": SemanticRole.workflow,
    "development lifecycle": SemanticRole.workflow,
    "new applications": SemanticRole.workflow,
    "git safety protocol": SemanticRole.workflow,
    "git repository": SemanticRole.workflow,
    # Memory
    "auto memory": SemanticRole.memory_policy,
    "how to save memories": SemanticRole.memory_policy,
    "what to save": SemanticRole.memory_policy,
    "what not to save": SemanticRole.memory_policy,
    "explicit user requests": SemanticRole.memory_policy,
    "history compression system prompt": SemanticRole.memory_policy,
    # Environment
    "environment": SemanticRole.environment,
    "sandbox": SemanticRole.environment,
    "hook context": SemanticRole.environment,
    # Meta
    "agents.md spec": SemanticRole.meta,
    "available sub-agents": SemanticRole.meta,
    "contextual instructions (gemini.md)": SemanticRole.meta,
    "examples": SemanticRole.meta,
    "goal": SemanticRole.meta,
    "strategic orchestration & delegation": SemanticRole.workflow,
}

_ROLE_TO_CHANNEL = {
    SemanticRole.identity: Channel.behavior,
    SemanticRole.policy: Channel.behavior,
    SemanticRole.safety: Channel.behavior,
    SemanticRole.tool_usage: Channel.tool_schema,
    SemanticRole.tool_definition: Channel.tool_schema,
    SemanticRole.workflow: Channel.behavior,
    SemanticRole.format: Channel.behavior,
    SemanticRole.memory_policy: Channel.memory,
    SemanticRole.environment: Channel.environment,
    SemanticRole.meta: Channel.environment,
    SemanticRole.unknown: Channel.behavior,
}

# Keyword patterns for classifying nodes without section context
_ROLE_PATTERNS = [
    (re.compile(r"\byou are\b", re.I), SemanticRole.identity),
    (re.compile(r"\b(security|safety|owasp|vulnerabilit|injection|xss)\b", re.I), SemanticRole.safety),
    (re.compile(r"\b(tool|bash|grep|glob|read|write|edit|notebook)\b", re.I), SemanticRole.tool_usage),
    (re.compile(r"\b(commit|pull request|git |push|branch)\b", re.I), SemanticRole.workflow),
    (re.compile(r"\b(memory|remember|forget|MEMORY\.md)\b", re.I), SemanticRole.memory_policy),
    (re.compile(r"\b(format|markdown|emoji|concise|output|tone)\b", re.I), SemanticRole.format),
    (re.compile(r"\b(working directory|platform|shell|os version|model.*id|knowledge cutoff)\b", re.I), SemanticRole.environment),
    (re.compile(r"\b(x-anthropic|billing|cc_version|entrypoint)\b", re.I), SemanticRole.meta),
]


def _classify_role(node: ASTNode, parent_role: SemanticRole | None = None) -> SemanticRole:
    """Classify a node's semantic role from context and content."""
    if node.kind == NodeKind.metadata:
        return SemanticRole.meta

    if node.kind == NodeKind.section:
        key = node.heading_text.lower().rstrip(":")
        if key in _SECTION_ROLE_MAP:
            return _SECTION_ROLE_MAP[key]

    # Inherit from parent section
    if parent_role and node.kind in (NodeKind.list_item, NodeKind.paragraph,
                                      NodeKind.directive, NodeKind.list_node):
        return parent_role

    # Keyword-based fallback
    text = node.text or node.heading_text
    for pattern, role in _ROLE_PATTERNS:
        if pattern.search(text):
            return role

    return SemanticRole.unknown


def annotate_semantics(node: ASTNode, parent_role: SemanticRole | None = None) -> None:
    """Walk the AST and annotate each node with semantic role and channel."""
    node.semantic_role = _classify_role(node, parent_role)
    node.channel = _ROLE_TO_CHANNEL.get(node.semantic_role, Channel.behavior)

    child_role = node.semantic_role if node.kind == NodeKind.section else parent_role
    for child in node.children:
        annotate_semantics(child, child_role)


def channel_summary(node: ASTNode) -> dict[str, dict]:
    """Summarize nodes by channel and semantic role."""
    counts: dict[str, dict[str, int]] = {}
    for n in node.walk():
        if n.channel is None:
            continue
        ch = n.channel.value
        role = n.semantic_role.value if n.semantic_role else "unknown"
        if ch not in counts:
            counts[ch] = {}
        counts[ch][role] = counts[ch].get(role, 0) + 1
    return counts
