"""Tests for quantity_metrics.py."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from zolletta_metaskill.grice.quantity_metrics import QuantityMetrics
from zolletta_metaskill.grice.structs import DocumentFeatures


class TestQuantityMetrics:
    # --- evaluate ---

    def test_evaluate_document_in_corpus_returns_all_five_metrics(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha beta gamma", sections=("alpha beta gamma",))
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert set(metrics) == {
            "section_balance",
            "section_redundancy",
            "sentence_redundancy",
            "corpus_duplication",
            "content_ratio",
        }

    def test_evaluate_document_in_corpus_returns_no_findings(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha beta")
        _, findings = QuantityMetrics.evaluate(features, (features,))
        assert findings == []

    @pytest.mark.parametrize(
        "metric",
        ["section_balance", "section_redundancy", "sentence_redundancy", "corpus_duplication"],
        ids=[
            "section_balance_stays_bounded",
            "section_redundancy_stays_bounded",
            "sentence_redundancy_stays_bounded",
            "corpus_duplication_stays_bounded",
        ],
    )
    def test_evaluate_any_document_returns_percentage_metrics(
        self, make_features: Callable[..., DocumentFeatures], metric: str
    ) -> None:
        features = make_features(prose="alpha beta gamma hi", sections=("alpha beta", "gamma hi"))
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert 0.0 <= metrics[metric] <= 100.0

    # --- section_balance ---

    def test_section_balance_document_at_corpus_median_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        words = " ".join(["word"] * 10)
        corpus = tuple(
            make_features(path=name, prose=words, sections=(words,))
            for name in ("a.md", "b.md", "c.md")
        )
        assert QuantityMetrics._section_balance(corpus[0], corpus) == pytest.approx(100.0)

    def test_section_balance_document_off_corpus_median_returns_lower_mark(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        median_words = " ".join(["word"] * 10)
        long_words = " ".join(["word"] * 40)
        corpus = (
            make_features(path="a.md", prose=median_words, sections=(median_words,)),
            make_features(path="b.md", prose=median_words, sections=(median_words,)),
            make_features(path="c.md", prose=long_words, sections=(long_words,)),
        )
        assert QuantityMetrics._section_balance(corpus[2], corpus) == pytest.approx(25.0)

    def test_section_balance_empty_document_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="", sections=("",))
        assert QuantityMetrics._section_balance(features, (features,)) == 0.0

    def test_section_balance_corpus_without_words_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        blank = make_features(path="a.md", prose="", sections=("",))
        other = make_features(path="b.md", prose="", sections=("",))
        assert QuantityMetrics._section_balance(blank, (blank, other)) == 0.0

    def test_section_balance_empty_peer_is_excluded_from_median(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        words = " ".join(["word"] * 20)
        features = make_features(path="a.md", prose=words, sections=(words,))
        empty = make_features(path="b.md", prose="", sections=("",))
        assert QuantityMetrics._section_balance(features, (features, empty)) == pytest.approx(100.0)

    def test_section_balance_one_word_peer_counts_toward_median(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        ten = " ".join(["word"] * 10)
        features = make_features(path="a.md", prose=ten, sections=(ten,))
        tiny = make_features(path="b.md", prose="word", sections=("word",))
        assert QuantityMetrics._section_balance(features, (features, tiny)) == pytest.approx(55.0)

    def test_section_balance_empty_document_in_nonempty_corpus_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(path="a.md", prose="", sections=("",))
        words = " ".join(["word"] * 20)
        peer = make_features(path="b.md", prose=words, sections=(words,))
        assert QuantityMetrics._section_balance(features, (features, peer)) == 0.0

    def test_section_balance_one_word_document_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="word", sections=("word",))
        assert QuantityMetrics._section_balance(features, (features,)) == pytest.approx(100.0)

    # --- section_redundancy ---

    def test_section_redundancy_duplicate_sections_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="alpha beta gamma",
            sections=("alpha beta gamma", "alpha beta gamma"),
        )
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["section_redundancy"] == pytest.approx(0.0)

    def test_section_redundancy_unrelated_sections_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha bravo", sections=("alpha", "bravo"))
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["section_redundancy"] == pytest.approx(100.0)

    # --- sentence_redundancy ---

    def test_sentence_redundancy_duplicate_sentences_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="alpha beta gamma",
            sections=("alpha beta gamma",),
            sentences=("alpha beta gamma", "alpha beta gamma"),
        )
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["sentence_redundancy"] == pytest.approx(0.0)

    def test_sentence_redundancy_unrelated_sentences_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="alpha bravo",
            sections=("alpha bravo",),
            sentences=("alpha", "bravo"),
        )
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["sentence_redundancy"] == pytest.approx(100.0)

    # --- corpus_duplication ---

    def test_corpus_duplication_identical_peer_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(path="a.md", prose="alpha beta gamma")
        peer = make_features(path="b.md", prose="alpha beta gamma")
        metrics, _ = QuantityMetrics.evaluate(features, (features, peer))
        assert metrics["corpus_duplication"] == pytest.approx(0.0)

    def test_corpus_duplication_unrelated_peer_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(path="a.md", prose="alpha beta gamma")
        peer = make_features(path="b.md", prose="delta epsilon zeta")
        metrics, _ = QuantityMetrics.evaluate(features, (features, peer))
        assert metrics["corpus_duplication"] == pytest.approx(100.0)

    def test_corpus_duplication_sole_document_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha beta gamma")
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["corpus_duplication"] == pytest.approx(100.0)

    # --- content_ratio ---

    def test_content_ratio_partly_boilerplate_returns_prose_share(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose=" ".join(["word"] * 10), boilerplate_words=2)
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["content_ratio"] == pytest.approx(80.0)

    def test_content_ratio_all_boilerplate_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose=" ".join(["word"] * 4), boilerplate_words=4)
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["content_ratio"] == pytest.approx(0.0)

    def test_content_ratio_document_without_words_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="", boilerplate_words=0)
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["content_ratio"] == pytest.approx(100.0)

    def test_content_ratio_single_word_all_boilerplate_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="word", boilerplate_words=1)
        metrics, _ = QuantityMetrics.evaluate(features, (features,))
        assert metrics["content_ratio"] == pytest.approx(0.0)
