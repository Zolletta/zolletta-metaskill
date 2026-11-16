"""TriageSelector — pick the outliers and the positive benchmarks of a corpus."""

from __future__ import annotations

from zolletta_metaskill.grice.diagnosis_engine import DiagnosisEngine
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores
from zolletta_metaskill.grice.structs.triage_entry import TriageEntry


class TriageSelector:
    """Select documents for the two triage tables, deterministically.

    Selection compares the index rounded to one decimal — the value the report
    prints — so a row shown as ``40.0`` is never listed under ``< 40``. Ties
    break on the path.
    """

    @staticmethod
    def outliers(documents: tuple[MaximScores, ...], threshold: float) -> tuple[TriageEntry, ...]:
        """Return every document below *threshold*, worst first, diagnosed.

        Args:
            documents: The scored corpus.
            threshold: The outlier threshold.

        Returns:
            One entry per outlier, sorted by index then path.

        """
        ranked = sorted(
            (pair for pair in TriageSelector._ranked(documents) if pair[0] < threshold),
            key=lambda pair: (pair[0], pair[1].path),
        )
        return tuple(TriageEntry(row, DiagnosisEngine.diagnose(row)) for _, row in ranked)

    @staticmethod
    def benchmarks(
        documents: tuple[MaximScores, ...], count: int, threshold: float
    ) -> tuple[TriageEntry, ...]:
        """Return the *count* best documents not below *threshold*, best first.

        Args:
            documents: The scored corpus.
            count: How many benchmarks to return at most.
            threshold: The outlier threshold — an outlier is never a model.

        Returns:
            One entry per benchmark, sorted by descending index then path.

        """
        ranked = sorted(
            (pair for pair in TriageSelector._ranked(documents) if pair[0] >= threshold),
            key=lambda pair: (-pair[0], pair[1].path),
        )
        return tuple(TriageEntry(row, DiagnosisEngine.strength(row)) for _, row in ranked[:count])

    @staticmethod
    def _ranked(documents: tuple[MaximScores, ...]) -> list[tuple[float, MaximScores]]:
        """Pair each document that has an index with its rounded index.

        Args:
            documents: The scored corpus.

        Returns:
            ``(rounded index, row)`` pairs, documents without an index omitted.

        """
        return [
            (round(row.grice_index, 1), row) for row in documents if row.grice_index is not None
        ]
