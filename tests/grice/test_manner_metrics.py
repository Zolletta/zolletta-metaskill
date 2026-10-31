"""Tests for manner_metrics.py."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from zolletta_metaskill.grice.manner_metrics import MannerMetrics
from zolletta_metaskill.grice.structs import DocumentFeatures

ENGLISH_PROSE = (
    "The cat sat on the mat. The dog ran in the park. "
    "A bird flew over the tree. The sun was very bright today."
)
ENGLISH_SENTENCES = (
    "The cat sat on the mat.",
    "The dog ran in the park.",
    "A bird flew over the tree.",
    "The sun was very bright today.",
)


class TestMannerMetrics:
    # --- evaluate ---

    def test_evaluate_english_document_returns_every_metric(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=ENGLISH_PROSE,
            sections=(ENGLISH_PROSE,),
            sentences=ENGLISH_SENTENCES,
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert set(metrics) == {
            "readability",
            "grade_level",
            "smog",
            "hedging",
            "passive_voice",
            "heading_hierarchy",
            "sentence_length",
            "section_structure",
        }

    def test_evaluate_non_english_document_drops_english_metrics(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=ENGLISH_PROSE,
            sections=(ENGLISH_PROSE,),
            sentences=ENGLISH_SENTENCES,
        )
        metrics, _ = MannerMetrics.evaluate(features, "it")
        assert set(metrics) == {"heading_hierarchy", "sentence_length", "section_structure"}

    def test_evaluate_short_document_drops_readability_metrics(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose="Too short.", sections=("Too short.",), sentences=("Too short.",)
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert "readability" not in metrics
        assert "grade_level" not in metrics

    def test_evaluate_two_sentence_document_drops_smog(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sections=(" ".join(["word"] * 20),),
            sentences=("First sentence here.", "Second sentence here."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert "smog" not in metrics
        assert "readability" in metrics

    # --- hedging and passive voice ---

    def test_hedging_one_of_two_sentences_returns_half_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("This is perhaps true.", "This is false."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["hedging"] == pytest.approx(50.0)

    def test_hedging_repeated_word_in_one_sentence_counts_once(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("Perhaps perhaps perhaps it works.", "It works."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["hedging"] == pytest.approx(50.0)

    def test_passive_voice_one_of_two_sentences_returns_half_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("The build was written by hand.", "It works."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["passive_voice"] == pytest.approx(50.0)

    def test_hedging_single_hedged_sentence_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("It is perhaps true.",),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["hedging"] == pytest.approx(0.0)

    def test_hedging_sentence_final_hedge_word_counts(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("It is perhaps.", "It works."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["hedging"] == pytest.approx(50.0)

    def test_hedging_hedge_lookalike_with_trailing_capital_x_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("It is perhapsX.", "It works."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["hedging"] == pytest.approx(100.0)

    # --- grade_level and smog ---

    def test_grade_level_simple_prose_returns_expected_score(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=ENGLISH_PROSE,
            sections=(ENGLISH_PROSE,),
            sentences=ENGLISH_SENTENCES,
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["grade_level"] == pytest.approx(88.0)

    def test_smog_simple_prose_returns_expected_score(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=ENGLISH_PROSE,
            sections=(ENGLISH_PROSE,),
            sentences=ENGLISH_SENTENCES,
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["smog"] == pytest.approx(84.3545)

    def test_smog_exactly_three_sentences_is_measured(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            prose=" ".join(["word"] * 20),
            sentences=("One two.", "Three four.", "Five six."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert "smog" in metrics

    # --- heading_hierarchy ---

    def test_heading_hierarchy_fewer_than_two_headings_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(headings=("Title",), heading_levels=(1,), heading_lines=(1,))
        metrics, findings = MannerMetrics.evaluate(features, "en")
        assert metrics["heading_hierarchy"] == 100.0
        assert findings == []

    def test_heading_hierarchy_descending_by_one_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            headings=("Title", "Step"),
            heading_levels=(1, 2),
            heading_lines=(1, 5),
        )
        metrics, findings = MannerMetrics.evaluate(features, "en")
        assert metrics["heading_hierarchy"] == 100.0
        assert findings == []

    def test_heading_hierarchy_skipped_level_returns_zero_and_a_finding(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            path="docs/a.md",
            headings=("Title", "Deep"),
            heading_levels=(1, 3),
            heading_lines=(1, 10),
        )
        metrics, findings = MannerMetrics.evaluate(features, "en")
        assert metrics["heading_hierarchy"] == 0.0
        assert len(findings) == 1
        assert findings[0].file == "docs/a.md"
        assert findings[0].line == 10
        assert findings[0].description == "heading 'Deep' jumps from level 1 to 3"

    def test_heading_hierarchy_one_skip_of_two_transitions_returns_half_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            headings=("Title", "Step", "Deep"),
            heading_levels=(1, 2, 4),
            heading_lines=(1, 5, 9),
        )
        metrics, findings = MannerMetrics.evaluate(features, "en")
        assert metrics["heading_hierarchy"] == pytest.approx(50.0)
        assert len(findings) == 1

    def test_heading_hierarchy_deeper_first_heading_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            headings=("Deep", "Top"),
            heading_levels=(3, 1),
            heading_lines=(1, 10),
        )
        metrics, findings = MannerMetrics.evaluate(features, "en")
        assert metrics["heading_hierarchy"] == 100.0
        assert findings == []

    def test_heading_hierarchy_skip_finding_carries_category_and_severity(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            path="docs/a.md",
            headings=("Title", "Deep"),
            heading_levels=(1, 3),
            heading_lines=(1, 10),
        )
        _, findings = MannerMetrics.evaluate(features, "en")
        assert findings[0].category == "grice"
        assert findings[0].severity == "low"

    # --- sentence_length ---

    def test_sentence_length_no_sentences_is_not_measured(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(sentences=())
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert "sentence_length" not in metrics

    def test_sentence_length_one_long_sentence_returns_half_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(
            sentences=(" ".join(["word"] * 30), "Short sentence."),
        )
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["sentence_length"] == pytest.approx(50.0)

    def test_sentence_length_all_short_sentences_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(sentences=("One short sentence.", "Another short one."))
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["sentence_length"] == 100.0

    def test_sentence_length_exactly_max_words_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(sentences=(" ".join(["word"] * 25),))
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["sentence_length"] == 100.0

    # --- section_structure ---

    def test_section_structure_no_sections_is_not_measured(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        features = make_features(sections=())
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert "section_structure" not in metrics

    def test_section_structure_sections_in_range_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        section = " ".join(["word"] * 30)
        features = make_features(prose=section, sections=(section, section))
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["section_structure"] == 100.0

    def test_section_structure_stub_and_sprawl_returns_zero(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        stub = "word"
        sprawl = " ".join(["word"] * 401)
        features = make_features(prose=f"{stub} {sprawl}", sections=(stub, sprawl))
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["section_structure"] == 0.0

    def test_section_structure_exactly_min_words_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        section = " ".join(["word"] * 20)
        features = make_features(prose=section, sections=(section,))
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["section_structure"] == 100.0

    def test_section_structure_exactly_max_words_returns_full_marks(
        self, make_features: Callable[..., DocumentFeatures]
    ) -> None:
        section = " ".join(["word"] * 400)
        features = make_features(prose=section, sections=(section,))
        metrics, _ = MannerMetrics.evaluate(features, "en")
        assert metrics["section_structure"] == 100.0

    # --- _clamp ---

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (150.0, 100.0),
            (-12.0, 0.0),
            (42.0, 42.0),
        ],
        ids=[
            "raw_above_hundred_clamps_to_hundred",
            "raw_below_zero_clamps_to_zero",
            "raw_inside_range_is_unchanged",
        ],
    )
    def test_clamp_out_of_range_value_returns_bounded_score(
        self, raw: float, expected: float
    ) -> None:
        assert MannerMetrics._clamp(raw) == expected
