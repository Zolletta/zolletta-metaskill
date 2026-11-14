"""Tests for git_exclude_ensurer.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.setup.git_exclude_ensurer import GitExcludeEnsurer


class TestGitExcludeEnsurer:
    # --- Tests for GitExcludeEnsurer.ensure_git_exclude(). ---

    def test_ensure_creates_new_file(self, tmp_path: Path) -> None:
        exclude = tmp_path / ".git" / "info" / "exclude"
        added = GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert added is True
        content = exclude.read_text(encoding="utf-8")
        assert ".zolletta-metaskill/" in content
        assert "# Zolletta-metaskill" in content

    def test_ensure_appends_to_existing_file(self, tmp_path: Path) -> None:
        exclude = tmp_path / "exclude"
        exclude.write_text(".venv/\nnode_modules/\n", encoding="utf-8")
        added = GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert added is True
        content = exclude.read_text(encoding="utf-8")
        assert ".venv/" in content
        assert ".zolletta-metaskill/" in content

    def test_ensure_idempotent_already_present(self, tmp_path: Path) -> None:
        exclude = tmp_path / "exclude"
        exclude.write_text(".venv/\n.zolletta-metaskill/\n", encoding="utf-8")
        added = GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert added is False
        content = exclude.read_text(encoding="utf-8")
        assert content.count(".zolletta-metaskill/") == 1

    def test_ensure_no_trailing_newline(self, tmp_path: Path) -> None:
        exclude = tmp_path / "exclude"
        exclude.write_text(".venv/", encoding="utf-8")
        added = GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert added is True
        content = exclude.read_text(encoding="utf-8")
        assert ".venv/" in content
        assert ".zolletta-metaskill/" in content

    def test_ensure_no_trailing_newline_exact_content(self, tmp_path: Path) -> None:
        """A missing final newline gets exactly one separator before the block."""
        exclude = tmp_path / "exclude"
        exclude.write_text(".venv/", encoding="utf-8")
        GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert exclude.read_text(encoding="utf-8") == (
            ".venv/\n\n# Zolletta-metaskill\n.zolletta-metaskill/\n"
        )

    def test_ensure_trailing_newline_exact_content(self, tmp_path: Path) -> None:
        """A well-formed file gets the block appended verbatim."""
        exclude = tmp_path / "exclude"
        exclude.write_text(".venv/\n", encoding="utf-8")
        GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert exclude.read_text(encoding="utf-8") == (
            ".venv/\n\n# Zolletta-metaskill\n.zolletta-metaskill/\n"
        )

    def test_ensure_empty_file_exact_content(self, tmp_path: Path) -> None:
        """An empty file gets exactly the leading blank line plus block."""
        exclude = tmp_path / "exclude"
        exclude.write_text("", encoding="utf-8")
        GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert exclude.read_text(encoding="utf-8") == (
            "\n# Zolletta-metaskill\n.zolletta-metaskill/\n"
        )

    def test_ensure_writes_utf8_on_existing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exclude = tmp_path / "exclude"
        exclude.write_text(".venv/\n", encoding="utf-8")
        written: list[dict[str, object]] = []
        real_write_text = Path.write_text

        def _spy(self: Path, data: str, **kwargs: Any) -> int:
            written.append(kwargs)
            return real_write_text(self, data, **kwargs)

        monkeypatch.setattr(Path, "write_text", _spy)
        GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert written and all(kw.get("encoding") == "utf-8" for kw in written)

    def test_ensure_writes_utf8_on_new_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exclude = tmp_path / "exclude"
        written: list[dict[str, object]] = []
        real_write_text = Path.write_text

        def _spy(self: Path, data: str, **kwargs: Any) -> int:
            written.append(kwargs)
            return real_write_text(self, data, **kwargs)

        monkeypatch.setattr(Path, "write_text", _spy)
        GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert written and all(kw.get("encoding") == "utf-8" for kw in written)

    def test_ensure_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        exclude = tmp_path / "nested" / "deeper" / "exclude"
        added = GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert added is True
        assert ".zolletta-metaskill/" in exclude.read_text(encoding="utf-8")

    def test_ensure_entry_without_trailing_slash_matched(self, tmp_path: Path) -> None:
        exclude = tmp_path / "exclude"
        exclude.write_text(".zolletta-metaskill\n", encoding="utf-8")
        added = GitExcludeEnsurer.ensure_git_exclude(exclude)
        assert added is False

    def test_ensure_default_path_inside_git_repo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Inside a real work tree the repo's ``.git/info/exclude`` is written."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        monkeypatch.chdir(tmp_path)
        added = GitExcludeEnsurer.ensure_git_exclude()
        assert added is True
        content = (tmp_path / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        assert ".zolletta-metaskill/" in content

    def test_ensure_default_path_outside_repo_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Outside a work tree nothing is written and ``None`` is returned."""
        monkeypatch.chdir(tmp_path)
        assert GitExcludeEnsurer.ensure_git_exclude() is None

    def test_ensure_default_path_falls_back_to_dot_git_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``.git`` dir git does not recognise still resolves via the fallback."""
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        added = GitExcludeEnsurer.ensure_git_exclude()
        assert added is True
        assert ".zolletta-metaskill/" in (tmp_path / ".git" / "info" / "exclude").read_text(
            encoding="utf-8"
        )

    # --- Tests for GitExcludeEnsurer.main(). ---

    def test_main_adds_entry(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        exclude = tmp_path / "exclude"
        monkeypatch.setattr(sys, "argv", ["prog", "--path", str(exclude)])
        rc = GitExcludeEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Added" in out
        assert ".zolletta-metaskill/" in exclude.read_text(encoding="utf-8")

    def test_main_already_present(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        exclude = tmp_path / "exclude"
        exclude.write_text(".zolletta-metaskill/\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", "--path", str(exclude)])
        rc = GitExcludeEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "already present" in out

    def test_main_output_echoes_given_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        exclude = tmp_path / "exclude"
        monkeypatch.setattr(sys, "argv", ["prog", "--path", str(exclude)])
        GitExcludeEnsurer.main()
        out = capsys.readouterr().out
        assert str(exclude) in out

    def test_main_inside_repo_uses_info_exclude(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With no ``--path`` inside a work tree the info/exclude path is echoed."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = GitExcludeEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert str(Path(".git") / "info" / "exclude") in out

    def test_main_outside_repo_prints_skip(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With no ``--path`` outside a work tree the skip is reported, exit 0."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = GitExcludeEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Not a git repository" in out

    def test_main_help_prints_description(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-h"])
        with pytest.raises(SystemExit):
            GitExcludeEnsurer.main()
        out = capsys.readouterr().out
        assert "\nEnsure .zolletta-metaskill/ is in the repo's .git/info/exclude." in out
