"""Tests for covering array generation — coverage property, constraints, edge cases.

Tests the contract specified in ablation_framework.md:
- generate_covering_array(n_factors, strength, constraints) -> list[list[int]]
- Every t-tuple of factors appears in all 2^t value combinations
- Constraints pin specific factors to fixed values
- load/save round-trip
"""

import json
import tempfile
from itertools import combinations
from pathlib import Path

import pytest

from arbiter.ablation.covering_array import (
    generate_covering_array,
    load_covering_array,
    save_covering_array,
    verify_coverage,
)


# --- Helpers ---


def verify_pairwise_coverage(array: list[list[int]], n_factors: int) -> bool:
    """Verify that every pair of factors appears in all 4 value combinations."""
    for i, j in combinations(range(n_factors), 2):
        seen = set()
        for row in array:
            seen.add((row[i], row[j]))
        if seen != {(0, 0), (0, 1), (1, 0), (1, 1)}:
            return False
    return True


def verify_t_coverage(array: list[list[int]], n_factors: int, strength: int) -> bool:
    """Verify that every t-tuple of factors appears in all 2^t value combinations."""
    for indices in combinations(range(n_factors), strength):
        seen = set()
        for row in array:
            seen.add(tuple(row[idx] for idx in indices))
        expected = 2 ** strength
        if len(seen) != expected:
            return False
    return True


# --- Basic generation tests ---


class TestCoveringArrayGeneration:
    def test_pairwise_coverage_small(self):
        """k=3, t=2: every pair of 3 factors in all 4 states."""
        array = generate_covering_array(n_factors=3, strength=2)
        assert verify_pairwise_coverage(array, 3)

    def test_pairwise_coverage_medium(self):
        """k=10, t=2: representative size."""
        array = generate_covering_array(n_factors=10, strength=2)
        assert verify_pairwise_coverage(array, 10)

    def test_pairwise_coverage_target_size(self):
        """k=23, t=2: the actual target size from the design doc."""
        array = generate_covering_array(n_factors=23, strength=2)
        assert verify_pairwise_coverage(array, 23)

    def test_all_values_binary(self):
        """Every cell must be 0 or 1."""
        array = generate_covering_array(n_factors=10, strength=2)
        for row in array:
            for val in row:
                assert val in (0, 1), f"Non-binary value: {val}"

    def test_row_length_matches_factors(self):
        """Each row has exactly n_factors entries."""
        n = 15
        array = generate_covering_array(n_factors=n, strength=2)
        for row in array:
            assert len(row) == n

    def test_returns_list_of_lists(self):
        """Return type is list[list[int]]."""
        array = generate_covering_array(n_factors=5, strength=2)
        assert isinstance(array, list)
        assert all(isinstance(row, list) for row in array)
        assert all(isinstance(val, int) for row in array for val in row)

    def test_reasonable_row_count_pairwise(self):
        """For k=23, t=2: design doc expects ~10-15 rows."""
        array = generate_covering_array(n_factors=23, strength=2)
        # Should be manageable — certainly under 100 rows
        assert len(array) >= 4  # minimum for pairwise coverage of 2 factors
        assert len(array) <= 50  # should be far fewer for pairwise


# --- Edge cases ---


class TestCoveringArrayEdgeCases:
    def test_single_factor(self):
        """k=1: trivially needs 2 rows (0 and 1)."""
        array = generate_covering_array(n_factors=1, strength=1)
        values = {row[0] for row in array}
        assert values == {0, 1}

    def test_two_factors_pairwise(self):
        """k=2, t=2: needs exactly 4 rows (all combinations)."""
        array = generate_covering_array(n_factors=2, strength=2)
        assert verify_pairwise_coverage(array, 2)
        # Must have at least 4 rows for full pairwise coverage
        assert len(array) >= 4

    def test_strength_one(self):
        """t=1: every factor appears in both states."""
        array = generate_covering_array(n_factors=5, strength=1)
        assert verify_t_coverage(array, 5, 1)
        # t=1 needs only 2 rows minimum
        assert len(array) >= 2

    def test_nonempty_result(self):
        """Should never return an empty array."""
        array = generate_covering_array(n_factors=3, strength=2)
        assert len(array) > 0


