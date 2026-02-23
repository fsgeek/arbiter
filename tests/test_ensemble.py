"""Ensemble evaluator — multi-model conflict detection.

Tests whether running multiple models in parallel catches conflicts that
any single model misses. The hypothesis: an ensemble with complementary
domain strengths (Haiku for instructions, Gemini for DB schemas) should
outperform any individual model.

Uses mock evaluators for unit tests and real APIs for integration tests.
"""

import os

import pytest

from arbiter.evaluator import (
    AnthropicEvaluator,
    EnsembleEvaluator,
    OpenAICompatibleEvaluator,
)
from arbiter.models import ConflictReport, DomainLayer, EvaluationResult, SystemLayer


# ---------------------------------------------------------------------------
# Mock evaluators for unit tests
# ---------------------------------------------------------------------------


class _AlwaysClean:
    """Mock evaluator that always resolves cleanly."""

    def evaluate(self, system, domain, query, *, budget_usd=None):
        return EvaluationResult(
            resolved=True,
            output="SELECT * FROM records",
            conflicts=[],
        )


class _AlwaysConflict:
    """Mock evaluator that always reports a conflict."""

    def __init__(self, source="entry A", target="entry B"):
        self._source = source
        self._target = target

    def evaluate(self, system, domain, query, *, budget_usd=None):
        return EvaluationResult(
            resolved=False,
            output=None,
            conflicts=[
                ConflictReport(
                    source=self._source,
                    target=self._target,
                    description="test conflict",
                    resolution_hint=None,
                )
            ],
        )


class _AlwaysRaise:
    """Mock evaluator that always raises."""

    def evaluate(self, system, domain, query, *, budget_usd=None):
        raise RuntimeError("API error")


_DUMMY_SYSTEM = SystemLayer(name="test", rules=["test rule"])
_DUMMY_DOMAIN = DomainLayer(name="test", entries=["test entry"])
_DUMMY_QUERY = "test query"


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_ensemble_requires_evaluators():
    with pytest.raises(ValueError, match="at least one"):
        EnsembleEvaluator([])


def test_ensemble_all_clean():
    """All evaluators agree clean → ensemble resolves."""
    ensemble = EnsembleEvaluator([_AlwaysClean(), _AlwaysClean()])
    result = ensemble.evaluate(_DUMMY_SYSTEM, _DUMMY_DOMAIN, _DUMMY_QUERY)
    assert result.resolved
    assert result.output is not None
    assert not result.conflicts


def test_ensemble_any_conflict_flags():
    """One evaluator flags, one resolves → ensemble flags (OR-gate)."""
    ensemble = EnsembleEvaluator([_AlwaysClean(), _AlwaysConflict()])
    result = ensemble.evaluate(_DUMMY_SYSTEM, _DUMMY_DOMAIN, _DUMMY_QUERY)
    assert not result.resolved
    assert len(result.conflicts) == 1
    assert result.output is None


def test_ensemble_all_conflict():
    """Both flag → ensemble collects all conflicts."""
    ensemble = EnsembleEvaluator([
        _AlwaysConflict("A", "B"),
        _AlwaysConflict("C", "D"),
    ])
    result = ensemble.evaluate(_DUMMY_SYSTEM, _DUMMY_DOMAIN, _DUMMY_QUERY)
    assert not result.resolved
    assert len(result.conflicts) == 2


def test_ensemble_deduplicates_conflicts():
    """Same conflict from multiple evaluators → deduplicated."""
    ensemble = EnsembleEvaluator([
        _AlwaysConflict("A", "B"),
        _AlwaysConflict("A", "B"),
    ])
    result = ensemble.evaluate(_DUMMY_SYSTEM, _DUMMY_DOMAIN, _DUMMY_QUERY)
    assert not result.resolved
    assert len(result.conflicts) == 1


def test_ensemble_propagates_errors():
    """If an evaluator raises, the ensemble propagates."""
    ensemble = EnsembleEvaluator([_AlwaysClean(), _AlwaysRaise()])
    with pytest.raises(RuntimeError, match="API error"):
        ensemble.evaluate(_DUMMY_SYSTEM, _DUMMY_DOMAIN, _DUMMY_QUERY)


def test_ensemble_single_evaluator():
    """Ensemble with one evaluator behaves identically to that evaluator."""
    ensemble = EnsembleEvaluator([_AlwaysClean()])
    result = ensemble.evaluate(_DUMMY_SYSTEM, _DUMMY_DOMAIN, _DUMMY_QUERY)
    assert result.resolved


