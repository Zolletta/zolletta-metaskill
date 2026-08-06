"""Comprehensive tests for doc_staleness_scorer.py."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.doc_staleness_scorer import DocStalenessScorer

# ---------------------------------------------------------------------------
# _load_gitignore_patterns
# ---------------------------------------------------------------------------


class TestLoadGitignorePatterns:
    def test_load_gitignore_patterns_no_gitignore_succeeds(self, tmp_path: Path) -> None:
        assert DocStalenessScorer._load_gitignore_patterns(str(tmp_path)) == set()

    def test_load_gitignore_patterns_simple_entries_excludes_value(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(".venv/\nnode_modules/\n*.pyc\n")
        patterns = DocStalenessScorer._load_gitignore_patterns(str(tmp_path))
        assert ".venv" in patterns
        assert "node_modules" in patterns
        # *.pyc has wildcard, should be skipped
        assert "*.pyc" not in patterns

    def test_comments_and_negation(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("# comment\n!important\nbuild/\n")
        patterns = DocStalenessScorer._load_gitignore_patterns(str(tmp_path))
        assert "build" in patterns
        assert "important" not in patterns

    def test_load_gitignore_patterns_nested_path_contains_bar(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("foo/bar/\n")
        patterns = DocStalenessScorer._load_gitignore_patterns(str(tmp_path))
        assert "bar" in patterns

    def test_oserror_returns_empty(self, tmp_path: Path) -> None:
        # Create a directory named .gitignore (causes OSError on open)
        (tmp_path / ".gitignore").mkdir()
        patterns = DocStalenessScorer._load_gitignore_patterns(str(tmp_path))
        assert patterns == set()


# ---------------------------------------------------------------------------
# get_label
# ---------------------------------------------------------------------------


class TestGetLabel:
    def test_get_label_excellent_returns_excellent(self) -> None:
        assert DocStalenessScorer.get_label(95) == "excellent"

    def test_get_label_good_returns_good(self) -> None:
        assert DocStalenessScorer.get_label(75) == "good"

    def test_get_label_stale_returns_stale(self) -> None:
        assert DocStalenessScorer.get_label(55) == "stale"

    def test_get_label_critical_returns_critical(self) -> None:
        assert DocStalenessScorer.get_label(35) == "critical"

    def test_get_label_abandoned_returns_abandoned(self) -> None:
        assert DocStalenessScorer.get_label(10) == "abandoned"

    def test_get_label_unknown_returns_unknown(self) -> None:
        assert DocStalenessScorer.get_label(101) == "unknown"

    def test_get_label_boundary_90_returns_good(self) -> None:
        assert DocStalenessScorer.get_label(90) == "good"

    def test_get_label_boundary_0_returns_abandoned(self) -> None:
        assert DocStalenessScorer.get_label(0) == "abandoned"


# ---------------------------------------------------------------------------
# run_git / git helpers
# ---------------------------------------------------------------------------


class TestRunGit:
    def test_run_git_success_returns_output(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "output\n"})()
            result = DocStalenessScorer.run_git(str(tmp_path), ["status"])
            assert result == "output"

    def test_run_git_failure_returns_def(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 1, "stdout": ""})()
            result = DocStalenessScorer.run_git(str(tmp_path), ["status"], default="def")
            assert result == "def"

    def test_run_git_timeout_returns_empty(self, tmp_path: Path) -> None:
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
            result = DocStalenessScorer.run_git(str(tmp_path), ["status"])
            assert result == ""

    def test_run_git_filenotfound_returns_empty(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = DocStalenessScorer.run_git(str(tmp_path), ["status"])
            assert result == ""


class TestGetFileLastCommitDate:
    def test_object_valid_date_returns_2024(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value="2024-01-15T10:00:00+00:00"):
            dt = DocStalenessScorer.get_file_last_commit_date(str(tmp_path), "doc.md")
            assert dt is not None
            assert dt.year == 2024

    def test_object_empty_input_returns_none(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value=""):
            assert DocStalenessScorer.get_file_last_commit_date(str(tmp_path), "doc.md") is None

    def test_object_invalid_date_returns_none(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value="not-a-date"):
            assert DocStalenessScorer.get_file_last_commit_date(str(tmp_path), "doc.md") is None


class TestGetCodeChangesSince:
    def test_object_with_changes_returns_2(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value="abc123\n def456\n"):
            assert DocStalenessScorer.get_code_changes_since(str(tmp_path), "2024-01-01") == 2

    def test_object_empty_input_returns_0(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value=""):
            assert DocStalenessScorer.get_code_changes_since(str(tmp_path), "2024-01-01") == 0


class TestGetLatestTag:
    def test_object_with_tag_returns_1_2_3(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value="v1.2.3"):
            assert DocStalenessScorer.get_latest_tag(str(tmp_path)) == "1.2.3"

    def test_object_no_tag_returns_none(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "run_git", return_value=""):
            assert DocStalenessScorer.get_latest_tag(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# find_doc_files
# ---------------------------------------------------------------------------


class TestFindDocFiles:
    def test_find_doc_files_finds_markdown_contains_guide_rst(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "guide.rst").write_text("Test")
        files = DocStalenessScorer.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert "guide.rst" in files

    def test_find_doc_files_skips_directories_contains_readme_md(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test")
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "lib.md").write_text("skip")
        files = DocStalenessScorer.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert not any("venv" in f for f in files)

    def test_find_doc_files_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        assert DocStalenessScorer.find_doc_files(str(tmp_path)) == []

    def test_find_doc_files_gitignore_skip_contains_readme_md(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("secrets/\n")
        (tmp_path / "README.md").write_text("# Test")
        secrets = tmp_path / "secrets"
        secrets.mkdir()
        (secrets / "secret.md").write_text("secret")
        files = DocStalenessScorer.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert not any("secrets" in f for f in files)

    def test_gitignore_skip_file_name(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("ignored.md\n")
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "ignored.md").write_text("# Ignored")
        files = DocStalenessScorer.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert "ignored.md" not in files

    def test_zolletta_metaskill_skipped_without_gitignore(self, tmp_path: Path) -> None:
        """`.zolletta-metaskill/` is skipped even when not in local .gitignore."""
        zm = tmp_path / ".zolletta-metaskill"
        zm.mkdir()
        (zm / "report.md").write_text("# Report")
        (tmp_path / "README.md").write_text("# Test")
        files = DocStalenessScorer.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert all(".zolletta-metaskill" not in f for f in files)


# ---------------------------------------------------------------------------
# score_last_updated
# ---------------------------------------------------------------------------


class TestScoreLastUpdated:
    def test_no_git_history(self, tmp_path: Path) -> None:
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 50.0
            assert "reason" in details

    def test_now_recent_returns_100_0(self, tmp_path: Path) -> None:
        recent = datetime.now(UTC) - timedelta(days=3)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=recent):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_now_30_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=20)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 80 <= score <= 100

    def test_now_90_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=60)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 50 <= score < 80

    def test_now_180_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=120)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 25 <= score < 50

    def test_now_365_days_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=250)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert 10 <= score < 25

    def test_now_very_old_succeeds(self, tmp_path: Path) -> None:
        dt = datetime.now(UTC) - timedelta(days=500)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score >= 0

    def test_now_naive_datetime_returns_100_0(self, tmp_path: Path) -> None:
        recent = datetime.now() - timedelta(days=3)
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=recent):
            score, details = DocStalenessScorer.score_last_updated(str(tmp_path), "doc.md")
            assert score == 100.0


# ---------------------------------------------------------------------------
# score_code_doc_alignment
# ---------------------------------------------------------------------------


class TestScoreCodeDocAlignment:
    def test_score_code_doc_alignment_no_file_returns_50_0(self, tmp_path: Path) -> None:
        score, details = DocStalenessScorer.score_code_doc_alignment(
            str(tmp_path), "nonexistent.md"
        )
        assert score == 50.0

    def test_no_refs_no_git(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content without refs.\n")
        with patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None):
            score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 70.0

    def test_no_refs_with_git_no_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt),
            patch.object(DocStalenessScorer, "get_code_changes_since", return_value=0),
        ):
            score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_no_refs_with_git_few_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt),
            patch.object(DocStalenessScorer, "get_code_changes_since", return_value=3),
        ):
            score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 80.0

    def test_no_refs_with_git_many_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt),
            patch.object(DocStalenessScorer, "get_code_changes_since", return_value=25),
        ):
            score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 40.0

    def test_no_refs_with_git_moderate_changes(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSome content.\n")
        dt = datetime.now(UTC) - timedelta(days=10)
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=dt),
            patch.object(DocStalenessScorer, "get_code_changes_since", return_value=10),
        ):
            score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
            assert score == 60.0

    def test_with_refs_all_exist(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee [module](module.py).\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details["referenced_files"] == 1
        assert details["existing_files"] == 1

    def test_with_refs_none_exist(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee [module](missing.py).\n")
        score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_backtick_file_refs(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee `module.py`.\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_ref_resolved_from_repo_root(self, tmp_path: Path) -> None:
        """File ref that doesn't exist relative to doc dir but exists at repo root."""
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\nSee [module](module.py).\n")
        (tmp_path / "module.py").write_text("# code")
        score, details = DocStalenessScorer.score_code_doc_alignment(str(tmp_path), "docs/doc.md")
        assert score == 100.0
        assert details["existing_files"] == 1


