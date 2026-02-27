"""Tests for evaluation rules — compilation, pre-filtering, and built-in rules."""

import json
from pathlib import Path

import pytest

from arbiter.prompt_blocks import (
    InterferenceType,
    Modality,
    PromptBlock,
    PromptCorpus,
    Severity,
    Tier,
)
from arbiter.rules import (
    BUILTIN_RULES,
    CompilationError,
    CompiledRuleSet,
    EvaluationRule,
    RuleSet,
    default_ruleset,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "prompts" / "claude-code"
BLOCKS_FILE = DATA_DIR / "v2.1.50_blocks.json"


# --- Fixtures ---


@pytest.fixture
def corpus():
    with open(BLOCKS_FILE) as f:
        data = json.load(f)
    return PromptCorpus(**data)


@pytest.fixture
def compiled():
    return default_ruleset().compile()


# --- Compilation tests ---


class TestRuleCompilation:
    def test_builtin_rules_compile(self):
        """Built-in rules should compile without errors."""
        rs = default_ruleset()
        compiled = rs.compile()
        assert len(compiled.rules) == len(BUILTIN_RULES)

    def test_duplicate_names_rejected(self):
        rs = RuleSet(
            name="bad",
            rules=[
                EvaluationRule(
                    name="dupe",
                    interference_type=InterferenceType.scope_overlap,
                    description="first",
                    severity=Severity.minor,
                    requires_llm=False,
                ),
                EvaluationRule(
                    name="dupe",
                    interference_type=InterferenceType.scope_overlap,
                    description="second",
                    severity=Severity.minor,
                    requires_llm=False,
                ),
            ],
        )
        with pytest.raises(CompilationError, match="Duplicate rule name"):
            rs.compile()

    def test_structural_rule_with_template_rejected(self):
        rs = RuleSet(
            name="bad",
            rules=[
                EvaluationRule(
                    name="confused",
                    interference_type=InterferenceType.scope_overlap,
                    description="structural but has template",
                    severity=Severity.minor,
                    requires_llm=False,
                    prompt_template="should not be here",
                ),
            ],
        )
        with pytest.raises(CompilationError, match="must not have a prompt_template"):
            rs.compile()

    def test_llm_rule_without_template_rejected(self):
        rs = RuleSet(
            name="bad",
            rules=[
                EvaluationRule(
                    name="incomplete",
                    interference_type=InterferenceType.direct_contradiction,
                    description="llm rule missing template",
                    severity=Severity.critical,
                    requires_llm=True,
                    prompt_template=None,
                ),
            ],
        )
        with pytest.raises(CompilationError, match="must have a prompt_template"):
            rs.compile()

    def test_multiple_errors_reported(self):
        """Compilation should report ALL errors, not just the first."""
        rs = RuleSet(
            name="bad",
            rules=[
                EvaluationRule(
                    name="a",
                    interference_type=InterferenceType.scope_overlap,
                    description="structural with template",
                    severity=Severity.minor,
                    requires_llm=False,
                    prompt_template="bad",
                ),
                EvaluationRule(
                    name="b",
                    interference_type=InterferenceType.direct_contradiction,
                    description="llm without template",
                    severity=Severity.critical,
                    requires_llm=True,
                    prompt_template=None,
                ),
            ],
        )
        with pytest.raises(CompilationError, match="2 error"):
            rs.compile()

    def test_empty_ruleset_compiles(self):
        rs = RuleSet(name="empty", rules=[])
        compiled = rs.compile()
        assert len(compiled.rules) == 0

    def test_compiled_separates_structural_and_llm(self, compiled):
        structural = compiled.structural_rules()
        llm = compiled.llm_rules()
        assert len(structural) + len(llm) == len(compiled.rules)
        for r in structural:
            assert not r.requires_llm
        for r in llm:
            assert r.requires_llm


# --- Pre-filter tests ---


class TestPreFiltering:
    def test_mandate_prohibition_filter(self):
        """mandate-prohibition-conflict requires scope overlap + specific modalities."""
        rule = next(r for r in BUILTIN_RULES if r.name == "mandate-prohibition-conflict")

        mandate_block = PromptBlock(
            id="test/mandate",
            source="test",
            tier=Tier.system,
            category="behavioral-constraint",
            text="Always do X.",
            modality=Modality.mandate,
            scope=["tool-usage"],
        )
        prohibition_block = PromptBlock(
            id="test/prohibition",
            source="test",
            tier=Tier.domain,
            category="behavioral-constraint",
            text="Never do X.",
            modality=Modality.prohibition,
            scope=["tool-usage"],
        )
        unrelated_block = PromptBlock(
            id="test/unrelated",
            source="test",
            tier=Tier.application,
            category="context",
            text="Context info.",
            modality=Modality.definition,
            scope=["identity"],
        )

        # Mandate + prohibition with scope overlap → applies
        assert rule.applies_to(mandate_block, prohibition_block)

        # Wrong modality order → does not apply (asymmetric)
        assert not rule.applies_to(prohibition_block, mandate_block)

        # No scope overlap → does not apply
        assert not rule.applies_to(mandate_block, unrelated_block)

    def test_verbatim_duplication_no_scope_required(self):
        """verbatim-duplication should apply to any pair (no filters)."""
        rule = next(r for r in BUILTIN_RULES if r.name == "verbatim-duplication")

        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system,
            category="policy", text="Same text", modality=Modality.prohibition,
            scope=["a"],
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain,
            category="context", text="Same text", modality=Modality.definition,
            scope=["b"],
        )
        assert rule.applies_to(block_a, block_b)

    def test_scope_overlap_filter(self):
        """scope-overlap-redundancy requires scope overlap but any modality."""
        rule = next(r for r in BUILTIN_RULES if r.name == "scope-overlap-redundancy")

        overlapping = PromptBlock(
            id="a", source="t", tier=Tier.system,
            category="policy", text="Do X", modality=Modality.mandate,
            scope=["tool-usage"],
        )
        also_overlapping = PromptBlock(
            id="b", source="t", tier=Tier.domain,
            category="policy", text="Also do X", modality=Modality.mandate,
            scope=["tool-usage", "output"],
        )
        no_overlap = PromptBlock(
            id="c", source="t", tier=Tier.system,
            category="identity", text="Identity", modality=Modality.definition,
            scope=["identity"],
        )

        assert rule.applies_to(overlapping, also_overlapping)
        assert not rule.applies_to(overlapping, no_overlap)

    def test_applicable_pairs_on_ground_truth(self, corpus, compiled):
        """Pre-filtering on the 56 ground truth blocks should heavily reduce
        LLM-evaluated triples. Structural rules are cheap, so being broad is fine."""
        triples = compiled.applicable_pairs(corpus.blocks)
        n = len(corpus.blocks)
        max_pairs = n * (n - 1) // 2

        # LLM rules (the expensive ones) should be heavily filtered
        llm_triples = [t for t in triples if t[2].requires_llm]
        llm_max = max_pairs * len(compiled.llm_rules())
        assert llm_triples, "Should have some LLM work to do"
        assert len(llm_triples) < llm_max * 0.3, (
            f"LLM pre-filtering insufficiently aggressive: {len(llm_triples)} triples "
            f"out of {llm_max} possible"
        )

        # Total should still be well below the theoretical maximum
        assert len(triples) > 0

    def test_applicable_pairs_includes_known_contradictions(self, corpus, compiled):
        """The known TodoWrite contradictions must survive pre-filtering."""
        triples = compiled.applicable_pairs(corpus.blocks)
        block_pairs_checked = {(t[0].id, t[1].id) for t in triples} | {
            (t[1].id, t[0].id) for t in triples
        }

        # The TodoWrite mandate vs commit prohibition is the canonical test case
        known_pairs = [
            ("claude-code/task-management-todowrite", "claude-code/tool-bash-commit-restrictions"),
            ("claude-code/todowrite-importance-repeated", "claude-code/tool-bash-commit-restrictions"),
        ]
        for a, b in known_pairs:
            assert (a, b) in block_pairs_checked or (b, a) in block_pairs_checked, (
                f"Known contradiction pair ({a}, {b}) was filtered out"
            )


