"""Tests for maxim_scores.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.structs import MaximScores


class TestMaximScores:
    # --- available ---

    def test_available_all_measured_returns_four_indices(self) -> None:
        row = MaximScores(path="a.md", quantity=1.0, quality=2.0, relation=3.0, manner=4.0)
        assert row.available == (1.0, 2.0, 3.0, 4.0)

    def test_available_unmeasured_maxims_returns_measured_only(self) -> None:
        row = MaximScores(path="a.md", quantity=None, quality=2.0, relation=None, manner=4.0)
        assert row.available == (2.0, 4.0)

    def test_available_nothing_measured_returns_empty_tuple(self) -> None:
        row = MaximScores(path="a.md", quantity=None, quality=None, relation=None, manner=None)
        assert row.available == ()

    # --- grice_index ---

    def test_grice_index_all_measured_returns_mean(self) -> None:
        row = MaximScores(path="a.md", quantity=10.0, quality=20.0, relation=30.0, manner=40.0)
        assert row.grice_index == 25.0

    def test_grice_index_partly_measured_ignores_unmeasured_maxims(self) -> None:
        row = MaximScores(path="a.md", quantity=None, quality=20.0, relation=None, manner=40.0)
        assert row.grice_index == 30.0

    def test_grice_index_nothing_measured_returns_none(self) -> None:
        row = MaximScores(path="a.md", quantity=None, quality=None, relation=None, manner=None)
        assert row.grice_index is None

    # --- to_dict ---

    def test_to_dict_measured_indices_round_to_one_decimal(self) -> None:
        row = MaximScores(path="a.md", quantity=1.26, quality=2.0, relation=3.0, manner=None)
        assert row.to_dict() == {
            "path": "a.md",
            "quantity": 1.3,
            "quality": 2.0,
            "relation": 3.0,
            "manner": None,
            "grice_index": 2.1,
        }

    def test_to_dict_unmeasured_index_stays_none(self) -> None:
        row = MaximScores(path="a.md", quantity=None, quality=None, relation=None, manner=None)
        assert row.to_dict()["grice_index"] is None

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (12.345, 12.3),
            (12.36, 12.4),
            (0.04, 0.0),
            (99.99, 100.0),
        ],
        ids=[
            "raw_twelve_three_rounds_down",
            "raw_twelve_four_rounds_up",
            "raw_zero_drops_to_zero",
            "raw_near_hundred_rounds_to_hundred",
        ],
    )
    def test_to_dict_single_index_rounds_to_one_decimal(self, raw: float, expected: float) -> None:
        row = MaximScores(path="a.md", quantity=raw, quality=None, relation=None, manner=None)
        assert row.to_dict()["quantity"] == expected
