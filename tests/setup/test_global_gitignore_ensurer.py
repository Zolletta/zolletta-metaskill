"""Tests for global_gitignore_ensurer.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.global_gitignore_ensurer import GlobalGitignoreEnsurer


class TestEnsureGlobalGitignore:
    """Tests for GlobalGitignoreEnsurer.ensure_global_gitignore()."""

    def test_creates_new_file(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        added = GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert added is True
        content = gitignore.read_text(encoding="utf-8")
        assert ".zolletta-metaskill/" in content
        assert "# Zolletta-metaskill" in content

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".venv/\nnode_modules/\n", encoding="utf-8")
        added = GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert added is True
        content = gitignore.read_text(encoding="utf-8")
        assert ".venv/" in content
        assert ".zolletta-metaskill/" in content

    def test_idempotent_already_present(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".venv/\n.zolletta-metaskill/\n", encoding="utf-8")
        added = GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert added is False
        content = gitignore.read_text(encoding="utf-8")
        assert content.count(".zolletta-metaskill/") == 1

    def test_no_trailing_newline(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".venv/", encoding="utf-8")
        added = GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert added is True
        content = gitignore.read_text(encoding="utf-8")
        assert ".venv/" in content
        assert ".zolletta-metaskill/" in content

    def test_entry_without_trailing_slash_matched(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".zolletta-metaskill\n", encoding="utf-8")
        added = GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert added is False

    def test_ensure_global_gitignore_default_path_contains_zolletta_metaskill(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        added = GlobalGitignoreEnsurer.ensure_global_gitignore()
        assert added is True
        assert ".zolletta-metaskill/" in (tmp_path / ".gitignore").read_text()


class TestMain:
    """Tests for GlobalGitignoreEnsurer.main()."""

    def test_main_adds_entry(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gitignore = tmp_path / ".gitignore"
        monkeypatch.setattr(sys, "argv", ["prog", "--path", str(gitignore)])
        rc = GlobalGitignoreEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Added" in out
        assert ".zolletta-metaskill/" in gitignore.read_text(encoding="utf-8")

    def test_main_already_present(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".zolletta-metaskill/\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", "--path", str(gitignore)])
        rc = GlobalGitignoreEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "already present" in out
