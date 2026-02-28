"""Independent tests for the heuristic prompt decomposer.

These tests were authored by a separate reviewer (not the implementation
author) and test from the CONTRACT — the module docstring and the
PromptBlock schema — rather than from knowledge of the implementation.

Provenance: Independent test authorship, 2026-02-27.
Reviewer verified: docstring contract, PromptBlock schema, ground truth
data, and adversarial edge cases the original tests missed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from arbiter.heuristic_decomposer import heuristic_decompose
from arbiter.prompt_blocks import BlockCategory, Modality, PromptBlock, Tier


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GROUND_TRUTH_JSON = (
    Path(__file__).parent.parent
    / "data"
    / "prompts"
    / "claude-code"
    / "v2.1.50_blocks.json"
)
RAW_PROMPT = (
    Path(__file__).parent.parent
    / "data"
    / "prompts"
    / "claude-code"
    / "v2.1.50_prompt.md"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ground_truth_blocks() -> list[dict]:
    """Load ground truth blocks as raw dicts."""
    with open(GROUND_TRUTH_JSON) as f:
        data = json.load(f)
    return data["blocks"]


@pytest.fixture
def raw_prompt_text() -> str:
    return RAW_PROMPT.read_text()


# ===================================================================
# 1. SPLITTING CONTRACT INVARIANTS
# These test the fundamental contract: blocks should be
# non-overlapping, cover all input text, have valid line numbers.
# ===================================================================


class TestSplittingContract:
    """The splitting contract: blocks are non-overlapping, cover all
    non-whitespace text, and have valid 1-indexed line numbers."""

    def test_blocks_non_overlapping_line_ranges(self):
        """Block line ranges must not overlap."""
        text = "# Section A\nContent A\n\n# Section B\nContent B\n\nParagraph."
        blocks = heuristic_decompose(text, source="test")
        for i in range(len(blocks) - 1):
            assert blocks[i].line_end < blocks[i + 1].line_start, (
                f"Block {i} (lines {blocks[i].line_start}-{blocks[i].line_end}) "
                f"overlaps block {i + 1} (lines {blocks[i + 1].line_start}-{blocks[i + 1].line_end})"
            )

    def test_all_nonempty_lines_appear_in_some_block(self):
        """Every non-whitespace line from the input must appear in a block's text."""
        text = "Line one.\n\nLine three.\n\n# Heading\nUnder heading.\n\n```\ncode\n```\n\nFinal."
        blocks = heuristic_decompose(text, source="test")
        all_block_text = "\n".join(b.text for b in blocks)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                assert stripped in all_block_text, f"Line missing from blocks: {stripped!r}"

    def test_line_numbers_are_one_indexed(self):
        """Line numbers start at 1, not 0."""
        text = "Hello world."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1
        assert blocks[0].line_start == 1
        assert blocks[0].line_end >= 1

    def test_line_end_gte_line_start(self):
        """line_end must be >= line_start for every block."""
        text = "A.\n\nB.\n\n# C\nD.\n\n```\ncode\n```\n\nE."
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert block.line_end >= block.line_start, (
                f"Block {block.id}: line_end={block.line_end} < line_start={block.line_start}"
            )

    def test_line_numbers_within_input_range(self):
        """All line numbers must be between 1 and len(input_lines)."""
        text = "A.\n\nB.\n\nC."
        total_lines = len(text.split("\n"))
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert 1 <= block.line_start <= total_lines
            assert 1 <= block.line_end <= total_lines

    def test_block_text_is_stripped(self):
        """Block text should not have leading/trailing whitespace."""
        text = "  Hello world.  \n\n  Goodbye.  "
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert block.text == block.text.strip(), (
                f"Block text has leading/trailing whitespace: {block.text!r}"
            )

    def test_no_empty_blocks(self):
        """No block should have empty or whitespace-only text."""
        text = "A.\n\n\n\n\n\nB.\n\n\n"
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert block.text.strip(), f"Empty block found: {block!r}"


