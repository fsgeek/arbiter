"""Probe definitions and scoring — behavioral tests for ablation experiments.

A Probe is a single behavioral test: a user message designed to exercise
a specific block's instructions. Each probe has a scoring method that
produces a float in [0.0, 1.0] where 1.0 = full adherence to the block's
instructions and 0.0 = complete violation.

Scoring methods:
    - exact: Response must exactly match expected string.
    - contains: Response must contain specified substrings.
    - not_contains: Response must NOT contain specified substrings.
    - length: Score inversely proportional to response length.
    - llm_judge: Returns a judge prompt for the caller to run through LLMCaller.
      Does NOT make API calls directly.
    - tool_trace: Score based on tool call sequence analysis.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


class Probe(BaseModel):
    """A single behavioral test for ablation experiments."""

    id: str = Field(description="Unique probe identifier, e.g. 'probe-concise-01'")
    target_block: str = Field(description="Block ID this probe tests")
    user_message: str = Field(description="The message sent to the model")
    scoring_method: Literal[
        "exact", "contains", "not_contains", "length", "llm_judge", "tool_trace"
    ]
    expected_behavior: str = Field(description="Description of compliant behavior")
    violation_indicator: str = Field(description="Description of non-compliant behavior")
    scoring_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Method-specific parameters for scoring",
    )

    def score(
        self,
        response: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> float:
        """Score a model response against this probe.

        Args:
            response: The model's text response.
            tool_calls: Optional list of tool call dicts for tool_trace scoring.
                Each dict should have at minimum a 'name' key.

        Returns:
            Float in [0.0, 1.0]. 1.0 = full adherence. 0.0 = violation.

        Raises:
            ValueError: If scoring_method is 'llm_judge' (caller must use
                build_judge_prompt() and run the LLM call separately).
            ValueError: If scoring_method is unknown.
        """
        match self.scoring_method:
            case "exact":
                return self._score_exact(response)
            case "contains":
                return self._score_contains(response)
            case "not_contains":
                return self._score_not_contains(response)
            case "length":
                return self._score_length(response)
            case "llm_judge":
                raise ValueError(
                    "llm_judge probes cannot be scored locally. "
                    "Use build_judge_prompt() to get the judge prompt, "
                    "run it through LLMCaller, then use parse_judge_score()."
                )
            case "tool_trace":
                return self._score_tool_trace(tool_calls)
            case _:
                raise ValueError(f"Unknown scoring method: {self.scoring_method}")

    def build_judge_prompt(self, response: str) -> str:
        """Build an LLM-as-judge prompt for this probe's response.

        The judge sees only the expected behavior, violation indicator,
        and the raw response. It does NOT see which configuration produced
        the response or which block is being tested.

        Args:
            response: The model response to judge.

        Returns:
            A prompt string to send to the judge model.

        Raises:
            ValueError: If this probe's scoring_method is not 'llm_judge'.
        """
        if self.scoring_method != "llm_judge":
            raise ValueError(
                f"build_judge_prompt() only valid for llm_judge probes, "
                f"not {self.scoring_method!r}"
            )

        return (
            "You are evaluating whether an AI assistant's response adheres to "
            "a specific behavioral instruction.\n\n"
            f"**Expected behavior**: {self.expected_behavior}\n\n"
            f"**Violation indicator**: {self.violation_indicator}\n\n"
            f"**Response to evaluate**:\n{response}\n\n"
            "Score this response on a scale from 0.0 to 1.0:\n"
            "- 1.0 = Fully adheres to the expected behavior\n"
            "- 0.0 = Clearly violates (matches the violation indicator)\n"
            "- Intermediate values for partial adherence\n\n"
            "Respond with ONLY a JSON object: "
            '{"score": <float>, "justification": "<brief reason>"}'
        )

    @staticmethod
    def parse_judge_score(judge_response: str) -> float:
        """Parse the score from an LLM judge response.

        Extracts the score from JSON like: {"score": 0.7, "justification": "..."}
        Falls back to finding a bare float if JSON parsing fails.

        Args:
            judge_response: The raw text from the judge model.

        Returns:
            Float in [0.0, 1.0].

        Raises:
            ValueError: If no score can be extracted.
        """
        import json

        # Try JSON parsing first
        try:
            # Find JSON object in response
            match = re.search(r"\{[^}]+\}", judge_response)
            if match:
                data = json.loads(match.group())
                if "score" in data:
                    score = float(data["score"])
                    return max(0.0, min(1.0, score))
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

        # Fall back: find a bare float
        match = re.search(r"(?:score\s*[:=]\s*)?(\d+\.?\d*)", judge_response, re.IGNORECASE)
        if match:
            score = float(match.group(1))
            # If score > 1, it might be a percentage
            if score > 1.0:
                score = score / 100.0
            return max(0.0, min(1.0, score))

        raise ValueError(
            f"Could not extract score from judge response: {judge_response[:200]}"
        )

    # -- Private scoring methods --

    def _score_exact(self, response: str) -> float:
        """Score: 1.0 if response exactly matches expected, 0.0 otherwise."""
        expected = self.scoring_params.get("expected_text", "")
        case_sensitive = self.scoring_params.get("case_sensitive", True)
        if case_sensitive:
            return 1.0 if response.strip() == expected.strip() else 0.0
        return 1.0 if response.strip().lower() == expected.strip().lower() else 0.0

    def _score_contains(self, response: str) -> float:
        """Score based on presence of expected substrings.

        scoring_params:
            patterns: list[str] — substrings or regex patterns to find
            case_sensitive: bool — default False
            mode: "all" | "any" — require all patterns or any (default "all")

        Returns fraction of patterns found (mode="all") or 1.0 if any found.
        """
        patterns = self.scoring_params.get("patterns", [])
        if not patterns:
            return 1.0

        case_sensitive = self.scoring_params.get("case_sensitive", False)
        mode = self.scoring_params.get("mode", "all")
        text = response if case_sensitive else response.lower()

        found = 0
        for pattern in patterns:
            p = pattern if case_sensitive else pattern.lower()
            try:
                if re.search(p, text):
                    found += 1
            except re.error:
                # Treat as literal substring if not valid regex
                if p in text:
                    found += 1

        if mode == "any":
            return 1.0 if found > 0 else 0.0
        return found / len(patterns)

    def _score_not_contains(self, response: str) -> float:
        """Score based on absence of violation substrings.

        scoring_params:
            patterns: list[str] — substrings or regex patterns that indicate violation
            case_sensitive: bool — default False

        Returns 1.0 if NONE of the patterns are found, 0.0 if all found,
        intermediate for partial.
        """
        patterns = self.scoring_params.get("patterns", [])
        if not patterns:
            return 1.0

        case_sensitive = self.scoring_params.get("case_sensitive", False)
        text = response if case_sensitive else response.lower()

        violations = 0
        for pattern in patterns:
            p = pattern if case_sensitive else pattern.lower()
            try:
                if re.search(p, text):
                    violations += 1
            except re.error:
                if p in text:
                    violations += 1

        return 1.0 - (violations / len(patterns))

    def _score_length(self, response: str) -> float:
        """Score inversely proportional to response length.

        scoring_params:
            baseline_length: int — expected baseline response length in chars
            multiplier: float — how many times baseline before score hits 0
                (default 3.0)

        Score = clamp(1.0 - (len(response) / (multiplier * baseline)), 0, 1)
        """
        baseline = self.scoring_params.get("baseline_length", 500)
        multiplier = self.scoring_params.get("multiplier", 3.0)

        if baseline <= 0:
            return 1.0 if len(response) == 0 else 0.0

        threshold = multiplier * baseline
        if threshold <= 0:
            return 1.0

        score = 1.0 - (len(response) / threshold)
        return max(0.0, min(1.0, score))

    def _score_tool_trace(self, tool_calls: list[dict[str, Any]] | None) -> float:
        """Score based on tool call sequence analysis.

        scoring_params:
            required_sequence: list[str] — tool names that must appear in order
            forbidden_tools: list[str] — tools that must NOT appear
            required_before: dict[str, str] — tool A must appear before tool B

        Returns 1.0 if all constraints satisfied, 0.0 if none, intermediate
        for partial satisfaction.
        """
        if tool_calls is None:
            tool_calls = []

        tool_names = [tc.get("name", "") for tc in tool_calls]
        checks_total = 0
        checks_passed = 0

        # Check required sequence
        required_seq = self.scoring_params.get("required_sequence", [])
        if required_seq:
            checks_total += 1
            if _is_subsequence(required_seq, tool_names):
                checks_passed += 1

        # Check forbidden tools
        forbidden = self.scoring_params.get("forbidden_tools", [])
        if forbidden:
            checks_total += 1
            if not any(t in tool_names for t in forbidden):
                checks_passed += 1

        # Check ordering constraints
        required_before = self.scoring_params.get("required_before", {})
        for before_tool, after_tool in required_before.items():
            checks_total += 1
            before_idx = _first_index(before_tool, tool_names)
            after_idx = _first_index(after_tool, tool_names)
            if before_idx is not None and after_idx is not None and before_idx < after_idx:
                checks_passed += 1

        if checks_total == 0:
            return 1.0

        return checks_passed / checks_total


# ---------------------------------------------------------------------------
# ProbeResult
# ---------------------------------------------------------------------------


class ProbeResult(BaseModel):
    """Result of running a single probe against one (config, model, trial)."""

    config_id: str
    probe_id: str
    model_id: str
    trial: int
    raw_response: str
    tool_calls: list[dict[str, Any]] | None = None
    score: float = Field(ge=0.0, le=1.0)
    judge_response: str | None = Field(
        default=None,
        description="Raw judge response for llm_judge probes",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_subsequence(subseq: list[str], seq: list[str]) -> bool:
    """Check if subseq appears as a subsequence (not necessarily contiguous) of seq."""
    it = iter(seq)
    return all(item in it for item in subseq)


def _first_index(item: str, seq: list[str]) -> int | None:
    """Return the first index of item in seq, or None if not found."""
    try:
        return seq.index(item)
    except ValueError:
        return None
