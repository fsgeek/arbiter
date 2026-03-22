"""Structural conflict detection for prompt block corpora.

Detects conflicts between prompt blocks using their annotated metadata
(scope, exports, imports, modality) without running any LLM. This is
the "compiler" layer that catches structural interference patterns.

The detected conflicts are empirically validated by cross-linguistic
ablation: the todowrite/commit-restrictions conflict produces the
highest cross-linguistic variance (0.157) and the strongest inter-model
inversion (Haiku en=1.0→zh=0.0, Gemini en=0.0→zh=1.0).

Reference: docs/research/instruction_fragility_taxonomy.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .prompt_blocks import (
    DetectionMethod,
    InterferencePattern,
    InterferenceType,
    Modality,
    PromptBlock,
    PromptCorpus,
    Severity,
)


# Negation patterns that indicate a prohibition in export names
_NEGATION_PREFIXES = ("no-", "never-", "not-", "dont-", "avoid-", "ban-", "disable-")
_AFFIRMATION_PREFIXES = ("use-", "always-", "require-", "must-", "enable-")


@dataclass
class ConflictReport:
    """Summary of detected structural conflicts in a corpus."""

    corpus_name: str
    conflicts: list[InterferencePattern] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def by_severity(self, severity: Severity) -> list[InterferencePattern]:
        return [c for c in self.conflicts if c.severity == severity]

    def summary(self) -> str:
        lines = [f"Conflict report for {self.corpus_name}:"]
        lines.append(f"  {len(self.conflicts)} conflicts detected")
        for sev in (Severity.critical, Severity.major, Severity.minor):
            n = len(self.by_severity(sev))
            if n:
                lines.append(f"    {sev.value}: {n}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


def _extract_referent(export_name: str) -> str | None:
    """Extract the core referent from an export name.

    'no-todowrite-during-commit' -> 'todowrite'
    'always-use-todowrite' -> 'todowrite'
    'use-todowrite-very-frequently' -> 'todowrite'
    """
    name = export_name.lower()
    # Strip negation/affirmation prefixes
    for prefix in _NEGATION_PREFIXES + _AFFIRMATION_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # Strip common suffixes
    for suffix in ("-during-commit", "-in-commits", "-very-frequently",
                   "-unless-asked", "-immediately"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name if name else None


def _is_negation(export_name: str) -> bool:
    """Does this export name express a prohibition?"""
    return any(export_name.lower().startswith(p) for p in _NEGATION_PREFIXES)


def _is_affirmation(export_name: str) -> bool:
    """Does this export name express a mandate?"""
    return any(export_name.lower().startswith(p) for p in _AFFIRMATION_PREFIXES)


def detect_export_contradictions(
    corpus: PromptCorpus,
) -> list[InterferencePattern]:
    """Find blocks that export contradictory claims about the same referent.

    Example: block A exports 'always-use-todowrite', block B exports
    'no-todowrite-during-commit'. Both reference 'todowrite' but with
    opposite polarity.
    """
    conflicts = []

    # Build referent -> [(block_id, export_name, is_negation)] map
    referent_map: dict[str, list[tuple[str, str, bool]]] = {}
    for block in corpus.blocks:
        for export in block.exports:
            referent = _extract_referent(export)
            if referent:
                entry = (block.id, export, _is_negation(export))
                referent_map.setdefault(referent, []).append(entry)

    # Check for polarity conflicts within same referent
    for referent, entries in referent_map.items():
        negations = [(bid, exp) for bid, exp, neg in entries if neg]
        affirmations = [(bid, exp) for bid, exp, neg in entries if not neg and _is_affirmation(exp)]

        for neg_bid, neg_exp in negations:
            for aff_bid, aff_exp in affirmations:
                if neg_bid == aff_bid:
                    continue  # Same block — internal tension, not inter-block conflict
                conflicts.append(
                    InterferencePattern(
                        block_a=aff_bid,
                        block_b=neg_bid,
                        type=InterferenceType.direct_contradiction,
                        description=(
                            f"Block '{aff_bid}' exports '{aff_exp}' (affirmation) "
                            f"while block '{neg_bid}' exports '{neg_exp}' (prohibition). "
                            f"Both reference '{referent}'."
                        ),
                        severity=Severity.major,
                        detection=DetectionMethod.static,
                        would_compiler_catch=True,
                        evidence=f"Affirmation: {aff_exp}, Prohibition: {neg_exp}",
                    )
                )

    return conflicts


def detect_scope_overlaps(
    corpus: PromptCorpus,
) -> list[InterferencePattern]:
    """Find blocks with overlapping scopes that have different modalities.

    A prohibition and a mandate in the same scope are potentially conflicting.
    """
    conflicts = []
    blocks = corpus.blocks

    for i, a in enumerate(blocks):
        for b in blocks[i + 1 :]:
            if not a.scopes_overlap(b):
                continue
            # Different modalities in overlapping scope → potential conflict
            if a.modality != b.modality and {a.modality, b.modality} & {
                Modality.prohibition,
                Modality.mandate,
            }:
                shared_scopes = sorted(set(a.scope) & set(b.scope))
                conflicts.append(
                    InterferencePattern(
                        block_a=a.id,
                        block_b=b.id,
                        type=InterferenceType.scope_overlap,
                        description=(
                            f"Blocks share scope {shared_scopes} with different modalities: "
                            f"'{a.id}' is {a.modality.value}, '{b.id}' is {b.modality.value}."
                        ),
                        severity=Severity.minor,
                        detection=DetectionMethod.static,
                        would_compiler_catch=True,
                    )
                )

    return conflicts


def detect_text_contradictions(
    corpus: PromptCorpus,
) -> list[InterferencePattern]:
    """Find blocks where one says NEVER/DO NOT about something another promotes.

    Scans for tool names mentioned in prohibition context in one block
    and promotion context in another.
    """
    conflicts = []

    # Extract tool-name mentions with polarity
    prohibition_re = re.compile(
        r"(?:NEVER|never|DO NOT|do not|Don't|don't|MUST NOT|must not|绝对不要|NE JAMAIS|NUNCA)\s+"
        r"(?:use|run|execute|utilizar?|usar?|使用|utiliser?)\s+"
        r"(?:the\s+)?(\w+)",
        re.IGNORECASE,
    )
    promotion_re = re.compile(
        r"(?:ALWAYS|always|MUST|must|Use|use|IMPORTANT.*use|使用|Utilisez|Utiliza)\s+"
        r"(?:the\s+)?(\w+)\s+(?:tool|工具|outil|herramienta|very frequently|for)",
        re.IGNORECASE,
    )

    prohibitions: dict[str, list[str]] = {}  # tool_name -> [block_ids]
    promotions: dict[str, list[str]] = {}

    for block in corpus.blocks:
        for match in prohibition_re.finditer(block.text):
            tool = match.group(1)
            prohibitions.setdefault(tool, []).append(block.id)
        for match in promotion_re.finditer(block.text):
            tool = match.group(1)
            promotions.setdefault(tool, []).append(block.id)

    # Cross-reference
    for tool in set(prohibitions) & set(promotions):
        for p_bid in prohibitions[tool]:
            for m_bid in promotions[tool]:
                if p_bid == m_bid:
                    continue
                conflicts.append(
                    InterferencePattern(
                        block_a=m_bid,
                        block_b=p_bid,
                        type=InterferenceType.direct_contradiction,
                        description=(
                            f"Block '{m_bid}' promotes use of '{tool}' "
                            f"while block '{p_bid}' prohibits it."
                        ),
                        severity=Severity.major,
                        detection=DetectionMethod.static,
                        would_compiler_catch=True,
                        evidence=f"Tool '{tool}' is both promoted and prohibited.",
                    )
                )

    return conflicts


def detect_conflicts(corpus: PromptCorpus) -> ConflictReport:
    """Run all structural conflict detectors on a corpus.

    Returns a ConflictReport with all detected conflicts and warnings.
    """
    report = ConflictReport(corpus_name=corpus.name)

    # Run detectors
    report.conflicts.extend(detect_export_contradictions(corpus))
    report.conflicts.extend(detect_scope_overlaps(corpus))
    report.conflicts.extend(detect_text_contradictions(corpus))

    # Deduplicate: same block pair with same type
    seen = set()
    deduped = []
    for c in report.conflicts:
        key = (frozenset([c.block_a, c.block_b]), c.type)
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    report.conflicts = deduped

    # Upgrade severity for empirically validated conflicts
    # (If a conflict is detected structurally AND confirmed by ablation data)
    # This is a hook for future integration with ablation results

    return report
