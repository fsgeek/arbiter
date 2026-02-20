"""Core data models for Arbiter's three-tier evaluation framework."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SystemLayer(BaseModel):
    """The constitution — invariant evaluation rules.

    Defines how the LLM judge operates. Must be internally consistent;
    no contradictions permitted. Validated once, does not change at runtime.
    """

    name: str = Field(description="Identifier for this system layer definition")
    rules: list[str] = Field(
        default_factory=list,
        description="Invariant rules governing evaluation behavior",
    )


class DomainLayer(BaseModel):
    """Contextual domain knowledge — mutable, conflicts expected.

    Provides domain-specific information the LLM judge needs. Changes as the
    domain evolves. Conflicts within this layer are detected and reported,
    governed by the system layer.
    """

    name: str = Field(description="Identifier for this domain definition")
    entries: list[str] = Field(
        default_factory=list,
        description="Domain knowledge entries that may conflict",
    )


class ConflictReport(BaseModel):
    """Describes a detected conflict between layers or within a layer.

    Answers: what conflicted, where it arose, and what would resolve it.
    """

    source: str = Field(description="Which layer or entry the conflict originates from")
    target: str = Field(description="Which layer or entry it conflicts with")
    description: str = Field(description="What the conflict is")
    resolution_hint: str | None = Field(
        default=None,
        description="What information or change would resolve this conflict",
    )


class EvaluationResult(BaseModel):
    """Result of evaluating an application query against system and domain layers."""

    resolved: bool = Field(description="Whether the query was cleanly resolved")
    output: str | None = Field(
        default=None,
        description="The resolved output, if resolution succeeded",
    )
    conflicts: list[ConflictReport] = Field(
        default_factory=list,
        description="Conflicts detected during evaluation",
    )
