"""Tests for diagnosis.py."""

from __future__ import annotations

from zolletta_metaskill.grice.structs import Diagnosis


class TestDiagnosis:
    # --- to_dict ---

    def test_to_dict_full_diagnosis_serializes_every_field(self) -> None:
        diagnosis = Diagnosis("isolated", "relation", "Isolated page", "Link it.")
        assert diagnosis.to_dict() == {
            "code": "isolated",
            "maxim": "relation",
            "summary": "Isolated page",
            "action": "Link it.",
        }

    def test_to_dict_unmeasured_diagnosis_keeps_null_maxim(self) -> None:
        assert Diagnosis("unmeasured", None, "Nothing", "").to_dict()["maxim"] is None
