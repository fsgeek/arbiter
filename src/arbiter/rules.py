"""Evaluation rule language — compilable rules for prompt interference detection.

Rules are the system and domain layers of Arbiter's three-tier model.
They define what interference patterns to look for in prompt blocks.
The compiler validates internal consistency: if the rule set compiles,
the evaluator can run it without hitting structural errors.

Built-in rules are seeded from the 21 interference patterns found in
archaeology of Claude Code v2.1.50 (session 7).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .prompt_blocks import InterferenceType, Modality, PromptBlock, Severity


class EvaluationRule(BaseModel):
    """A single rule for detecting interference between prompt blocks.

    Rules come in two flavors:
    - Structural: evaluated as Python predicates, no LLM call needed.
    - LLM-evaluated: uses a prompt template to ask the LLM about a block pair.
    """

    name: str = Field(description="Unique rule identifier, e.g. 'mandate-prohibition-conflict'")
    interference_type: InterferenceType
    description: str
    severity: Severity

    # Static pre-filter: which block pairs to check
    requires_scope_overlap: bool = Field(
        default=False,
        description="Only evaluate pairs with shared scope entries",
    )
    modality_a: Modality | None = Field(
        default=None,
        description="Filter: block A must have this modality (None = any)",
    )
    modality_b: Modality | None = Field(
        default=None,
        description="Filter: block B must have this modality (None = any)",
    )

    # Whether LLM is needed to confirm
    requires_llm: bool = Field(
        default=True,
        description="False = structural check only (Python predicate)",
    )
    prompt_template: str | None = Field(
        default=None,
        description="LLM prompt template with {block_a_text} and {block_b_text} placeholders",
    )

    def applies_to(self, block_a: PromptBlock, block_b: PromptBlock) -> bool:
        """Pre-filter: does this rule apply to this block pair?"""
        if self.requires_scope_overlap:
            if not set(block_a.scope) & set(block_b.scope):
                return False
        if self.modality_a is not None and block_a.modality != self.modality_a:
            return False
        if self.modality_b is not None and block_b.modality != self.modality_b:
            return False
        return True


class CompilationError(Exception):
    """Raised when a rule set fails consistency checking."""


class CompiledRuleSet(BaseModel):
    """A validated, ready-to-execute rule set.

    Created only via RuleSet.compile(). The existence of this object
    is the static guarantee: the evaluator can run these rules without
    hitting structural errors.
    """

    name: str
    rules: list[EvaluationRule]

    def structural_rules(self) -> list[EvaluationRule]:
        """Rules that don't need an LLM (Python predicates only)."""
        return [r for r in self.rules if not r.requires_llm]

    def llm_rules(self) -> list[EvaluationRule]:
        """Rules that require LLM evaluation."""
        return [r for r in self.rules if r.requires_llm]

    def scopes(self) -> set[str]:
        """All scopes this rule set cares about, for guiding decomposition."""
        # Derived from built-in rule descriptions — the decomposer uses this
        # to know what dimensions to look for in the prompt blob.
        # For now, we extract from rule names/descriptions as a heuristic.
        # A more formal approach would add explicit scope declarations to rules.
        return set()

    def applicable_pairs(
        self, blocks: list[PromptBlock]
    ) -> list[tuple[PromptBlock, PromptBlock, EvaluationRule]]:
        """All (block_a, block_b, rule) triples that pass pre-filtering.

        Considers unordered pairs only (no self-pairs, no duplicates).
        """
        triples = []
        for i, a in enumerate(blocks):
            for b in blocks[i + 1 :]:
                for rule in self.rules:
                    # Check both orderings for asymmetric modality filters
                    if rule.applies_to(a, b):
                        triples.append((a, b, rule))
                    elif rule.modality_a != rule.modality_b and rule.applies_to(b, a):
                        triples.append((b, a, rule))
        return triples


class RuleSet(BaseModel):
    """An unvalidated collection of rules. Must be compiled before use."""

    name: str
    rules: list[EvaluationRule] = Field(default_factory=list)

    def compile(self) -> CompiledRuleSet:
        """Validate internal consistency and return a CompiledRuleSet.

        Checks:
        - No duplicate rule names
        - All interference types are in the taxonomy
        - No structural rule with a prompt_template (contradictory)
        - No LLM rule without a prompt_template (incomplete)

        Raises CompilationError with all issues found (not just the first).
        """
        errors: list[str] = []

        # Check for duplicate names
        names = [r.name for r in self.rules]
        seen: set[str] = set()
        for name in names:
            if name in seen:
                errors.append(f"Duplicate rule name: {name!r}")
            seen.add(name)

        for rule in self.rules:
            # Structural rule should not have a prompt template
            if not rule.requires_llm and rule.prompt_template is not None:
                errors.append(
                    f"Rule {rule.name!r}: structural rule (requires_llm=False) "
                    f"must not have a prompt_template"
                )

            # LLM rule must have a prompt template
            if rule.requires_llm and rule.prompt_template is None:
                errors.append(
                    f"Rule {rule.name!r}: LLM rule (requires_llm=True) "
                    f"must have a prompt_template"
                )

        if errors:
            raise CompilationError(
                f"Rule set {self.name!r} failed compilation with "
                f"{len(errors)} error(s):\n" + "\n".join(f"  - {e}" for e in errors)
            )

        return CompiledRuleSet(name=self.name, rules=list(self.rules))


