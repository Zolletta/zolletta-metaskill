"""Tests for git_helper.py."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class TestGitHelper:
    # --- run_git ---

    def test_run_git_success_returns_output(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "output\n"})()
            result = GitHelper.run_git(str(tmp_path), ["status"])
            assert result == "output"

    def test_run_git_failure_returns_default(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 1, "stdout": ""})()
            result = GitHelper.run_git(str(tmp_path), ["status"], default="def")
            assert result == "def"

    def test_run_git_timeout_returns_empty(self, tmp_path: Path) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
        ):
            result = GitHelper.run_git(str(tmp_path), ["status"])
            assert result == ""

    def test_run_git_filenotfound_returns_empty(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = GitHelper.run_git(str(tmp_path), ["status"])
            assert result == ""

    # --- get_file_last_commit_date ---

    def test_get_file_last_commit_date_valid_returns_2024(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="2024-01-15T10:00:00+00:00"):
            dt = GitHelper.get_file_last_commit_date(str(tmp_path), "doc.md")
            assert dt is not None
            assert dt.year == 2024

    def test_get_file_last_commit_date_empty_returns_none(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_file_last_commit_date(str(tmp_path), "doc.md") is None

    def test_get_file_last_commit_date_invalid_returns_none(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="not-a-date"):
            assert GitHelper.get_file_last_commit_date(str(tmp_path), "doc.md") is None

    # --- get_code_changes_since ---

    def test_get_code_changes_since_with_changes_returns_2(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="abc123\n def456\n"):
            assert GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01") == 2

    def test_get_code_changes_since_empty_returns_0(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01") == 0

    # --- get_files_changed_since ---

    def test_get_files_changed_since_parses_name_status(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="M\tsrc/a.py\nA\tdocs/b.md\n"):
            changes = GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            assert {"status": "M", "file": "src/a.py"} in changes
            assert {"status": "A", "file": "docs/b.md"} in changes

    def test_get_files_changed_since_empty_returns_empty(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01") == []

    # --- get_renamed_files ---

    def test_get_renamed_files_parses_renames(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="R100\told.py\tnew.py\n"):
            renames = GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            assert ("old.py", "new.py") in renames

    def test_get_renamed_files_empty_returns_empty(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_renamed_files(str(tmp_path), "2024-01-01") == []

    # --- get_latest_tag ---

    def test_get_latest_tag_with_tag_returns_1_2_3(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="v1.2.3"):
            assert GitHelper.get_latest_tag(str(tmp_path)) == "1.2.3"

    def test_get_latest_tag_no_tag_returns_none(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_latest_tag(str(tmp_path)) is None
