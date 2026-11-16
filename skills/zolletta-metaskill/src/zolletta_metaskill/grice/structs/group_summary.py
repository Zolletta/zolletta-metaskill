"""GroupSummary — one Executive Summary row: a documentation group at a glance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GroupSummary:
    """The counts and the median index of one presentation group.

    Groups only affect presentation: every index in the row was normalised
    against the whole corpus, so a group median is "where this group sits in
    the corpus", never a ranking inside the group.

    Attributes:
        name: Group name — a first-level child of ``documentation.dir``, or
            ``(root)``.
        documents: How many scored documents the group holds.
        median_index: Median ``grice_index`` of the group, or ``None`` when no
            document in it produced one.
        outliers: How many of its documents fall below the outlier threshold.
        defects: How many structural defects occur in it at least once.

    """

    name: str
    documents: int
    median_index: float | None
    outliers: int
    defects: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the row for the JSON report.

        Returns:
            A mapping with the name, the counts and the median rounded to one
            decimal place, ``None`` preserved.

        """
        return {
            "name": self.name,
            "documents": self.documents,
            "median_index": None if self.median_index is None else round(self.median_index, 1),
            "outliers": self.outliers,
            "defects": self.defects,
        }
