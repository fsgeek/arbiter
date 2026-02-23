"""Arbiter eating its own dog food — detecting conflicts in the Claude Code system prompt.

The Claude Code system prompt contains real contradictions that instances
must silently navigate. This test feeds those contradictions through Arbiter
as domain entries to see if the conflict detection models catch them.

This is both a different-domain validation (instruction-following, not database
queries) and a meta-level test: can the tool detect contradictions in the
instructions that constrain its own builder?

Source: docs/claude-code-system-prompt.md (from public system prompt collection)
"""

import os

import pytest

from arbiter.evaluator import AnthropicEvaluator, OpenAICompatibleEvaluator
from arbiter.models import DomainLayer, SystemLayer

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/fsgeek/arbiter",
    "X-Title": "Arbiter conflict-detection",
}


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
    pytest.param(_openrouter_grok, id="x-ai/grok-3-mini"),
]

# The system layer: evaluating instructions for internal consistency.
SYSTEM = SystemLayer(
    name="instruction-consistency-audit",
    rules=[
        "Examine the provided instructions for internal contradictions.",
        "Report conflicts rather than resolving them silently.",
        "A conflict exists when one instruction requires behavior that another instruction prohibits.",
    ],
)


# ---------------------------------------------------------------------------
# Conflict 1: TodoWrite is MANDATORY and FORBIDDEN
#
# The prompt spends 225 lines explaining TodoWrite, says to use it
# "VERY frequently" and that not using it is "unacceptable," then
# two separate sections say "NEVER use the TodoWrite or Task tools."
# ---------------------------------------------------------------------------

TODOWRITE_DOMAIN = DomainLayer(
    name="claude-code-system-prompt-excerpt",
    entries=[
        "You have access to the TodoWrite tools to help you manage and plan tasks. Use these tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress.",
        "These tools are also EXTREMELY helpful for planning tasks, and for breaking down larger complex tasks into smaller steps. If you do not use this tool when planning, you may forget to do important tasks - and that is unacceptable.",
        "IMPORTANT: Always use the TodoWrite tool to plan and track tasks throughout the conversation.",
        "Important notes: NEVER use the TodoWrite or Task tools.",
        "Important: DO NOT use the TodoWrite or Task tools.",
    ],
)


# ---------------------------------------------------------------------------
# Conflict 2: Be CONCISE vs Use TodoWrite EXTENSIVELY
#
# "Your responses should be short and concise" vs extensive TodoWrite
# tracking with per-task status updates that inflate response length.
# ---------------------------------------------------------------------------

CONCISE_VS_VERBOSE_DOMAIN = DomainLayer(
    name="claude-code-system-prompt-excerpt",
    entries=[
        "Your output will be displayed on a command line interface. Your responses should be short and concise.",
        "Use the TodoWrite tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress.",
        "Update task status in real-time as you work. Mark tasks complete IMMEDIATELY after finishing. Exactly ONE task must be in_progress at any time.",
        "When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully.",
    ],
)


# ---------------------------------------------------------------------------
# Conflict 3: Use Task tool for search vs DON'T use Task tool for search
#
# "When doing file search, prefer to use the Task tool" vs
# "When NOT to use the Task tool: If you want to read a specific file path,
# use the Read or Glob tool instead"
# ---------------------------------------------------------------------------

TASK_SEARCH_DOMAIN = DomainLayer(
    name="claude-code-system-prompt-excerpt",
    entries=[
        "When doing file search, prefer to use the Task tool in order to reduce context usage.",
        "When NOT to use the Task tool: If you want to read a specific file path, use the Read or Glob tool instead of the Task tool, to find the match more quickly.",
        "If you are searching for a specific class definition like 'class Foo', use the Glob tool instead, to find the match more quickly.",
        "For broader codebase exploration and deep research, use the Task tool with subagent_type=Explore.",
    ],
)


# ---------------------------------------------------------------------------
# Conflict 4: Proactive action vs scope-matching
#
# EnterPlanMode says "Use this tool proactively." TodoWrite says use it
# "proactively." But other instructions say match scope to what was
# requested and don't do more than asked.
# ---------------------------------------------------------------------------

PROACTIVE_VS_SCOPE_DOMAIN = DomainLayer(
    name="claude-code-system-prompt-excerpt",
    entries=[
        "Use this tool proactively when you're about to start a non-trivial implementation task.",
        "IMPORTANT: Always use the TodoWrite tool to plan and track tasks throughout the conversation.",
        "Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused.",
        "Don't add features, refactor code, or make improvements beyond what was asked.",
        "NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.",
    ],
)


# ---------------------------------------------------------------------------
# Control case: No conflict (consistent instructions)
# ---------------------------------------------------------------------------

CLEAN_DOMAIN = DomainLayer(
    name="claude-code-consistent-excerpt",
    entries=[
        "Use the Read tool to read files before editing them.",
        "Use the Edit tool to modify existing files rather than creating new ones.",
        "Always read a file's contents before attempting to write changes to it.",
    ],
)


QUERY = "An AI assistant receives these instructions and must follow all of them. Can it comply with every instruction simultaneously?"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_todowrite_mandatory_and_forbidden(make_evaluator):
    """The most direct contradiction: TodoWrite is required AND prohibited."""
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, TODOWRITE_DOMAIN, QUERY)
    assert not result.resolved, (
        f"Should detect TodoWrite mandatory/forbidden conflict, got: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_concise_vs_verbose_tracking(make_evaluator):
    """Be concise vs track everything with verbose status updates."""
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, CONCISE_VS_VERBOSE_DOMAIN, QUERY)
    assert not result.resolved, (
        f"Should detect concise vs verbose tracking conflict, got: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_task_search_contradictory_guidance(make_evaluator):
    """Use Task for search vs don't use Task for search."""
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, TASK_SEARCH_DOMAIN, QUERY)
    assert not result.resolved, (
        f"Should detect Task search contradiction, got: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_proactive_vs_scope_matching(make_evaluator):
    """Be proactive vs only do what's requested."""
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, PROACTIVE_VS_SCOPE_DOMAIN, QUERY)
    assert not result.resolved, (
        f"Should detect proactive vs scope-matching conflict, got: {result.output}"
    )
    assert len(result.conflicts) >= 1


@pytest.mark.integration
@pytest.mark.parametrize("make_evaluator", MODELS)
def test_clean_instructions_resolve(make_evaluator):
    """Control case: consistent instructions should resolve cleanly."""
    evaluator = make_evaluator()
    result = evaluator.evaluate(SYSTEM, CLEAN_DOMAIN, QUERY)
    assert result.resolved, (
        f"Consistent instructions should not show conflicts, got: {result.conflicts}"
    )
