"""Tests for the scourer — undirected prompt exploration."""

import json

import pytest

from arbiter.scourer import (
    Finding,
    Scourer,
    ScourerReport,
    ScourerStack,
    UnexploredTerritory,
)


class TestScourerParsing:
    def test_parse_first_pass_response(self):
        scourer = Scourer()
        raw = json.dumps({
            "pass_number": 1,
            "findings": [
                {
                    "description": "Security policy appears twice",
                    "location": "Lines 40-41 and line 145",
                    "category": "verbatim-duplication",
                    "severity_guess": "notable",
                }
            ],
            "unexplored": [
                {
                    "description": "Tool definitions section",
                    "why_interesting": "Very long, may have internal contradictions",
                }
            ],
            "should_send_another": True,
            "rationale_for_continuation": "Tool section needs deeper exploration",
        })
        report = scourer.parse_response(raw, model="test-model")
        assert report.pass_number == 1
        assert report.model == "test-model"
        assert len(report.findings) == 1
        assert report.findings[0].category == "verbatim-duplication"
        assert len(report.unexplored) == 1
        assert report.should_send_another is True

    def test_parse_markdown_wrapped(self):
        scourer = Scourer()
        raw = '```json\n{"pass_number":1,"findings":[],"unexplored":[],"should_send_another":false}\n```'
        report = scourer.parse_response(raw)
        assert report.pass_number == 1
        assert not report.should_send_another

    def test_parse_invalid_raises(self):
        scourer = Scourer()
        with pytest.raises(ValueError, match="unparseable"):
            scourer.parse_response("not json")

    def test_pass_number_assigned_from_stack_not_model(self):
        """Bug fix: pass_number comes from stack position, not model's claim."""
        scourer = Scourer()
        # Add a report so stack has 1 report
        scourer.add_report(ScourerReport(
            pass_number=1, should_send_another=True,
        ))
        # Model claims pass_number=99, but we should get 2
        raw = json.dumps({
            "pass_number": 99,
            "findings": [],
            "unexplored": [],
            "should_send_another": True,
        })
        report = scourer.parse_response(raw)
        assert report.pass_number == 2  # from stack, not model

    def test_severity_guess_normalized_to_lowercase(self):
        """Bug fix: models return mixed case severity labels."""
        scourer = Scourer()
        raw = json.dumps({
            "pass_number": 1,
            "findings": [{
                "description": "test",
                "location": "test",
                "category": "test",
                "severity_guess": "Notable",  # mixed case
            }],
            "unexplored": [],
            "should_send_another": False,
        })
        report = scourer.parse_response(raw)
        assert report.findings[0].severity_guess == "notable"

    def test_model_provenance_tracked(self):
        scourer = Scourer()
        raw = json.dumps({
            "pass_number": 1,
            "findings": [],
            "unexplored": [],
            "should_send_another": False,
        })
        report = scourer.parse_response(raw, model="deepseek/deepseek-v3.2")
        assert report.model == "deepseek/deepseek-v3.2"

    def test_model_defaults_to_none(self):
        scourer = Scourer()
        raw = json.dumps({
            "pass_number": 1,
            "findings": [],
            "unexplored": [],
            "should_send_another": False,
        })
        report = scourer.parse_response(raw)
        assert report.model is None


