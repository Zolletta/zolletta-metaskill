"""Tests for DocCompletenessScorer."""

from __future__ import annotations

import json
from pathlib import Path

from zolletta_metaskill.documentor.doc_completeness_scorer import DocCompletenessScorer


class TestDocCompletenessScorer:
    """Tests for document completeness and Diátaxis quadrant scoring."""

    # --- Quadrant Detection ---

    def test_detect_diataxis_quadrant_tutorials(self) -> None:
        """Detect tutorials quadrant from doc path."""
        quad = DocCompletenessScorer.detect_diataxis_quadrant("docs/tutorials/quickstart.md")
        assert quad is not None
        assert "what we will learn" in quad["required_sections"]

    def test_detect_diataxis_quadrant_how_to(self) -> None:
        """Detect how-to quadrant from doc path."""
        quad = DocCompletenessScorer.detect_diataxis_quadrant("docs/how-to/configure.md")
        assert quad is not None

    def test_detect_diataxis_quadrant_reference(self) -> None:
        """Detect reference quadrant from doc path."""
        quad = DocCompletenessScorer.detect_diataxis_quadrant("docs/reference/api.md")
        assert quad is not None

    def test_detect_diataxis_quadrant_explanation(self) -> None:
        """Detect explanation quadrant from doc path."""
        quad = DocCompletenessScorer.detect_diataxis_quadrant("docs/explanation/design.md")
        assert quad is not None

    def test_detect_diataxis_quadrant_no_quadrant(self) -> None:
        """Return None when path does not match any quadrant."""
        assert DocCompletenessScorer.detect_diataxis_quadrant("README.md") is None

    # --- Translations ---

    def test_load_and_merge_translations(self, tmp_path: Path) -> None:
        """Load translated Diátaxis signposts and merge into quadrants."""
        trans_file = tmp_path / "translations.json"
        trans_file.write_text(
            json.dumps(
                {
                    "readme_sections": ["installazione", "uso"],
                    "quadrants": {
                        "how-to": {
                            "dir_names": ["guide-pratiche"],
                            "any_of_groups": [["prerequisiti"]],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        loaded = DocCompletenessScorer.load_diataxis_translations(str(trans_file))
        assert loaded["readme_sections"] == ["installazione", "uso"]
        original = {k: dict(v) for k, v in DocCompletenessScorer.DIATAXIS_QUADRANTS.items()}
        try:
            DocCompletenessScorer.merge_translations(loaded)
            quad = DocCompletenessScorer.detect_diataxis_quadrant("docs/guide-pratiche/start.md")
            assert quad is not None
        finally:
            for k, v in original.items():
                DocCompletenessScorer.DIATAXIS_QUADRANTS[k].clear()
                DocCompletenessScorer.DIATAXIS_QUADRANTS[k].update(v)

    # --- Completeness Scoring ---

    def test_score_completeness_missing_file_returns_0(self, tmp_path: Path) -> None:
        """Missing file returns 0.0 completeness."""
        score, details = DocCompletenessScorer.score_completeness(
            str(tmp_path), "missing.md", ["Usage"]
        )
        assert score == 0.0
        assert details["expected_sections"] == ["Usage"]

    def test_score_completeness_all_sections_present(self, tmp_path: Path) -> None:
        """Doc with all required sections scores 100."""
        doc = tmp_path / "doc.md"
        doc.write_text(
            "# Title\n\n## Installation\nSteps\n\n## Usage\nExample\n\n## License\nMIT\n" * 5,
            encoding="utf-8",
        )
        score, details = DocCompletenessScorer.score_completeness(
            str(tmp_path), "doc.md", ["Installation", "Usage", "License"]
        )
        assert score == 100.0
        assert "Installation" in details["found_sections"]
        assert "Usage" in details["found_sections"]
        assert "License" in details["found_sections"]
