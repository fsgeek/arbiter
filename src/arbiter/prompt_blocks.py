"""Data models for system prompt archaeology — decomposing and classifying prompt blocks."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Tier(str, Enum):
    """Maps to Arbiter's three-tier model."""

    system = "system"
    domain = "domain"
    application = "application"


class BlockCategory(str, Enum):
    """What kind of prompt block this is."""

    identity = "identity"
    behavioral_constraint = "behavioral-constraint"
    tool_definition = "tool-definition"
    workflow = "workflow"
    policy = "policy"
    context = "context"
    meta = "meta"


class Modality(str, Enum):
    """The deontic modality of the block's behavioral directives."""

    prohibition = "prohibition"
    mandate = "mandate"
    permission = "permission"
    definition = "definition"
    mixed = "mixed"  # block contains multiple modalities


class InterferenceType(str, Enum):
    """How two blocks interfere with each other."""

    direct_contradiction = "direct-contradiction"
    scope_overlap = "scope-overlap"
    implicit_dependency = "implicit-dependency"
    ordering_sensitivity = "ordering-sensitivity"
    priority_ambiguity = "priority-ambiguity"


class Severity(str, Enum):
    minor = "minor"
    major = "major"
    critical = "critical"


class DetectionMethod(str, Enum):
    manual = "manual"
    static = "static"
    dynamic = "dynamic"


class PromptBlock(BaseModel):
    """A contiguous unit of prompt text that establishes behavioral contracts."""

    id: str = Field(description="e.g. 'claude-code/git-safety'")
    source: str = Field(description="Corpus identifier + version, e.g. 'claude-code/v2.1.50'")
    tier: Tier
    category: BlockCategory
    text: str = Field(description="The raw block text")
    modality: Modality
    scope: list[str] = Field(
        default_factory=list,
        description="What aspects of behavior this block constrains",
    )
    exports: list[str] = Field(
        default_factory=list,
        description="Behavioral contracts this block establishes",
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Contracts this block depends on from other blocks",
    )
    line_start: int | None = Field(
        default=None, description="Start line in source file (1-indexed)"
    )
    line_end: int | None = Field(
        default=None, description="End line in source file (1-indexed)"
    )

    def scopes_overlap(self, other: PromptBlock) -> bool:
        """True if this block shares any scope entries with another."""
        return bool(set(self.scope) & set(other.scope))


class InterferencePattern(BaseModel):
    """A detected composition bug between two prompt blocks."""

    block_a: str = Field(description="Block ID")
    block_b: str = Field(description="Block ID")
    type: InterferenceType
    description: str = Field(description="What the interference is")
    severity: Severity
    detection: DetectionMethod
    would_compiler_catch: bool = Field(
        description="Could a static type system for prompts catch this?"
    )
    evidence: str | None = Field(
        default=None,
        description="Specific text snippets demonstrating the interference",
    )


class PromptCorpus(BaseModel):
    """A collection of decomposed prompt blocks with interference analysis."""

    name: str = Field(description="e.g. 'claude-code/v2.1.50'")
    source_file: str = Field(description="Path to the original prompt file")
    blocks: list[PromptBlock] = Field(default_factory=list)
    interference: list[InterferencePattern] = Field(default_factory=list)
