"""Tests for the analysis pipeline — end-to-end with ground truth data.

All tests are unit tests (no API calls). LLM responses are mocked.
"""

import json
from pathlib import Path

import pytest

from arbiter.block_evaluator import BlockEvaluator, BlockScore
from arbiter.decomposer import Decomposer, DecompositionError
from arbiter.interference_tensor import InterferenceTensor
from arbiter.pipeline import AnalysisResult, PromptAnalyzer
from arbiter.prompt_blocks import (
    BlockCategory,
    InterferencePattern,
    Modality,
    PromptBlock,
    PromptCorpus,
    Severity,
    Tier,
)
from arbiter.rules import CompiledRuleSet, default_ruleset

DATA_DIR = Path(__file__).parent.parent / "data" / "prompts" / "claude-code"
BLOCKS_FILE = DATA_DIR / "v2.1.50_blocks.json"
INTERFERENCE_FILE = DATA_DIR / "v2.1.50_interference.json"


# --- Fixtures ---


@pytest.fixture
def corpus():
    with open(BLOCKS_FILE) as f:
        data = json.load(f)
    return PromptCorpus(**data)


@pytest.fixture
def interference():
    with open(INTERFERENCE_FILE) as f:
        data = json.load(f)
    return [InterferencePattern(**p) for p in data]


@pytest.fixture
def compiled():
    return default_ruleset().compile()


@pytest.fixture
def analyzer(compiled):
    return PromptAnalyzer(compiled)


# --- Decomposer tests (parse_response, no LLM) ---


class TestDecomposerParsing:
    def test_parse_valid_response(self, compiled):
        decomposer = Decomposer(compiled)
        raw = json.dumps([
            {
                "id": "test/identity",
                "tier": "system",
                "category": "identity",
                "text": "You are a test agent.",
                "modality": "definition",
                "scope": ["identity"],
                "exports": ["is-test"],
                "imports": [],
            },
            {
                "id": "test/policy",
                "tier": "domain",
                "category": "policy",
                "text": "Never do bad things.",
                "modality": "prohibition",
                "scope": ["content-policy"],
                "exports": ["no-bad-things"],
                "imports": [],
                "line_start": 5,
                "line_end": 5,
            },
        ])
        blocks = decomposer.parse_response(raw, "test/v1")
        assert len(blocks) == 2
        assert blocks[0].id == "test/identity"
        assert blocks[0].source == "test/v1"
        assert blocks[1].modality == Modality.prohibition

    def test_parse_markdown_wrapped(self, compiled):
        decomposer = Decomposer(compiled)
        raw = '```json\n[{"id":"a","tier":"system","category":"identity","text":"Hi","modality":"definition"}]\n```'
        blocks = decomposer.parse_response(raw, "test/v1")
        assert len(blocks) == 1

    def test_parse_invalid_json_raises(self, compiled):
        decomposer = Decomposer(compiled)
        with pytest.raises(DecompositionError, match="unparseable"):
            decomposer.parse_response("not json at all", "test/v1")

    def test_parse_non_array_raises(self, compiled):
        decomposer = Decomposer(compiled)
        with pytest.raises(DecompositionError, match="Expected JSON array"):
            decomposer.parse_response('{"not": "an array"}', "test/v1")

    def test_parse_invalid_block_raises(self, compiled):
        decomposer = Decomposer(compiled)
        raw = json.dumps([{"id": "a", "tier": "invalid-tier", "category": "identity",
                           "text": "Hi", "modality": "definition"}])
        with pytest.raises(DecompositionError, match="failed validation"):
            decomposer.parse_response(raw, "test/v1")

    def test_build_prompt_includes_rules(self, compiled):
        decomposer = Decomposer(compiled)
        prompt = decomposer.build_prompt("Test prompt text")
        assert "mandate-prohibition-conflict" in prompt
        assert "Test prompt text" in prompt


# --- Block evaluator tests (structural, no LLM) ---


