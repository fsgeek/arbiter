"""Ablation configuration — build system prompts from block subsets.

Each AblationConfig specifies which blocks to include/exclude and how to
assemble the resulting system prompt. Phase-specific builders generate
the full set of configurations for each experimental phase.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..prompt_blocks import PromptBlock, PromptCorpus


# ---------------------------------------------------------------------------
# Padding generators for Phase 2
# ---------------------------------------------------------------------------


def _whitespace_padding(text: str) -> str:
    """Generate whitespace of approximately equal length to the input text.

    Uses newlines and spaces to roughly match the original text's
    visual footprint and approximate token count.
    """
    # Rough heuristic: 1 token ~ 4 chars for English text
    n_chars = len(text)
    # Mix of newlines and spaces to fill the space
    n_lines = max(1, n_chars // 80)
    chars_per_line = n_chars // n_lines
    return "\n".join(" " * chars_per_line for _ in range(n_lines))


# Semantically inert filler paragraphs from unrelated domains
_FILLER_PARAGRAPHS: list[str] = [
    (
        "The formation of sedimentary rock layers occurs through the gradual "
        "accumulation of mineral particles deposited by wind and water. Over "
        "geological time scales, these layers compact under pressure and "
        "undergo lithification to form distinct strata visible in exposed "
        "cliff faces and canyon walls."
    ),
    (
        "Traditional bread-making involves mixing flour, water, salt, and "
        "yeast to form a dough that must be kneaded until the gluten network "
        "develops sufficient elasticity. The fermentation process produces "
        "carbon dioxide gas, which causes the dough to rise and creates the "
        "characteristic open crumb structure."
    ),
    (
        "The migration patterns of Arctic terns represent one of the longest "
        "annual journeys in the animal kingdom. These birds travel from their "
        "Arctic breeding grounds to Antarctic feeding areas and back, covering "
        "roughly 70,000 kilometers each year along coastal and oceanic routes."
    ),
    (
        "The construction of Roman aqueducts required precise engineering "
        "calculations to maintain a consistent gradient over long distances. "
        "The Pont du Gard in southern France stands as one of the best-preserved "
        "examples, with its three tiers of arches spanning the Gardon River "
        "valley at a height of nearly fifty meters."
    ),
    (
        "Cotton cultivation requires a long growing season with adequate "
        "moisture during early growth and dry conditions at harvest time. "
        "The bolls open to reveal the white fibrous material that has been "
        "a primary textile crop since ancient civilizations in the Indus "
        "Valley first domesticated the plant."
    ),
    (
        "The crystalline structure of quartz consists of silicon and oxygen "
        "atoms arranged in a continuous framework of SiO4 tetrahedra. Each "
        "oxygen atom is shared between two tetrahedra, giving an overall "
        "chemical formula of SiO2. This mineral is the second most abundant "
        "in Earth's continental crust."
    ),
    (
        "Fermentation of grape juice into wine involves the conversion of "
        "sugars by yeast into ethanol and carbon dioxide. The specific "
        "strain of yeast, ambient temperature, and sugar concentration all "
        "influence the resulting flavor profile and alcohol content of the "
        "finished wine."
    ),
    (
        "The orbital mechanics of binary star systems follow Kepler's laws "
        "of planetary motion, with both stars orbiting their common center "
        "of mass. The period and eccentricity of the orbit depend on the "
        "masses of the component stars and the total energy of the system."
    ),
]


def _semantic_padding(text: str, seed: int = 0) -> str:
    """Generate semantically inert text of approximately equal length.

    Uses filler paragraphs from unrelated domains (geology, cooking,
    biology, history) to preserve attentional load while removing
    instruction-relevant content.

    Args:
        text: Original block text to match in length.
        seed: Random seed for reproducible paragraph selection.

    Returns:
        Filler text of approximately equal character length.
    """
    target_len = len(text)
    rng = random.Random(seed)

    # Shuffle and cycle through paragraphs
    paragraphs = list(_FILLER_PARAGRAPHS)
    rng.shuffle(paragraphs)

    result_parts: list[str] = []
    current_len = 0
    idx = 0

    while current_len < target_len:
        para = paragraphs[idx % len(paragraphs)]
        result_parts.append(para)
        current_len += len(para) + 1  # +1 for newline
        idx += 1

    result = "\n\n".join(result_parts)
    # Trim to approximately target length
    if len(result) > target_len * 1.2:
        result = result[: int(target_len * 1.1)]

    return result


# ---------------------------------------------------------------------------
# AblationConfig
# ---------------------------------------------------------------------------


class AblationConfig(BaseModel):
    """A specific block configuration for an ablation experiment."""

    id: str = Field(description="Unique config identifier, e.g. 'phase0-block5-removed'")
    phase: Literal["baseline", "phase0", "phase1", "phase2", "phase3"]
    present_blocks: list[str] = Field(description="Block IDs included in this config")
    absent_blocks: list[str] = Field(description="Block IDs removed from this config")
    padding: dict[str, str] | None = Field(
        default=None,
        description="Block ID -> padding text (Phase 2 only)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., covering array row index, condition)",
    )

    def assemble_prompt(self, corpus: PromptCorpus) -> str:
        """Build the system prompt for this configuration.

        Concatenates text of present blocks in original corpus order.
        For Phase 2 configs, inserts padding text where blocks were removed.

        Args:
            corpus: The prompt corpus containing all blocks.

        Returns:
            The assembled system prompt string.

        Raises:
            ValueError: If a block ID in present_blocks or absent_blocks
                is not found in the corpus.
        """
        corpus_index: dict[str, PromptBlock] = {b.id: b for b in corpus.blocks}

        # Validate all referenced block IDs exist
        for block_id in self.present_blocks + self.absent_blocks:
            if block_id not in corpus_index:
                raise ValueError(
                    f"Block {block_id!r} not found in corpus {corpus.name!r}. "
                    f"Available: {sorted(corpus_index.keys())}"
                )

        parts: list[str] = []

        # Iterate in corpus order to preserve original block positions
        for block in corpus.blocks:
            if block.id in self.present_blocks:
                parts.append(block.text)
            elif block.id in self.absent_blocks and self.padding:
                padding_text = self.padding.get(block.id)
                if padding_text is not None:
                    parts.append(padding_text)
                # else: block is absent with no padding — omit entirely

        return "\n\n".join(parts)

    def prompt_hash(self, corpus: PromptCorpus) -> str:
        """SHA-256 hash of the assembled prompt, for caching/deduplication."""
        prompt = self.assemble_prompt(corpus)
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Phase config builders
# ---------------------------------------------------------------------------


def _validate_block_partition(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> None:
    """Validate that free and constrained blocks are valid and non-overlapping.

    Raises:
        ValueError: If validation fails.
    """
    corpus_ids = {b.id for b in corpus.blocks}

    for block_id in free_block_ids:
        if block_id not in corpus_ids:
            raise ValueError(
                f"Free block {block_id!r} not found in corpus {corpus.name!r}"
            )

    for block_id in constrained_block_ids:
        if block_id not in corpus_ids:
            raise ValueError(
                f"Constrained block {block_id!r} not found in corpus {corpus.name!r}"
            )

    overlap = set(free_block_ids) & set(constrained_block_ids)
    if overlap:
        raise ValueError(
            f"Blocks appear in both free and constrained lists: {sorted(overlap)}"
        )


def _all_block_ids(corpus: PromptCorpus) -> list[str]:
    """All block IDs in corpus order."""
    return [b.id for b in corpus.blocks]


def _baseline_present(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> list[str]:
    """Block IDs that are present in the baseline (all blocks)."""
    all_ids = set(free_block_ids) | set(constrained_block_ids)
    # Return in corpus order
    return [b.id for b in corpus.blocks if b.id in all_ids]


def build_baseline_config(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> AblationConfig:
    """Build the baseline configuration (all blocks present)."""
    _validate_block_partition(corpus, free_block_ids, constrained_block_ids)

    present = _baseline_present(corpus, free_block_ids, constrained_block_ids)
    return AblationConfig(
        id="baseline",
        phase="baseline",
        present_blocks=present,
        absent_blocks=[],
    )


def build_phase0_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> list[AblationConfig]:
    """Build Phase 0 configs: one config per free block removed, plus baseline.

    Returns:
        List of AblationConfigs. First element is baseline, followed by
        one config per free block with that block removed.
    """
    _validate_block_partition(corpus, free_block_ids, constrained_block_ids)

    configs: list[AblationConfig] = []

    # Baseline
    configs.append(
        build_baseline_config(corpus, free_block_ids, constrained_block_ids)
    )

    # One config per free block removed
    for block_id in free_block_ids:
        present = constrained_block_ids + [
            bid for bid in free_block_ids if bid != block_id
        ]
        # Maintain corpus order
        corpus_order = [b.id for b in corpus.blocks]
        present_ordered = [bid for bid in corpus_order if bid in set(present)]

        configs.append(
            AblationConfig(
                id=f"phase0-{block_id}-removed",
                phase="phase0",
                present_blocks=present_ordered,
                absent_blocks=[block_id],
                metadata={"removed_block": block_id},
            )
        )

    return configs


def build_phase1_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
    covering_array: list[list[int]],
) -> list[AblationConfig]:
    """Build Phase 1 configs from a covering array.

    Each row of the covering array is a binary vector over free_block_ids.
    1 = block present, 0 = block absent.

    Args:
        corpus: The prompt corpus.
        free_block_ids: Block IDs that can be toggled.
        constrained_block_ids: Block IDs always present.
        covering_array: List of binary vectors, each of length len(free_block_ids).

    Returns:
        List of AblationConfigs, one per covering array row.

    Raises:
        ValueError: If covering array dimensions don't match free_block_ids.
    """
    _validate_block_partition(corpus, free_block_ids, constrained_block_ids)

    if covering_array and len(covering_array[0]) != len(free_block_ids):
        raise ValueError(
            f"Covering array has {len(covering_array[0])} columns but "
            f"there are {len(free_block_ids)} free blocks"
        )

    corpus_order = [b.id for b in corpus.blocks]
    configs: list[AblationConfig] = []

    for row_idx, row in enumerate(covering_array):
        present_free = [
            bid for bid, val in zip(free_block_ids, row) if val == 1
        ]
        absent_free = [
            bid for bid, val in zip(free_block_ids, row) if val == 0
        ]
        present = set(constrained_block_ids) | set(present_free)
        present_ordered = [bid for bid in corpus_order if bid in present]

        configs.append(
            AblationConfig(
                id=f"phase1-row{row_idx:03d}",
                phase="phase1",
                present_blocks=present_ordered,
                absent_blocks=absent_free,
                metadata={
                    "covering_array_row": row_idx,
                    "row_vector": row,
                },
            )
        )

    return configs


def build_phase2_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> list[AblationConfig]:
    """Build Phase 2 configs: position controls for each free block.

    For each free block, creates two configs:
    - Condition A (whitespace padding): block replaced with whitespace
    - Condition B (semantic padding): block replaced with inert filler text

    Both conditions preserve positional structure. Condition B also
    preserves attentional load.

    Returns:
        List of AblationConfigs, two per free block (whitespace + semantic).
    """
    _validate_block_partition(corpus, free_block_ids, constrained_block_ids)

    corpus_index: dict[str, PromptBlock] = {b.id: b for b in corpus.blocks}
    corpus_order = [b.id for b in corpus.blocks]
    configs: list[AblationConfig] = []

    for i, block_id in enumerate(free_block_ids):
        block = corpus_index[block_id]
        present_free = [bid for bid in free_block_ids if bid != block_id]
        present = set(constrained_block_ids) | set(present_free)
        # Include the padded block's ID in present since padding replaces it
        present_ordered = [bid for bid in corpus_order if bid in present]

        # Condition A: whitespace padding
        ws_padding = _whitespace_padding(block.text)
        configs.append(
            AblationConfig(
                id=f"phase2-{block_id}-whitespace",
                phase="phase2",
                present_blocks=present_ordered,
                absent_blocks=[block_id],
                padding={block_id: ws_padding},
                metadata={
                    "removed_block": block_id,
                    "condition": "whitespace",
                    "padding_length": len(ws_padding),
                    "original_length": len(block.text),
                },
            )
        )

        # Condition B: semantic padding
        sem_padding = _semantic_padding(block.text, seed=i)
        configs.append(
            AblationConfig(
                id=f"phase2-{block_id}-semantic",
                phase="phase2",
                present_blocks=present_ordered,
                absent_blocks=[block_id],
                padding={block_id: sem_padding},
                metadata={
                    "removed_block": block_id,
                    "condition": "semantic",
                    "padding_length": len(sem_padding),
                    "original_length": len(block.text),
                },
            )
        )

    return configs


def build_phase3_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
    removal_counts: list[int] | None = None,
    samples_per_count: int = 5,
    seed: int = 42,
) -> list[AblationConfig]:
    """Build Phase 3 configs: response surface mapping.

    Tests at multiple removal counts to map the non-monotonic response
    surface predicted by Baxi's U-curve.

    Args:
        corpus: The prompt corpus.
        free_block_ids: Block IDs that can be toggled.
        constrained_block_ids: Block IDs always present.
        removal_counts: Number of blocks to remove at each level.
            Default: [1, 5, 10, 15, 20] (capped at len(free_block_ids)).
        samples_per_count: Random subsets per removal count.
        seed: Random seed for reproducibility.

    Returns:
        List of AblationConfigs.
    """
    _validate_block_partition(corpus, free_block_ids, constrained_block_ids)

    if removal_counts is None:
        removal_counts = [1, 5, 10, 15, 20]

    # Cap removal counts at the number of free blocks
    removal_counts = [min(c, len(free_block_ids)) for c in removal_counts]

    corpus_order = [b.id for b in corpus.blocks]
    rng = random.Random(seed)
    configs: list[AblationConfig] = []

    for count in removal_counts:
        for sample_idx in range(samples_per_count):
            removed = rng.sample(free_block_ids, count)
            removed_set = set(removed)
            present_free = [bid for bid in free_block_ids if bid not in removed_set]
            present = set(constrained_block_ids) | set(present_free)
            present_ordered = [bid for bid in corpus_order if bid in present]

            configs.append(
                AblationConfig(
                    id=f"phase3-remove{count}-sample{sample_idx:02d}",
                    phase="phase3",
                    present_blocks=present_ordered,
                    absent_blocks=sorted(removed),
                    metadata={
                        "removal_count": count,
                        "sample_index": sample_idx,
                        "seed": seed,
                    },
                )
            )

    return configs
