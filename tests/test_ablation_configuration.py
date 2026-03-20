"""Tests for ablation configuration — prompt assembly, phase builders, constraints.

Tests the contract specified in ablation_framework.md:
- AblationConfig.assemble_prompt() builds correct system prompts
- Constrained blocks are never removed
- Phase builders produce correct number of configs
- Phase 2 padding insertion works correctly
"""

import pytest

from arbiter.ablation.configuration import (
    AblationConfig,
    build_phase0_configs,
    build_phase1_configs,
    build_phase2_configs,
)
from arbiter.prompt_blocks import (
    BlockCategory,
    Modality,
    PromptBlock,
    PromptCorpus,
    Tier,
)


# --- Fixtures ---


def _make_block(block_id: str, text: str) -> PromptBlock:
    """Create a minimal PromptBlock for testing."""
    return PromptBlock(
        id=block_id,
        source="test/v1",
        tier=Tier.system,
        category=BlockCategory.behavioral_constraint,
        text=text,
        modality=Modality.mandate,
        scope=["test"],
    )


@pytest.fixture
def small_corpus():
    """A small corpus with 3 constrained + 4 free blocks."""
    blocks = [
        _make_block("constrained-1", "Identity block."),
        _make_block("constrained-2", "Safety block."),
        _make_block("constrained-3", "Tool definition block."),
        _make_block("free-1", "Be concise in all responses."),
        _make_block("free-2", "Never use emojis."),
        _make_block("free-3", "Always read before editing."),
        _make_block("free-4", "Use parallel tool calls when possible."),
    ]
    return PromptCorpus(
        name="test/v1",
        source_file="test.md",
        blocks=blocks,
    )


@pytest.fixture
def constrained_ids():
    return ["constrained-1", "constrained-2", "constrained-3"]


@pytest.fixture
def free_ids():
    return ["free-1", "free-2", "free-3", "free-4"]


# --- AblationConfig assembly tests ---


class TestAblationConfigAssembly:
    def test_baseline_includes_all_blocks(self, small_corpus, constrained_ids, free_ids):
        """Baseline config includes all blocks."""
        config = AblationConfig(
            id="baseline",
            phase="baseline",
            present_blocks=constrained_ids + free_ids,
            absent_blocks=[],
            padding=None,
        )
        prompt = config.assemble_prompt(small_corpus)
        for block in small_corpus.blocks:
            assert block.text in prompt

    def test_absent_blocks_excluded(self, small_corpus, constrained_ids, free_ids):
        """Absent blocks should not appear in the assembled prompt."""
        config = AblationConfig(
            id="test-remove-free1",
            phase="phase0",
            present_blocks=constrained_ids + ["free-2", "free-3", "free-4"],
            absent_blocks=["free-1"],
            padding=None,
        )
        prompt = config.assemble_prompt(small_corpus)
        assert "Be concise" not in prompt
        assert "Never use emojis" in prompt

    def test_constrained_blocks_always_present(self, small_corpus, constrained_ids):
        """AblationConfig validates block existence, not constrained/free semantics."""
        config = AblationConfig(
            id="bad-config",
            phase="phase0",
            present_blocks=["constrained-2", "constrained-3"],
            absent_blocks=["constrained-1"],
            padding=None,
        )
        prompt = config.assemble_prompt(small_corpus)
        assert "Identity block." not in prompt

    def test_block_order_preserved(self, small_corpus, constrained_ids, free_ids):
        """Blocks should appear in their original corpus order."""
        config = AblationConfig(
            id="baseline",
            phase="baseline",
            present_blocks=constrained_ids + free_ids,
            absent_blocks=[],
            padding=None,
        )
        prompt = config.assemble_prompt(small_corpus)
        # Check that constrained blocks come before free blocks (since that's
        # their order in the corpus)
        pos_constrained = prompt.index("Identity block")
        pos_free = prompt.index("Be concise")
        assert pos_constrained < pos_free

    def test_phase2_padding_inserted(self, small_corpus, constrained_ids):
        """Phase 2 configs replace removed blocks with padding text."""
        padding_text = "   " * 20  # whitespace padding
        config = AblationConfig(
            id="phase2-free1-whitespace",
            phase="phase2",
            present_blocks=constrained_ids + ["free-2", "free-3", "free-4"],
            absent_blocks=["free-1"],
            padding={"free-1": padding_text},
        )
        prompt = config.assemble_prompt(small_corpus)
        # Original text should be gone
        assert "Be concise" not in prompt
        # Padding should be present
        assert padding_text in prompt

    def test_assembled_prompt_is_string(self, small_corpus, constrained_ids, free_ids):
        """assemble_prompt returns a string."""
        config = AblationConfig(
            id="baseline",
            phase="baseline",
            present_blocks=constrained_ids + free_ids,
            absent_blocks=[],
            padding=None,
        )
        result = config.assemble_prompt(small_corpus)
        assert isinstance(result, str)

    def test_unknown_block_id_raises(self, small_corpus):
        config = AblationConfig(
            id="bad-id",
            phase="phase0",
            present_blocks=["missing-block"],
            absent_blocks=[],
            padding=None,
        )
        with pytest.raises(ValueError):
            config.assemble_prompt(small_corpus)


# --- Phase 0 builder tests ---


