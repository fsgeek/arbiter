"""Tests for probe scoring methods — known inputs to known outputs.

Tests the contract specified in ablation_framework.md:
- Probe.score(response, tool_calls) -> float in [0.0, 1.0]
- Each scoring method: exact, contains, not_contains, length, llm_judge, tool_trace
- Edge cases: empty response, very long response, tool calls without text
"""

import pytest

from arbiter.ablation.probe import Probe, ProbeResult


# --- Helpers ---


def _make_probe(scoring_method: str, scoring_params: dict | None = None) -> Probe:
    """Create a minimal Probe for testing a specific scoring method."""
    return Probe(
        id=f"test-{scoring_method}",
        target_block="test-block",
        user_message="Test question?",
        scoring_method=scoring_method,
        expected_behavior="Expected behavior description",
        violation_indicator="Violation indicator description",
        scoring_params=scoring_params or {},
    )


# --- Exact scoring ---


class TestExactScoring:
    def test_exact_match_scores_one(self):
        probe = _make_probe("exact", {"expected_text": "hello world"})
        assert probe.score("hello world") == 1.0

    def test_exact_mismatch_scores_zero(self):
        probe = _make_probe("exact", {"expected_text": "hello world"})
        assert probe.score("goodbye world") == 0.0

    def test_exact_case_sensitive(self):
        probe = _make_probe("exact", {"expected_text": "Hello"})
        assert probe.score("hello") == 0.0

    def test_exact_empty_response(self):
        probe = _make_probe("exact", {"expected_text": "something"})
        assert probe.score("") == 0.0

    def test_exact_empty_expected(self):
        probe = _make_probe("exact", {"expected_text": ""})
        assert probe.score("") == 1.0


# --- Contains scoring ---


class TestContainsScoring:
    def test_contains_present_scores_one(self):
        probe = _make_probe("contains", {"patterns": ["time estimate"]})
        assert probe.score("I cannot provide a time estimate.") == 1.0

    def test_contains_absent_scores_zero(self):
        probe = _make_probe("contains", {"patterns": ["time estimate"]})
        assert probe.score("I'll help with that refactoring.") == 0.0

    def test_contains_empty_response(self):
        probe = _make_probe("contains", {"patterns": ["anything"]})
        assert probe.score("") == 0.0

    def test_contains_substring_match(self):
        probe = _make_probe("contains", {"patterns": ["hours"]})
        assert probe.score("It will take about 3 hours to complete.") == 1.0


# --- Not-contains scoring ---


class TestNotContainsScoring:
    def test_not_contains_absent_scores_one(self):
        """Score 1.0 when the violation pattern is NOT present (adherence)."""
        probe = _make_probe("not_contains", {"patterns": ["hours"]})
        assert probe.score("I'll help with the refactoring.") == 1.0

    def test_not_contains_present_scores_zero(self):
        """Score 0.0 when the violation pattern IS present (violation)."""
        probe = _make_probe("not_contains", {"patterns": ["hours"]})
        assert probe.score("This will take about 2 hours.") == 0.0

    def test_not_contains_multiple_violation_terms(self):
        """Design doc example: no-time-estimates checks for hours, days, minutes, weeks."""
        # Each pattern check is a separate probe or the impl handles lists;
        # test the basic single-pattern contract
        probe = _make_probe("not_contains", {"patterns": ["days"]})
        assert probe.score("It should take 3 days.") == 0.0
        assert probe.score("I can help with that.") == 1.0

    def test_not_contains_empty_response(self):
        """Empty response doesn't contain the pattern -> score 1.0."""
        probe = _make_probe("not_contains", {"patterns": ["error"]})
        assert probe.score("") == 1.0


# --- Length scoring ---


class TestLengthScoring:
    def test_short_response_scores_high(self):
        """Design doc formula: clamp(1.0 - (len / (3 * baseline)), 0, 1).
        Shorter = higher score for conciseness probes."""
        baseline_length = 100
        probe = _make_probe("length", {"baseline_length": baseline_length})
        # Response shorter than baseline -> high score
        short_response = "x" * 50
        score = probe.score(short_response)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # shorter than baseline should score well

    def test_very_long_response_scores_low(self):
        """Response much longer than baseline should score near 0."""
        baseline_length = 100
        probe = _make_probe("length", {"baseline_length": baseline_length})
        long_response = "x" * 500
        score = probe.score(long_response)
        assert 0.0 <= score <= 1.0
        assert score < 0.5

    def test_response_at_3x_baseline_scores_zero(self):
        """At 3x baseline length, score should be 0 per the formula."""
        baseline_length = 100
        probe = _make_probe("length", {"baseline_length": baseline_length})
        response = "x" * 300
        score = probe.score(response)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_empty_response_scores_one(self):
        """Empty response is maximally concise -> score 1.0."""
        probe = _make_probe("length", {"baseline_length": 100})
        score = probe.score("")
        assert score == pytest.approx(1.0)

    def test_score_clamped_to_unit_interval(self):
        """Score never exceeds [0, 1] regardless of input."""
        probe = _make_probe("length", {"baseline_length": 100})
        # Extremely long
        assert 0.0 <= probe.score("x" * 10000) <= 1.0
        # Zero length
        assert 0.0 <= probe.score("") <= 1.0

    def test_score_monotonically_decreases_with_length(self):
        """Longer responses should score equal or lower."""
        probe = _make_probe("length", {"baseline_length": 100})
        scores = [probe.score("x" * n) for n in [0, 50, 100, 150, 200, 300, 500]]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Score should decrease: {scores[i]} at length {[0,50,100,150,200,300,500][i]} "
                f"> {scores[i+1]} at length {[0,50,100,150,200,300,500][i+1]}"
            )