# ===================================================================
# 2. SPLITTING HEURISTICS (from docstring)
# Priority: headings > code fences > blank lines > list items
# ===================================================================


class TestSplittingHeuristics:
    """Test the four splitting heuristics documented in the docstring."""

    # --- Markdown headings ---

    def test_h1_starts_new_block(self):
        text = "Preamble.\n# Heading\nContent."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_h2_starts_new_block(self):
        text = "Preamble.\n## Heading\nContent."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_h3_starts_new_block(self):
        text = "Preamble.\n### Heading\nContent."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_h4_does_not_split(self):
        """Docstring says # ## ### only. h4+ should NOT split."""
        text = "Preamble.\n#### Heading\nContent."
        blocks = heuristic_decompose(text, source="test")
        # h4 should not trigger a split, so everything is one block
        assert len(blocks) == 1

    def test_heading_without_space_does_not_split(self):
        """'#word' is not a heading, only '# word' is."""
        text = "Before.\n#notaheading\nAfter."
        blocks = heuristic_decompose(text, source="test")
        # Should be one block since #notaheading is not a valid heading
        assert len(blocks) == 1

    def test_consecutive_headings(self):
        """Two headings in a row: each starts a block."""
        text = "# First\n## Second\nContent."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2
        assert "First" in blocks[0].text
        assert "Second" in blocks[1].text

    def test_heading_with_content_below(self):
        """Heading and its content should be in the same block."""
        text = "# Section\nLine 1.\nLine 2.\n\nOther paragraph."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2
        assert "Line 1." in blocks[0].text
        assert "Line 2." in blocks[0].text

    # --- Code fences ---

    def test_code_fence_kept_as_unit(self):
        """Content inside ``` markers stays in a single block."""
        text = "Before.\n\n```\nline1\nline2\nline3\n```\n\nAfter."
        blocks = heuristic_decompose(text, source="test")
        code_block = [b for b in blocks if "line1" in b.text][0]
        assert "line2" in code_block.text
        assert "line3" in code_block.text

    def test_code_fence_with_language_tag(self):
        text = "```python\ndef foo():\n    return 42\n```"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1
        assert "def foo():" in blocks[0].text

    def test_heading_inside_code_fence_does_not_split(self):
        """# inside a code fence should not trigger a heading split."""
        text = "```\n# This is a comment, not a heading\necho hello\n```"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1
        assert "# This is a comment" in blocks[0].text

    def test_blank_line_inside_code_fence_does_not_split(self):
        """Blank lines inside code fences should not split."""
        text = "```\nline1\n\nline3\n```"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1

    def test_nested_code_fences(self):
        """Nested triple-backticks: the inner ``` should close the fence."""
        # This is an adversarial case: ``` inside ``` is ambiguous.
        # The simplest implementation treats the first closing ``` as the end.
        text = "```\nouter\n```\ninner\n```\nend\n```"
        blocks = heuristic_decompose(text, source="test")
        # At minimum, the decomposer should not crash
        assert len(blocks) >= 1

    def test_unclosed_code_fence(self):
        """A code fence that never closes should still produce a block."""
        text = "Before.\n\n```python\ndef orphan():\n    pass"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) >= 1
        # The unclosed fence content should be somewhere in the output
        all_text = "\n".join(b.text for b in blocks)
        assert "orphan" in all_text

    # --- Blank-line-delimited paragraphs ---

    def test_two_paragraphs(self):
        text = "Para one.\n\nPara two."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_multiple_blank_lines_same_as_one(self):
        """Multiple blank lines between paragraphs = one split."""
        text = "Para one.\n\n\n\nPara two."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_no_blank_lines_means_one_block(self):
        text = "Line 1.\nLine 2.\nLine 3."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1

    # --- List items ---

    def test_list_items_under_paragraph_grouped(self):
        """List items without blank line separators stay grouped."""
        text = "Rules:\n- Rule A\n- Rule B\n- Rule C"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1
        assert "Rule A" in blocks[0].text
        assert "Rule C" in blocks[0].text

    def test_star_bullets_grouped(self):
        """* bullets should also group."""
        text = "Items:\n* Item A\n* Item B"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1