# ---------------------------------------------------------------------------
# score_link_health
# ---------------------------------------------------------------------------


class TestScoreLinkHealth:
    def test_score_link_health_no_file_returns_100_0(self, tmp_path: Path) -> None:
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "nonexistent.md")
        assert score == 100.0

    def test_score_link_health_no_links_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nNo links here.\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_valid_file_link(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md)\n")
        (tmp_path / "other.md").write_text("# Other")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details["valid_links"] == 1

    def test_broken_file_link(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](missing.md)\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0
        assert "missing.md" in details["broken_links"]

    def test_anchor_only_valid(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n## Section\n\n[link](#section)\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_anchor_only_broken(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](#missing)\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_cross_doc_anchor_valid(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#section)\n")
        (tmp_path / "other.md").write_text("# Other\n\n## Section\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_cross_doc_anchor_broken(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](other.md#missing)\n")
        (tmp_path / "other.md").write_text("# Other\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 0.0

    def test_external_links_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\n[link](https://example.com)\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0

    def test_empty_anchor_link(self, tmp_path: Path) -> None:
        """A link to just '#' (no file, no anchor) counts as valid."""
        (tmp_path / "doc.md").write_text("# Title\n\n[empty](#)\n")
        score, details = DocStalenessScorer.score_link_health(str(tmp_path), "doc.md")
        assert score == 100.0
        assert details["valid_links"] == 1


# ---------------------------------------------------------------------------
# _detect_diataxis_quadrant
# ---------------------------------------------------------------------------


class TestDetectDiataxisQuadrant:
    def test_detect_diataxis_quadrant_tutorials_contains_what_we_will_learn(self) -> None:
        quad = DocStalenessScorer._detect_diataxis_quadrant("docs/tutorials/quickstart.md")
        assert quad is not None
        assert "what we will learn" in quad["required_sections"]

    def test_detect_diataxis_quadrant_how_to_succeeds(self) -> None:
        quad = DocStalenessScorer._detect_diataxis_quadrant("docs/how-to/configure.md")
        assert quad is not None

    def test_detect_diataxis_quadrant_reference_succeeds(self) -> None:
        quad = DocStalenessScorer._detect_diataxis_quadrant("docs/reference/api.md")
        assert quad is not None

    def test_detect_diataxis_quadrant_explanation_succeeds(self) -> None:
        quad = DocStalenessScorer._detect_diataxis_quadrant("docs/explanation/design.md")
        assert quad is not None

    def test_detect_diataxis_quadrant_no_quadrant_returns_none(self) -> None:
        assert DocStalenessScorer._detect_diataxis_quadrant("README.md") is None

    def test_detect_diataxis_quadrant_nested_path_succeeds(self) -> None:
        quad = DocStalenessScorer._detect_diataxis_quadrant(
            ".backstage/docs/v1/how-to/configure.md"
        )
        assert quad is not None


# ---------------------------------------------------------------------------
# score_completeness
# ---------------------------------------------------------------------------


class TestScoreCompleteness:
    def test_all_sections_present(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "# Installation\n\n# Usage\n\n# API\n\n# Contributing\n\n# License\n"
        )
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path),
            "doc.md",
            ["installation", "usage", "api", "contributing", "license"],
        )
        assert score == 100.0

    def test_score_completeness_missing_sections_contains_api(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Installation\n\n# Usage\n")
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "doc.md", ["installation", "usage", "api"]
        )
        assert score < 100.0
        assert "api" in details["missing_sections"]

    def test_score_completeness_no_file_returns_0_0(self, tmp_path: Path) -> None:
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "nonexistent.md", ["usage"]
        )
        assert score == 0.0

    def test_score_completeness_diataxis_tutorials_returns_100_0(self, tmp_path: Path) -> None:
        tutorials = tmp_path / "tutorials"
        tutorials.mkdir()
        (tutorials / "guide.md").write_text(
            "# What We Will Learn\n\n# Prerequisites\n\nLots of content.\n" + "x\n" * 15
        )
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "tutorials/guide.md", ["installation"]
        )
        assert details.get("doc_structure") == "diataxis"
        assert score == 100.0

    def test_diataxis_how_to_any_of(self, tmp_path: Path) -> None:
        howto = tmp_path / "how-to"
        howto.mkdir()
        (howto / "guide.md").write_text("# Prerequisites\n\n" + "content\n" * 15)
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "how-to/guide.md", ["installation"]
        )
        assert details.get("doc_structure") == "diataxis"
        assert details["any_of_groups_found"] == 1
        assert score == 100.0

    def test_diataxis_how_to_any_of_missing(self, tmp_path: Path) -> None:
        howto = tmp_path / "how-to"
        howto.mkdir()
        (howto / "guide.md").write_text("# Solution\n\n" + "content\n" * 15)
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "how-to/guide.md", ["installation"]
        )
        assert details.get("doc_structure") == "diataxis"
        assert details["any_of_groups_found"] == 0
        assert len(details["any_of_groups_missing"]) == 1
        assert score < 100.0

    def test_diataxis_reference_no_requirements(self, tmp_path: Path) -> None:
        ref = tmp_path / "reference"
        ref.mkdir()
        (ref / "api.md").write_text("# API\n\n" + "content\n" * 15)
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "reference/api.md", ["installation"]
        )
        assert score == 100.0

    def test_length_penalty_short(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Installation\n\nshort\n")
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "doc.md", ["installation"]
        )
        # Only 2 non-empty lines → penalty 30
        assert score == 70.0

    def test_length_penalty_medium(self, tmp_path: Path) -> None:
        content = "# Installation\n\n" + "line\n" * 15
        (tmp_path / "doc.md").write_text(content)
        score, details = DocStalenessScorer.score_completeness(
            str(tmp_path), "doc.md", ["installation"]
        )
        # 16 non-empty lines → penalty 15
        assert score == 85.0