class TestBlockEvaluatorStructural:
    def test_verbatim_duplication_detects_identical(self):
        evaluator = BlockEvaluator(structural_only=True)
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="IMPORTANT: Never do X. This is critical for safety.",
            modality=Modality.prohibition,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="IMPORTANT: Never do X. This is critical for safety.",
            modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "verbatim-duplication")
        result = evaluator.evaluate_pair_structural(block_a, block_b, rule)
        assert result is not None
        assert result.score == pytest.approx(1.0)

    def test_verbatim_duplication_low_for_different(self):
        evaluator = BlockEvaluator(structural_only=True)
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.identity,
            text="You are a helpful assistant.",
            modality=Modality.definition,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.workflow,
            text="When committing code, follow these steps carefully.",
            modality=Modality.mandate,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "verbatim-duplication")
        result = evaluator.evaluate_pair_structural(block_a, block_b, rule)
        assert result is not None
        assert result.score == 0.0

    def test_priority_markers_both_have_markers(self):
        evaluator = BlockEvaluator(structural_only=True)
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="IMPORTANT: You MUST always follow safety rules. NEVER skip this.",
            modality=Modality.mandate,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.workflow,
            text="CRITICAL: You MUST NEVER use this tool during commits.",
            modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "priority-marker-ambiguity")
        result = evaluator.evaluate_pair_structural(block_a, block_b, rule)
        assert result is not None
        assert result.score > 0.3  # Shared markers (MUST, NEVER)

    def test_priority_markers_none_in_one_block(self):
        evaluator = BlockEvaluator(structural_only=True)
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.identity,
            text="You are a helpful assistant.",
            modality=Modality.definition,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="IMPORTANT: Follow safety rules ALWAYS.",
            modality=Modality.mandate,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "priority-marker-ambiguity")
        result = evaluator.evaluate_pair_structural(block_a, block_b, rule)
        assert result is not None
        assert result.score == 0.0

    def test_structural_on_ground_truth_finds_security_dup(self, corpus, compiled):
        """Structural analysis on ground truth should find the security policy duplication."""
        evaluator = BlockEvaluator(structural_only=True)
        scores = evaluator.evaluate_all_structural(corpus.blocks, compiled)

        # Find security policy duplication
        sec_scores = [
            s for s in scores
            if s.rule == "verbatim-duplication"
            and "security" in s.block_a
            and "security" in s.block_b
        ]
        assert len(sec_scores) >= 1, "Should detect security policy verbatim duplication"
        assert sec_scores[0].score > 0.8


# --- LLM response parsing ---


class TestBlockEvaluatorLLMParsing:
    def test_parse_valid_llm_response(self):
        evaluator = BlockEvaluator()
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="Always use X.", modality=Modality.mandate,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.workflow,
            text="Never use X.", modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "mandate-prohibition-conflict")

        raw = '{"score": 0.95, "explanation": "Direct always/never contradiction"}'
        result = evaluator.parse_llm_score(raw, block_a, block_b, rule)
        assert result.score == pytest.approx(0.95)
        assert result.explanation == "Direct always/never contradiction"
        assert result.severity == Severity.critical

    def test_parse_markdown_wrapped_response(self):
        evaluator = BlockEvaluator()
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="A", modality=Modality.mandate,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="B", modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "mandate-prohibition-conflict")

        raw = '```json\n{"score": 0.8, "explanation": "test"}\n```'
        result = evaluator.parse_llm_score(raw, block_a, block_b, rule)
        assert result.score == pytest.approx(0.8)

    def test_parse_unparseable_returns_uncertain(self):
        evaluator = BlockEvaluator()
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="A", modality=Modality.mandate,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="B", modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "mandate-prohibition-conflict")

        result = evaluator.parse_llm_score("not json", block_a, block_b, rule)
        assert result.score == 0.5  # Uncertain
        assert "Unparseable" in result.explanation

    def test_build_llm_prompt(self):
        evaluator = BlockEvaluator()
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="Always do X.", modality=Modality.mandate,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="Never do X.", modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "mandate-prohibition-conflict")

        prompt = evaluator.build_llm_prompt(block_a, block_b, rule)
        assert "Always do X." in prompt
        assert "Never do X." in prompt
        assert "Block A" in prompt

    def test_build_llm_prompt_returns_none_for_structural(self):
        evaluator = BlockEvaluator()
        block_a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="A", modality=Modality.mandate,
        )
        block_b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="B", modality=Modality.prohibition,
        )
        from arbiter.rules import BUILTIN_RULES
        rule = next(r for r in BUILTIN_RULES if r.name == "verbatim-duplication")

        assert evaluator.build_llm_prompt(block_a, block_b, rule) is None


# --- Pipeline tests ---


