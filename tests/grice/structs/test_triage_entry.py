"""Tests for triage_entry.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import Diagnosis, MaximScores, TriageEntry


class TestTriageEntry:
    # --- to_dict ---

    def test_to_dict_entry_nests_diagnosis_under_the_row(self) -> None:
        row = MaximScores("docs/a/x.md", 10.0, 20.0, 30.0, 40.0, group="a")
        diagnosis = Diagnosis("weak_quantity", "quantity", "Stub", "Fill it.")
        assert TriageEntry(row, diagnosis).to_dict() == {
            **row.to_dict(),
            "diagnosis": diagnosis.to_dict(),
        }
