"""GroupTriage — the outliers and positive benchmarks of one presentation group."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.grice.structs.benchmark_entry import BenchmarkEntry
from zolletta_metaskill.grice.structs.triage_entry import TriageEntry


@dataclass(frozen=True)
class GroupTriage:
    """One group's two triage tables, already selected and sorted.

    Attributes:
        name: Group name — a first-level child of ``documentation.dir``, or
            ``(root)``.
        outliers: The group's documents below the outlier threshold, worst
            first, each with its diagnosis.
        benchmarks: At most five non-outliers — the best ``balanced``
            document and the top document for each maxim — in slot order.

    """

    name: str
    outliers: tuple[TriageEntry, ...]
    benchmarks: tuple[BenchmarkEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the group's triage for the JSON report.

        Returns:
            A mapping with the group name, its outliers and its benchmarks.

        """
        return {
            "group": self.name,
            "outliers": [entry.to_dict() for entry in self.outliers],
            "benchmarks": [entry.to_dict() for entry in self.benchmarks],
        }
