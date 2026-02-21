"""Adversarial conflict detection — can models catch deliberately hidden conflicts?

Three tiers of obfuscation, all encoding the same underlying conflict:
  "Use field X for time queries" + "X is unindexed" + "Never use unindexed fields"

Tier 1 (synonym): uses different words for the same concepts
Tier 2 (buried): hides the prohibition inside unrelated context
Tier 3 (split): distributes the conflict across entries that look unrelated,
       requiring the model to connect information from multiple entries that
       individually seem benign

Each tier tests whether the model can see through surface-level formatting
to the underlying logical contradiction.

Run:
    pytest tests/test_adversarial.py -v -s
"""

import os

import pytest

from arbiter.evaluator import AnthropicEvaluator, OpenAICompatibleEvaluator
from arbiter.models import DomainLayer, EvaluationResult, SystemLayer


# ---------------------------------------------------------------------------
# OpenRouter attribution
# ---------------------------------------------------------------------------

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/fsgeek/arbiter",
    "X-Title": "Arbiter conflict-detection",
}


# ---------------------------------------------------------------------------
# Model configurations
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
# Shared system layer
# ---------------------------------------------------------------------------

SYSTEM = SystemLayer(
    name="query-rules",
    rules=[
        "Generate valid SQL for the user query.",
        "Report conflicts rather than resolving them silently.",
    ],
)

QUERY = "Find records created in the last 30 days"


# ---------------------------------------------------------------------------
# Adversarial tier 1: Synonym substitution
#
# Same conflict, different vocabulary. "Unindexed" becomes "lacks index
# coverage." The field name is wrapped in a longer description.
# ---------------------------------------------------------------------------

TIER1_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "For temporal filtering on the records collection, the preferred column is records.created_ts.",
        "Index coverage on the records collection: primary key (id), name lookup (name). Remaining columns lack index coverage.",
        "Columns without index coverage must not appear in filter predicates on high-volume collections due to full-scan overhead.",
    ],
)


# ---------------------------------------------------------------------------
# Adversarial tier 2: Buried in context
#
# The prohibition is embedded in a longer entry about database best practices.
# The index information is a parenthetical aside. The recommendation is
# sandwiched between unrelated entries.
# ---------------------------------------------------------------------------

TIER2_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "The records collection stores audit trail data. Each record has an id (UUID), name (varchar), created_ts (timestamp), updated_ts (timestamp), and payload (jsonb).",
        "For time-based queries against records, use the created_ts column.",
        "Database performance guidelines: always use LIMIT on unbounded queries; prefer batch inserts for bulk operations; columns that are not indexed should never be used in WHERE clauses on tables with more than 10k rows, as the query planner will resort to sequential scans.",
        "The records table currently maintains two indexes: a B-tree on id (primary key) and a hash index on name for exact-match lookups.",
    ],
)


# ---------------------------------------------------------------------------
# Adversarial tier 3: Split and scatter
#
# The three pieces of the conflict are distributed across five entries.
# Two are distractors. No single entry mentions both the field and the
# index status. The prohibition is stated as a positive ("only use indexed
# columns") rather than a negative.
# ---------------------------------------------------------------------------

TIER3_DOMAIN = DomainLayer(
    name="schema-knowledge",
    entries=[
        "The records table is one of the largest in the system, containing approximately 50 million rows across all tenants.",
        "For time-based queries, the created_ts column in the records table provides millisecond-precision timestamps.",
        "Query optimizer hints: the records table has indexes on id and name only. Plan accordingly.",
        "All queries against tables exceeding 1 million rows must use indexed columns in their WHERE clause to maintain SLA response times.",
        "The payload column in records stores arbitrary JSON. Use jsonb_path_query for structured access.",
    ],
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_adversarial_tier1_synonym(make_evaluator):
    """Tier 1: same conflict, synonym substitution.

    'Preferred column is created_ts' + 'remaining columns lack index coverage'
    + 'columns without index coverage must not appear in filter predicates'

    The vocabulary is different but the logical chain is identical to the
    semantic conflict case.
    """
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, TIER1_DOMAIN, QUERY)

    assert not result.resolved, (
        f"Tier 1 (synonym): should detect conflict, got output: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_adversarial_tier2_buried(make_evaluator):
    """Tier 2: prohibition buried in database best practices paragraph.

    The index exclusion is in a separate entry from the prohibition.
    The prohibition is one clause in a multi-topic sentence about DB practices.
    The model must extract the relevant clause and connect it to index status.
    """
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, TIER2_DOMAIN, QUERY)

    assert not result.resolved, (
        f"Tier 2 (buried): should detect conflict, got output: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_adversarial_tier3_split(make_evaluator):
    """Tier 3: conflict split across 5 entries with 2 distractors.

    No single entry contains the conflict. The model must:
    1. Note created_ts is recommended for time queries
    2. Note that records has indexes on id and name ONLY
    3. Note that tables >1M rows require indexed WHERE columns
    4. Note that records has 50M rows (making rule 3 apply)
    5. Connect: created_ts is not in {id, name}, records is large,
       therefore using created_ts in WHERE violates the SLA rule

    This is a 4-hop chain with distractors. Significantly harder than
    the 3-hop semantic case from the characterization.
    """
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, TIER3_DOMAIN, QUERY)

    assert not result.resolved, (
        f"Tier 3 (split): should detect conflict, got output: {result.output}"
    )
    assert len(result.conflicts) >= 1