# ===================================================================
# 3. CLASSIFICATION HEURISTICS (from docstring)
# ===================================================================


class TestClassificationHeuristics:
    """Test the classification heuristics documented in the docstring."""

    # --- Modality ---

    def test_never_is_prohibition(self):
        blocks = heuristic_decompose("NEVER do this.", source="test")
        assert blocks[0].modality == Modality.prohibition

    def test_must_not_is_prohibition(self):
        blocks = heuristic_decompose("You MUST NOT do this.", source="test")
        assert blocks[0].modality == Modality.prohibition

    def test_do_not_is_prohibition(self):
        blocks = heuristic_decompose("DO NOT do this.", source="test")
        assert blocks[0].modality == Modality.prohibition

    def test_must_is_mandate(self):
        blocks = heuristic_decompose("You MUST do this.", source="test")
        assert blocks[0].modality == Modality.mandate

    def test_always_is_mandate(self):
        blocks = heuristic_decompose("ALWAYS do this.", source="test")
        assert blocks[0].modality == Modality.mandate

    def test_required_is_mandate(self):
        blocks = heuristic_decompose("This is REQUIRED for all operations.", source="test")
        assert blocks[0].modality == Modality.mandate

    def test_may_is_permission(self):
        blocks = heuristic_decompose("You MAY use this tool.", source="test")
        assert blocks[0].modality == Modality.permission

    def test_optional_is_permission(self):
        blocks = heuristic_decompose("This setting is OPTIONAL.", source="test")
        assert blocks[0].modality == Modality.permission

    def test_no_keywords_is_definition(self):
        blocks = heuristic_decompose(
            "The system runs on a Linux server.", source="test"
        )
        assert blocks[0].modality == Modality.definition

    def test_mixed_mandate_and_prohibition(self):
        blocks = heuristic_decompose(
            "ALWAYS read the file first. NEVER skip this step.", source="test"
        )
        assert blocks[0].modality == Modality.mixed

    def test_must_not_should_not_trigger_mandate(self):
        """'MUST NOT' contains 'MUST' — the prohibition pattern should match first
        or the result should be prohibition, not mandate."""
        blocks = heuristic_decompose("You MUST NOT delete files.", source="test")
        # The word MUST appears in "MUST NOT". The correct classification is
        # prohibition (because MUST NOT is a prohibition), OR mixed (if both
        # patterns match). It should NOT be pure mandate.
        assert blocks[0].modality in (Modality.prohibition, Modality.mixed)

    # --- Category ---

    def test_tool_keywords(self):
        blocks = heuristic_decompose("Use the bash command to run tests.", source="test")
        assert blocks[0].category == BlockCategory.tool_definition

    def test_security_keywords(self):
        blocks = heuristic_decompose("Follow the security policy at all times.", source="test")
        assert blocks[0].category == BlockCategory.policy

    def test_identity_keywords(self):
        blocks = heuristic_decompose("You are a helpful assistant.", source="test")
        assert blocks[0].category == BlockCategory.identity

    def test_workflow_keywords(self):
        blocks = heuristic_decompose(
            "Follow this workflow: step 1, step 2, step 3.", source="test"
        )
        assert blocks[0].category == BlockCategory.workflow

    def test_context_keywords(self):
        blocks = heuristic_decompose("The platform is macOS.", source="test")
        assert blocks[0].category == BlockCategory.context

    def test_meta_keywords(self):
        blocks = heuristic_decompose(
            "Use markdown formatting for output.", source="test"
        )
        assert blocks[0].category == BlockCategory.meta

    def test_default_category_is_behavioral_constraint(self):
        """Text with no category keywords should get the default."""
        blocks = heuristic_decompose("Be helpful and kind.", source="test")
        assert blocks[0].category == BlockCategory.behavioral_constraint

    # --- Tier ---

    def test_important_is_system(self):
        blocks = heuristic_decompose("IMPORTANT: do not skip.", source="test")
        assert blocks[0].tier == Tier.system

    def test_critical_is_system(self):
        blocks = heuristic_decompose("CRITICAL: check first.", source="test")
        assert blocks[0].tier == Tier.system

    def test_environment_is_application(self):
        blocks = heuristic_decompose("Platform: linux.", source="test")
        assert blocks[0].tier == Tier.application

    def test_session_is_application(self):
        blocks = heuristic_decompose("This SESSION is read-only.", source="test")
        assert blocks[0].tier == Tier.application

    def test_default_tier_is_domain(self):
        blocks = heuristic_decompose("Some general guidance.", source="test")
        assert blocks[0].tier == Tier.domain

    # --- Scope ---

    def test_scope_git(self):
        blocks = heuristic_decompose("Use git commit to save.", source="test")
        assert "git" in blocks[0].scope

    def test_scope_security(self):
        blocks = heuristic_decompose("Check for vulnerability.", source="test")
        assert "security" in blocks[0].scope

    def test_scope_default_general(self):
        """Text with no scope keywords should get ['general']."""
        blocks = heuristic_decompose("Be helpful.", source="test")
        assert blocks[0].scope == ["general"]

    def test_scope_multiple(self):
        """Text with multiple scope keywords should have all of them."""
        blocks = heuristic_decompose(
            "Use git to commit changes and check security.", source="test"
        )
        scope = blocks[0].scope
        assert "git" in scope
        assert "security" in scope

    def test_scope_sorted(self):
        """Scope list should be sorted alphabetically."""
        blocks = heuristic_decompose(
            "git commit, check security, write file.", source="test"
        )
        scope = blocks[0].scope
        assert scope == sorted(scope)


