"""Integration tests — end-to-end pipeline against ground truth.

These tests verify the full flow from raw text or pre-decomposed JSON
through to an interference tensor, using the Claude Code v2.1.50 ground
truth as the reference.
"""

from pathlib import Path

import json
import pytest

from arbiter.heuristic_decomposer import heuristic_decompose
from arbiter.pipeline import PromptAnalyzer
from arbiter.prompt_blocks import PromptBlock, PromptCorpus
from arbiter.rules import default_ruleset


GROUND_TRUTH_JSON = Path(__file__).parent.parent / "data" / "prompts" / "claude-code" / "v2.1.50_blocks.json"
RAW_PROMPT = Path(__file__).parent.parent / "data" / "prompts" / "claude-code" / "v2.1.50_prompt.md"


@pytest.fixture
def ground_truth_blocks() -> list[PromptBlock]:
    """Load ground truth blocks from JSON."""
    with open(GROUND_TRUTH_JSON) as f:
        data = json.load(f)
    corpus = PromptCorpus(**data)
    return corpus.blocks


@pytest.fixture
def raw_prompt_text() -> str:
    """Load raw prompt text."""
    return RAW_PROMPT.read_text()


@pytest.fixture
def rule_set():
    return default_ruleset().compile()


class TestHeuristicDecomposerCoverage:
    """Verify heuristic decomposer produces reasonable output on real data."""

    def test_produces_minimum_blocks(self, raw_prompt_text):
        """Heuristic decomposer should produce at least 30 blocks.

        Ground truth has 56 hand-labeled blocks. The heuristic won't
        match exactly, but should produce a reasonable count. We set
        the bar at 30 to allow for different splitting strategies while
        still catching catastrophic failures.
        """
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        assert len(blocks) >= 30, f"Expected >= 30 blocks, got {len(blocks)}"

    def test_all_text_covered(self, raw_prompt_text):
        """Every non-whitespace line from the raw prompt appears in some block."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        block_texts = "\n".join(b.text for b in blocks)
        for line in raw_prompt_text.splitlines():
            stripped = line.strip()
            if stripped:
                assert stripped in block_texts, f"Line not covered: {stripped[:80]}"

    def test_blocks_have_valid_fields(self, raw_prompt_text):
        """All blocks have required fields with valid enum values."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        for block in blocks:
            assert block.id
            assert block.source == "claude-code/v2.1.50"
            assert block.text.strip()
            assert block.scope  # at least one scope keyword


class TestStructuralPipelineOnHeuristicBlocks:
    """Verify structural analysis works on heuristic-decomposed blocks."""

    def test_tensor_non_empty(self, raw_prompt_text, rule_set):
        """Structural analysis on heuristic blocks should find something.

        The Claude Code prompt has a known verbatim duplication (security
        policy repeated) that should be detectable even with rough block
        boundaries.
        """
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(blocks)
        assert len(result.tensor.entries) > 0, "Expected non-empty tensor"

    def test_verbatim_duplication_found(self, raw_prompt_text, rule_set):
        """The security policy duplication should be caught."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(blocks)
        dup_entries = [e for e in result.tensor.entries if e.rule == "verbatim-duplication"]
        assert len(dup_entries) > 0, "Expected verbatim duplication findings"

    def test_summary_report_generated(self, raw_prompt_text, rule_set):
        """Summary report should be non-empty."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(blocks)
        assert result.summary
        assert "interference" in result.summary.lower() or "detected" in result.summary.lower() or "tensor" in result.summary.lower()


class TestGroundTruthRoundTrip:
    """Verify structural analysis on ground truth blocks (regression test)."""

    def test_ground_truth_structural(self, ground_truth_blocks, rule_set):
        """Structural analysis on ground truth should produce a non-empty tensor."""
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(ground_truth_blocks)
        assert len(result.tensor.entries) > 0

    def test_ground_truth_has_56_blocks(self, ground_truth_blocks):
        """Ground truth should have exactly 56 blocks."""
        assert len(ground_truth_blocks) == 56

    def test_ground_truth_score_positive(self, ground_truth_blocks, rule_set):
        """Ground truth analysis should have positive interference score."""
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(ground_truth_blocks)
        assert result.score > 0.0

    def test_tensor_shape_consistent(self, ground_truth_blocks, rule_set):
        """Tensor dimensions should match inputs."""
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(ground_truth_blocks)
        shape = result.tensor.shape()
        assert shape[0] == 56  # blocks
        assert shape[1] == 56  # blocks
        assert shape[2] == len(rule_set.rules)  # rules
