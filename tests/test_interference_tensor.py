"""Tests for interference tensor — shape, aggregation, extensibility, serialization."""

import json

import pytest

from arbiter.interference_tensor import InterferenceTensor, TensorEntry
from arbiter.prompt_blocks import Severity


# --- Fixtures ---


def _make_entries() -> list[TensorEntry]:
    """A small set of entries mimicking archaeology findings."""
    return [
        TensorEntry(
            block_a="claude-code/task-management-todowrite",
            block_b="claude-code/tool-bash-commit-restrictions",
            rule="mandate-prohibition-conflict",
            score=0.95,
            severity=Severity.critical,
            explanation="'Use VERY frequently' vs 'NEVER use'",
        ),
        TensorEntry(
            block_a="claude-code/tone-concise",
            block_b="claude-code/task-management-todowrite",
            rule="scope-overlap-redundancy",
            score=0.7,
            severity=Severity.major,
            explanation="Conciseness vs frequent task tracking output",
        ),
        TensorEntry(
            block_a="claude-code/security-policy",
            block_b="claude-code/security-policy-repeated",
            rule="verbatim-duplication",
            score=1.0,
            severity=Severity.minor,
            explanation="Identical security policy text at two locations",
        ),
        TensorEntry(
            block_a="claude-code/tool-policy-parallel-calls",
            block_b="claude-code/tool-bash-commit-workflow",
            rule="priority-marker-ambiguity",
            score=0.4,
            severity=Severity.minor,
            explanation="Both use escalating language about parallel execution",
        ),
    ]


@pytest.fixture
def tensor():
    block_ids = [
        "claude-code/task-management-todowrite",
        "claude-code/tool-bash-commit-restrictions",
        "claude-code/tone-concise",
        "claude-code/security-policy",
        "claude-code/security-policy-repeated",
        "claude-code/tool-policy-parallel-calls",
        "claude-code/tool-bash-commit-workflow",
    ]
    rule_names = [
        "mandate-prohibition-conflict",
        "scope-overlap-redundancy",
        "verbatim-duplication",
        "priority-marker-ambiguity",
    ]
    return InterferenceTensor.from_scores(
        block_ids=block_ids, rule_names=rule_names, entries=_make_entries()
    )


@pytest.fixture
def empty_tensor():
    return InterferenceTensor(block_ids=["a", "b"], rule_names=["r1"])


# --- Shape tests ---


class TestTensorShape:
    def test_shape(self, tensor):
        assert tensor.shape() == (7, 7, 4)

    def test_entry_count(self, tensor):
        assert len(tensor.entries) == 4

    def test_density(self, tensor):
        # 7 blocks, 4 rules → 7*6/2 * 4 = 84 possible; 4 entries
        assert tensor.density() == pytest.approx(4 / 84)

    def test_empty_density(self, empty_tensor):
        # 2 blocks, 1 rule → 1 possible; 0 entries
        assert empty_tensor.density() == 0.0


# --- Aggregation tests ---


class TestAggregation:
    def test_summary_score_max_weighted(self, tensor):
        # critical 0.95 * 1.0 = 0.95
        # major 0.7 * 0.6 = 0.42
        # minor 1.0 * 0.3 = 0.3
        # minor 0.4 * 0.3 = 0.12
        # max = 0.95
        assert tensor.summary_score() == pytest.approx(0.95)

    def test_summary_score_empty(self, empty_tensor):
        assert empty_tensor.summary_score() == 0.0

    def test_by_severity(self, tensor):
        grouped = tensor.by_severity()
        assert len(grouped[Severity.critical]) == 1
        assert len(grouped[Severity.major]) == 1
        assert len(grouped[Severity.minor]) == 2

    def test_by_rule(self, tensor):
        grouped = tensor.by_rule()
        assert "mandate-prohibition-conflict" in grouped
        assert len(grouped["mandate-prohibition-conflict"]) == 1
        assert len(grouped["verbatim-duplication"]) == 1

    def test_by_block(self, tensor):
        todowrite = tensor.by_block("claude-code/task-management-todowrite")
        assert len(todowrite) == 2  # appears in 2 entries

    def test_top_n(self, tensor):
        top = tensor.top_n(2)
        assert len(top) == 2
        # Highest weighted: critical 0.95 * 1.0 = 0.95
        assert top[0].severity == Severity.critical
        assert top[0].score == pytest.approx(0.95)

    def test_top_n_larger_than_entries(self, tensor):
        top = tensor.top_n(100)
        assert len(top) == 4


# --- Threshold filtering ---


class TestThresholdFiltering:
    def test_from_scores_with_threshold(self):
        entries = _make_entries()
        tensor = InterferenceTensor.from_scores(
            block_ids=["a", "b"],
            rule_names=["r1"],
            entries=entries,
            threshold=0.5,
        )
        # Only entries with score > 0.5 survive
        assert all(e.score > 0.5 for e in tensor.entries)
        assert len(tensor.entries) == 3  # 0.95, 0.7, 1.0 pass; 0.4 doesn't

    def test_from_scores_zero_threshold_keeps_all(self):
        entries = _make_entries()
        tensor = InterferenceTensor.from_scores(
            block_ids=["a"], rule_names=["r1"], entries=entries, threshold=0.0
        )
        assert len(tensor.entries) == 4


# --- Extensibility ---


class TestExtensibility:
    def test_adding_rule_extends_axis(self, tensor):
        """Adding a rule name extends axis 2 without invalidating existing entries."""
        old_shape = tensor.shape()
        old_entries = len(tensor.entries)

        tensor.rule_names.append("new-rule")
        new_entry = TensorEntry(
            block_a="claude-code/tone-concise",
            block_b="claude-code/tool-bash-commit-workflow",
            rule="new-rule",
            score=0.5,
            severity=Severity.major,
        )
        tensor.entries.append(new_entry)

        assert tensor.shape() == (old_shape[0], old_shape[1], old_shape[2] + 1)
        assert len(tensor.entries) == old_entries + 1

    def test_adding_block_extends_axes_0_1(self, tensor):
        """Adding a block ID extends axes 0 and 1."""
        tensor.block_ids.append("new-block")
        n, _, r = tensor.shape()
        assert tensor.shape() == (n, n, r)


# --- Serialization ---


class TestSerialization:
    def test_json_round_trip(self, tensor):
        json_str = tensor.to_json()
        data = json.loads(json_str)
        restored = InterferenceTensor(**data)
        assert restored.shape() == tensor.shape()
        assert len(restored.entries) == len(tensor.entries)

    def test_model_dump_round_trip(self, tensor):
        data = tensor.model_dump()
        restored = InterferenceTensor(**data)
        assert restored.summary_score() == pytest.approx(tensor.summary_score())

    def test_summary_report_nonempty(self, tensor):
        report = tensor.summary_report()
        assert "critical" in report
        assert "0.95" in report

    def test_summary_report_empty(self, empty_tensor):
        report = empty_tensor.summary_report()
        assert "No interference detected" in report