class TestScourerComposition:
    def test_first_pass_prompt_has_no_prior_map(self):
        scourer = Scourer()
        prompt = scourer.build_prompt("Test prompt")
        assert "previous explorer" not in prompt
        assert "Test prompt" in prompt

    def test_second_pass_prompt_includes_prior_findings(self):
        scourer = Scourer()
        report = ScourerReport(
            pass_number=1,
            findings=[
                Finding(
                    description="Found a contradiction",
                    location="line 5",
                    category="contradiction",
                    severity_guess="concerning",
                )
            ],
            unexplored=[
                UnexploredTerritory(
                    description="Tool section",
                    why_interesting="Long and complex",
                )
            ],
            should_send_another=True,
        )
        scourer.add_report(report)
        prompt = scourer.build_prompt("Test prompt")
        assert "Previous explorers" in prompt
        assert "Found a contradiction" in prompt
        assert "Tool section" in prompt
        assert "pass_number" in prompt

    def test_second_pass_includes_finding_count(self):
        scourer = Scourer()
        scourer.add_report(ScourerReport(
            pass_number=1,
            findings=[
                Finding(description="A", location="1", category="x", severity_guess="curious"),
                Finding(description="B", location="2", category="y", severity_guess="notable"),
            ],
            should_send_another=True,
        ))
        prompt = scourer.build_prompt("Test prompt")
        assert "2 total" in prompt
        assert "1 passes" in prompt

    def test_second_pass_includes_stopping_criteria(self):
        scourer = Scourer()
        scourer.add_report(ScourerReport(
            pass_number=1, should_send_another=True,
        ))
        prompt = scourer.build_prompt("Test prompt")
        assert "diminishing returns" in prompt
        assert "FALSE" in prompt

    def test_second_pass_includes_model_provenance(self):
        scourer = Scourer()
        scourer.add_report(ScourerReport(
            pass_number=1,
            model="claude-opus-4-6",
            findings=[
                Finding(description="test", location="1", category="x",
                        severity_guess="curious"),
            ],
            should_send_another=True,
        ))
        prompt = scourer.build_prompt("Test prompt")
        assert "(claude-opus-4-6)" in prompt

    def test_should_continue_true_when_empty(self):
        stack = ScourerStack()
        assert stack.should_continue()

    def test_should_continue_reflects_last_report(self):
        stack = ScourerStack()
        stack.reports.append(ScourerReport(
            pass_number=1, should_send_another=True,
        ))
        assert stack.should_continue()
        stack.reports.append(ScourerReport(
            pass_number=2, should_send_another=False,
        ))
        assert not stack.should_continue()

    def test_all_findings_aggregates_across_passes(self):
        stack = ScourerStack()
        stack.reports.append(ScourerReport(
            pass_number=1,
            findings=[Finding(description="A", location="1", category="x", severity_guess="curious")],
            should_send_another=True,
        ))
        stack.reports.append(ScourerReport(
            pass_number=2,
            findings=[
                Finding(description="B", location="2", category="y", severity_guess="notable"),
                Finding(description="C", location="3", category="z", severity_guess="alarming"),
            ],
            should_send_another=False,
        ))
        assert stack.finding_count() == 3
        assert len(stack.all_findings()) == 3

    def test_all_unexplored_from_latest_only(self):
        stack = ScourerStack()
        stack.reports.append(ScourerReport(
            pass_number=1,
            unexplored=[UnexploredTerritory(description="old", why_interesting="")],
            should_send_another=True,
        ))
        stack.reports.append(ScourerReport(
            pass_number=2,
            unexplored=[UnexploredTerritory(description="new", why_interesting="")],
            should_send_another=False,
        ))
        unexplored = stack.all_unexplored()
        assert len(unexplored) == 1
        assert unexplored[0].description == "new"


class TestStackManagement:
    def test_remove_pass_and_renumber(self):
        stack = ScourerStack()
        stack.reports.append(ScourerReport(
            pass_number=1, model="a", should_send_another=True,
        ))
        stack.reports.append(ScourerReport(
            pass_number=2, model="b", should_send_another=True,
        ))
        stack.reports.append(ScourerReport(
            pass_number=3, model="c", should_send_another=True,
        ))
        removed = stack.remove_pass(1)  # remove "b"
        assert removed.model == "b"
        assert len(stack.reports) == 2
        assert stack.reports[0].pass_number == 1
        assert stack.reports[0].model == "a"
        assert stack.reports[1].pass_number == 2
        assert stack.reports[1].model == "c"

    def test_models_used(self):
        stack = ScourerStack()
        stack.reports.append(ScourerReport(
            pass_number=1, model="claude", should_send_another=True,
        ))
        stack.reports.append(ScourerReport(
            pass_number=2, model="gemini", should_send_another=True,
        ))
        stack.reports.append(ScourerReport(
            pass_number=3, should_send_another=False,
        ))
        assert stack.models_used() == ["claude", "gemini", "unknown"]


class TestMultilingual:
    def test_first_pass_with_language(self):
        scourer = Scourer()
        prompt = scourer.build_prompt("Test prompt", language="Hindi")
        assert "Hindi" in prompt
        assert "Test prompt" in prompt

    def test_subsequent_pass_with_language(self):
        scourer = Scourer()
        scourer.add_report(ScourerReport(
            pass_number=1, should_send_another=True,
        ))
        prompt = scourer.build_prompt("Test prompt", language="Chinese")
        assert "Chinese" in prompt
        assert "conceptual categories" in prompt

    def test_no_language_no_preamble(self):
        scourer = Scourer()
        prompt = scourer.build_prompt("Test prompt")
        assert "Conduct your entire analysis" not in prompt
