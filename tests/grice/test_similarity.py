"""Tests for similarity.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.similarity import Similarity


class TestSimilarity:
    # --- cosine ---

    def test_cosine_identical_texts_returns_one(self) -> None:
        assert Similarity.cosine("alpha beta", "alpha beta") == pytest.approx(1.0)

    def test_cosine_disjoint_vocabulary_returns_zero(self) -> None:
        assert Similarity.cosine("alpha", "bravo") == pytest.approx(0.0)

    def test_cosine_blank_left_text_returns_zero(self) -> None:
        assert Similarity.cosine("", "alpha") == 0.0

    def test_cosine_blank_right_text_returns_zero(self) -> None:
        assert Similarity.cosine("alpha", "  ") == 0.0

    def test_cosine_both_texts_blank_returns_zero(self) -> None:
        assert Similarity.cosine("", "") == 0.0

    def test_cosine_texts_too_short_for_terms_returns_zero(self) -> None:
        assert Similarity.cosine("a", "a") == 0.0

    def test_cosine_partial_overlap_returns_value_between_zero_and_one(self) -> None:
        overlap = Similarity.cosine("alpha beta gamma", "alpha beta delta")
        assert 0.0 < overlap < 1.0

    # --- max_pairwise ---

    def test_max_pairwise_no_texts_returns_zero(self) -> None:
        assert Similarity.max_pairwise(()) == 0.0

    def test_max_pairwise_single_text_returns_zero(self) -> None:
        assert Similarity.max_pairwise(("alpha beta",)) == 0.0

    def test_max_pairwise_blank_texts_returns_zero(self) -> None:
        assert Similarity.max_pairwise(("", "   ")) == 0.0

    def test_max_pairwise_texts_too_short_for_terms_returns_zero(self) -> None:
        """Single-character texts vectorise to an empty vocabulary — the ValueError guard."""
        assert Similarity.max_pairwise(("a", "a")) == 0.0

    def test_max_pairwise_repeated_text_returns_one(self) -> None:
        assert Similarity.max_pairwise(("alpha beta", "alpha beta")) == pytest.approx(1.0)

    def test_max_pairwise_distinct_texts_returns_zero(self) -> None:
        assert Similarity.max_pairwise(("alpha", "bravo")) == pytest.approx(0.0)

    def test_max_pairwise_three_texts_returns_the_strongest_pair(self) -> None:
        duplicate = Similarity.max_pairwise(("alpha beta", "alpha beta", "charlie"))
        assert duplicate == pytest.approx(1.0)

    # --- max_against ---

    def test_max_against_no_other_texts_returns_zero(self) -> None:
        assert Similarity.max_against("alpha beta", ()) == 0.0

    def test_max_against_blank_text_returns_zero(self) -> None:
        assert Similarity.max_against("", ("alpha",)) == 0.0

    def test_max_against_identical_other_text_returns_one(self) -> None:
        assert Similarity.max_against("alpha beta", ("alpha beta",)) == pytest.approx(1.0)

    def test_max_against_two_others_returns_the_strongest_similarity(self) -> None:
        strongest = Similarity.max_against("alpha beta gamma", ("delta", "alpha beta gamma"))
        assert strongest == pytest.approx(1.0)

    # --- pair_scores ---

    def test_pair_scores_no_comparable_pair_returns_empty_tuple(self) -> None:
        assert Similarity.pair_scores(("", ""), ("", "")) == ()

    def test_pair_scores_matching_pairs_returns_one_per_pair(self) -> None:
        scores = Similarity.pair_scores(
            ("alpha beta", "gamma delta"), ("alpha beta", "gamma delta")
        )
        assert scores == pytest.approx((1.0, 1.0))

    def test_pair_scores_blank_pair_is_skipped(self) -> None:
        scores = Similarity.pair_scores(("alpha beta", ""), ("alpha beta", ""))
        assert scores == pytest.approx((1.0,))

    def test_pair_scores_half_blank_pair_returns_zero(self) -> None:
        scores = Similarity.pair_scores(("",), ("alpha",))
        assert scores == (0.0,)

    def test_pair_scores_fewer_rights_than_lefts_compares_the_common_prefix(self) -> None:
        scores = Similarity.pair_scores(("alpha", "bravo"), ("alpha",))
        assert scores == pytest.approx((1.0,))

    def test_pair_scores_unrelated_pairs_return_zero(self) -> None:
        scores = Similarity.pair_scores(("alpha",), ("bravo",))
        assert scores == (0.0,)