# --- LLM judge scoring ---


class TestLLMJudgeScoring:
    def test_llm_judge_raises_without_judge(self):
        """Calling score() with llm_judge method and no judge configured should raise."""
        probe = _make_probe("llm_judge")
        with pytest.raises(ValueError):
            probe.score("Some response")

    def test_build_judge_prompt_only_valid_for_llm_judge(self):
        probe = _make_probe("contains", {"patterns": ["x"]})
        with pytest.raises(ValueError):
            probe.build_judge_prompt("response")

    def test_parse_judge_score_from_json(self):
        score = Probe.parse_judge_score('{"score": 0.7, "justification": "ok"}')
        assert score == pytest.approx(0.7)

    def test_parse_judge_score_percentage(self):
        score = Probe.parse_judge_score("score: 85")
        assert score == pytest.approx(0.85)

    def test_parse_judge_score_invalid_raises(self):
        with pytest.raises(ValueError):
            Probe.parse_judge_score("no usable score here")


# --- Tool trace scoring ---


class TestToolTraceScoring:
    def test_read_before_edit_scores_one(self):
        """Tool trace: Read before Edit -> score 1.0 (read-first adherence)."""
        probe = _make_probe("tool_trace", {
            "required_sequence": ["Read", "Edit"],
        })
        tool_calls = [
            {"name": "Read", "arguments": {"file_path": "utils.py"}},
            {"name": "Edit", "arguments": {"file_path": "utils.py", "old": "foo", "new": "bar"}},
        ]
        score = probe.score("I'll read the file first.", tool_calls=tool_calls)
        assert score == 1.0

    def test_edit_without_read_scores_zero(self):
        """Tool trace: Edit without preceding Read -> score 0.0."""
        probe = _make_probe("tool_trace", {
            "required_sequence": ["Read", "Edit"],
        })
        tool_calls = [
            {"name": "Edit", "arguments": {"file_path": "utils.py", "old": "foo", "new": "bar"}},
        ]
        score = probe.score("Let me edit that.", tool_calls=tool_calls)
        assert score == 0.0

    def test_no_tool_calls_scores_zero(self):
        """No tool calls at all -> score 0.0 for tool_trace probes."""
        probe = _make_probe("tool_trace", {
            "required_sequence": ["Read", "Edit"],
        })
        score = probe.score("I would edit the file.", tool_calls=None)
        assert score == 0.0

    def test_empty_tool_calls_scores_zero(self):
        """Empty tool call list -> score 0.0."""
        probe = _make_probe("tool_trace", {
            "required_sequence": ["Read", "Edit"],
        })
        score = probe.score("Response text.", tool_calls=[])
        assert score == 0.0

    def test_required_before_partial_credit(self):
        probe = _make_probe(
            "tool_trace",
            {
                "required_sequence": ["Read", "Edit"],
                "required_before": {"Read": "Edit", "Plan": "Edit"},
            },
        )
        tool_calls = [{"name": "Read"}, {"name": "Edit"}]
        # required_sequence pass, Read before Edit pass, Plan before Edit fails
        assert probe.score("ok", tool_calls=tool_calls) == pytest.approx(2 / 3)


# --- Score range contract ---


class TestScoreRangeContract:
    """All scoring methods must return floats in [0.0, 1.0]."""

    @pytest.mark.parametrize("method,params,response", [
        ("exact", {"expected_text": "test"}, "test"),
        ("exact", {"expected_text": "test"}, "other"),
        ("contains", {"patterns": ["x"]}, "has x here"),
        ("contains", {"patterns": ["x"]}, "no match"),
        ("not_contains", {"patterns": ["x"]}, "has x here"),
        ("not_contains", {"patterns": ["x"]}, "no match"),
        ("length", {"baseline_length": 100}, "short"),
        ("length", {"baseline_length": 100}, "x" * 1000),
        ("length", {"baseline_length": 1}, "x" * 100),
    ])
    def test_score_in_unit_interval(self, method, params, response):
        probe = _make_probe(method, params)
        score = probe.score(response)
        assert isinstance(score, float) or isinstance(score, int)
        assert 0.0 <= score <= 1.0, f"Score {score} out of range for {method}"


# --- ProbeResult ---


class TestProbeResult:
    def test_probe_result_creation(self):
        """ProbeResult should hold all required fields."""
        result = ProbeResult(
            config_id="phase0-block5-removed",
            probe_id="probe-concise-01",
            model_id="anthropic/claude-haiku-4.5",
            trial=1,
            raw_response="A short response.",
            tool_calls=None,
            score=0.85,
            timestamp="2026-03-16T12:00:00Z",
        )
        assert result.config_id == "phase0-block5-removed"
        assert result.score == 0.85
        assert result.trial == 1

    def test_probe_result_with_tool_calls(self):
        """ProbeResult can hold tool call traces."""
        tool_calls = [
            {"name": "Read", "arguments": {"file_path": "test.py"}},
        ]
        result = ProbeResult(
            config_id="baseline",
            probe_id="probe-read-first-01",
            model_id="google/gemini-2.0-flash",
            trial=2,
            raw_response="Reading file...",
            tool_calls=tool_calls,
            score=1.0,
            timestamp="2026-03-16T12:01:00Z",
        )
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
