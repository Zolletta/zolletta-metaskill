"""TriageSelector — pick the outliers and the positive benchmarks of a corpus."""

from __future__ import annotations

from zolletta_metaskill.grice.diagnosis_engine import DiagnosisEngine
from zolletta_metaskill.grice.document_grouper import DocumentGrouper
from zolletta_metaskill.grice.structs.benchmark_entry import BenchmarkEntry
from zolletta_metaskill.grice.structs.diagnosis import Diagnosis
from zolletta_metaskill.grice.structs.group_triage import GroupTriage
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores
from zolletta_metaskill.grice.structs.triage_entry import TriageEntry


class TriageSelector:
    """Select documents for the triage tables, deterministically.

    Selection compares values rounded to one decimal — the value the report
    prints — so a row shown as ``40.0`` is never listed under ``< 40``. Ties
    break on the higher index, then on the path.
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
        documents: tuple[MaximScores, ...], threshold: float
    ) -> tuple[BenchmarkEntry, ...]:
        """Return the benchmark slots of one group, each document listed once.

        The slots are the best-ranked ``balanced`` document and the document
        with the highest score on each maxim, in that order. A document that
        wins several slots appears once, at its first slot, carrying all of
        them — so a group yields at most five rows, fewer when slots share a
        winner or no document qualifies as ``balanced``.

        Args:
            documents: The scored documents of one group.
            threshold: The outlier threshold — an outlier is never a model.

        Returns:
            One entry per distinct winner, in slot order.

        """
        candidates = [
            row
            for _, row in sorted(
                (pair for pair in TriageSelector._ranked(documents) if pair[0] >= threshold),
                key=lambda pair: (-pair[0], pair[1].path),
            )
        ]
        picks = [
            (row, strength)
            for row, strength in ((row, DiagnosisEngine.strength(row)) for row in candidates)
            if strength.code == "balanced"
        ][:1]
        for maxim in DiagnosisEngine.MAXIMS:
            scored = [
                (round(measured[maxim], 1), row)
                for row, measured in ((row, DiagnosisEngine.measured(row)) for row in candidates)
                if maxim in measured
            ]
            if scored:
                picks.append(
                    (max(scored, key=lambda pair: pair[0])[1], DiagnosisEngine.strong(maxim))
                )
        return TriageSelector._merged(picks)

    @staticmethod
    def by_group(
        documents: tuple[MaximScores, ...], outliers: tuple[TriageEntry, ...], threshold: float
    ) -> tuple[GroupTriage, ...]:
        """Split the triage per presentation group.

        Args:
            documents: The scored corpus.
            outliers: The corpus outliers, as :meth:`outliers` returns them.
            threshold: The outlier threshold.

        Returns:
            One entry per group in :meth:`DocumentGrouper.order`, each with
            its outliers worst first and its benchmarks in slot order.

        """
        return tuple(
            GroupTriage(
                name,
                tuple(entry for entry in outliers if entry.scores.group == name),
                TriageSelector.benchmarks(
                    tuple(row for row in documents if row.group == name), threshold
                ),
            )
            for name in DocumentGrouper.order(row.group for row in documents)
        )

    @staticmethod
    def _merged(picks: list[tuple[MaximScores, Diagnosis]]) -> tuple[BenchmarkEntry, ...]:
        """Fold the slot winners into one entry per document.

        Args:
            picks: ``(row, strength)`` per won slot, in slot order.

        Returns:
            One entry per document, at its first slot, with every strength.

        """
        merged: dict[str, BenchmarkEntry] = {}
        for row, strength in picks:
            prior = merged.get(row.path)
            strengths = (strength,) if prior is None else (*prior.strengths, strength)
            merged[row.path] = BenchmarkEntry(row, strengths)
        return tuple(merged.values())

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
