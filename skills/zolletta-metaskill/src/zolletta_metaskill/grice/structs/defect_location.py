"""DefectLocation — one place in the corpus where a structural defect occurs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DefectLocation:
    """A file and line carrying one occurrence of a defect.

    Attributes:
        file: Repository-relative path of the document.
        line: 1-based line of the occurrence.
        group: Presentation group of the document.

    """

    file: str
    line: int
    group: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the location for the JSON report.

        Returns:
            A mapping with the file, the line and the group.

        """
        return {"file": self.file, "line": self.line, "group": self.group}
