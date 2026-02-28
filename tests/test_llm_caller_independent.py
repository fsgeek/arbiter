"""Independent tests for LLMCaller with mock client.

These tests were authored by a separate reviewer (not the implementation
author). They test the LLMCaller contract using a mock OpenAI client,
verifying: correct prompt passing, API error handling, concurrency
semaphore behavior, and parse error propagation.

Provenance: Independent test authorship, 2026-02-27.

Note: Uses asyncio.run() wrapper instead of pytest-asyncio to avoid
an extra dependency.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from arbiter.block_evaluator import BlockScore
from arbiter.decomposer import DecompositionError
from arbiter.llm_caller import LLMCaller
from arbiter.prompt_blocks import (
    BlockCategory,
    Modality,
    PromptBlock,
    Tier,
)
from arbiter.rules import default_ruleset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine synchronously. Wrapper for tests that
    avoids requiring pytest-asyncio."""
    return asyncio.run(coro)


def _make_mock_response(content: str):
    """Build a mock OpenAI chat completion response."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _make_block(
    block_id: str,
    text: str = "Some text.",
    tier: Tier = Tier.domain,
    category: BlockCategory = BlockCategory.behavioral_constraint,
    modality: Modality = Modality.definition,
    scope: list[str] | None = None,
) -> PromptBlock:
    """Build a PromptBlock for testing."""
    return PromptBlock(
        id=block_id,
        source="test",
        tier=tier,
        category=category,
        text=text,
        modality=modality,
        scope=scope or ["general"],
        exports=[],
        imports=[],
        line_start=1,
        line_end=1,
    )


def _valid_decomposition_response(source: str = "test") -> str:
    """Return a valid JSON decomposition response for testing."""
    return json.dumps([
        {
            "id": f"{source}/block-0",
            "tier": "system",
            "category": "identity",
            "text": "You are a helpful assistant.",
            "modality": "definition",
            "scope": ["identity"],
            "exports": ["is-assistant"],
            "imports": [],
            "line_start": 1,
            "line_end": 1,
        },
        {
            "id": f"{source}/block-1",
            "tier": "domain",
            "category": "behavioral-constraint",
            "text": "Be concise.",
            "modality": "mandate",
            "scope": ["communication"],
            "exports": ["conciseness"],
            "imports": [],
            "line_start": 3,
            "line_end": 3,
        },
    ])


def _make_conflicting_blocks() -> list[PromptBlock]:
    """Build a pair of blocks that will trigger LLM rules.

    Need: mandate + prohibition with scope overlap to trigger
    mandate-prohibition-conflict rule."""
    return [
        _make_block(
            "test:a",
            text="You MUST always use git commit.",
            modality=Modality.mandate,
            scope=["git"],
        ),
        _make_block(
            "test:b",
            text="NEVER use git commit directly.",
            modality=Modality.prohibition,
            scope=["git"],
        ),
    ]


@pytest.fixture
def rule_set():
    return default_ruleset().compile()


# ===================================================================
# 1. CONSTRUCTION AND BASIC CONTRACT
# ===================================================================


class TestConstruction:
    """Test LLMCaller construction and basic attributes."""

    def test_stores_client_and_model(self):
        client = MagicMock()
        caller = LLMCaller(client, "test-model")
        assert caller._client is client
        assert caller._model == "test-model"

    def test_default_max_concurrent(self):
        caller = LLMCaller(MagicMock(), "test-model")
        assert caller._max_concurrent == 5

    def test_custom_max_concurrent(self):
        caller = LLMCaller(MagicMock(), "test-model", max_concurrent=10)
        assert caller._max_concurrent == 10


# ===================================================================
# 2. _call_llm — the synchronous LLM call
# ===================================================================


class TestCallLLM:
    """Test the synchronous _call_llm method."""

    def test_calls_client_with_correct_params(self):
        """Verify the client is called with the right model, tokens, and messages."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response("Hello")

        caller = LLMCaller(client, "my-model")
        result = caller._call_llm("What is 2+2?")

        client.chat.completions.create.assert_called_once_with(
            model="my-model",
            max_tokens=4096,
            messages=[{"role": "user", "content": "What is 2+2?"}],
        )
        assert result == "Hello"

    def test_custom_max_tokens(self):
        """max_tokens parameter is forwarded to the API call."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response("OK")

        caller = LLMCaller(client, "model")
        caller._call_llm("prompt", max_tokens=8192)

        client.chat.completions.create.assert_called_once()
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == 8192

    def test_propagates_api_error(self):
        """If the client raises, the error should propagate."""
        client = MagicMock()
        client.chat.completions.create.side_effect = ConnectionError("Network down")

        caller = LLMCaller(client, "model")
        with pytest.raises(ConnectionError, match="Network down"):
            caller._call_llm("prompt")

    def test_returns_first_choice_content(self):
        """Response content comes from choices[0].message.content."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response("The answer is 4.")

        caller = LLMCaller(client, "model")
        assert caller._call_llm("What is 2+2?") == "The answer is 4."