# --- Built-in rule properties ---


class TestBuiltinRules:
    def test_five_builtin_rules(self):
        assert len(BUILTIN_RULES) == 5

    def test_unique_names(self):
        names = [r.name for r in BUILTIN_RULES]
        assert len(names) == len(set(names))

    def test_all_interference_types_covered(self):
        """Built-in rules should cover the main interference types."""
        types = {r.interference_type for r in BUILTIN_RULES}
        assert InterferenceType.direct_contradiction in types
        assert InterferenceType.scope_overlap in types
        assert InterferenceType.priority_ambiguity in types
        assert InterferenceType.implicit_dependency in types

    def test_has_both_structural_and_llm(self):
        structural = [r for r in BUILTIN_RULES if not r.requires_llm]
        llm = [r for r in BUILTIN_RULES if r.requires_llm]
        assert len(structural) >= 2
        assert len(llm) >= 2

    def test_llm_rules_have_placeholders(self):
        for rule in BUILTIN_RULES:
            if rule.requires_llm:
                assert "{block_a_text}" in rule.prompt_template
                assert "{block_b_text}" in rule.prompt_template

    def test_default_ruleset_factory(self):
        rs = default_ruleset()
        assert rs.name == "arbiter-builtin"
        assert len(rs.rules) == len(BUILTIN_RULES)