class TestPipelineStructuralOnly:
    def test_structural_analysis_on_ground_truth(self, corpus, analyzer):
        """Structural-only pipeline on ground truth produces valid result."""
        result = analyzer.analyze_structural(corpus.blocks)

        assert isinstance(result, AnalysisResult)
        assert len(result.blocks) == len(corpus.blocks)
        assert result.score >= 0.0
        assert len(result.summary) > 0

    def test_structural_finds_known_patterns(self, corpus, analyzer):
        """Structural analysis should find at least some of the 21 ground truth patterns."""
        result = analyzer.analyze_structural(corpus.blocks)
        assert len(result.tensor.entries) > 0

    def test_structural_finds_security_dup(self, corpus, analyzer):
        """Must find the verbatim security policy duplication."""
        result = analyzer.analyze_structural(corpus.blocks)
        sec_entries = [
            e for e in result.tensor.entries
            if "security" in e.block_a and "security" in e.block_b
        ]
        assert len(sec_entries) >= 1

    def test_threshold_filtering(self, corpus, analyzer):
        """Threshold should filter out low-score entries."""
        result_all = analyzer.analyze_structural(corpus.blocks, threshold=0.0)
        result_high = analyzer.analyze_structural(corpus.blocks, threshold=0.5)
        assert len(result_high.tensor.entries) <= len(result_all.tensor.entries)


class TestPipelineWithMockLLM:
    def test_analyze_with_mock_llm_scores(self, corpus, compiled):
        """Full pipeline with mock LLM scores produces valid result."""
        analyzer = PromptAnalyzer(compiled)

        # Simulate LLM scores for the 4 critical TodoWrite contradictions
        mock_scores = [
            BlockScore(
                block_a="claude-code/task-management-todowrite",
                block_b="claude-code/tool-bash-commit-restrictions",
                rule="mandate-prohibition-conflict",
                score=0.95,
                severity=Severity.critical,
                explanation="'Use VERY frequently' vs 'NEVER use'",
            ),
            BlockScore(
                block_a="claude-code/todowrite-importance-repeated",
                block_b="claude-code/tool-bash-commit-restrictions",
                rule="mandate-prohibition-conflict",
                score=0.95,
                severity=Severity.critical,
                explanation="'Always use' vs 'NEVER use'",
            ),
        ]

        result = analyzer.analyze_with_scores(corpus.blocks, mock_scores)
        assert isinstance(result, AnalysisResult)
        assert result.score > 0.5  # Critical contradictions should dominate

        # TodoWrite should be in top findings
        top = result.tensor.top_n(5)
        todowrite_top = [
            e for e in top
            if "todowrite" in e.block_a.lower() or "todowrite" in e.block_b.lower()
        ]
        assert len(todowrite_top) >= 1

    def test_pending_llm_work_nonempty(self, corpus, analyzer):
        """Should have LLM work to do on ground truth blocks."""
        pending = analyzer.pending_llm_work(corpus.blocks)
        assert len(pending) > 0
        # Each tuple is (block_a, block_b, rule, prompt_str)
        for block_a, block_b, rule, prompt in pending[:3]:
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_tensor_has_correct_axes(self, corpus, compiled):
        """Tensor axes should match blocks and rules."""
        analyzer = PromptAnalyzer(compiled)
        result = analyzer.analyze_structural(corpus.blocks)

        n_blocks = len(corpus.blocks)
        n_rules = len(compiled.rules)
        assert result.tensor.shape() == (n_blocks, n_blocks, n_rules)


# --- PromptBlock.scopes_overlap tests ---


class TestScopesOverlap:
    def test_overlapping_scopes(self):
        a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.policy,
            text="A", modality=Modality.mandate, scope=["tool-usage", "output"],
        )
        b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.workflow,
            text="B", modality=Modality.prohibition, scope=["tool-usage", "security"],
        )
        assert a.scopes_overlap(b)
        assert b.scopes_overlap(a)

    def test_non_overlapping_scopes(self):
        a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.identity,
            text="A", modality=Modality.definition, scope=["identity"],
        )
        b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="B", modality=Modality.prohibition, scope=["security"],
        )
        assert not a.scopes_overlap(b)

    def test_empty_scopes(self):
        a = PromptBlock(
            id="a", source="t", tier=Tier.system, category=BlockCategory.identity,
            text="A", modality=Modality.definition, scope=[],
        )
        b = PromptBlock(
            id="b", source="t", tier=Tier.domain, category=BlockCategory.policy,
            text="B", modality=Modality.prohibition, scope=["security"],
        )
        assert not a.scopes_overlap(b)
