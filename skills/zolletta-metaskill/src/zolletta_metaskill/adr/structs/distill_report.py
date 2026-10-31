"""Distill report data model.

Result of a distiller refresh run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DistillReport:
    """Result of a refresh run.

    Deliberately unfrozen (structs.1 deviation): the orchestrator builds the
    report incrementally — appending to ``new``/``stale``/``removed`` /
    ``dropped``/``lead_ins`` and assigning ``has_adrs`` after the ADR records
    are known — so it is an accumulator, not a value object.
    """

    new: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    lead_ins: list[str] = field(default_factory=list)
    has_adrs: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return {
            "new": self.new,
            "stale": self.stale,
            "removed": self.removed,
            "dropped": self.dropped,
            "lead_ins": self.lead_ins,
            "has_adrs": self.has_adrs,
        }
