"""Tests for relation_metrics.py."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from zolletta_metaskill.grice.relation_metrics import RelationMetrics
from zolletta_metaskill.grice.structs import DocumentFeatures


class TestRelationMetrics:
    # --- evaluate ---

    def test_evaluate_heading_and_frontmatter_returns_all_three_metrics(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="alpha beta gamma",
            frontmatter="alpha beta",
            sections=("alpha beta gamma",),
            headings=("alpha beta",),
        )
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert set(metrics) == {"heading_body", "frontmatter_content", "corpus_pertinence"}

    def test_evaluate_document_in_corpus_returns_no_findings(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha beta")
        _, findings = RelationMetrics.evaluate(features, (features,))
        assert findings == []

    # --- heading_body ---

    def test_heading_body_matching_section_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="installation steps",
            sections=("installation steps",),
            headings=("installation steps",),
        )
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["heading_body"] == pytest.approx(100.0)

    def test_heading_body_unrelated_section_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="installation steps",
            sections=("installation steps",),
            headings=("legal disclaimer",),
        )
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["heading_body"] == pytest.approx(0.0)

    def test_heading_body_without_headings_is_not_measured(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha beta", sections=("alpha beta",))
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert "heading_body" not in metrics

    def test_heading_body_with_blank_sections_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(sections=("",), headings=("Title",))
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["heading_body"] == 0.0

    def test_heading_body_headings_without_sections_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(headings=("Title",), sections=())
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["heading_body"] == 0.0

    def test_heading_body_one_matching_one_unrelated_pair_returns_the_mean(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="alpha beta gamma delta",
            sections=("alpha beta", "gamma delta"),
            headings=("alpha beta", "epsilon zeta"),
        )
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["heading_body"] == pytest.approx(50.0)

    # --- frontmatter_content ---

    def test_frontmatter_content_matching_prose_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(frontmatter="alpha beta", prose="alpha beta")
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["frontmatter_content"] == pytest.approx(100.0)

    def test_frontmatter_content_unrelated_prose_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(frontmatter="alpha beta", prose="gamma delta")
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["frontmatter_content"] == pytest.approx(0.0)

    def test_frontmatter_content_without_frontmatter_is_not_measured(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(frontmatter="  ", prose="alpha beta")
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert "frontmatter_content" not in metrics

    # --- corpus_pertinence ---

    def test_corpus_pertinence_sole_document_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(prose="alpha beta")
        metrics, _ = RelationMetrics.evaluate(features, (features,))
        assert metrics["corpus_pertinence"] == 0.0

    def test_corpus_pertinence_unrelated_corpus_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(path="a.md", prose="alpha beta")
        peers = (
            make_features(path="b.md", prose="gamma"),
            make_features(path="c.md", prose="delta"),
        )
        metrics, _ = RelationMetrics.evaluate(features, (features, *peers))
        assert metrics["corpus_pertinence"] == pytest.approx(0.0)

    def test_corpus_pertinence_matching_corpus_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(path="a.md", prose="alpha beta")
        peers = (
            make_features(path="b.md", prose="alpha beta"),
            make_features(path="c.md", prose="alpha beta"),
        )
        metrics, _ = RelationMetrics.evaluate(features, (features, *peers))
        assert metrics["corpus_pertinence"] == pytest.approx(100.0)
