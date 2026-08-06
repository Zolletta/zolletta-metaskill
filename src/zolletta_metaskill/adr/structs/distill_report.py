"""Distill report data model.

Result of a distiller refresh run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DistillReport:
    """Result of a refresh run."""

    new: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    has_adrs: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return {
            "new": self.new,
            "stale": self.stale,
            "removed": self.removed,
            "has_adrs": self.has_adrs,
        }
