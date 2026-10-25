"""Tests for document_features.py."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from zolletta_metaskill.grice.structs import DocumentFeatures


class TestDocumentFeatures:
    # --- word_count ---

    def test_word_count_blank_prose_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features(prose="   \n\t ").word_count == 0

    def test_word_count_prose_returns_whitespace_separated_tokens(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features(prose="one two\nthree").word_count == 3

    # --- section_count ---

    def test_section_count_no_sections_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features().section_count == 0

    def test_section_count_three_bodies_returns_three(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features(sections=("a", "b", "c")).section_count == 3

    # --- sentence_count ---

    def test_sentence_count_no_sentences_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features().sentence_count == 0

    def test_sentence_count_two_sentences_returns_two(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features(sentences=("One.", "Two.")).sentence_count == 2

    # --- words_per_section ---

    def test_words_per_section_without_sections_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        assert make_features(prose="one two").words_per_section == 0.0

    def test_words_per_section_split_evenly_returns_each_section_length(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="a b c d e f", sections=("a b c", "d e f"))
        assert features.words_per_section == 3.0

    @pytest.mark.parametrize(
        ("prose", "sections", "expected"),
        [
            ("a b c d", ("a", "b c d"), 2.0),
            ("a b c d e", ("a b", "c d e"), 2.5),
            ("a", ("a",), 1.0),
        ],
        ids=[
            "prose_four_words_gives_two",
            "prose_five_words_gives_two_point_five",
            "prose_one_word_gives_one",
        ],
    )
    def test_words_per_section_uneven_split_returns_mean_length(
        self,
        make_features: Callable[..., DocumentFeatures],
        prose: str,
        sections: tuple[str, ...],
        expected: float,
    ) -> None:
        assert make_features(prose=prose, sections=sections).words_per_section == expected
