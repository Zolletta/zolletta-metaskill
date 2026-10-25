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

    def test_run_git_invokes_git_with_captured_text_and_timeout(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "ok"})()
            GitHelper.run_git(str(tmp_path), ["status"])
            mock_run.assert_called_once_with(
                ["git", "-C", str(tmp_path), "status"],
                capture_output=True,
                text=True,
                timeout=30,
            )

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

    def test_get_file_last_commit_date_passes_log_args(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_file_last_commit_date(str(tmp_path), "doc.md")
            repo, args = mock_run.call_args.args
            assert repo == str(tmp_path)
            assert args == ["log", "-1", "--format=%aI", "--", "doc.md"]

    # --- get_code_changes_since ---

    def test_get_code_changes_since_with_changes_returns_2(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="abc123\n def456\n"):
            assert GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01") == 2

    def test_get_code_changes_since_empty_returns_0(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01") == 0

    def test_get_code_changes_since_passes_since_and_directory(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01", directory="src")
            _, args = mock_run.call_args.args
            assert args == ["log", "--since", "2024-01-01", "--oneline", "--", "src"]

    def test_get_code_changes_since_defaults_directory_to_dot(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01")
            _, args = mock_run.call_args.args
            assert args[-1] == "."

    def test_get_code_changes_since_passes_repo_path(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_code_changes_since(str(tmp_path), "2024-01-01")
            assert mock_run.call_args.args[0] == str(tmp_path)

    # --- get_files_changed_since ---

    def test_get_files_changed_since_parses_name_status(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="M\tsrc/a.py\nA\tdocs/b.md\n"):
            changes = GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            assert {"status": "M", "file": "src/a.py"} in changes
            assert {"status": "A", "file": "docs/b.md"} in changes

    def test_get_files_changed_since_with_scope_passes_pathspec(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="M\tsrc/a.py\n") as mock_run:
            GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01", scope="src")
            args = mock_run.call_args.args[1]
            assert args[-2:] == ["--", "src"]

    def test_get_files_changed_since_skips_blank_lines(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="\n\nM\tsrc/a.py\n\n"):
            changes = GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            assert changes == [{"status": "M", "file": "src/a.py"}]

    def test_get_files_changed_since_empty_returns_empty(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01") == []

    def test_get_files_changed_since_skips_malformed_lines(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="orphan\nM\tsrc/a.py\n"):
            changes = GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            assert changes == [{"status": "M", "file": "src/a.py"}]

    def test_get_files_changed_since_passes_exact_log_args(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            repo, args = mock_run.call_args.args
            assert repo == str(tmp_path)
            assert args == [
                "log",
                "--since",
                "2024-01-01",
                "--name-status",
                "--pretty=format:",
                "--diff-filter=ACDMRT",
            ]

    def test_get_files_changed_since_with_scope_passes_full_args(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01", scope="src")
            _, args = mock_run.call_args.args
            assert args == [
                "log",
                "--since",
                "2024-01-01",
                "--name-status",
                "--pretty=format:",
                "--diff-filter=ACDMRT",
                "--",
                "src",
            ]

    def test_get_files_changed_since_filename_with_spaces_returns_full_name(
        self, tmp_path: Path
    ) -> None:
        with patch.object(GitHelper, "run_git", return_value="M\tsrc/my file.py\n"):
            changes = GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            assert changes == [{"status": "M", "file": "src/my file.py"}]

    def test_get_files_changed_since_rename_line_returns_last_column(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="R100\told.py\tnew.py\n"):
            changes = GitHelper.get_files_changed_since(str(tmp_path), "2024-01-01")
            assert changes == [{"status": "R", "file": "new.py"}]

    # --- get_renamed_files ---

    def test_get_renamed_files_parses_renames(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="R100\told.py\tnew.py\n"):
            renames = GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            assert ("old.py", "new.py") in renames

    def test_get_renamed_files_skips_non_rename_lines(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="M\tsrc/a.py\nR100\told.py\tnew.py\n"):
            renames = GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            assert renames == [("old.py", "new.py")]

    def test_get_renamed_files_skips_blank_lines(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="\n\nR100\told.py\tnew.py\n\n"):
            renames = GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            assert renames == [("old.py", "new.py")]

    def test_get_renamed_files_empty_returns_empty(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_renamed_files(str(tmp_path), "2024-01-01") == []

    def test_get_renamed_files_passes_rename_log_args(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            _, args = mock_run.call_args.args
            assert args[:3] == ["log", "--since", "2024-01-01"]
            assert "--name-status" in args
            assert args[-2:] == ["--diff-filter=R", "-M"]

    def test_get_renamed_files_passes_repo_and_full_args(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            repo, args = mock_run.call_args.args
            assert repo == str(tmp_path)
            assert args == [
                "log",
                "--since",
                "2024-01-01",
                "--name-status",
                "--pretty=format:",
                "--diff-filter=R",
                "-M",
            ]

    def test_get_renamed_files_filename_with_spaces_returns_full_paths(
        self, tmp_path: Path
    ) -> None:
        with patch.object(
            GitHelper,
            "run_git",
            return_value="R100\told dir/a.py\tnew dir/b.py\n",
        ):
            renames = GitHelper.get_renamed_files(str(tmp_path), "2024-01-01")
            assert renames == [("old dir/a.py", "new dir/b.py")]

    def test_get_renamed_files_modified_line_with_extra_column_ignored(
        self, tmp_path: Path
    ) -> None:
        with patch.object(GitHelper, "run_git", return_value="M\ta.py\tb.py\n"):
            assert GitHelper.get_renamed_files(str(tmp_path), "2024-01-01") == []

    # --- get_latest_tag ---

    def test_get_latest_tag_with_tag_returns_1_2_3(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="v1.2.3"):
            assert GitHelper.get_latest_tag(str(tmp_path)) == "1.2.3"

    def test_get_latest_tag_no_tag_returns_none(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value=""):
            assert GitHelper.get_latest_tag(str(tmp_path)) is None

    def test_get_latest_tag_passes_describe_args(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="") as mock_run:
            GitHelper.get_latest_tag(str(tmp_path))
            repo, args = mock_run.call_args.args
            assert repo == str(tmp_path)
            assert args == ["describe", "--tags", "--abbrev=0"]

    def test_get_latest_tag_x_prefix_kept_after_v_strip(self, tmp_path: Path) -> None:
        with patch.object(GitHelper, "run_git", return_value="vX1.2.3"):
            assert GitHelper.get_latest_tag(str(tmp_path)) == "X1.2.3"
