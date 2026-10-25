"""GriceReport — the whole corpus scored, with the notes that qualify it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores


@dataclass(frozen=True)
class GriceReport:
    """The corpus-wide result of a Grice scan.

    Carries the disqualifying context next to the numbers rather than in the
    tool's stdout, because a percentile computed over four documents is not the
    same measurement as one computed over sixty. A reader who receives only the
    indices cannot tell the two apart, so :attr:`notes` always travels with
    them.

    Attributes:
        documents: One row per document, sorted by path.
        findings: Corpus-independent defects — broken links, unresolved
            references, skipped heading levels. Kept separate from the indices
            because a defect is actionable where a relative rank is not.
        disabled_metrics: Metrics that did not run, with the reason as the
            value's spelling (currently the English-only ones).
        notes: Human-readable caveats about the corpus this scan measured.

    """

    documents: tuple[MaximScores, ...]
    findings: tuple[Finding, ...]
    disabled_metrics: tuple[str, ...]
    notes: tuple[str, ...]

    @property
    def corpus_size(self) -> int:
        """Return how many documents the scan scored.

        Returns:
            The number of scored documents.

        """
        return len(self.documents)

    @property
    def corpus_index(self) -> float | None:
        """Return the mean ``grice_index`` across the corpus.

        Returns:
            The 0-100 aggregate, or ``None`` when no document produced one.

        """
        measured = tuple(
            index for index in (row.grice_index for row in self.documents) if index is not None
        )
        if not measured:
            return None
        return sum(measured) / len(measured)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report for the JSON output.

        Returns:
            A mapping with the corpus size, the aggregate index, one row per
            document, the findings, and the caveats. The aggregate is rounded
            to one decimal place like every other index.

        """
        index = self.corpus_index
        return {
            "corpus_size": self.corpus_size,
            "corpus_index": GriceReport._round(index),
            "documents": [row.to_dict() for row in self.documents],
            "findings": [
                {
                    "file": finding.file,
                    "line": finding.line,
                    "category": finding.category,
                    "severity": finding.severity,
                    "description": finding.description,
                }
                for finding in self.findings
            ],
            "disabled_metrics": list(self.disabled_metrics),
            "notes": list(self.notes),
        }

    @staticmethod
    def _round(value: float | None) -> float | None:
        """Round *value* to one decimal, preserving ``None``.

        Args:
            value: The index to round, or ``None``.

        Returns:
            The rounded index, or ``None`` when nothing was measured.

        """
        if value is None:
            return None
        return round(value, 1)
