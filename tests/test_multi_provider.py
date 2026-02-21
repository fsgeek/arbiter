"""Cross-provider conflict detection — testing the model-tier hypothesis.

The question: is semantic conflict detection a capability boundary that varies
by model, or something any decent model can do? Testing only within one
vendor's lineup (Haiku → Sonnet → Opus) answers "should you pay Anthropic
more?" not "can models detect semantic conflicts?"

This test runs the same conflict cases against multiple providers and models,
collecting pass/fail and response quality data.

Run:
    pytest tests/test_multi_provider.py -v -s

Requires at least one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY
"""

import os

import pytest

from arbiter.evaluator import AnthropicEvaluator, OpenAICompatibleEvaluator
from arbiter.models import DomainLayer, EvaluationResult, SystemLayer


# OpenRouter attribution so Sam from accounting can charge this back.
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/fsgeek/arbiter",
    "X-Title": "Arbiter conflict-detection",
}


# ---------------------------------------------------------------------------
# Model configurations — each is (evaluator_factory, display_name)
# ---------------------------------------------------------------------------


def _anthropic_haiku():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return AnthropicEvaluator(model="claude-haiku-4-5-20251001", api_key=key)


def _openai_gpt4o_mini():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return OpenAICompatibleEvaluator(model="gpt-4o-mini", api_key=key)


def _openrouter_gemini_flash():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return OpenAICompatibleEvaluator(
        model="google/gemini-2.0-flash-001",
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        extra_headers=_OPENROUTER_HEADERS,
    )


def _openrouter_qwen():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return OpenAICompatibleEvaluator(
        model="qwen/qwen-2.5-72b-instruct",
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        extra_headers=_OPENROUTER_HEADERS,
    )


def _openrouter_grok():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return OpenAICompatibleEvaluator(
        model="x-ai/grok-3-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        extra_headers=_OPENROUTER_HEADERS,
    )


MODELS = [
    pytest.param(_anthropic_haiku, id="anthropic/haiku-4.5"),
    pytest.param(_openai_gpt4o_mini, id="openai/gpt-4o-mini"),
    pytest.param(_openrouter_gemini_flash, id="google/gemini-2.0-flash"),
    pytest.param(_openrouter_qwen, id="qwen/qwen-2.5-72b"),
    pytest.param(_openrouter_grok, id="x-ai/grok-3-mini"),
]


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------


STRUCTURAL_SYSTEM = SystemLayer(
    name="query-rules",
    rules=[
        "Generate valid SQL for the user query.",
        "Report conflicts rather than resolving them silently.",
    ],
)

STRUCTURAL_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "Use the column records.attributes_st_mtime for time-based queries.",
        "Do not use records.attributes_* columns; they are not indexed and queries against them will be slow.",
    ],
)

CLEAN_SYSTEM = SystemLayer(
    name="query-rules",
    rules=["Generate valid SQL for the user query."],
)

CLEAN_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "Use the column files.modified_at for time-based queries.",
        "The files table has indexes on: id, modified_at, name.",
    ],
)

SEMANTIC_SYSTEM = SystemLayer(
    name="query-rules",
    rules=[
        "Generate valid SQL for the user query.",
        "Report conflicts rather than resolving them silently.",
    ],
)

SEMANTIC_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "Use the column records.created_ts for time-based queries.",
        "The records table indexes: id, name. No other columns are indexed.",
        "Never use unindexed columns in WHERE clauses on large tables.",
    ],
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_structural_conflict(make_evaluator):
    """Direct namespace overlap — the Indaleko case.

    'use attributes_st_mtime' vs 'never use attributes_*'
    This is the easy case. Any model should catch it.
    """
    evaluator = make_evaluator()
    result = evaluator.evaluate(
        STRUCTURAL_SYSTEM, STRUCTURAL_DOMAIN,
        "Find files modified in the last 7 days",
    )

    assert not result.resolved, f"Should detect conflict, got output: {result.output}"
    assert result.output is None
    assert len(result.conflicts) >= 1
    sources = " ".join(c.source + c.target for c in result.conflicts).lower()
    assert "attributes" in sources, f"Conflict should reference attributes, got: {sources}"


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_clean_resolution(make_evaluator):
    """No conflicts — domain is consistent, query should resolve to SQL."""
    evaluator = make_evaluator()
    result = evaluator.evaluate(
        CLEAN_SYSTEM, CLEAN_DOMAIN,
        "Find files modified in the last 7 days",
    )

    assert result.resolved, f"Clean domain should resolve, got conflicts: {result.conflicts}"
    assert result.output is not None
    assert not result.conflicts
    assert "modified_at" in result.output.lower()


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_semantic_conflict(make_evaluator):
    """Three-hop reasoning: recommended field → not in index list → unindexed columns banned.

    This is the hard case. Haiku 4.5 fails it non-deterministically.
    The question is whether other models/providers do better.
    """
    evaluator = make_evaluator()
    result = evaluator.evaluate(
        SEMANTIC_SYSTEM, SEMANTIC_DOMAIN,
        "Find records created in the last 30 days",
    )

    assert not result.resolved, f"Should detect semantic conflict, got output: {result.output}"
    assert len(result.conflicts) >= 1
