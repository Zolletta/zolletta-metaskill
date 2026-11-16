"""TriageEntry — one document selected for the outlier or benchmark table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.grice.structs.diagnosis import Diagnosis
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores


@dataclass(frozen=True)
class TriageEntry:
    """A scored document paired with the rule-based reading of its scores.

    Attributes:
        scores: The document's row — path, group and the four indices.
        diagnosis: The outlier diagnosis or the benchmark strength.

    """

    scores: MaximScores
    diagnosis: Diagnosis

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry for the JSON report.

        Returns:
            The document row with the diagnosis nested under ``diagnosis``.

        """
        return {**self.scores.to_dict(), "diagnosis": self.diagnosis.to_dict()}
