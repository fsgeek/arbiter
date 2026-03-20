"""Probe battery management — validation, serialization, and querying.

A ProbeBattery is the full set of probes run against each configuration
in an ablation experiment. The battery ensures coverage (every free block
has at least one probe) and provides serialization for reproducibility.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .probe import Probe


class ProbeBattery(BaseModel):
    """A collection of probes for ablation experiments."""

    probes: list[Probe] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Version, creation date, author, etc.",
    )

    def probes_for_block(self, block_id: str) -> list[Probe]:
        """Return probes targeting a specific block.

        Args:
            block_id: The block ID to filter by.

        Returns:
            List of probes whose target_block matches block_id.
        """
        return [p for p in self.probes if p.target_block == block_id]

    def validate(self, free_block_ids: list[str]) -> list[str]:
        """Check that every free block has at least one probe.

        Args:
            free_block_ids: Block IDs that should have probe coverage.

        Returns:
            List of block IDs with no probes (should be empty for a
            complete battery).
        """
        covered = {p.target_block for p in self.probes}
        return [bid for bid in free_block_ids if bid not in covered]

    def validate_strict(self, free_block_ids: list[str]) -> None:
        """Validate and raise if any blocks lack probes.

        Raises:
            ValueError: If any free blocks have no probes.
        """
        uncovered = self.validate(free_block_ids)
        if uncovered:
            raise ValueError(
                f"Battery is incomplete: {len(uncovered)} free block(s) have no probes: "
                f"{uncovered}"
            )

    def probe_by_id(self, probe_id: str) -> Probe:
        """Look up a probe by its ID.

        Raises:
            KeyError: If no probe with this ID exists.
        """
        for p in self.probes:
            if p.id == probe_id:
                return p
        raise KeyError(
            f"No probe with id {probe_id!r}. "
            f"Available: {[p.id for p in self.probes]}"
        )

    def add_probe(self, probe: Probe) -> None:
        """Add a probe to the battery.

        Raises:
            ValueError: If a probe with this ID already exists.
        """
        existing_ids = {p.id for p in self.probes}
        if probe.id in existing_ids:
            raise ValueError(
                f"Probe with id {probe.id!r} already exists in battery"
            )
        self.probes.append(probe)

    @property
    def target_blocks(self) -> list[str]:
        """Unique block IDs targeted by probes, in first-seen order."""
        seen: set[str] = set()
        result: list[str] = []
        for p in self.probes:
            if p.target_block not in seen:
                seen.add(p.target_block)
                result.append(p.target_block)
        return result

    def __len__(self) -> int:
        return len(self.probes)


def load_battery(path: Path) -> ProbeBattery:
    """Load probe battery from JSON.

    Expected format matches ProbeBattery.model_dump() output.

    Args:
        path: Path to the JSON file.

    Returns:
        A ProbeBattery instance.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If the file format is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Battery file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    try:
        return ProbeBattery.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid battery file format in {path}: {e}") from e


def save_battery(battery: ProbeBattery, path: Path) -> None:
    """Save probe battery to JSON.

    Adds a save timestamp to metadata if not already present.

    Args:
        battery: The battery to save.
        path: Output file path.
    """
    # Add save timestamp
    if "saved_at" not in battery.metadata:
        battery.metadata["saved_at"] = datetime.now(timezone.utc).isoformat()

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(battery.model_dump_json(indent=2))
        f.write("\n")