# ---------------------------------------------------------------------------
# score_accuracy
# ---------------------------------------------------------------------------


class TestScoreAccuracy:
    def test_score_accuracy_no_file_returns_50_0(self, tmp_path: Path) -> None:
        score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "nonexistent.md")
        assert score == 50.0

    def test_no_verifiable_facts(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nJust some text.\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 75.0

    def test_object_version_match_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 1.2.3\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value="1.2.3"):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_object_version_mismatch_returns_0_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 0.9.0\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value="1.2.3"):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 0.0

    def test_manifest_version_match(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 1.0.0\n")
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_manifest_version_mismatch(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 0.9.0\n")
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 0.0
            assert any("FAIL" in c for c in details["checks"])

    def test_file_paths_valid(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("# code")
        (tmp_path / "doc.md").write_text("# Title\n\nSee `src/mod.py`.\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_file_paths_resolved_from_repo_root(self, tmp_path: Path) -> None:
        """File ref that doesn't exist relative to doc dir but exists at repo root."""
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\nSee `src/mod.py`.\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("# code")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "docs/doc.md")
            assert score == 100.0

    def test_file_paths_broken(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee `src/missing.py`.\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 0.0

    def test_strftime_future_date_returns_0_0(self, tmp_path: Path) -> None:
        future = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%d")
        (tmp_path / "doc.md").write_text(f"# Title\n\nDate: {future}\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 0.0

    def test_strftime_valid_date_returns_100_0(self, tmp_path: Path) -> None:
        past = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
        (tmp_path / "doc.md").write_text(f"# Title\n\nDate: {past}\n")
        with patch.object(DocStalenessScorer, "get_latest_tag", return_value=None):
            score, details = DocStalenessScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 100.0


# ---------------------------------------------------------------------------
# _extract_headings / _slugify
# ---------------------------------------------------------------------------


class TestExtractHeadings:
    def test_extract_headings_basic_input_contains_section_two(self) -> None:
        content = "# Title\n\n## Section Two\n"
        headings = DocStalenessScorer._extract_headings(content)
        assert "title" in headings
        assert "section-two" in headings

    def test_extract_headings_no_headings_succeeds(self) -> None:
        assert DocStalenessScorer._extract_headings("just text\n") == set()


class TestSlugify:
    def test_slugify_basic_input_returns_hello_world(self) -> None:
        assert DocStalenessScorer._slugify("Hello World") == "hello-world"

    def test_slugify_special_chars_returns_hello_world(self) -> None:
        assert DocStalenessScorer._slugify("Hello, World!") == "hello-world"

    def test_slugify_multiple_spaces_returns_hello_world(self) -> None:
        assert DocStalenessScorer._slugify("Hello   World") == "hello-world"

    def test_leading_trailing_hyphens(self) -> None:
        assert DocStalenessScorer._slugify("--Hello--") == "hello"


# ---------------------------------------------------------------------------
# _extract_version_from_manifest
# ---------------------------------------------------------------------------


class TestExtractVersionFromManifest:
    def test_extract_version_from_manifest_package_json_returns_1_2_3(self, tmp_path: Path) -> None:
        p = tmp_path / "package.json"
        p.write_text('{"name": "test", "version": "1.2.3"}')
        assert DocStalenessScorer._extract_version_from_manifest(str(p), "package.json") == "1.2.3"

    def test_extract_version_from_manifest_pyproject_toml_returns_2_0_0(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text('[project]\nversion = "2.0.0"\n')
        assert (
            DocStalenessScorer._extract_version_from_manifest(str(p), "pyproject.toml") == "2.0.0"
        )

    def test_extract_version_from_manifest_setup_py_returns_3_1_0(self, tmp_path: Path) -> None:
        p = tmp_path / "setup.py"
        p.write_text('setup(version="3.1.0")')
        assert DocStalenessScorer._extract_version_from_manifest(str(p), "setup.py") == "3.1.0"

    def test_extract_version_from_manifest_cargo_toml_returns_0_1_0(self, tmp_path: Path) -> None:
        p = tmp_path / "Cargo.toml"
        p.write_text('[package]\nversion = "0.1.0"\n')
        assert DocStalenessScorer._extract_version_from_manifest(str(p), "Cargo.toml") == "0.1.0"

    def test_extract_version_from_manifest_no_version_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "package.json"
        p.write_text('{"name": "test"}')
        assert DocStalenessScorer._extract_version_from_manifest(str(p), "package.json") is None

    def test_extract_version_from_manifest_unknown_manifest_returns_none(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "unknown.txt"
        p.write_text("nothing")
        assert DocStalenessScorer._extract_version_from_manifest(str(p), "unknown.txt") is None

    def test_extract_version_from_manifest_oserror_returns_none(self, tmp_path: Path) -> None:
        assert (
            DocStalenessScorer._extract_version_from_manifest(
                str(tmp_path / "nope.json"), "package.json"
            )
            is None
        )


# ---------------------------------------------------------------------------
# _load_diataxis_translations / _merge_translations
# ---------------------------------------------------------------------------


class TestLoadDiataxisTranslations:
    def test_load_diataxis_translations_valid_file_contains_guide(self, tmp_path: Path) -> None:
        p = tmp_path / "trans.json"
        p.write_text(
            json.dumps(
                {
                    "readme_sections": ["installazione"],
                    "quadrants": {"tutorials": {"dir_names": ["guide"]}},
                }
            )
        )
        result = DocStalenessScorer._load_diataxis_translations(str(p))
        assert result["readme_sections"] == ["installazione"]
        assert "guide" in result["quadrants"]["tutorials"]["dir_names"]

    def test_load_diataxis_translations_nonexistent_file_returns_dict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        result = DocStalenessScorer._load_diataxis_translations(str(tmp_path / "nope.json"))
        assert result == {"readme_sections": None, "quadrants": {}}

    def test_load_diataxis_translations_invalid_json_returns_dict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{invalid json")
        result = DocStalenessScorer._load_diataxis_translations(str(p))
        assert result == {"readme_sections": None, "quadrants": {}}


class TestMergeTranslations:
    def test_merge_dir_names(self) -> None:
        # Save original to restore after test
        original = {k: dict(v) for k, v in DocStalenessScorer.DIATAXIS_QUADRANTS.items()}
        try:
            translations = {"quadrants": {"tutorials": {"dir_names": ["guide", "tutorial"]}}}
            DocStalenessScorer._merge_translations(translations)
            assert "guide" in DocStalenessScorer.DIATAXIS_QUADRANTS["tutorials"]["dir_names"]
        finally:
            for k, v in original.items():
                DocStalenessScorer.DIATAXIS_QUADRANTS[k].clear()
                DocStalenessScorer.DIATAXIS_QUADRANTS[k].update(v)

    def test_replace_required_sections(self) -> None:
        original = {k: dict(v) for k, v in DocStalenessScorer.DIATAXIS_QUADRANTS.items()}
        try:
            translations = {"quadrants": {"tutorials": {"required_sections": ["nuova sezione"]}}}
            DocStalenessScorer._merge_translations(translations)
            assert DocStalenessScorer.DIATAXIS_QUADRANTS["tutorials"]["required_sections"] == [
                "nuova sezione"
            ]
        finally:
            for k, v in original.items():
                DocStalenessScorer.DIATAXIS_QUADRANTS[k].clear()
                DocStalenessScorer.DIATAXIS_QUADRANTS[k].update(v)

    def test_unknown_quadrant_skipped(self) -> None:
        translations = {"quadrants": {"unknown": {"dir_names": ["x"]}}}
        DocStalenessScorer._merge_translations(translations)  # should not raise

    def test_merge_translations_empty_translations_succeeds(self) -> None:
        DocStalenessScorer._merge_translations({})  # should not raise

    def test_merge_any_of_groups(self) -> None:
        original = {k: dict(v) for k, v in DocStalenessScorer.DIATAXIS_QUADRANTS.items()}
        try:
            translations = {
                "quadrants": {"how-to": {"any_of_groups": [["Prerequisiti", "Prima di iniziare"]]}}
            }
            DocStalenessScorer._merge_translations(translations)
            assert DocStalenessScorer.DIATAXIS_QUADRANTS["how-to"]["any_of_groups"] == [
                ["prerequisiti", "prima di iniziare"]
            ]
        finally:
            for k, v in original.items():
                DocStalenessScorer.DIATAXIS_QUADRANTS[k].clear()
                DocStalenessScorer.DIATAXIS_QUADRANTS[k].update(v)


# ---------------------------------------------------------------------------
# score_document
# ---------------------------------------------------------------------------


class TestScoreDocument:
    def test_object_basic_input_returns_set(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "# Installation\n\n# Usage\n\n# API\n\n" + "content\n" * 15
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            result = DocStalenessScorer.score_document(
                str(tmp_path),
                "doc.md",
                DocStalenessScorer.DEFAULT_WEIGHTS,
                DocStalenessScorer.DEFAULT_README_SECTIONS,
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


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_generate_report_empty_json_returns_0(self) -> None:
        report = DocStalenessScorer.generate_report([], as_json=True)
        data = json.loads(report)
        assert data["documents"] == []
        assert data["aggregate_score"] == 0

    def test_generate_report_empty_text_contains_no_documentation_files_found(self) -> None:
        report = DocStalenessScorer.generate_report([], as_json=False)
        assert "No documentation files found" in report

    def test_with_scores_json(self) -> None:
        scores = [
            {"file": "a.md", "total_score": 80.0, "label": "good", "dimensions": {}},
            {"file": "b.md", "total_score": 60.0, "label": "stale", "dimensions": {}},
        ]
        report = DocStalenessScorer.generate_report(scores, as_json=True)
        data = json.loads(report)
        assert data["aggregate_score"] == 70.0
        assert data["total_documents"] == 2

    def test_with_scores_text(self) -> None:
        scores = [
            {
                "file": "a.md",
                "total_score": 80.0,
                "label": "good",
                "dimensions": {
                    "last_updated": {"score": 80.0, "weight": 0.2, "weighted": 16.0},
                    "code_doc_alignment": {"score": 80.0, "weight": 0.3, "weighted": 24.0},
                    "link_health": {"score": 80.0, "weight": 0.15, "weighted": 12.0},
                    "completeness": {"score": 80.0, "weight": 0.2, "weighted": 16.0},
                    "accuracy": {"score": 80.0, "weight": 0.15, "weighted": 12.0},
                },
            },
        ]
        report = DocStalenessScorer.generate_report(scores, as_json=False)
        assert "Documentation Staleness Report" in report
        assert "a.md" in report
        assert "DIMENSION BREAKDOWN" in report


class TestScoreBar:
    def test_score_bar_full_returns_bar(self) -> None:
        bar = DocStalenessScorer._score_bar(100)
        assert bar == "[" + "#" * 20 + "]"

    def test_score_bar_empty_input_returns_bar(self) -> None:
        bar = DocStalenessScorer._score_bar(0)
        assert bar == "[" + "." * 20 + "]"

    def test_score_bar_half_returns_bar(self) -> None:
        bar = DocStalenessScorer._score_bar(50)
        assert bar == "[" + "#" * 10 + "." * 10 + "]"


# ---------------------------------------------------------------------------
# DocStalenessScorer.main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_not_a_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "file.txt"
        f.write_text("not a dir")
        monkeypatch.setattr(sys, "argv", ["doc_staleness_scorer.py", str(f)])
        with pytest.raises(SystemExit) as exc:
            DocStalenessScorer.main()
        assert exc.value.code == 2

    def test_no_docs_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["doc_staleness_scorer.py", str(tmp_path), "--json"])
        with pytest.raises(SystemExit) as exc:
            DocStalenessScorer.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert json.loads(out)["error"] == "No documentation files found"

    def test_no_docs_text(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["doc_staleness_scorer.py", str(tmp_path)])
        with pytest.raises(SystemExit) as exc:
            DocStalenessScorer.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "No documentation files found" in out

    def test_no_docs_quiet(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            ["doc_staleness_scorer.py", str(tmp_path), "--quiet"],
        )
        with pytest.raises(SystemExit) as exc:
            DocStalenessScorer.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out.strip()
        assert out == "0"

    def test_object_with_docs_raises_systemexit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n# Usage\n\n" + "content\n" * 15)
        monkeypatch.setattr(sys, "argv", ["doc_staleness_scorer.py", str(tmp_path)])
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0
            out = capsys.readouterr().out
            assert "Documentation Staleness Report" in out

    def test_object_readme_focus_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        (tmp_path / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            ["doc_staleness_scorer.py", str(tmp_path), "--readme-focus"],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0

    def test_object_threshold_fail_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            ["doc_staleness_scorer.py", str(tmp_path), "--threshold", "99"],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 1

    def test_object_threshold_pass_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "README.md").write_text(
            "# Installation\n\n# Usage\n\n# API\n\n# Contributing\n\n# License\n" + "x\n" * 15
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["doc_staleness_scorer.py", str(tmp_path), "--threshold", "10"],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0

    def test_object_custom_weights_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc_staleness_scorer.py",
                str(tmp_path),
                "--weight-updated",
                "0.5",
                "--weight-alignment",
                "0.5",
            ],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0

    def test_all_weight_flags(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc_staleness_scorer.py",
                str(tmp_path),
                "--weight-links",
                "0.2",
                "--weight-completeness",
                "0.2",
                "--weight-accuracy",
                "0.2",
            ],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0

    def test_required_sections_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "README.md").write_text("# Foo\n\n# Bar\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc_staleness_scorer.py",
                str(tmp_path),
                "--required-sections",
                "Foo,Bar",
            ],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0

    def test_object_json_output_raises_systemexit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        monkeypatch.setattr(sys, "argv", ["doc_staleness_scorer.py", str(tmp_path), "--json"])
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "aggregate_score" in data

    def test_object_quiet_output_raises_systemexit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        monkeypatch.setattr(sys, "argv", ["doc_staleness_scorer.py", str(tmp_path), "--quiet"])
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0
            out = capsys.readouterr().out.strip()
            float(out)  # should be a number

    def test_dumps_diataxis_translations_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        trans = tmp_path / "trans.json"
        trans.write_text(
            json.dumps(
                {
                    "readme_sections": ["installazione", "utilizzo"],
                    "quadrants": {"tutorials": {"dir_names": ["guide"]}},
                }
            )
        )
        (tmp_path / "README.md").write_text("# Installazione\n\n# Utilizzo\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc_staleness_scorer.py",
                str(tmp_path),
                "--diataxis-translations",
                str(trans),
            ],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0

    def test_diataxis_translations_no_readme_sections(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Translations without readme_sections fall back.

        Uses DocStalenessScorer.DEFAULT_README_SECTIONS.
        """
        trans = tmp_path / "trans.json"
        trans.write_text(
            json.dumps(
                {
                    "quadrants": {"tutorials": {"dir_names": ["guide"]}},
                }
            )
        )
        (tmp_path / "README.md").write_text("# Installation\n\n# Usage\n" + "content\n" * 15)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "doc_staleness_scorer.py",
                str(tmp_path),
                "--diataxis-translations",
                str(trans),
            ],
        )
        with (
            patch.object(DocStalenessScorer, "get_file_last_commit_date", return_value=None),
            patch.object(DocStalenessScorer, "get_latest_tag", return_value=None),
        ):
            with pytest.raises(SystemExit) as exc:
                DocStalenessScorer.main()
            assert exc.value.code == 0
