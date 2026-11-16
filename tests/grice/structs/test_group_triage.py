"""Tests for group_triage.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import (
    BenchmarkEntry,
    Diagnosis,
    GroupTriage,
    MaximScores,
    TriageEntry,
)


class TestGroupTriage:
    # --- to_dict ---

    def test_to_dict_group_serializes_name_outliers_and_benchmarks(self) -> None:
        weak = TriageEntry(
            MaximScores("docs/a/x.md", 10.0, 10.0, 10.0, 10.0, group="a"),
            Diagnosis("uniform_deficit", "quantity", "Weak", "Fix."),
        )
        strong = BenchmarkEntry(
            MaximScores("docs/a/y.md", 90.0, 50.0, 50.0, 50.0, group="a"),
            (Diagnosis("strong_quantity", "quantity", "Dense", "Copy."),),
        )
        assert GroupTriage("a", (weak,), (strong,)).to_dict() == {
            "group": "a",
            "outliers": [weak.to_dict()],
            "benchmarks": [strong.to_dict()],
        }

    def test_to_dict_empty_group_serializes_empty_lists(self) -> None:
        assert GroupTriage("(root)", (), ()).to_dict() == {
            "group": "(root)",
            "outliers": [],
            "benchmarks": [],
        }
