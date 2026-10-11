"""Tests for DocCompletenessScorer."""

from __future__ import annotations

import json
from pathlib import Path

from zolletta_metaskill.documentor.quality.doc_completeness_scorer import DocCompletenessScorer


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
        """Load translated signposts and merge them into a new quadrant mapping."""
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
        quadrants = DocCompletenessScorer.merged_quadrants(loaded)
        quad = DocCompletenessScorer.detect_diataxis_quadrant(
            "docs/guide-pratiche/start.md", quadrants
        )
        assert quad is not None
        assert "guide-pratiche" in quad["dir_names"]

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

    # --- Translations Edge Cases ---

    def test_load_translations_non_dict_payload_returns_empty(self, tmp_path: Path) -> None:
        """A JSON payload that is not an object yields empty quadrants."""
        trans_file = tmp_path / "translations.json"
        trans_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
        loaded = DocCompletenessScorer.load_diataxis_translations(str(trans_file))
        assert loaded == {"readme_sections": None, "quadrants": {}}

    def test_load_translations_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """A missing translations file yields empty quadrants instead of raising."""
        loaded = DocCompletenessScorer.load_diataxis_translations(str(tmp_path / "missing.json"))
        assert loaded == {"readme_sections": None, "quadrants": {}}

    def test_load_translations_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        """Malformed JSON yields empty quadrants instead of raising."""
        trans_file = tmp_path / "translations.json"
        trans_file.write_text("{not valid json", encoding="utf-8")
        loaded = DocCompletenessScorer.load_diataxis_translations(str(trans_file))
        assert loaded == {"readme_sections": None, "quadrants": {}}

    def test_merge_translations_skips_non_dict_quadrant(self) -> None:
        """Quadrant entries that are not objects are ignored."""
        quadrants = DocCompletenessScorer.merged_quadrants({"quadrants": {"recipes": "not-a-dict"}})
        assert "recipes" not in quadrants

    def test_merged_quadrants_lowercases_required_sections(self) -> None:
        """Translated required sections are lower-cased into the returned mapping."""
        quadrants = DocCompletenessScorer.merged_quadrants(
            {
                "quadrants": {
                    "recipes": {
                        "dir_names": ["Recetas"],
                        "required_sections": ["Ingredients", "Steps"],
                    }
                }
            }
        )
        quad = quadrants["recipes"]
        assert quad["dir_names"] == {"recetas"}
        assert quad["required_sections"] == ["ingredients", "steps"]

    def test_merged_quadrants_does_not_mutate_class_attribute(self) -> None:
        """The class attribute is never touched — that was the whole point."""
        before = DocCompletenessScorer.DIATAXIS_QUADRANTS
        snapshot = {
            k: {kk: set(vv) if isinstance(vv, set) else list(vv) for kk, vv in q.items()}
            for k, q in before.items()
        }
        DocCompletenessScorer.merged_quadrants(
            {
                "quadrants": {
                    "how-to": {"dir_names": ["guide-pratiche"]},
                    "brand-new": {"dir_names": ["nuovo"]},
                }
            }
        )
        assert DocCompletenessScorer.DIATAXIS_QUADRANTS is before
        assert set(before) == set(snapshot)
        for name, quad in snapshot.items():
            current = before[name]
            assert set(current["dir_names"]) == set(quad["dir_names"])
            assert current["required_sections"] == quad["required_sections"]

    def test_merged_quadrants_is_idempotent_across_calls(self) -> None:
        """Two calls with the same input produce equal, independent results."""
        payload = {"quadrants": {"how-to": {"dir_names": ["guide-pratiche"]}}}
        first = DocCompletenessScorer.merged_quadrants(payload)
        second = DocCompletenessScorer.merged_quadrants(payload)
        assert first["how-to"]["dir_names"] == second["how-to"]["dir_names"]
        first["how-to"]["dir_names"].add("mutated")
        assert "mutated" not in second["how-to"]["dir_names"]
        assert "mutated" not in DocCompletenessScorer.DIATAXIS_QUADRANTS["how-to"]["dir_names"]

    # --- Diataxis Structure Scoring ---

    def test_score_completeness_diataxis_overrides_required_sections(self, tmp_path: Path) -> None:
        """A how-to doc uses the quadrant signposts instead of the requested sections."""
        how_to = tmp_path / "docs" / "how-to"
        how_to.mkdir(parents=True)
        (how_to / "configure.md").write_text(
            "# Configure\n\n## Prerequisites\n\nInstall it.\n", encoding="utf-8"
        )
        score, details = DocCompletenessScorer.score_completeness(
            str(tmp_path), "docs/how-to/configure.md", ["Totally Unrelated"]
        )
        assert details["doc_structure"] == "diataxis"
        assert details["expected_sections"] == []
        assert details["any_of_groups_found"] == 1
        assert details["any_of_groups_missing"] == []
        assert score == 100.0

    def test_score_completeness_diataxis_missing_group_returns_0(self, tmp_path: Path) -> None:
        """A how-to doc without any signpost from the group scores zero."""
        how_to = tmp_path / "docs" / "how-to"
        how_to.mkdir(parents=True)
        (how_to / "configure.md").write_text("# Configure\n\nJust do it.\n", encoding="utf-8")
        score, details = DocCompletenessScorer.score_completeness(
            str(tmp_path), "docs/how-to/configure.md", []
        )
        assert details["any_of_groups_found"] == 0
        assert details["any_of_groups_missing"] == [["prerequisites", "before starting"]]
        assert score == 0.0

    # --- Length Penalty ---

    def test_short_doc_applies_full_length_penalty(self, tmp_path: Path) -> None:
        """A non-Diataxis doc under ten lines loses the full 30 point penalty."""
        (tmp_path / "doc.md").write_text("# Title\none line\n", encoding="utf-8")
        score, details = DocCompletenessScorer.score_completeness(
            str(tmp_path), "doc.md", ["Installation"]
        )
        assert details["missing_sections"] == ["Installation"]
        assert score == 0.0

    def test_no_requirements_uses_length_penalty_only(self, tmp_path: Path) -> None:
        """With no requirements the score is 100 minus the length penalty."""
        (tmp_path / "doc.md").write_text("# Title\none line\n", encoding="utf-8")
        score, details = DocCompletenessScorer.score_completeness(str(tmp_path), "doc.md", [])
        assert score == 70.0
        assert details["found_sections"] == []
