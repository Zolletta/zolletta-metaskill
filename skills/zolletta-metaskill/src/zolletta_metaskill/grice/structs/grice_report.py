"""GriceReport — the whole corpus scored, triaged, and the notes that qualify it."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.structs.grice_settings import GriceSettings
from zolletta_metaskill.grice.structs.group_summary import GroupSummary
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores
from zolletta_metaskill.grice.structs.structural_defect import StructuralDefect
from zolletta_metaskill.grice.structs.triage_entry import TriageEntry


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
        excluded_adrs: ADR files left out before normalisation, sorted.
        groups: One Executive Summary row per presentation group.
        defects: :attr:`findings` numbered ``G1``, ``G2``… with broken links
            deduplicated per target.
        outliers: Documents below the outlier threshold, worst first, each
            with its rule-based diagnosis.
        benchmarks: The top-ranked documents, best first, each with its
            strongest maxim.
        settings: The thresholds that selected the outliers and benchmarks.

    """

    documents: tuple[MaximScores, ...]
    findings: tuple[Finding, ...]
    disabled_metrics: tuple[str, ...]
    notes: tuple[str, ...]
    excluded_adrs: tuple[str, ...] = ()
    groups: tuple[GroupSummary, ...] = ()
    defects: tuple[StructuralDefect, ...] = ()
    outliers: tuple[TriageEntry, ...] = ()
    benchmarks: tuple[TriageEntry, ...] = ()
    settings: GriceSettings = field(default_factory=GriceSettings)

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

    @property
    def corpus_median(self) -> float | None:
        """Return the median ``grice_index`` across the corpus.

        The median is the headline figure: the indices are percentile-based,
        so the median sits near 50 by construction and a mean would be pulled
        by the few documents at either end.

        Returns:
            The 0-100 median, or ``None`` when no document produced an index.

        """
        measured = [row.grice_index for row in self.documents if row.grice_index is not None]
        if not measured:
            return None
        return float(statistics.median(measured))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report for the JSON output.

        Returns:
            A mapping with the corpus size, the median and mean indices, the
            excluded ADRs, the thresholds, the Executive Summary groups, the
            numbered defects, the outliers and benchmarks, one row per
            document, the raw findings, and the caveats. Aggregates are
            rounded to one decimal place like every other index.

        """
        return {
            "corpus_size": self.corpus_size,
            "corpus_median": GriceReport._round(self.corpus_median),
            "corpus_index": GriceReport._round(self.corpus_index),
            "excluded_adrs": {"count": len(self.excluded_adrs), "paths": list(self.excluded_adrs)},
            "settings": self.settings.to_dict(),
            "groups": [group.to_dict() for group in self.groups],
            "defects": [defect.to_dict() for defect in self.defects],
            "outliers": [entry.to_dict() for entry in self.outliers],
            "benchmarks": [entry.to_dict() for entry in self.benchmarks],
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