class TestPhase0Configs:
    def test_count_is_nfree_plus_baseline(self, small_corpus, free_ids, constrained_ids):
        """Phase 0: one config per free block removed + 1 baseline = N+1."""
        configs = build_phase0_configs(small_corpus, free_ids, constrained_ids)
        assert len(configs) == len(free_ids) + 1

    def test_baseline_config_present(self, small_corpus, free_ids, constrained_ids):
        """One config should be the baseline (all blocks present)."""
        configs = build_phase0_configs(small_corpus, free_ids, constrained_ids)
        baselines = [c for c in configs if c.phase == "baseline"]
        assert len(baselines) == 1
        assert baselines[0].absent_blocks == []

    def test_each_free_block_removed_once(self, small_corpus, free_ids, constrained_ids):
        """Each free block should be absent in exactly one non-baseline config."""
        configs = build_phase0_configs(small_corpus, free_ids, constrained_ids)
        non_baseline = [c for c in configs if c.phase != "baseline"]
        removed_blocks = []
        for config in non_baseline:
            assert len(config.absent_blocks) == 1
            removed_blocks.append(config.absent_blocks[0])
        assert sorted(removed_blocks) == sorted(free_ids)

    def test_constrained_blocks_never_absent(self, small_corpus, free_ids, constrained_ids):
        """No config should ever have a constrained block in absent_blocks."""
        configs = build_phase0_configs(small_corpus, free_ids, constrained_ids)
        for config in configs:
            for cid in constrained_ids:
                assert cid not in config.absent_blocks
                assert cid in config.present_blocks

    def test_phase_label_correct(self, small_corpus, free_ids, constrained_ids):
        """Non-baseline configs should have phase='phase0'."""
        configs = build_phase0_configs(small_corpus, free_ids, constrained_ids)
        for config in configs:
            assert config.phase in ("baseline", "phase0")


# --- Phase 1 builder tests ---


class TestPhase1Configs:
    def test_count_matches_covering_array(self, small_corpus, free_ids, constrained_ids):
        """Phase 1: one config per covering array row."""
        # A simple covering array for 4 factors
        covering_array = [
            [1, 1, 1, 1],
            [0, 0, 0, 0],
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [1, 1, 0, 0],
            [0, 0, 1, 1],
        ]
        configs = build_phase1_configs(
            small_corpus, free_ids, constrained_ids, covering_array
        )
        assert len(configs) == len(covering_array)

    def test_present_absent_match_array_row(self, small_corpus, free_ids, constrained_ids):
        """Each config's present/absent blocks must match its covering array row."""
        covering_array = [
            [1, 0, 1, 0],  # free-1 present, free-2 absent, free-3 present, free-4 absent
        ]
        configs = build_phase1_configs(
            small_corpus, free_ids, constrained_ids, covering_array
        )
        config = configs[0]
        assert "free-1" in config.present_blocks
        assert "free-2" in config.absent_blocks
        assert "free-3" in config.present_blocks
        assert "free-4" in config.absent_blocks

    def test_constrained_always_present_in_phase1(self, small_corpus, free_ids, constrained_ids):
        """Constrained blocks present in every Phase 1 config."""
        covering_array = [
            [0, 0, 0, 0],  # all free blocks absent
            [1, 1, 1, 1],  # all free blocks present
        ]
        configs = build_phase1_configs(
            small_corpus, free_ids, constrained_ids, covering_array
        )
        for config in configs:
            for cid in constrained_ids:
                assert cid in config.present_blocks

    def test_phase_label_is_phase1(self, small_corpus, free_ids, constrained_ids):
        """All Phase 1 configs should have phase='phase1'."""
        covering_array = [[1, 0, 1, 0]]
        configs = build_phase1_configs(
            small_corpus, free_ids, constrained_ids, covering_array
        )
        for config in configs:
            assert config.phase == "phase1"

    def test_covering_array_column_mismatch_raises(
        self, small_corpus, free_ids, constrained_ids
    ):
        with pytest.raises(ValueError):
            build_phase1_configs(
                small_corpus,
                free_ids,
                constrained_ids,
                covering_array=[[1, 0, 1]],  # 3 cols, should be 4
            )


# --- Phase 2 builder tests ---


class TestPhase2Configs:
    def test_count_is_2x_free(self, small_corpus, free_ids, constrained_ids):
        """Phase 2 returns 2 conditions per free block (whitespace + semantic)."""
        configs = build_phase2_configs(small_corpus, free_ids, constrained_ids)
        expected = len(free_ids) * 2
        assert len(configs) == expected

    def test_phase2_configs_have_padding(self, small_corpus, free_ids, constrained_ids):
        """Non-baseline Phase 2 configs should have padding dictionaries."""
        configs = build_phase2_configs(small_corpus, free_ids, constrained_ids)
        non_baseline = [c for c in configs if c.phase != "baseline"]
        for config in non_baseline:
            assert config.padding is not None
            assert len(config.padding) > 0

    def test_phase2_has_no_baseline_config(self, small_corpus, free_ids, constrained_ids):
        """Phase 2 builder does not include a baseline config."""
        configs = build_phase2_configs(small_corpus, free_ids, constrained_ids)
        baselines = [c for c in configs if c.phase == "baseline"]
        assert baselines == []

    def test_constrained_blocks_never_absent_phase2(
        self, small_corpus, free_ids, constrained_ids
    ):
        """Constrained blocks are never in absent_blocks for Phase 2."""
        configs = build_phase2_configs(small_corpus, free_ids, constrained_ids)
        for config in configs:
            for cid in constrained_ids:
                assert cid not in config.absent_blocks


# --- Config ID uniqueness ---


class TestConfigIds:
    def test_phase0_ids_unique(self, small_corpus, free_ids, constrained_ids):
        configs = build_phase0_configs(small_corpus, free_ids, constrained_ids)
        ids = [c.id for c in configs]
        assert len(ids) == len(set(ids)), "Phase 0 config IDs must be unique"

    def test_phase2_ids_unique(self, small_corpus, free_ids, constrained_ids):
        configs = build_phase2_configs(small_corpus, free_ids, constrained_ids)
        ids = [c.id for c in configs]
        assert len(ids) == len(set(ids)), "Phase 2 config IDs must be unique"