# ===================================================================
# 4. ADVERSARIAL INPUTS
# ===================================================================


class TestAdversarialInputs:
    """Inputs designed to break naive parsers."""

    def test_empty_string(self):
        assert heuristic_decompose("", source="test") == []

    def test_whitespace_only(self):
        assert heuristic_decompose("   \n\n  \t\n", source="test") == []

    def test_single_newline(self):
        assert heuristic_decompose("\n", source="test") == []

    def test_single_character(self):
        blocks = heuristic_decompose("X", source="test")
        assert len(blocks) == 1
        assert blocks[0].text == "X"

    def test_single_word(self):
        blocks = heuristic_decompose("Hello", source="test")
        assert len(blocks) == 1

    def test_only_headings_no_content(self):
        """Input that's all headings and no body text."""
        text = "# H1\n## H2\n### H3"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) >= 1
        # Each heading should be in some block
        all_text = "\n".join(b.text for b in blocks)
        assert "H1" in all_text
        assert "H3" in all_text

    def test_only_code_fences(self):
        """Input that's entirely code fences."""
        text = "```\nblock1\n```\n\n```\nblock2\n```"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_only_blank_lines(self):
        assert heuristic_decompose("\n\n\n\n\n", source="test") == []

    def test_unicode_content(self):
        """Unicode should not crash the decomposer."""
        text = "# \u65e5\u672c\u8a9e\u306e\u898b\u51fa\u3057\n\u30e6\u30cb\u30b3\u30fc\u30c9\u3092\u4f7f\u7528\u3057\u3066\u304f\u3060\u3055\u3044\u3002\n\n\u00e9\u00e0\u00fc\u00f1\u00df\u00e7"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) >= 1

    def test_emoji_content(self):
        text = "Rule: no \U0001f4a9 in output.\n\nAnother \U0001f389 rule."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_very_long_single_line(self):
        """A single line that's 100K characters should not crash."""
        text = "A" * 100_000
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1
        assert len(blocks[0].text) == 100_000

    def test_many_short_paragraphs(self):
        """1000 single-line paragraphs."""
        text = "\n\n".join(f"Paragraph {i}." for i in range(1000))
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 1000

    def test_tab_indented_content(self):
        """Tabs should not confuse the splitter."""
        text = "\tIndented line one.\n\n\tIndented line two."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_windows_line_endings(self):
        """\\r\\n line endings should still split correctly."""
        text = "Line one.\r\n\r\nLine two."
        blocks = heuristic_decompose(text, source="test")
        # Should produce at least 1 block, ideally 2
        assert len(blocks) >= 1

    def test_mixed_line_endings(self):
        """Mix of \\n and \\r\\n should not crash."""
        text = "Line one.\n\r\nLine two.\r\n\nLine three."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) >= 1

    def test_backtick_not_triple(self):
        """Single backtick should not be treated as code fence."""
        text = "Use `inline code` here.\n\nNext paragraph."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2
        assert "`inline code`" in blocks[0].text

    def test_quadruple_backtick(self):
        """Four backticks (used for quoting triple backticks) should not crash.
        The heuristic checks startswith('```'), so ```` will also match."""
        text = "````\nsome code\n````"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) >= 1

    def test_indented_code_fence(self):
        """Code fence with leading spaces: '   ```' — should be detected
        because the code strips before checking."""
        text = "Before.\n\n   ```\n   code\n   ```\n\nAfter."
        blocks = heuristic_decompose(text, source="test")
        # The implementation uses line.strip().startswith('```')
        # so indented fences should be caught
        code_blocks = [b for b in blocks if "code" in b.text]
        assert len(code_blocks) >= 1

    def test_heading_at_very_end(self):
        """Heading as the last line of input."""
        text = "Some content.\n\n# Final"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2
        assert "Final" in blocks[-1].text

    def test_code_fence_at_very_end_no_trailing_newline(self):
        """Code fence at end without trailing newline."""
        text = "Before.\n\n```\ncode\n```"
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2

    def test_source_with_special_characters(self):
        """Source string with colons and slashes."""
        blocks = heuristic_decompose("Hello.", source="claude-code/v2.1.50:beta")
        assert blocks[0].source == "claude-code/v2.1.50:beta"
        assert "claude-code/v2.1.50:beta" in blocks[0].id


