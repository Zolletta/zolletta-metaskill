"""Tests for structural_defect.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import DefectLocation, StructuralDefect


def _defect(*locations: DefectLocation) -> StructuralDefect:
    return StructuralDefect(
        id="G1",
        kind="broken_link",
        severity="medium",
        description="internal link 'x.md' does not resolve",
        target="docs/x.md",
        locations=locations,
    )


class TestStructuralDefect:
    # --- groups ---

    def test_groups_repeated_groups_returns_sorted_distinct_names(self) -> None:
        defect = _defect(
            DefectLocation("docs/old/a.md", 1, "old"),
            DefectLocation("docs/current/b.md", 2, "current"),
            DefectLocation("docs/old/c.md", 3, "old"),
        )
        assert defect.groups == ("current", "old")

    # --- to_dict ---

    def test_to_dict_defect_serializes_count_groups_and_locations(self) -> None:
        defect = _defect(
            DefectLocation("docs/old/a.md", 1, "old"),
            DefectLocation("docs/old/c.md", 3, "old"),
        )
        assert defect.to_dict() == {
            "id": "G1",
            "kind": "broken_link",
            "severity": "medium",
            "description": "internal link 'x.md' does not resolve",
            "target": "docs/x.md",
            "count": 2,
            "groups": ["old"],
            "locations": [
                {"file": "docs/old/a.md", "line": 1, "group": "old"},
                {"file": "docs/old/c.md", "line": 3, "group": "old"},
            ],
        }
