"""Tests for corpus_normalizer.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.corpus_normalizer import CorpusNormalizer


class TestCorpusNormalizer:
    # --- normalise ---

    def test_normalise_empty_sample_returns_empty_tuple(self) -> None:
        assert CorpusNormalizer.normalise(()) == ()

    def test_normalise_single_value_returns_neutral(self) -> None:
        assert CorpusNormalizer.normalise((7.0,)) == (CorpusNormalizer.NEUTRAL,)

    def test_normalise_flat_sample_returns_neutral_for_every_value(self) -> None:
        assert CorpusNormalizer.normalise((5.0, 5.0, 5.0)) == (50.0, 50.0, 50.0)

    def test_normalise_two_symmetric_values_returns_mirrored_percentiles(self) -> None:
        low, high = CorpusNormalizer.normalise((0.0, 100.0))
        assert low + high == pytest.approx(100.0)
        assert low < 50.0 < high

    def test_normalise_two_symmetric_values_returns_normal_cdf_percentiles(self) -> None:
        low, high = CorpusNormalizer.normalise((0.0, 100.0))
        assert low == pytest.approx(15.865525393145708)
        assert high == pytest.approx(84.1344746068543)

    def test_normalise_three_ascending_values_returns_ascending_percentiles(self) -> None:
        low, middle, high = CorpusNormalizer.normalise((1.0, 2.0, 3.0))
        assert low < middle < high
        assert middle == pytest.approx(CorpusNormalizer.NEUTRAL)

    @pytest.mark.parametrize(
        "value",
        [0.0, 1.0, 50.0, 100.0, 1234.5],
        ids=[
            "value_zero_stays_bounded",
            "value_one_stays_bounded",
            "value_fifty_stays_bounded",
            "value_hundred_stays_bounded",
            "value_outlier_stays_bounded",
        ],
    )
    def test_normalise_any_value_returns_a_percentile(self, value: float) -> None:
        percentile = CorpusNormalizer.normalise((value, 10.0, 20.0, 30.0))[0]
        assert 0.0 <= percentile <= 100.0

    # --- normalise_rows ---

    def test_normalise_rows_empty_corpus_returns_empty_tuple(self) -> None:
        assert CorpusNormalizer.normalise_rows(()) == ()

    def test_normalise_rows_absent_metric_stays_absent(self) -> None:
        normalised = CorpusNormalizer.normalise_rows(({"alpha": 1.0}, {"beta": 2.0}))
        assert normalised == ({"alpha": 50.0}, {"beta": 50.0})

    def test_normalise_rows_documents_receive_their_own_metric_values(self) -> None:
        rows = (
            {"shared": 1.0},
            {"shared": 2.0, "sparse": 5.0},
            {"shared": 3.0, "sparse": 7.0},
        )
        normalised = CorpusNormalizer.normalise_rows(rows)
        assert set(normalised[0]) == {"shared"}
        assert normalised[0]["shared"] == CorpusNormalizer.normalise((1.0, 2.0, 3.0))[0]
        assert normalised[1]["sparse"] == CorpusNormalizer.normalise((5.0, 7.0))[0]
        assert normalised[2]["sparse"] == CorpusNormalizer.normalise((5.0, 7.0))[1]

    def test_normalise_rows_shared_metric_spans_every_document(self) -> None:
        rows = ({"shared": 1.0}, {"shared": 2.0}, {"shared": 3.0})
        normalised = CorpusNormalizer.normalise_rows(rows)
        expected = CorpusNormalizer.normalise((1.0, 2.0, 3.0))
        assert tuple(row["shared"] for row in normalised) == pytest.approx(expected)

    # --- aggregate ---

    def test_aggregate_empty_values_returns_none(self) -> None:
        assert CorpusNormalizer.aggregate(()) is None

    def test_aggregate_two_values_returns_their_mean(self) -> None:
        assert CorpusNormalizer.aggregate((40.0, 60.0)) == 50.0

    # --- aggregate_maxim ---

    def test_aggregate_maxim_document_index_returns_that_document_index(self) -> None:
        normalised = {"quantity": ({"a": 10.0}, {"a": 90.0})}
        assert CorpusNormalizer.aggregate_maxim(normalised, "quantity", 1) == 90.0

    def test_aggregate_maxim_unmeasured_document_returns_none(self) -> None:
        normalised: dict[str, tuple[dict[str, float], ...]] = {"quantity": ({}, {})}
        assert CorpusNormalizer.aggregate_maxim(normalised, "quantity", 0) is None

    def test_aggregate_maxim_multiple_metrics_returns_mean(self) -> None:
        normalised = {"manner": ({"a": 20.0, "b": 40.0},)}
        assert CorpusNormalizer.aggregate_maxim(normalised, "manner", 0) == 30.0