# --- Constraint tests ---


class TestCoveringArrayConstraints:
    def test_pinned_factor_always_one(self):
        """Constrained factor pinned to 1 must be 1 in every row."""
        constraints = {0: 1}
        array = generate_covering_array(n_factors=5, strength=2, constraints=constraints)
        for row in array:
            assert row[0] == 1, f"Constrained factor 0 should be 1, got {row[0]}"

    def test_pinned_factor_always_zero(self):
        """Constrained factor pinned to 0 must be 0 in every row."""
        constraints = {2: 0}
        array = generate_covering_array(n_factors=5, strength=2, constraints=constraints)
        for row in array:
            assert row[2] == 0, f"Constrained factor 2 should be 0, got {row[2]}"

    def test_multiple_pinned_factors(self):
        """Multiple constrained factors all respected."""
        constraints = {0: 1, 3: 0, 4: 1}
        array = generate_covering_array(n_factors=6, strength=2, constraints=constraints)
        for row in array:
            assert row[0] == 1
            assert row[3] == 0
            assert row[4] == 1

    def test_coverage_maintained_with_constraints(self):
        """Pairwise coverage of unconstrained factors still holds."""
        constraints = {0: 1}
        array = generate_covering_array(n_factors=5, strength=2, constraints=constraints)
        # Check pairwise coverage of unconstrained factors (1,2,3,4)
        unconstrained = [1, 2, 3, 4]
        for i, j in combinations(unconstrained, 2):
            seen = set()
            for row in array:
                seen.add((row[i], row[j]))
            assert seen == {(0, 0), (0, 1), (1, 0), (1, 1)}, (
                f"Unconstrained pair ({i}, {j}) missing combinations: "
                f"got {seen}"
            )

    def test_no_constraints_same_as_none(self):
        """constraints=None and constraints={} should behave the same."""
        array_none = generate_covering_array(n_factors=4, strength=2, constraints=None)
        assert verify_pairwise_coverage(array_none, 4)

        array_empty = generate_covering_array(n_factors=4, strength=2, constraints={})
        assert verify_pairwise_coverage(array_empty, 4)


# --- Persistence tests ---


class TestCoveringArrayPersistence:
    def test_save_and_load_round_trip(self):
        """Saving and loading should produce identical arrays."""
        array = generate_covering_array(n_factors=8, strength=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_array.json"
            save_covering_array(array, path)
            loaded = load_covering_array(path)
        assert loaded == array

    def test_save_creates_valid_json(self):
        """Saved file should be valid JSON."""
        array = generate_covering_array(n_factors=4, strength=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_array.json"
            save_covering_array(array, path)
            with open(path) as f:
                data = json.load(f)
            # Should be parseable; exact format is implementation detail
            assert data is not None

    def test_load_nonexistent_file_raises(self):
        """Loading from a nonexistent path should raise."""
        with pytest.raises(Exception):
            load_covering_array(Path("/nonexistent/path/array.json"))


class TestCoveringArrayValidation:
    def test_invalid_strength_raises(self):
        with pytest.raises(ValueError):
            generate_covering_array(n_factors=3, strength=0)

    def test_strength_greater_than_factors_raises(self):
        with pytest.raises(ValueError):
            generate_covering_array(n_factors=2, strength=3)

    def test_constraint_index_out_of_range_raises(self):
        with pytest.raises(ValueError):
            generate_covering_array(n_factors=3, strength=2, constraints={3: 1})

    def test_constraint_value_not_binary_raises(self):
        with pytest.raises(ValueError):
            generate_covering_array(n_factors=3, strength=2, constraints={1: 2})

    def test_verify_coverage_respects_constraints(self):
        array = generate_covering_array(n_factors=4, strength=2, constraints={0: 1})
        assert verify_coverage(array, n_factors=4, strength=2, constraints={0: 1})
