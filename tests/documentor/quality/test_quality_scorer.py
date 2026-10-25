"""Comprehensive tests for quality_scorer.py."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.quality.doc_accuracy_scorer import DocAccuracyScorer
from zolletta_metaskill.documentor.quality.doc_completeness_scorer import DocCompletenessScorer
from zolletta_metaskill.documentor.quality.quality_scorer import QualityScorer
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class TestQualityScorer:
    # --- get_label ---

    def test_get_label_excellent_returns_excellent(self) -> None:
        assert QualityScorer.get_label(95) == "excellent"

    def test_get_label_good_returns_good(self) -> None:
        assert QualityScorer.get_label(75) == "good"

    def test_get_label_stale_returns_stale(self) -> None:
        assert QualityScorer.get_label(55) == "stale"

    def test_get_label_critical_returns_critical(self) -> None:
        assert QualityScorer.get_label(35) == "critical"

    def test_get_label_abandoned_returns_abandoned(self) -> None:
        assert QualityScorer.get_label(10) == "abandoned"

    def test_get_label_unknown_returns_unknown(self) -> None:
        assert QualityScorer.get_label(101) == "unknown"

    def test_get_label_boundary_90_returns_good(self) -> None:
        assert QualityScorer.get_label(90) == "good"

    def test_get_label_boundary_0_returns_abandoned(self) -> None:
        assert QualityScorer.get_label(0) == "abandoned"

    @staticmethod
    def _patch_git(
        last_commit: datetime | None = None,
        code_changes: int | None = None,
    ) -> ExitStack:
        """Patch the GitHelper reads the scorers make; second patch only when given."""
        stack = ExitStack()
        stack.enter_context(
            patch.object(GitHelper, "get_file_last_commit_date", return_value=last_commit)
        )
        if code_changes is not None:
            stack.enter_context(
                patch.object(GitHelper, "get_code_changes_since", return_value=code_changes)
            )
        return stack

    # --- score_last_updated ---

    def test_score_last_updated_no_history_returns_reason_details(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "get_file_last_commit_date", return_value=None) as last_commit:
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 50.0
            assert details == {"reason": "No git history found"}
            last_commit.assert_called_once_with(str(tmp_path), "doc.md")

    def test_score_last_updated_naive_datetime_returns_100_0(self, tmp_path: Path) -> None:
        recent = datetime.now() - timedelta(days=3)
        with self._patch_git(last_commit=recent):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_score_last_updated_recent_records_details(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=3)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 100.0
            assert details == {
                "last_modified": dt.strftime("%Y-%m-%d"),
                "days_ago": 3,
            }

    @pytest.mark.parametrize(
        ("days", "expected"),
        [
            (7, 100.0),
            (8, 89.6),
            (30, 80.8),
            (31, 79.5),
            (89, 50.5),
            (90, 50.0),
            (91, 49.7),
            (180, 23.0),
            (181, 24.9),
            (365, 6.5),
            (366, 9.98),
            (500, 7.3),
            (900, 0.0),
        ],
        ids=[
            "test_last_updated_days_7_returns_100_0",
            "test_last_updated_days_8_returns_89_6",
            "test_last_updated_days_30_returns_80_8",
            "test_last_updated_days_31_returns_79_5",
            "test_last_updated_days_89_returns_50_5",
            "test_last_updated_days_90_returns_50_0",
            "test_last_updated_days_91_returns_49_7",
            "test_last_updated_days_180_returns_23_0",
            "test_last_updated_days_181_returns_24_9",
            "test_last_updated_days_365_returns_6_5",
            "test_last_updated_days_366_returns_9_98",
            "test_last_updated_days_500_returns_7_3",
            "test_last_updated_days_900_returns_0_0",
        ],
    )
    def test_score_last_updated_day_boundary_returns_exact_score(
        self, tmp_path: Path, days: int, expected: float
    ) -> None:
        dt = datetime.now(UTC) - timedelta(days=days)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == pytest.approx(expected, abs=0.01)
            assert details["days_ago"] == days

    # --- score_code_doc_alignment ---

    def test_score_code_doc_alignment_no_file_returns_50_0(self, tmp_path: Path) -> None:
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "nonexistent.md")
        assert score == 50.0
        assert details == {
            "referenced_files": 0,
            "existing_files": 0,
            "referenced_functions": 0,
        }

    def test_score_code_doc_alignment_no_refs_calls_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content without refs.\n")
        with patch.object(
            QualityScorer, "_score_fallback_alignment", return_value=42.0
        ) as fallback:
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 42.0
            fallback.assert_called_once_with(
                str(tmp_path),
                "doc.md",
                {"referenced_files": 0, "existing_files": 0, "referenced_functions": 0},
            )

    def test_score_code_doc_alignment_fallback_reads_git(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime(2020, 1, 15, tzinfo=UTC)
        with (
            patch.object(GitHelper, "get_file_last_commit_date", return_value=dt) as last,
            patch.object(GitHelper, "get_code_changes_since", return_value=3) as changes,
        ):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "sub/doc.md")
            assert score == 80.0
            assert details == {
                "referenced_files": 0,
                "existing_files": 0,
                "referenced_functions": 0,
                "code_changes_since_update": 3,
            }
            last.assert_called_with(str(tmp_path), "sub/doc.md")
            changes.assert_called_once_with(str(tmp_path), "2020-01-15", "sub")

    def test_score_code_doc_alignment_fallback_no_history_returns_70_0(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        with self._patch_git(last_commit=None):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 70.0
            assert details == {
                "referenced_files": 0,
                "existing_files": 0,
                "referenced_functions": 0,
            }

    @pytest.mark.parametrize(
        ("changes", "expected"),
        [(0, 100.0), (4, 80.0), (5, 60.0), (19, 60.0), (20, 40.0)],
        ids=[
            "test_fallback_changes_0_returns_100_0",
            "test_fallback_changes_4_returns_80_0",
            "test_fallback_changes_5_returns_60_0",
            "test_fallback_changes_19_returns_60_0",
            "test_fallback_changes_20_returns_40_0",
        ],
    )
    def test_score_code_doc_alignment_fallback_change_band_returns_exact_score(
        self, tmp_path: Path, changes: int, expected: float
    ) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with self._patch_git(last_commit=dt, code_changes=changes):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == expected
            assert details["code_changes_since_update"] == changes

    def test_score_code_doc_alignment_all_refs_exist_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee [module](module.py) and `other.py`.\n")
        (tmp_path / "module.py").write_text("# code")
        (tmp_path / "other.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details == {
            "referenced_files": 2,
            "existing_files": 2,
            "referenced_functions": 0,
        }

    def test_score_code_doc_alignment_half_refs_exist_returns_50_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "# Title\n\nSee [module](module.py) and [gone](gone.py).\n"
        )
        (tmp_path / "module.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 50.0
        assert details == {
            "referenced_files": 2,
            "existing_files": 1,
            "referenced_functions": 0,
        }

    def test_score_code_doc_alignment_no_refs_exist_returns_0_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee [module](missing.py).\n")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_score_code_doc_alignment_ref_resolved_from_repo_root(self, tmp_path: Path) -> None:
        """File ref that doesn't exist relative to doc dir but exists at repo root."""
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\nSee [module](module.py).\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "docs/doc.md")
        assert score == 100.0
        assert details["existing_files"] == 1

    def test_score_code_doc_alignment_ref_resolved_from_doc_dir(self, tmp_path: Path) -> None:
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\nSee [module](module.py).\n")
        (sub / "module.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "docs/doc.md")
        assert score == 100.0
        assert details["existing_files"] == 1

    def test_score_code_doc_alignment_two_root_refs_exist_returns_100_0(
        self, tmp_path: Path
    ) -> None:
        """Both refs miss the doc dir and resolve via the repo-root fallback."""
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\n[a](r1.py) [b](r2.py)\n")
        (tmp_path / "r1.py").write_text("# code")
        (tmp_path / "r2.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "docs/doc.md")
        assert score == 100.0
        assert details["existing_files"] == 2

    # --- _extract_alignment_refs ---

    def test_extract_alignment_refs_fragment_target_returns_bare_path(self) -> None:
        refs = QualityScorer._extract_alignment_refs("[a](m.py#sec)\n")
        assert refs == {"m.py"}

    def test_extract_alignment_refs_empty_target_returns_empty(self) -> None:
        assert QualityScorer._extract_alignment_refs("[a]()\n") == set()

    def test_extract_alignment_refs_external_schemes_returns_empty(self) -> None:
        content = "[a](http://x) [b](https://y) [c](mailto:z@w)\n"
        assert QualityScorer._extract_alignment_refs(content) == set()

    def test_extract_alignment_refs_backtick_doc_exts_returns_refs(self) -> None:
        content = "`a.md` `b.rst` `c.txt` `d.adoc` `e.py`\n"
        assert QualityScorer._extract_alignment_refs(content) == {
            "a.md",
            "b.rst",
            "c.txt",
            "d.adoc",
            "e.py",
        }

    def test_extract_alignment_refs_backtick_unknown_ext_returns_empty(self) -> None:
        assert QualityScorer._extract_alignment_refs("`a.weirdext`\n") == set()

    # --- score_link_health ---

    def test_score_link_health_no_file_returns_100_0(self, tmp_path: Path) -> None:
        score, details = QualityScorer.score_link_health(str(tmp_path), "nonexistent.md")
        assert score == 100.0
        assert details == {"total_links": 0, "valid_links": 0, "broken_links": []}

    def test_score_link_health_no_links_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nNo links here.\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details == {"total_links": 0, "valid_links": 0, "broken_links": []}

    def test_score_link_health_external_links_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "# Title\n\n[a](http://x) [b](https://y) [c](mailto:z@w)\n"
        )
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details == {"total_links": 0, "valid_links": 0, "broken_links": []}

    def test_score_link_health_valid_file_link_returns_details(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md)\n")
        (tmp_path / "other.md").write_text("# Other")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details == {"total_links": 1, "valid_links": 1, "broken_links": []}

    def test_score_link_health_broken_file_link_returns_details(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](missing.md)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0
        assert details == {
            "total_links": 1,
            "valid_links": 0,
            "broken_links": ["missing.md"],
        }

    def test_score_link_health_half_valid_returns_50_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[ok](other.md) [bad](missing.md)\n")
        (tmp_path / "other.md").write_text("# Other")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 50.0
        assert details["valid_links"] == 1
        assert details["total_links"] == 2

    def test_score_link_health_anchor_only_valid_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n## Section\n\n[link](#section)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_score_link_health_anchor_only_broken_returns_0_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](#missing)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0
        assert details["broken_links"] == ["#missing"]

    def test_score_link_health_cross_doc_anchor_valid_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#section)\n")
        (tmp_path / "other.md").write_text("# Other\n\n## Section\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_score_link_health_cross_doc_anchor_broken_returns_0_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#missing)\n")
        (tmp_path / "other.md").write_text("# Other\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0
        assert details["broken_links"] == ["other.md#missing"]

    def test_score_link_health_multi_fragment_link_valid_returns_100_0(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#a#b)\n")
        (tmp_path / "other.md").write_text("# Other\n\n## a#b\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_score_link_health_rst_anchor_broken_returns_0_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.rst#nope)\n")
        (tmp_path / "other.rst").write_text("# Other\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0
        assert details["broken_links"] == ["other.rst#nope"]

    def test_score_link_health_doc_dir_link_valid_returns_100_0(self, tmp_path: Path) -> None:
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\n[link](sibling.md)\n")
        (sub / "sibling.md").write_text("# Sib")
        score, details = QualityScorer.score_link_health(str(tmp_path), "docs/doc.md")
        assert score == 100.0

    def test_score_link_health_root_link_valid_returns_100_0(self, tmp_path: Path) -> None:
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\n[link](rootfile.md)\n")
        (tmp_path / "rootfile.md").write_text("# Root")
        score, details = QualityScorer.score_link_health(str(tmp_path), "docs/doc.md")
        assert score == 100.0

    def test_score_link_health_empty_anchor_returns_valid(self, tmp_path: Path) -> None:
        """A link to just '#' (no file, no anchor) counts as valid."""
        (tmp_path / "doc.md").write_text("# Title\n\n[empty](#)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details["valid_links"] == 1

    # --- _extract_headings / _slugify ---

    def test_extract_headings_basic_input_contains_section_two(self) -> None:
        content = "# Title\n\n## Section Two\n"
        headings = QualityScorer._extract_headings(content)
        assert "title" in headings
        assert "section-two" in headings

    def test_extract_headings_no_headings_succeeds(self) -> None:
        assert QualityScorer._extract_headings("just text\n") == set()

    def test_slugify_basic_input_returns_hello_world(self) -> None:
        assert QualityScorer._slugify("Hello World") == "hello-world"

    def test_slugify_special_chars_returns_hello_world(self) -> None:
        assert QualityScorer._slugify("Hello, World!") == "hello-world"

    def test_slugify_multiple_spaces_returns_hello_world(self) -> None:
        assert QualityScorer._slugify("Hello   World") == "hello-world"

    def test_slugify_leading_trailing_hyphens_returns_hello(self) -> None:
        assert QualityScorer._slugify("--Hello--") == "hello"

    # --- score_document ---

    def test_score_document_fixed_scores_returns_exact_result(self, tmp_path: Path) -> None:
        weights = {
            "last_updated": 0.2,
            "code_doc_alignment": 0.35,
            "link_health": 0.1,
            "completeness": 0.25,
            "accuracy": 0.15,
        }
        quadrants = {"custom": {"dir_names": {"x"}, "required_sections": []}}
        required = ["Installation"]
        with (
            patch.object(
                QualityScorer,
                "score_last_updated",
                return_value=(83.25, {"u": 1}),
            ) as m_updated,
            patch.object(
                QualityScorer,
                "score_code_doc_alignment",
                return_value=(66.65, {"a": 2}),
            ) as m_align,
            patch.object(
                QualityScorer,
                "score_link_health",
                return_value=(33.35, {"l": 3}),
            ) as m_links,
            patch.object(
                DocCompletenessScorer,
                "score_completeness",
                return_value=(91.15, {"c": 4}),
            ) as m_compl,
            patch.object(
                DocAccuracyScorer,
                "score_accuracy",
                return_value=(47.45, {"ac": 5}),
            ) as m_acc,
            patch.object(GitHelper, "get_latest_tag", return_value="v1.2.3") as m_tag,
        ):
            result = QualityScorer.score_document(
                str(tmp_path), "doc.md", weights, required, quadrants
            )
        assert result == {
            "file": "doc.md",
            "total_score": 73.2,
            "label": "good",
            "dimensions": {
                "last_updated": {
                    "score": 83.2,
                    "weight": 0.2,
                    "weighted": 16.7,
                    "details": {"u": 1},
                },
                "code_doc_alignment": {
                    "score": 66.7,
                    "weight": 0.35,
                    "weighted": 23.3,
                    "details": {"a": 2},
                },
                "link_health": {
                    "score": 33.4,
                    "weight": 0.1,
                    "weighted": 3.3,
                    "details": {"l": 3},
                },
                "completeness": {
                    "score": 91.2,
                    "weight": 0.25,
                    "weighted": 22.8,
                    "details": {"c": 4},
                },
                "accuracy": {
                    "score": 47.5,
                    "weight": 0.15,
                    "weighted": 7.1,
                    "details": {"ac": 5},
                },
            },
        }
        m_updated.assert_called_once_with(str(tmp_path), "doc.md")
        m_align.assert_called_once_with(str(tmp_path), "doc.md")
        m_links.assert_called_once_with(str(tmp_path), "doc.md")
        m_compl.assert_called_once_with(str(tmp_path), "doc.md", required, quadrants)
        m_acc.assert_called_once_with(str(tmp_path), "doc.md", latest_tag="v1.2.3")
        m_tag.assert_called_once_with(str(tmp_path))

    def test_score_document_basic_input_returns_dimensions(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "# Installation\n\n# Usage\n\n# API\n\n" + "content\n" * 15
        )
        with (
            patch.object(GitHelper, "get_file_last_commit_date", return_value=None),
            patch.object(GitHelper, "get_latest_tag", return_value=None),
        ):
            result = QualityScorer.score_document(
                str(tmp_path),
                "doc.md",
                DocumentorSettings.DEFAULT_WEIGHTS,
                list(DocumentorSettings.DEFAULT_README_SECTIONS),
            )
            assert "total_score" in result
            assert "label" in result
            assert "dimensions" in result
            assert set(result["dimensions"].keys()) == {
                "last_updated",
                "code_doc_alignment",
                "link_health",
                "completeness",
                "accuracy",
            }
