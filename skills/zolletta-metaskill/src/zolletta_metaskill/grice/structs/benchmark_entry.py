"""BenchmarkEntry — one positive benchmark and every slot it won in its group."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.grice.structs.diagnosis import Diagnosis
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores


@dataclass(frozen=True)
class BenchmarkEntry:
    """A scored document paired with the benchmark slots it won.

    A group has five slots — ``balanced`` and the top document for each
    maxim — and one document may win several, so it is listed once with
    all of them rather than repeated.

    Attributes:
        scores: The document's row — path, group and the four indices.
        strengths: One reading per slot won, in slot order: ``balanced``
            first, then ``strong_<maxim>`` in maxim order.

    """

    scores: MaximScores
    strengths: tuple[Diagnosis, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry for the JSON report.

        Returns:
            The document row with the won slots listed under ``strengths``.

        """
        return {
            **self.scores.to_dict(),
            "strengths": [strength.to_dict() for strength in self.strengths],
        }