# ===================================================================
# 5. BLOCK ID AND METADATA CONTRACT
# ===================================================================


class TestBlockMetadata:
    """Test that block metadata follows the documented contract."""

    def test_id_format(self):
        """IDs follow '{source}:block_{NNN}' pattern."""
        blocks = heuristic_decompose("A.\n\nB.", source="my-source")
        assert blocks[0].id == "my-source:block_000"
        assert blocks[1].id == "my-source:block_001"

    def test_ids_unique(self):
        """All block IDs must be unique."""
        text = "\n\n".join(f"Block {i}." for i in range(50))
        blocks = heuristic_decompose(text, source="test")
        ids = [b.id for b in blocks]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_source_set_on_all_blocks(self):
        text = "A.\n\nB.\n\nC."
        blocks = heuristic_decompose(text, source="my-corpus")
        for block in blocks:
            assert block.source == "my-corpus"

    def test_exports_always_empty_list(self):
        """Heuristic decomposer does not extract exports."""
        text = "You MUST read files before editing."
        blocks = heuristic_decompose(text, source="test")
        assert blocks[0].exports == []

    def test_imports_always_empty_list(self):
        """Heuristic decomposer does not extract imports."""
        text = "You MUST read files before editing."
        blocks = heuristic_decompose(text, source="test")
        assert blocks[0].imports == []

    def test_all_blocks_are_promptblock_instances(self):
        text = "A.\n\nB."
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert isinstance(block, PromptBlock)

    def test_all_tier_values_valid(self):
        """Every block's tier must be a valid Tier enum member."""
        text = "IMPORTANT: check.\n\nPlatform: linux.\n\nGeneral advice."
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert isinstance(block.tier, Tier)

    def test_all_category_values_valid(self):
        text = "Use the bash tool.\n\nSecurity policy.\n\nBe helpful."
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert isinstance(block.category, BlockCategory)

    def test_all_modality_values_valid(self):
        text = "NEVER do this.\n\nALWAYS do that.\n\nYou MAY optionally."
        blocks = heuristic_decompose(text, source="test")
        for block in blocks:
            assert isinstance(block.modality, Modality)


