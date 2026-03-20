"""Tests for probe battery — validation, filtering, serialization.

Tests the contract specified in ablation_framework.md:
- ProbeBattery.validate() catches uncovered blocks
- ProbeBattery.probes_for_block() filters correctly
- load_battery/save_battery round-trip fidelity
"""

import json
import tempfile
from pathlib import Path

import pytest

from arbiter.ablation.battery import (
    ProbeBattery,
    load_battery,
    save_battery,
)
from arbiter.ablation.probe import Probe


# --- Helpers ---


def _make_probe(probe_id: str, target_block: str) -> Probe:
    return Probe(
        id=probe_id,
        target_block=target_block,
        user_message=f"Test message for {target_block}",
        scoring_method="contains",
        expected_behavior="Expected behavior",
        violation_indicator="Violation indicator",
        scoring_params={"pattern": "test"},
    )


@pytest.fixture
def full_battery():
    """Battery with probes covering blocks free-1 through free-4."""
    return ProbeBattery(
        probes=[
            _make_probe("probe-free1-01", "free-1"),
            _make_probe("probe-free1-02", "free-1"),
            _make_probe("probe-free2-01", "free-2"),
            _make_probe("probe-free3-01", "free-3"),
            _make_probe("probe-free4-01", "free-4"),
        ],
        metadata={"version": "1.0", "author": "test"},
    )


@pytest.fixture
def free_block_ids():
    return ["free-1", "free-2", "free-3", "free-4"]


# --- Validation tests ---


class TestBatteryValidation:
    def test_fully_covered_returns_empty(self, full_battery, free_block_ids):
        """When every free block has at least one probe, validate returns empty list."""
        uncovered = full_battery.validate(free_block_ids)
        assert uncovered == []

    def test_missing_block_detected(self, free_block_ids):
        """Battery missing probes for some blocks returns those block IDs."""
        partial_battery = ProbeBattery(
            probes=[
                _make_probe("probe-free1-01", "free-1"),
                _make_probe("probe-free3-01", "free-3"),
            ],
            metadata={"version": "1.0"},
        )
        uncovered = partial_battery.validate(free_block_ids)
        assert sorted(uncovered) == ["free-2", "free-4"]

    def test_empty_battery_returns_all_blocks(self, free_block_ids):
        """Empty battery means all blocks are uncovered."""
        empty = ProbeBattery(probes=[], metadata={"version": "1.0"})
        uncovered = empty.validate(free_block_ids)
        assert sorted(uncovered) == sorted(free_block_ids)

    def test_extra_probes_dont_cause_errors(self):
        """Probes targeting blocks not in free_block_ids are harmless."""
        battery = ProbeBattery(
            probes=[
                _make_probe("probe-free1-01", "free-1"),
                _make_probe("probe-extra-01", "extra-block"),
            ],
            metadata={"version": "1.0"},
        )
        uncovered = battery.validate(["free-1"])
        assert uncovered == []

    def test_empty_free_blocks_returns_empty(self, full_battery):
        """No free blocks to cover -> nothing uncovered."""
        uncovered = full_battery.validate([])
        assert uncovered == []


# --- probes_for_block tests ---


class TestProbesForBlock:
    def test_returns_matching_probes(self, full_battery):
        """probes_for_block returns only probes targeting that block."""
        probes = full_battery.probes_for_block("free-1")
        assert len(probes) == 2
        assert all(p.target_block == "free-1" for p in probes)

    def test_returns_single_probe(self, full_battery):
        """Block with one probe returns list of length 1."""
        probes = full_battery.probes_for_block("free-2")
        assert len(probes) == 1
        assert probes[0].target_block == "free-2"

    def test_nonexistent_block_returns_empty(self, full_battery):
        """Block with no probes returns empty list."""
        probes = full_battery.probes_for_block("nonexistent")
        assert probes == []

    def test_preserves_probe_identity(self, full_battery):
        """Returned probes should be the same objects (or equivalent)."""
        probes = full_battery.probes_for_block("free-4")
        assert len(probes) == 1
        assert probes[0].id == "probe-free4-01"


# --- Serialization tests ---


class TestBatterySerialization:
    def test_save_and_load_round_trip(self, full_battery):
        """Save then load produces equivalent battery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_battery.json"
            save_battery(full_battery, path)
            loaded = load_battery(path)

        assert len(loaded.probes) == len(full_battery.probes)
        for orig, loaded_probe in zip(full_battery.probes, loaded.probes):
            assert orig.id == loaded_probe.id
            assert orig.target_block == loaded_probe.target_block
            assert orig.scoring_method == loaded_probe.scoring_method

    def test_save_creates_valid_json(self, full_battery):
        """Saved file is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_battery.json"
            save_battery(full_battery, path)
            with open(path) as f:
                data = json.load(f)
            assert data is not None

    def test_metadata_preserved(self, full_battery):
        """Metadata survives serialization round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_battery.json"
            save_battery(full_battery, path)
            loaded = load_battery(path)
        assert loaded.metadata.get("version") == "1.0"

    def test_load_nonexistent_raises(self):
        """Loading from nonexistent path should raise."""
        with pytest.raises(Exception):
            load_battery(Path("/nonexistent/path/battery.json"))

    def test_round_trip_probe_scoring_params(self):
        """Scoring parameters survive serialization."""
        battery = ProbeBattery(
            probes=[
                Probe(
                    id="test-length",
                    target_block="block-1",
                    user_message="Explain decorators.",
                    scoring_method="length",
                    expected_behavior="Concise",
                    violation_indicator="Verbose",
                    scoring_params={"baseline_length": 150},
                ),
            ],
            metadata={"version": "2.0"},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "battery.json"
            save_battery(battery, path)
            loaded = load_battery(path)
        assert loaded.probes[0].scoring_params["baseline_length"] == 150


class TestBatteryAdditionalContracts:
    def test_validate_strict_raises_for_uncovered(self):
        battery = ProbeBattery(probes=[_make_probe("p1", "free-1")])
        with pytest.raises(ValueError):
            battery.validate_strict(["free-1", "free-2"])

    def test_probe_by_id_raises_for_missing(self, full_battery):
        with pytest.raises(KeyError):
            full_battery.probe_by_id("missing-id")

    def test_add_probe_rejects_duplicate_ids(self, full_battery):
        with pytest.raises(ValueError):
            full_battery.add_probe(_make_probe("probe-free1-01", "free-9"))

    def test_target_blocks_preserves_first_seen_order(self):
        battery = ProbeBattery(
            probes=[
                _make_probe("p1", "b"),
                _make_probe("p2", "a"),
                _make_probe("p3", "b"),
                _make_probe("p4", "c"),
            ]
        )
        assert battery.target_blocks == ["b", "a", "c"]
