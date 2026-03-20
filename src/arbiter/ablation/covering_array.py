"""Covering array generation — combinatorial test design for ablation experiments.

A covering array CA(N; t, k, v) is an N x k array over v symbols such that
every t-column sub-array contains all v^t possible rows at least once.

For ablation: k = number of free blocks, v = 2 (present/absent), t = 2
(pairwise coverage). This guarantees every pair of blocks appears in all
four states (both-present, both-absent, A-only, B-only).

Uses allpairspy if available; falls back to a greedy generator.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path


def generate_covering_array(
    n_factors: int,
    strength: int = 2,
    constraints: dict[int, int] | None = None,
) -> list[list[int]]:
    """Generate a covering array CA(N; t, k, 2).

    Args:
        n_factors: Number of binary factors (free blocks).
        strength: Interaction strength to cover (2=pairwise).
        constraints: Factor indices pinned to specific values.
            These factors are fixed in every row.

    Returns:
        List of configurations. Each configuration is a list of 0/1
        values, one per factor. Length of outer list is N (number of
        test configurations).

    Guarantees:
        Every t-tuple of factors appears in all 2^t value combinations
        across the returned configurations.

    Raises:
        ValueError: If n_factors < strength or strength < 1.
    """
    if strength < 1:
        raise ValueError(f"Strength must be >= 1, got {strength}")
    if n_factors < strength:
        raise ValueError(
            f"Need at least {strength} factors for strength-{strength} "
            f"coverage, got {n_factors}"
        )
    constraints = constraints or {}

    # Validate constraints
    for idx, val in constraints.items():
        if not (0 <= idx < n_factors):
            raise ValueError(f"Constraint index {idx} out of range [0, {n_factors})")
        if val not in (0, 1):
            raise ValueError(f"Constraint value must be 0 or 1, got {val}")

    # Try allpairspy first
    array = _try_allpairspy(n_factors, strength, constraints)
    if array is not None:
        return array

    # Fall back to greedy generator
    return _greedy_covering_array(n_factors, strength, constraints)


def _try_allpairspy(
    n_factors: int,
    strength: int,
    constraints: dict[int, int],
) -> list[list[int]] | None:
    """Attempt to use allpairspy for covering array generation."""
    try:
        from allpairspy import AllPairs  # type: ignore[import-untyped]
    except ImportError:
        return None

    # allpairspy only supports pairwise (strength=2)
    if strength != 2:
        return None

    # Build parameter lists: constrained factors get single-value lists
    parameters: list[list[int]] = []
    for i in range(n_factors):
        if i in constraints:
            parameters.append([constraints[i]])
        else:
            parameters.append([0, 1])

    rows: list[list[int]] = []
    for row in AllPairs(parameters):
        rows.append(list(row))

    # Verify coverage (allpairspy should guarantee it, but fail-stop)
    if not verify_coverage(rows, n_factors, strength, constraints):
        # allpairspy failed to cover — fall back to greedy
        return None

    return rows


def _greedy_covering_array(
    n_factors: int,
    strength: int,
    constraints: dict[int, int],
) -> list[list[int]]:
    """Greedy covering array generator (IPOG-like).

    For binary factors with pairwise strength, this is straightforward:
    greedily add rows that cover the most uncovered tuples.

    For higher strengths, the same greedy approach works but is less
    optimal. This is acceptable — the array will be correct (all tuples
    covered) but may have more rows than a theoretically minimal array.
    """
    # Identify free (unconstrained) factor indices
    free_indices = [i for i in range(n_factors) if i not in constraints]

    # Build the set of all t-tuples that need coverage.
    # Each tuple is (factor_indices, value_tuple) where both are sorted
    # by factor index.
    uncovered: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()

    for combo in combinations(free_indices, strength):
        # All possible value assignments for this factor combination
        for vals in _binary_tuples(strength):
            uncovered.add((combo, vals))

    # Also need tuples involving constrained factors paired with free ones.
    # Constrained factors are pinned, so only achievable value combinations
    # are included (the constrained factor's value is fixed).
    constrained_indices = sorted(constraints.keys())
    for t_size in range(1, strength):
        # t_size constrained factors + (strength - t_size) free factors
        for c_combo in combinations(constrained_indices, t_size):
            free_needed = strength - t_size
            if free_needed > len(free_indices):
                continue
            for f_combo in combinations(free_indices, free_needed):
                all_factors = tuple(sorted(c_combo + f_combo))
                # Only the free factors vary; constrained are fixed
                for free_vals in _binary_tuples(free_needed):
                    # Build the full value tuple in factor order
                    vals_list: list[int] = []
                    fi = 0  # index into f_combo
                    for factor in all_factors:
                        if factor in constraints:
                            vals_list.append(constraints[factor])
                        else:
                            vals_list.append(free_vals[fi])
                            fi += 1
                    uncovered.add((all_factors, tuple(vals_list)))

    # Note: constrained-constrained pairs are NOT added because they
    # have only one achievable value combination (both pinned), which
    # is trivially covered by every row.

    rows: list[list[int]] = []

    while uncovered:
        best_row: list[int] | None = None
        best_count = -1

        # Try a set of candidate rows and pick the one covering most uncovered tuples
        candidates = _generate_candidates(n_factors, free_indices, constraints)

        for candidate in candidates:
            covered = _count_covered(candidate, uncovered, strength)
            if covered > best_count:
                best_count = covered
                best_row = candidate

        if best_row is None or best_count == 0:
            # Should not happen if algorithm is correct — fail-stop
            raise RuntimeError(
                f"Greedy covering array stuck with {len(uncovered)} uncovered tuples. "
                f"This is a bug in the covering array generator."
            )

        rows.append(best_row)
        # Remove covered tuples
        _remove_covered(best_row, uncovered, strength)

    return rows


def _binary_tuples(n: int) -> list[tuple[int, ...]]:
    """All binary tuples of length n."""
    if n == 0:
        return [()]
    result: list[tuple[int, ...]] = []
    for i in range(2**n):
        t = tuple((i >> bit) & 1 for bit in range(n - 1, -1, -1))
        result.append(t)
    return result


def _generate_candidates(
    n_factors: int,
    free_indices: list[int],
    constraints: dict[int, int],
) -> list[list[int]]:
    """Generate candidate rows for the greedy search.

    For small factor counts (< 20 free factors), enumerate all 2^k
    possibilities. For larger counts, use random sampling + structured
    candidates (all-zeros, all-ones, single-flips).
    """
    import random

    n_free = len(free_indices)

    if n_free <= 18:
        # Enumerate all possibilities
        candidates: list[list[int]] = []
        for i in range(2**n_free):
            row = [0] * n_factors
            # Set constrained values
            for idx, val in constraints.items():
                row[idx] = val
            # Set free values from bit pattern
            for bit_pos, factor_idx in enumerate(reversed(free_indices)):
                row[factor_idx] = (i >> bit_pos) & 1
            candidates.append(row)
        return candidates

    # For large factor counts, sample
    candidates = []
    n_samples = min(10000, 2**n_free)

    # Always include all-zeros and all-ones (for free factors)
    for base_val in (0, 1):
        row = [0] * n_factors
        for idx, val in constraints.items():
            row[idx] = val
        for idx in free_indices:
            row[idx] = base_val
        candidates.append(row)

    # Random samples
    for _ in range(n_samples):
        row = [0] * n_factors
        for idx, val in constraints.items():
            row[idx] = val
        for idx in free_indices:
            row[idx] = random.randint(0, 1)
        candidates.append(row)

    return candidates


def _count_covered(
    row: list[int],
    uncovered: set[tuple[tuple[int, ...], tuple[int, ...]]],
    strength: int,
) -> int:
    """Count how many uncovered tuples this row covers."""
    count = 0
    for factors, vals in uncovered:
        if all(row[factors[i]] == vals[i] for i in range(strength)):
            count += 1
    return count


def _remove_covered(
    row: list[int],
    uncovered: set[tuple[tuple[int, ...], tuple[int, ...]]],
    strength: int,
) -> None:
    """Remove tuples covered by this row from the uncovered set."""
    to_remove: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for factors, vals in uncovered:
        if all(row[factors[i]] == vals[i] for i in range(strength)):
            to_remove.append((factors, vals))
    for item in to_remove:
        uncovered.discard(item)


def verify_coverage(
    array: list[list[int]],
    n_factors: int,
    strength: int,
    constraints: dict[int, int] | None = None,
) -> bool:
    """Verify that a covering array has complete t-way coverage.

    Args:
        array: The covering array to verify.
        n_factors: Number of factors.
        strength: Required interaction strength.
        constraints: Factor indices pinned to specific values. When
            constraints are present, only achievable value combinations
            are required for tuples involving constrained factors.

    Returns:
        True if every t-tuple of factors has all achievable value
        combinations present in the array.
    """
    if not array:
        return n_factors == 0

    constraints = constraints or {}

    for combo in combinations(range(n_factors), strength):
        # Determine which value combinations are achievable for this tuple
        expected: set[tuple[int, ...]] = set()
        for vals in _binary_tuples(strength):
            achievable = True
            for idx, val in zip(combo, vals):
                if idx in constraints and constraints[idx] != val:
                    achievable = False
                    break
            if achievable:
                expected.add(vals)

        if not expected:
            # All-constrained tuple with single achievable value — trivially covered
            continue

        # Collect all value tuples seen for this factor combination
        seen: set[tuple[int, ...]] = set()
        for row in array:
            vals_tuple = tuple(row[i] for i in combo)
            seen.add(vals_tuple)

        if not expected.issubset(seen):
            return False

    return True


def load_covering_array(path: Path) -> list[list[int]]:
    """Load a pre-generated covering array from JSON.

    Expected format:
        {
            "n_factors": int,
            "strength": int,
            "array": [[0, 1, ...], ...],
            "metadata": {...}
        }

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If the file format is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Covering array file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    if "array" not in data:
        raise ValueError(f"Covering array file missing 'array' key: {path}")

    array = data["array"]
    if not isinstance(array, list) or (array and not isinstance(array[0], list)):
        raise ValueError(f"Invalid array format in {path}: expected list of lists")

    return array


def save_covering_array(
    array: list[list[int]],
    path: Path,
    *,
    n_factors: int | None = None,
    strength: int = 2,
    metadata: dict | None = None,
) -> None:
    """Save a covering array to JSON with metadata.

    Args:
        array: The covering array.
        path: Output file path.
        n_factors: Number of factors (inferred from array if not given).
        strength: Interaction strength.
        metadata: Additional metadata to include.
    """
    if n_factors is None and array:
        n_factors = len(array[0])

    data = {
        "n_factors": n_factors,
        "strength": strength,
        "n_configurations": len(array),
        "array": array,
        "metadata": metadata or {},
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