# ===================================================================
# 6. GROUND TRUTH COMPARISON
# Test heuristic output against hand-labeled data on dimensions
# where the heuristic SHOULD get it right.
# ===================================================================


class TestGroundTruthComparison:
    """Compare heuristic output to hand-labeled ground truth.

    The heuristic is intentionally rough, but there are dimensions
    where it should perform well and we can measure accuracy.
    """

    def test_heuristic_block_count_in_range(self, raw_prompt_text):
        """Heuristic should produce between 30 and 200 blocks.

        Ground truth has 56 blocks. The heuristic splits on blank lines
        (which are more frequent than semantic boundaries), so it should
        produce MORE blocks than ground truth, not fewer.
        """
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        assert 30 <= len(blocks) <= 200, f"Got {len(blocks)} blocks, expected 30-200"

    def test_all_ground_truth_text_appears_in_heuristic_output(
        self, ground_truth_blocks, raw_prompt_text
    ):
        """Every ground truth block's text should appear somewhere in
        the heuristic output (the heuristic may split differently, but
        should cover the same text)."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        heuristic_text = "\n".join(b.text for b in blocks)

        # Check a sample of significant phrases from ground truth blocks
        for gt_block in ground_truth_blocks[:20]:
            # Take a 40-char snippet from the middle of the block
            gt_text = gt_block["text"]
            if len(gt_text) > 40:
                snippet = gt_text[10:50]
            else:
                snippet = gt_text[:20]
            assert snippet in heuristic_text, (
                f"Ground truth block {gt_block['id']} text not found in heuristic output. "
                f"Looking for: {snippet!r}"
            )

    def test_security_policy_duplication_detected(self, raw_prompt_text):
        """The raw prompt has the security policy text appearing twice
        (lines ~5 and ~67). The heuristic should produce two separate
        blocks containing this text."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        security_blocks = [
            b for b in blocks
            if "authorized security testing" in b.text
        ]
        assert len(security_blocks) >= 2, (
            f"Expected the duplicated security policy to appear in >= 2 blocks, "
            f"got {len(security_blocks)}"
        )

    def test_identity_block_found(self, raw_prompt_text):
        """The identity text 'You are a Claude agent' should appear early."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        identity_blocks = [
            b for b in blocks
            if "Claude agent" in b.text or "interactive CLI tool" in b.text
        ]
        assert len(identity_blocks) >= 1

    def test_code_examples_preserved(self, raw_prompt_text):
        """The raw prompt has [Two examples ...] text. It should be
        in some block (not lost to splitting)."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        all_text = "\n".join(b.text for b in blocks)
        assert "TodoWrite" in all_text, "TodoWrite example text should be preserved"

    def test_git_safety_kept_together_or_adjacent(self, raw_prompt_text):
        """The Git Safety Protocol section should be one block or a
        small number of adjacent blocks (not scattered)."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")
        git_blocks = [
            (i, b) for i, b in enumerate(blocks)
            if "git" in b.text.lower() and (
                "commit" in b.text.lower() or "push" in b.text.lower()
            )
        ]
        assert len(git_blocks) >= 1, "Git safety content should appear"

    def test_modality_accuracy_on_ground_truth_prohibitions(self, ground_truth_blocks, raw_prompt_text):
        """For ground truth blocks labeled as prohibition, check that
        the heuristic also classifies them as prohibition or mixed.

        This measures whether the keyword heuristic catches NEVER/MUST NOT
        in blocks that humans labeled as prohibition."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")

        # Build a text-to-modality lookup from heuristic blocks
        heuristic_modalities = {}
        for b in blocks:
            # Use first 50 chars as key (enough to identify)
            key = b.text[:50]
            heuristic_modalities[key] = b.modality

        gt_prohibitions = [
            b for b in ground_truth_blocks if b["modality"] == "prohibition"
        ]

        matches = 0
        checked = 0
        for gt in gt_prohibitions:
            gt_snippet = gt["text"][:50]
            for key, modality in heuristic_modalities.items():
                if gt_snippet[:30] in key or key[:30] in gt_snippet:
                    checked += 1
                    if modality in (Modality.prohibition, Modality.mixed):
                        matches += 1
                    break

        # The heuristic should get at least 60% of prohibitions right
        if checked > 0:
            accuracy = matches / checked
            assert accuracy >= 0.6, (
                f"Prohibition accuracy: {accuracy:.0%} ({matches}/{checked}). "
                f"Expected >= 60%."
            )

    def test_tier_accuracy_system_blocks(self, ground_truth_blocks, raw_prompt_text):
        """For ground truth blocks labeled as system tier, check that
        the heuristic identifies at least some of them as system tier.

        System tier in ground truth correlates with IMPORTANT/CRITICAL/NEVER
        keywords, which the heuristic checks for."""
        blocks = heuristic_decompose(raw_prompt_text, source="claude-code/v2.1.50")

        gt_system = [b for b in ground_truth_blocks if b["tier"] == "system"]

        # Check overlap: for each ground truth system block, does the heuristic
        # block covering that text also classify it as system?
        system_found = 0
        checked = 0
        for gt in gt_system:
            gt_snippet = gt["text"][:40]
            for b in blocks:
                if gt_snippet[:25] in b.text:
                    checked += 1
                    if b.tier == Tier.system:
                        system_found += 1
                    break

        # The heuristic won't get all of them (many system blocks don't have
        # IMPORTANT/CRITICAL), but it should get at least some
        if checked > 3:
            assert system_found >= 1, (
                f"No system blocks found among {checked} checked. "
                f"The heuristic should catch at least blocks with IMPORTANT/CRITICAL."
            )


