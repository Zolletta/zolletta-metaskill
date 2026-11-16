"""Tests for defect_location.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import DefectLocation


class TestDefectLocation:
    # --- to_dict ---

    def test_to_dict_location_serializes_file_line_and_group(self) -> None:
        assert DefectLocation("docs/a/x.md", 3, "a").to_dict() == {
            "file": "docs/a/x.md",
            "line": 3,
            "group": "a",
        }
