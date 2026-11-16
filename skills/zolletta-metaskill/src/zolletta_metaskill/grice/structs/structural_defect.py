"""StructuralDefect — a broken link target or a heading skip, with its id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.grice.structs.defect_location import DefectLocation


@dataclass(frozen=True)
class StructuralDefect:
    """One defect of the corpus, numbered ``G1``, ``G2``… in report order.

    A broken link is deduplicated per resolved target: twenty pages pointing at
    the same missing anchor are one defect with twenty locations, because one
    fix — restore the anchor or retarget the links — resolves all of them. A
    heading skip always has exactly one location.

    Attributes:
        id: Report id, ``G`` followed by a progressive number.
        kind: ``"broken_link"`` or ``"heading_skip"``.
        severity: Severity of the underlying findings.
        description: The first occurrence's finding text.
        target: Repository-relative resolved link target, ``None`` for a
            heading skip.
        locations: Every occurrence, sorted by file and line.

    """

    id: str
    kind: str
    severity: str
    description: str
    target: str | None
    locations: tuple[DefectLocation, ...]

    @property
    def groups(self) -> tuple[str, ...]:
        """Return the groups the defect occurs in.

        Returns:
            The distinct groups of :attr:`locations`, sorted.

        """
        return tuple(sorted({location.group for location in self.locations}))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the defect for the JSON report.

        Returns:
            A mapping with the id, kind, severity, description, target, the
            occurrence count, the groups and every location.

        """
        return {
            "id": self.id,
            "kind": self.kind,
            "severity": self.severity,
            "description": self.description,
            "target": self.target,
            "count": len(self.locations),
            "groups": list(self.groups),
            "locations": [location.to_dict() for location in self.locations],
        }