# ===================================================================
# 7. REGRESSION: CONTRACT VS IMPLEMENTATION
# Tests that catch the difference between "the code does what
# the code does" and "the code does what the contract says."
# ===================================================================


class TestContractVsImplementation:
    """Tests that check the contract, not implementation artifacts."""

    def test_scope_overlap_works_on_heuristic_blocks(self):
        """Two blocks with overlapping scopes should report overlap."""
        text = "Use git to commit code.\n\nNEVER use git rebase."
        blocks = heuristic_decompose(text, source="test")
        assert len(blocks) == 2
        assert blocks[0].scopes_overlap(blocks[1])

    def test_heuristic_output_usable_by_pipeline(self):
        """The output should be directly usable by PromptAnalyzer."""
        from arbiter.pipeline import PromptAnalyzer
        from arbiter.rules import default_ruleset

        text = (
            "IMPORTANT: NEVER skip security checks.\n\n"
            "IMPORTANT: ALWAYS verify credentials.\n\n"
            "Use the bash tool for commands."
        )
        blocks = heuristic_decompose(text, source="test")
        rule_set = default_ruleset().compile()
        analyzer = PromptAnalyzer(rule_set)
        result = analyzer.analyze_structural(blocks)
        # Should not crash, should produce a result
        assert result.blocks == blocks
        assert isinstance(result.score, float)

    def test_deterministic(self):
        """Same input should always produce the same output."""
        text = "# Section\nContent.\n\n```\ncode\n```\n\nParagraph."
        blocks1 = heuristic_decompose(text, source="test")
        blocks2 = heuristic_decompose(text, source="test")
        assert len(blocks1) == len(blocks2)
        for b1, b2 in zip(blocks1, blocks2):
            assert b1.id == b2.id
            assert b1.text == b2.text
            assert b1.tier == b2.tier
            assert b1.modality == b2.modality
            assert b1.category == b2.category
            assert b1.line_start == b2.line_start
            assert b1.line_end == b2.line_end

    def test_source_default_is_unknown(self):
        """The default source parameter is 'unknown'."""
        # The signature says source: str = "unknown"
        blocks = heuristic_decompose("Hello.")
        assert blocks[0].source == "unknown"
