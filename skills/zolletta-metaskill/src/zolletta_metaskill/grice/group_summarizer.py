"""GroupSummarizer — build the Executive Summary rows, one per group."""

from __future__ import annotations

import statistics

from zolletta_metaskill.grice.document_grouper import DocumentGrouper
from zolletta_metaskill.grice.structs.group_summary import GroupSummary
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores
from zolletta_metaskill.grice.structs.structural_defect import StructuralDefect
from zolletta_metaskill.grice.structs.triage_entry import TriageEntry


class GroupSummarizer:
    """Aggregate the corpus-normalised rows per presentation group."""

    @staticmethod
    def summarise(
        documents: tuple[MaximScores, ...],
        outliers: tuple[TriageEntry, ...],
        defects: tuple[StructuralDefect, ...],
    ) -> tuple[GroupSummary, ...]:
        """Return one summary row per group that holds a scored document.

        Args:
            documents: The scored corpus.
            outliers: The selected outliers.
            defects: The numbered defects; one counts once per group it
                occurs in.

        Returns:
            The rows in :meth:`DocumentGrouper.order`.

        """
        return tuple(
            GroupSummary(
                name=name,
                documents=sum(1 for row in documents if row.group == name),
                median_index=GroupSummarizer.median(
                    [row.grice_index for row in documents if row.group == name]
                ),
                outliers=sum(1 for entry in outliers if entry.scores.group == name),
                defects=sum(1 for defect in defects if name in defect.groups),
            )
            for name in DocumentGrouper.order(row.group for row in documents)
        )

    @staticmethod
    def median(values: list[float | None]) -> float | None:
        """Return the median of the measured *values*.

        Args:
            values: Indices, ``None`` for unmeasured documents.

        Returns:
            The median, or ``None`` when nothing was measured.

        """
        measured = [value for value in values if value is not None]
        return float(statistics.median(measured)) if measured else None
