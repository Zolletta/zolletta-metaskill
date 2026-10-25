"""MaximScores — one documentation file scored against the four maxims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MaximScores:
    """The four maxim indices of one document, as corpus percentiles.

    An index is ``None`` when the maxim produced no applicable metric — a
    frontmatter-only file has no sentences to measure, so Manner is silent
    rather than zero. ``None`` and ``0`` mean different things here: the first
    is "not measured", the second is "measured and worst in the corpus".

    Attributes:
        path: Repository-relative path, the report row key.
        quantity: Quantity index in 0-100, or ``None``.
        quality: Quality index in 0-100, or ``None``.
        relation: Relation index in 0-100, or ``None``.
        manner: Manner index in 0-100, or ``None``.

    """

    path: str
    quantity: float | None
    quality: float | None
    relation: float | None
    manner: float | None

    @property
    def available(self) -> tuple[float, ...]:
        """Return the maxim indices that were actually measured.

        Returns:
            Every non-``None`` index, in maxim order.

        """
        return tuple(
            score
            for score in (self.quantity, self.quality, self.relation, self.manner)
            if score is not None
        )

    @property
    def grice_index(self) -> float | None:
        """Return the mean of the measured maxim indices.

        Returns:
            The 0-100 aggregate, or ``None`` when no maxim could be measured.

        """
        measured = self.available
        if not measured:
            return None
        return sum(measured) / len(measured)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the row for the JSON report.

        Returns:
            A mapping with the path, the four indices, and the aggregate, each
            rounded to one decimal place. ``None`` stays ``None`` so a reader
            can tell "not measured" from "measured low".

        """
        index = self.grice_index
        return {
            "path": self.path,
            "quantity": MaximScores._round(self.quantity),
            "quality": MaximScores._round(self.quality),
            "relation": MaximScores._round(self.relation),
            "manner": MaximScores._round(self.manner),
            "grice_index": MaximScores._round(index),
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
