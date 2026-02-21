"""Tests for conflict detection — the Indaleko case and its variants.

Unit tests run without any LLM. Integration tests require ANTHROPIC_API_KEY
and are marked with @pytest.mark.integration.

Run unit tests only:
    pytest tests/ -m "not integration"

Run all including integration:
    pytest tests/ -m integration
"""

import pytest

from arbiter.models import ConflictReport, DomainLayer, EvaluationResult, SystemLayer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _evaluator():
    """Return the default evaluator, skipping if Anthropic SDK not installed."""
    try:
        from arbiter.evaluator import AnthropicEvaluator
    except ImportError:
        pytest.skip("Anthropic SDK not installed (uv sync --extra spike)")
    return AnthropicEvaluator()


# ---------------------------------------------------------------------------
# Unit tests — no LLM, no network
# ---------------------------------------------------------------------------


def test_version():
    import arbiter
    assert arbiter.__version__ == "0.1.0"


def test_system_layer_instantiates():
    system = SystemLayer(
        name="test",
        rules=["Report conflicts rather than resolving them silently."],
    )
    assert system.name == "test"
    assert len(system.rules) == 1


def test_domain_layer_instantiates():
    domain = DomainLayer(
        name="test",
        entries=[
            "Use field records.attributes_st_mtime for time queries.",
            "Do not use records.attributes_* fields; they are unindexed.",
        ],
    )
    assert len(domain.entries) == 2


def test_conflict_report_instantiates():
    report = ConflictReport(
        source="Use field records.attributes_st_mtime for time queries.",
        target="Do not use records.attributes_* fields; they are unindexed.",
        description="Recommended field falls within prohibited namespace.",
        resolution_hint="Index the attributes_st_mtime column, or identify an indexed alternative.",
    )
    assert report.resolution_hint is not None


def test_evaluation_result_conflict_state():
    result = EvaluationResult(
        resolved=False,
        output=None,
        conflicts=[
            ConflictReport(
                source="entry A",
                target="entry B",
                description="A and B contradict each other.",
            )
        ],
    )
    assert not result.resolved
    assert result.output is None
    assert len(result.conflicts) == 1


def test_evaluation_result_resolved_state():
    result = EvaluationResult(
        resolved=True,
        output="SELECT * FROM files WHERE modified_at > NOW() - INTERVAL '7 days'",
        conflicts=[],
    )
    assert result.resolved
    assert result.output is not None
    assert not result.conflicts


# ---------------------------------------------------------------------------
# Integration tests — require ANTHROPIC_API_KEY
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_detects_field_conflict():
    """The Indaleko case: a recommended field falls within a prohibited namespace.

    Two good-faith authors wrote contradictory instructions:
    - Schema author: use attributes_st_mtime
    - Performance author: never use attributes_* (unindexed)

    Arbiter should surface this conflict rather than silently picking one.
    """
    evaluator = _evaluator()

    system = SystemLayer(
        name="query-rules",
        rules=[
            "Generate valid SQL for the user query.",
            "Report conflicts rather than resolving them silently.",
        ],
    )
    domain = DomainLayer(
        name="schema-knowledge",
        entries=[
            "Use the column records.attributes_st_mtime for time-based queries.",
            "Do not use records.attributes_* columns; they are not indexed and queries against them will be slow.",
        ],
    )

    result = evaluator.evaluate(
        system, domain, "Find files modified in the last 7 days"
    )

    assert not result.resolved, "Should detect conflict, not silently resolve"
    assert result.output is None, "Should not produce output when conflict exists"
    assert len(result.conflicts) >= 1
    # The conflict should reference both domain entries
    sources = " ".join(c.source + c.target for c in result.conflicts).lower()
    assert "attributes" in sources


@pytest.mark.integration
def test_resolves_clean_query():
    """No conflicts: domain entries are consistent; query resolves to SQL."""
    evaluator = _evaluator()

    system = SystemLayer(
        name="query-rules",
        rules=["Generate valid SQL for the user query."],
    )
    domain = DomainLayer(
        name="schema-knowledge",
        entries=[
            "Use the column files.modified_at for time-based queries.",
            "The files table has indexes on: id, modified_at, name.",
        ],
    )

    result = evaluator.evaluate(
        system, domain, "Find files modified in the last 7 days"
    )

    assert result.resolved, "Clean domain should resolve"
    assert result.output is not None, "Should produce SQL output"
    assert not result.conflicts
    assert "modified_at" in result.output.lower()


@pytest.mark.integration
@pytest.mark.xfail(
    reason=(
        "Semantic conflict requires three-hop reasoning: "
        "'use created_ts' + 'created_ts not in index list' + 'never use unindexed columns'. "
        "Haiku 4.5 is token-sensitive on this task (55% overall, 0-100% depending on "
        "prompt formatting). Not a capability limitation — GPT-4o-mini, Gemini Flash, "
        "and Grok 3 Mini all score 100% across all formatting variants. "
        "See tests/characterize_semantic.py and docs/cairn/semantic_characterization.json."
    ),
    strict=False,
)
def test_semantic_conflict_requires_domain_knowledge():
    """Harder case: conflict requires knowing that a field is unindexed.

    Entry A recommends a specific field.
    Entry B prohibits a semantic *property* (unindexed fields).
    The conflict is only visible if the evaluator knows A's field is unindexed.
    """
    evaluator = _evaluator()

    system = SystemLayer(
        name="query-rules",
        rules=[
            "Generate valid SQL for the user query.",
            "Report conflicts rather than resolving them silently.",
        ],
    )
    domain = DomainLayer(
        name="schema-knowledge",
        entries=[
            "Use the column records.created_ts for time-based queries.",
            "The records table indexes: id, name. No other columns are indexed.",
            "Never use unindexed columns in WHERE clauses on large tables.",
        ],
    )

    result = evaluator.evaluate(
        system, domain, "Find records created in the last 30 days"
    )

    # created_ts is recommended but not indexed — semantic conflict
    assert not result.resolved
    assert len(result.conflicts) >= 1
