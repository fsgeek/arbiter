"""Episodic memory for Arbiter — structured episodes with tensor anchors.

An episode is a situated record of something that happened: what the
context was, what went wrong or right, what was learned, and a small
tensor anchor that serves as a retrieval key. The anchor is cheap enough
to keep in working memory permanently. The full episode is retrieved
only when the anchor's interference signature matches the current situation.

This schema is designed to map onto Yanantin's existing primitives:
  Episode     → FactRecord (data dict, provider_id, timestamp)
  TensorAnchor → interference tensor dimensions (sparse floats)
  DeclaredLoss → DeclaredLoss (what_was_lost, why, category)

The JSON file store is a bootstrap backend. The production path is
Yanantin's ActivityStreamStore → ArangoDB.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class TensorAnchor(BaseModel):
    """Sparse retrieval key — a few floats encoding the shape of what happened.

    Dimensions are not predefined. Each episode declares the dimensions
    that matter to it. Retrieval matches on dimensional overlap, not
    exact equality. A future instance whose current situation has high
    provenance tension will match episodes that also had high provenance
    tension, regardless of what else they contain.
    """

    dimensions: dict[str, float] = Field(
        description="Dimension name → intensity (0.0-1.0). Sparse: only include relevant dimensions."
    )

    def similarity(self, other: TensorAnchor) -> float:
        """Cosine-like similarity over shared dimensions.

        Only dimensions present in both anchors contribute.
        Returns 0.0 if no shared dimensions.
        """
        shared = set(self.dimensions) & set(other.dimensions)
        if not shared:
            return 0.0
        dot = sum(self.dimensions[d] * other.dimensions[d] for d in shared)
        mag_self = sum(self.dimensions[d] ** 2 for d in shared) ** 0.5
        mag_other = sum(other.dimensions[d] ** 2 for d in shared) ** 0.5
        if mag_self == 0 or mag_other == 0:
            return 0.0
        return dot / (mag_self * mag_other)


class DeclaredLoss(BaseModel):
    """What was dropped from the episode summary and why.

    Maps to Yanantin's DeclaredLoss model. Honest loss tracking —
    the next instance knows what it's NOT getting.
    """

    what: str
    why: str


class Episode(BaseModel):
    """A situated record of something that happened.

    Not a fact. Not a rule. An episode: actors, actions, consequences,
    corrections. The tensor anchor is the retrieval key. The narrative
    is the human-readable context. The consequences are what makes it
    load-bearing.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    session: str = Field(description="Session identifier (e.g. 'session-10')")
    anchor: TensorAnchor
    title: str = Field(description="Short title for the episode")
    narrative: str = Field(
        description="What happened, in enough detail to reconstruct the situation"
    )
    actors: list[str] = Field(
        default_factory=list,
        description="Who was involved (e.g. 'opus-4.6-instance', 'independent-reviewer', 'tony')",
    )
    consequences: list[str] = Field(
        default_factory=list,
        description="What resulted — the load-bearing outcomes",
    )
    corrections: list[str] = Field(
        default_factory=list,
        description="What was wrong initially and how it was fixed",
    )
    declared_losses: list[DeclaredLoss] = Field(
        default_factory=list,
        description="What this summary drops and why",
    )
    related_artifacts: list[str] = Field(
        default_factory=list,
        description="File paths, commit hashes, test names — concrete references",
    )


class EpisodeStore:
    """JSON-file-backed episode store. Bootstrap backend.

    Production path: replace with Yanantin's ActivityStreamStore
    writing FactRecords to ArangoDB via ApachetaInterface.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]")

    def _load(self) -> list[dict]:
        return json.loads(self._path.read_text())

    def _save(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2))

    def store(self, episode: Episode) -> None:
        """Append an episode to the store."""
        data = self._load()
        data.append(episode.model_dump())
        self._save(data)

    def all(self) -> list[Episode]:
        """Load all episodes."""
        return [Episode(**d) for d in self._load()]

    def retrieve(self, query: TensorAnchor, *, threshold: float = 0.3) -> list[Episode]:
        """Retrieve episodes whose anchor matches the query above threshold.

        Returns episodes sorted by similarity, descending.
        """
        episodes = self.all()
        scored = [
            (ep, ep.anchor.similarity(query))
            for ep in episodes
        ]
        matched = [(ep, score) for ep, score in scored if score >= threshold]
        matched.sort(key=lambda x: -x[1])
        return [ep for ep, _ in matched]

    def retrieve_by_dimension(self, dimension: str, *, threshold: float = 0.5) -> list[Episode]:
        """Retrieve episodes with high intensity on a specific dimension."""
        episodes = self.all()
        matched = [
            ep for ep in episodes
            if ep.anchor.dimensions.get(dimension, 0.0) >= threshold
        ]
        matched.sort(
            key=lambda ep: -ep.anchor.dimensions.get(dimension, 0.0)
        )
        return matched