# ---------------------------------------------------------------------------
# Built-in rules — seeded from 21 interference patterns in archaeology
# ---------------------------------------------------------------------------

_MANDATE_PROHIBITION_PROMPT = """\
You are analyzing two blocks from a system prompt for interference.

## Block A
{block_a_text}

## Block B
{block_b_text}

## Task
Does Block A mandate (require) something that Block B prohibits (forbids), \
or vice versa? This is a direct contradiction if the same action is both \
required and forbidden, even if they apply in different contexts.

Respond with JSON only:
{{
  "score": <float 0.0 to 1.0, where 1.0 = certain contradiction>,
  "explanation": "<why this is or isn't a mandate/prohibition conflict>"
}}"""

_SCOPE_OVERLAP_PROMPT = """\
You are analyzing two blocks from a system prompt for interference.

## Block A
{block_a_text}

## Block B
{block_b_text}

## Task
Do these blocks regulate the same behavior with overlapping or redundant \
instructions? Score higher if the overlap creates ambiguity about which \
instruction takes precedence, or if they give subtly different guidance \
on the same topic.

Respond with JSON only:
{{
  "score": <float 0.0 to 1.0, where 1.0 = highly ambiguous overlap>,
  "explanation": "<what overlaps and whether it creates ambiguity>"
}}"""

_IMPLICIT_DEPENDENCY_PROMPT = """\
You are analyzing two blocks from a system prompt for interference.

## Block A
{block_a_text}

## Block B
{block_b_text}

## Task
Does Block A implicitly depend on or override Block B (or vice versa) \
without explicitly declaring the relationship? An implicit dependency \
exists when one block's instructions only make sense in the context of \
another block, or when one block silently narrows/broadens another's scope.

Respond with JSON only:
{{
  "score": <float 0.0 to 1.0, where 1.0 = strong undeclared dependency>,
  "explanation": "<what the implicit relationship is>"
}}"""


BUILTIN_RULES: list[EvaluationRule] = [
    EvaluationRule(
        name="mandate-prohibition-conflict",
        interference_type=InterferenceType.direct_contradiction,
        description=(
            "Detects when one block mandates an action that another block prohibits. "
            "The core contradiction pattern (e.g., 'always use X' vs 'never use X')."
        ),
        severity=Severity.critical,
        requires_scope_overlap=True,
        modality_a=Modality.mandate,
        modality_b=Modality.prohibition,
        requires_llm=True,
        prompt_template=_MANDATE_PROHIBITION_PROMPT,
    ),
    EvaluationRule(
        name="scope-overlap-redundancy",
        interference_type=InterferenceType.scope_overlap,
        description=(
            "Detects when two blocks regulate the same behavior with overlapping "
            "or redundant instructions, potentially creating ambiguity."
        ),
        severity=Severity.major,
        requires_scope_overlap=True,
        requires_llm=True,
        prompt_template=_SCOPE_OVERLAP_PROMPT,
    ),
    EvaluationRule(
        name="priority-marker-ambiguity",
        interference_type=InterferenceType.priority_ambiguity,
        description=(
            "Detects when multiple blocks use priority markers (IMPORTANT, CRITICAL, "
            "MUST, NEVER) on potentially conflicting instructions without declaring "
            "which takes precedence."
        ),
        severity=Severity.minor,
        requires_scope_overlap=False,
        requires_llm=False,
        prompt_template=None,
    ),
    EvaluationRule(
        name="implicit-dependency-unresolved",
        interference_type=InterferenceType.implicit_dependency,
        description=(
            "Detects when one block implicitly depends on or overrides another "
            "without declaring the relationship."
        ),
        severity=Severity.major,
        requires_scope_overlap=True,
        requires_llm=True,
        prompt_template=_IMPLICIT_DEPENDENCY_PROMPT,
    ),
    EvaluationRule(
        name="verbatim-duplication",
        interference_type=InterferenceType.scope_overlap,
        description=(
            "Detects when two blocks contain substantially identical text. "
            "Verbatim repetition may be intentional reinforcement or accidental, "
            "and raises questions about whether position affects priority."
        ),
        severity=Severity.minor,
        requires_scope_overlap=False,
        requires_llm=False,
        prompt_template=None,
    ),
]


def default_ruleset() -> RuleSet:
    """Return a RuleSet containing all built-in rules."""
    return RuleSet(name="arbiter-builtin", rules=list(BUILTIN_RULES))
