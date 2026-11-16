"""Tests for group_summary.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import GroupSummary


class TestGroupSummary:
    # --- to_dict ---

    def test_to_dict_measured_group_rounds_median_to_one_decimal(self) -> None:
        assert GroupSummary("current", 4, 51.26, 1, 2).to_dict() == {
            "name": "current",
            "documents": 4,
            "median_index": 51.3,
            "outliers": 1,
            "defects": 2,
        }

    def test_to_dict_unmeasured_group_keeps_null_median(self) -> None:
        assert GroupSummary("old", 1, None, 0, 0).to_dict()["median_index"] is None