# ---------------------------------------------------------------------------
# Integration tests — real API calls
# ---------------------------------------------------------------------------

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/fsgeek/arbiter",
    "X-Title": "Arbiter conflict-detection",
}


def _make_haiku():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    return AnthropicEvaluator(model="claude-haiku-4-5-20251001", api_key=key)


def _make_gemini():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    return OpenAICompatibleEvaluator(
        model="google/gemini-2.0-flash-001",
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        extra_headers=_OPENROUTER_HEADERS,
    )


# The system prompt instruction conflict that Gemini misses (60% at n=5)
# but Haiku catches (100%).
INSTRUCTION_SYSTEM = SystemLayer(
    name="instruction-consistency-audit",
    rules=[
        "Examine the provided instructions for internal contradictions.",
        "Report conflicts rather than resolving them silently.",
        "A conflict exists when one instruction requires behavior that another instruction prohibits.",
    ],
)

TASK_SEARCH_DOMAIN = DomainLayer(
    name="claude-code-system-prompt-excerpt",
    entries=[
        "When doing file search, prefer to use the Task tool in order to reduce context usage.",
        "When NOT to use the Task tool: If you want to read a specific file path, use the Read or Glob tool instead of the Task tool, to find the match more quickly.",
        "If you are searching for a specific class definition like 'class Foo', use the Glob tool instead, to find the match more quickly.",
        "For broader codebase exploration and deep research, use the Task tool with subagent_type=Explore.",
    ],
)

INSTRUCTION_QUERY = "An AI assistant receives these instructions and must follow all of them. Can it comply with every instruction simultaneously?"

# The DB semantic conflict that Haiku misses (55%) but Gemini catches (100%).
DB_SYSTEM = SystemLayer(
    name="query-rules",
    rules=[
        "Generate valid SQL for the user query.",
        "Report conflicts rather than resolving them silently.",
    ],
)

DB_SEMANTIC_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "Use the column records.created_ts for time-based queries.",
        "The records table indexes: id, name. No other columns are indexed.",
        "Never use unindexed columns in WHERE clauses on large tables.",
    ],
)

DB_QUERY = "Find records created in the last 30 days"


@pytest.mark.integration
def test_ensemble_catches_instruction_conflict():
    """Haiku + Gemini ensemble on an instruction conflict Gemini sometimes misses."""
    haiku = _make_haiku()
    gemini = _make_gemini()
    if not haiku or not gemini:
        pytest.skip("Need both ANTHROPIC_API_KEY and OPENROUTER_API_KEY")

    ensemble = EnsembleEvaluator([haiku, gemini])
    result = ensemble.evaluate(INSTRUCTION_SYSTEM, TASK_SEARCH_DOMAIN, INSTRUCTION_QUERY)

    assert not result.resolved, (
        f"Ensemble should detect task-search contradiction, got: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
def test_ensemble_catches_db_conflict():
    """Haiku + Gemini ensemble on a DB conflict Haiku sometimes misses."""
    haiku = _make_haiku()
    gemini = _make_gemini()
    if not haiku or not gemini:
        pytest.skip("Need both ANTHROPIC_API_KEY and OPENROUTER_API_KEY")

    ensemble = EnsembleEvaluator([haiku, gemini])
    result = ensemble.evaluate(DB_SYSTEM, DB_SEMANTIC_DOMAIN, DB_QUERY)

    assert not result.resolved, (
        f"Ensemble should detect DB semantic conflict, got: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
def test_ensemble_clean_agreement():
    """Both models should agree on clean input."""
    haiku = _make_haiku()
    gemini = _make_gemini()
    if not haiku or not gemini:
        pytest.skip("Need both ANTHROPIC_API_KEY and OPENROUTER_API_KEY")

    clean_domain = DomainLayer(
        name="schema-knowledge",
        entries=[
            "Use the column files.modified_at for time-based queries.",
            "The files table has indexes on: id, modified_at, name.",
        ],
    )

    ensemble = EnsembleEvaluator([haiku, gemini])
    result = ensemble.evaluate(
        DB_SYSTEM, clean_domain, "Find files modified in the last 7 days"
    )

    assert result.resolved, (
        f"Clean input should resolve, got conflicts: {result.conflicts}"
    )