# ===================================================================
# 3. decompose() — async LLM decomposition
# ===================================================================


class TestDecompose:
    """Test the async decompose method."""

    def test_decompose_returns_prompt_blocks(self, rule_set):
        """decompose() should return a list of PromptBlock instances."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            _valid_decomposition_response("my-source")
        )

        caller = LLMCaller(client, "model")
        blocks = _run(caller.decompose(
            "You are a helpful assistant.\n\nBe concise.", "my-source", rule_set
        ))

        assert len(blocks) == 2
        assert all(isinstance(b, PromptBlock) for b in blocks)
        assert blocks[0].source == "my-source"
        assert blocks[1].source == "my-source"

    def test_decompose_calls_llm_once(self, rule_set):
        """decompose() should make exactly one LLM call."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            _valid_decomposition_response()
        )

        caller = LLMCaller(client, "model")
        _run(caller.decompose("Hello.", "test", rule_set))

        assert client.chat.completions.create.call_count == 1

    def test_decompose_uses_8192_max_tokens(self, rule_set):
        """decompose() should request 8192 max tokens (more than default 4096)."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            _valid_decomposition_response()
        )

        caller = LLMCaller(client, "model")
        _run(caller.decompose("Hello.", "test", rule_set))

        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == 8192

    def test_decompose_propagates_parse_error(self, rule_set):
        """If the LLM returns garbage, DecompositionError should propagate."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            "This is not JSON at all, just random text."
        )

        caller = LLMCaller(client, "model")
        with pytest.raises(DecompositionError):
            _run(caller.decompose("Hello.", "test", rule_set))

    def test_decompose_propagates_api_error(self, rule_set):
        """If the API call fails, the error should propagate from decompose()."""
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("API timeout")

        caller = LLMCaller(client, "model")
        with pytest.raises(RuntimeError, match="API timeout"):
            _run(caller.decompose("Hello.", "test", rule_set))

    def test_decompose_prompt_contains_input_text(self, rule_set):
        """The prompt sent to the LLM should contain the input text."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            _valid_decomposition_response()
        )

        caller = LLMCaller(client, "model")
        _run(caller.decompose("UNIQUE_INPUT_TEXT_12345", "test", rule_set))

        call_args = client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages")
        prompt_text = messages[0]["content"]
        assert "UNIQUE_INPUT_TEXT_12345" in prompt_text

    def test_decompose_with_code_fence_wrapped_response(self, rule_set):
        """LLM response wrapped in ```json ... ``` should still parse."""
        wrapped = "```json\n" + _valid_decomposition_response() + "\n```"
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(wrapped)

        caller = LLMCaller(client, "model")
        blocks = _run(caller.decompose("Hello.", "test", rule_set))
        assert len(blocks) == 2


# ===================================================================
# 4. evaluate_llm_rules() — concurrent LLM evaluation
# ===================================================================


class TestEvaluateLLMRules:
    """Test the async evaluate_llm_rules method."""

    def test_returns_empty_when_no_pending(self, rule_set):
        """With no applicable LLM rules, should return empty list."""
        blocks = [
            _make_block("test:a", scope=["alpha"]),
            _make_block("test:b", scope=["beta"]),
        ]
        client = MagicMock()
        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))
        assert scores == []
        client.chat.completions.create.assert_not_called()

    def test_calls_llm_for_each_pending_evaluation(self, rule_set):
        """Each pending (block_a, block_b, rule) triple should get one LLM call."""
        blocks = _make_conflicting_blocks()

        from arbiter.block_evaluator import BlockEvaluator
        evaluator = BlockEvaluator(structural_only=False)
        pending = evaluator.pending_llm_evaluations(blocks, rule_set)
        expected_calls = len(pending)
        assert expected_calls > 0, "Test setup: should have pending evaluations"

        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"score": 0.8, "explanation": "Clear conflict."})
        )

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))

        assert client.chat.completions.create.call_count == expected_calls
        assert len(scores) == expected_calls

    def test_scores_are_block_score_instances(self, rule_set):
        """All returned scores should be BlockScore instances."""
        blocks = _make_conflicting_blocks()

        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"score": 0.7, "explanation": "Conflict detected."})
        )

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))

        for score in scores:
            assert isinstance(score, BlockScore)
            assert 0.0 <= score.score <= 1.0

    def test_api_error_does_not_crash(self, rule_set):
        """If one LLM call fails, the others should still complete.

        The contract says: 'Log but don't crash — partial results are better than none.'
        """
        blocks = _make_conflicting_blocks()

        call_count = 0

        def _side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("First call fails")
            return _make_mock_response(
                json.dumps({"score": 0.5, "explanation": "OK"})
            )

        client = MagicMock()
        client.chat.completions.create.side_effect = _side_effect

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))

        from arbiter.block_evaluator import BlockEvaluator
        evaluator = BlockEvaluator(structural_only=False)
        pending = evaluator.pending_llm_evaluations(blocks, rule_set)
        assert len(scores) == len(pending) - 1

    def test_unparseable_llm_response_returns_fallback_score(self, rule_set):
        """If the LLM returns non-JSON, the evaluator's parse_llm_score
        should return a fallback score of 0.5 (not crash)."""
        blocks = _make_conflicting_blocks()

        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            "I don't understand the question."
        )

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))

        for score in scores:
            assert score.score == 0.5
            assert score.explanation is not None
            assert "Unparseable" in score.explanation

    def test_semaphore_limits_concurrency(self, rule_set):
        """The semaphore should limit concurrent LLM calls to max_concurrent.

        We create blocks that trigger many evaluations, set max_concurrent=1,
        and verify that calls don't actually overlap.
        """
        blocks = [
            _make_block("a", text="ALWAYS use git.", modality=Modality.mandate, scope=["git", "tool-usage"]),
            _make_block("b", text="NEVER use git.", modality=Modality.prohibition, scope=["git", "tool-usage"]),
            _make_block("c", text="ALWAYS commit.", modality=Modality.mandate, scope=["git"]),
        ]

        from arbiter.block_evaluator import BlockEvaluator
        evaluator = BlockEvaluator(structural_only=False)
        pending = evaluator.pending_llm_evaluations(blocks, rule_set)

        if len(pending) < 2:
            pytest.skip("Need at least 2 pending evaluations to test concurrency")

        # Use a threading lock to detect concurrent access
        lock = threading.Lock()
        max_observed_concurrent = 0
        concurrent_count = 0

        def _tracking_create(**kwargs):
            nonlocal concurrent_count, max_observed_concurrent
            # The lock protects the counter update, but NOT the sleep
            with lock:
                concurrent_count += 1
                if concurrent_count > max_observed_concurrent:
                    max_observed_concurrent = concurrent_count
            time.sleep(0.02)
            with lock:
                concurrent_count -= 1
            return _make_mock_response(
                json.dumps({"score": 0.3, "explanation": "test"})
            )

        client = MagicMock()
        client.chat.completions.create.side_effect = _tracking_create

        caller = LLMCaller(client, "model", max_concurrent=1)
        _run(caller.evaluate_llm_rules(blocks, rule_set))

        assert max_observed_concurrent == 1, (
            f"Expected max 1 concurrent call, observed {max_observed_concurrent}"
        )

    def test_prompts_contain_block_text(self, rule_set):
        """The LLM prompts should contain the block texts being evaluated."""
        blocks = _make_conflicting_blocks()

        prompts_received = []

        def _capture_create(**kwargs):
            messages = kwargs.get("messages", [])
            if messages:
                prompts_received.append(messages[0]["content"])
            return _make_mock_response(
                json.dumps({"score": 0.5, "explanation": "test"})
            )

        client = MagicMock()
        client.chat.completions.create.side_effect = _capture_create

        caller = LLMCaller(client, "model")
        _run(caller.evaluate_llm_rules(blocks, rule_set))

        assert len(prompts_received) > 0
        for prompt in prompts_received:
            assert (
                "git commit" in prompt
            ), f"Block text not found in prompt: {prompt[:200]}"

    def test_model_name_passed_to_every_call(self, rule_set):
        """The model name should be used in every API call."""
        blocks = _make_conflicting_blocks()

        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"score": 0.5, "explanation": "test"})
        )

        caller = LLMCaller(client, "my-special-model")
        _run(caller.evaluate_llm_rules(blocks, rule_set))

        for c in client.chat.completions.create.call_args_list:
            model = c.kwargs.get("model")
            assert model == "my-special-model"


# ===================================================================
# 5. EDGE CASES AND ERROR CONDITIONS
# ===================================================================


class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_empty_blocks_list(self, rule_set):
        """evaluate_llm_rules with empty block list should return empty."""
        client = MagicMock()
        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules([], rule_set))
        assert scores == []
        client.chat.completions.create.assert_not_called()

    def test_single_block(self, rule_set):
        """A single block has no pairs, so no evaluations."""
        client = MagicMock()
        caller = LLMCaller(client, "model")
        blocks = [_make_block("test:a")]
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))
        assert scores == []
        client.chat.completions.create.assert_not_called()

    def test_decompose_with_empty_text(self, rule_set):
        """Decomposing empty text — the LLM should still get called,
        and the result depends on what the LLM returns."""
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response("[]")

        caller = LLMCaller(client, "model")
        blocks = _run(caller.decompose("", "test", rule_set))
        assert blocks == []

    def test_all_calls_fail_returns_empty(self, rule_set):
        """If every LLM call fails, should return empty list (not crash)."""
        blocks = [
            _make_block("a", text="ALWAYS use git.", modality=Modality.mandate, scope=["git"]),
            _make_block("b", text="NEVER use git.", modality=Modality.prohibition, scope=["git"]),
        ]

        client = MagicMock()
        client.chat.completions.create.side_effect = ConnectionError("All down")

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))
        assert scores == []

    def test_score_clamped_to_0_1_range(self, rule_set):
        """Scores outside [0,1] from LLM should be clamped."""
        blocks = [
            _make_block("a", text="ALWAYS use git.", modality=Modality.mandate, scope=["git"]),
            _make_block("b", text="NEVER use git.", modality=Modality.prohibition, scope=["git"]),
        ]

        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"score": 5.0, "explanation": "Very bad"})
        )

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))

        for score in scores:
            assert 0.0 <= score.score <= 1.0, f"Score {score.score} not in [0,1]"

    def test_negative_score_clamped(self, rule_set):
        """Negative scores from LLM should be clamped to 0."""
        blocks = [
            _make_block("a", text="ALWAYS use git.", modality=Modality.mandate, scope=["git"]),
            _make_block("b", text="NEVER use git.", modality=Modality.prohibition, scope=["git"]),
        ]

        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response(
            json.dumps({"score": -1.0, "explanation": "No conflict"})
        )

        caller = LLMCaller(client, "model")
        scores = _run(caller.evaluate_llm_rules(blocks, rule_set))

        for score in scores:
            assert score.score >= 0.0
