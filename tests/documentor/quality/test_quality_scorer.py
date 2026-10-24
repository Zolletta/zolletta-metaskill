"""Comprehensive tests for quality_scorer.py."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

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

    def test_no_git_history(self, tmp_path: Path) -> None:
        with self._patch_git(last_commit=None):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 50.0
            assert "reason" in details

    def test_now_recent_returns_100_0(self, tmp_path: Path) -> None:
        recent = datetime.now(UTC) - timedelta(days=3)
        with self._patch_git(last_commit=recent):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_now_30_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=20)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 80 <= score <= 100

    def test_now_90_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=60)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 50 <= score < 80

    def test_now_180_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=120)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 25 <= score < 50

    def test_now_365_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=250)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 10 <= score < 25

    def test_now_very_old_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=500)
        with self._patch_git(last_commit=dt):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == pytest.approx(7.3)

    def test_now_naive_datetime_returns_100_0(self, tmp_path: Path) -> None:
        recent = datetime.now() - timedelta(days=3)
        with self._patch_git(last_commit=recent):
            score, details = QualityScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 100.0

    # --- score_code_doc_alignment ---

    def test_score_code_doc_alignment_no_file_returns_50_0(self, tmp_path: Path) -> None:
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "nonexistent.md")
        assert score == 50.0

    def test_no_refs_no_git(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content without refs.\n")
        with self._patch_git(last_commit=None):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 70.0

    def test_no_refs_with_git_no_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with self._patch_git(last_commit=dt, code_changes=0):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_no_refs_with_git_few_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with self._patch_git(last_commit=dt, code_changes=3):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 80.0

    def test_no_refs_with_git_many_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with self._patch_git(last_commit=dt, code_changes=25):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 40.0

    def test_no_refs_with_git_moderate_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with self._patch_git(last_commit=dt, code_changes=10):
            score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 60.0

    def test_with_refs_all_exist(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee [module](module.py).\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details["referenced_files"] == 1
        assert details["existing_files"] == 1

    def test_with_refs_none_exist(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee [module](missing.py).\n")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_backtick_file_refs(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee `module.py`.\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_ref_resolved_from_repo_root(self, tmp_path: Path) -> None:
        """File ref that doesn't exist relative to doc dir but exists at repo root."""
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\nSee [module](module.py).\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = QualityScorer.score_code_doc_alignment(str(tmp_path), "docs/doc.md")
        assert score == 100.0
        assert details["existing_files"] == 1

    # --- score_link_health ---

    def test_score_link_health_no_file_returns_100_0(self, tmp_path: Path) -> None:
        score, details = QualityScorer.score_link_health(str(tmp_path), "nonexistent.md")
        assert score == 100.0

    def test_score_link_health_no_links_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nNo links here.\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_valid_file_link(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md)\n")
        (tmp_path / "other.md").write_text("# Other")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details["valid_links"] == 1

    def test_broken_file_link(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](missing.md)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0
        assert "missing.md" in details["broken_links"]

    def test_anchor_only_valid(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n## Section\n\n[link](#section)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_anchor_only_broken(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](#missing)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_cross_doc_anchor_valid(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#section)\n")
        (tmp_path / "other.md").write_text("# Other\n\n## Section\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_cross_doc_anchor_broken(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#missing)\n")
        (tmp_path / "other.md").write_text("# Other\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_external_links_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](https://example.com)\n")
        score, details = QualityScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_empty_anchor_link(self, tmp_path: Path) -> None:
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

    def test_slugify_leading_trailing_hyphens(self) -> None:
        assert QualityScorer._slugify("--Hello--") == "hello"

    # --- score_document ---

    def test_score_document_basic_input_returns_set(self, tmp_path: Path) -> None:
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
