"""Tests for benchmark_entry.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import BenchmarkEntry, Diagnosis, MaximScores


class TestBenchmarkEntry:
    # --- to_dict ---

    def test_to_dict_entry_lists_every_strength_under_the_row(self) -> None:
        row = MaximScores("docs/a/x.md", 70.0, 65.0, 80.0, 62.0, group="a")
        balanced = Diagnosis("balanced", "relation", "Above", "Copy.")
        relation = Diagnosis("strong_relation", "relation", "Cohesive", "Copy.")
        assert BenchmarkEntry(row, (balanced, relation)).to_dict() == {
            **row.to_dict(),
            "strengths": [balanced.to_dict(), relation.to_dict()],
        }
