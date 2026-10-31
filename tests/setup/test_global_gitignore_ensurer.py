"""Tests for global_gitignore_ensurer.py."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.setup.global_gitignore_ensurer import GlobalGitignoreEnsurer


class TestGlobalGitignoreEnsurer:
    # --- Tests for GlobalGitignoreEnsurer.ensure_global_gitignore(). ---

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

    def test_no_trailing_newline_exact_content(self, tmp_path: Path) -> None:
        """A missing final newline gets exactly one separator before the block."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".venv/", encoding="utf-8")
        GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert gitignore.read_text(encoding="utf-8") == (
            ".venv/\n\n# Zolletta-metaskill\n.zolletta-metaskill/\n"
        )

    def test_trailing_newline_exact_content(self, tmp_path: Path) -> None:
        """A well-formed file gets the block appended verbatim."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".venv/\n", encoding="utf-8")
        GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert gitignore.read_text(encoding="utf-8") == (
            ".venv/\n\n# Zolletta-metaskill\n.zolletta-metaskill/\n"
        )

    def test_empty_file_exact_content(self, tmp_path: Path) -> None:
        """An empty file gets exactly the leading blank line plus block."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("", encoding="utf-8")
        GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert gitignore.read_text(encoding="utf-8") == (
            "\n# Zolletta-metaskill\n.zolletta-metaskill/\n"
        )

    def test_writes_utf8_on_existing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".venv/\n", encoding="utf-8")
        written: list[dict[str, object]] = []
        real_write_text = Path.write_text

        def _spy(self: Path, data: str, **kwargs: Any) -> int:
            written.append(kwargs)
            return real_write_text(self, data, **kwargs)

        monkeypatch.setattr(Path, "write_text", _spy)
        GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert written and all(kw.get("encoding") == "utf-8" for kw in written)

    def test_writes_utf8_on_new_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        gitignore = tmp_path / ".gitignore"
        written: list[dict[str, object]] = []
        real_write_text = Path.write_text

        def _spy(self: Path, data: str, **kwargs: Any) -> int:
            written.append(kwargs)
            return real_write_text(self, data, **kwargs)

        monkeypatch.setattr(Path, "write_text", _spy)
        GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert written and all(kw.get("encoding") == "utf-8" for kw in written)

    def test_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        gitignore = tmp_path / "nested" / "deeper" / ".gitignore"
        added = GlobalGitignoreEnsurer.ensure_global_gitignore(gitignore)
        assert added is True
        assert ".zolletta-metaskill/" in gitignore.read_text(encoding="utf-8")

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

    # --- Tests for GlobalGitignoreEnsurer.main(). ---

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

    def test_main_output_echoes_given_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        gitignore = tmp_path / ".gitignore"
        monkeypatch.setattr(sys, "argv", ["prog", "--path", str(gitignore)])
        GlobalGitignoreEnsurer.main()
        out = capsys.readouterr().out
        assert str(gitignore) in out

    def test_main_without_path_uses_home_gitignore(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With no ``--path`` the fallback ``~/.gitignore`` is echoed."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = GlobalGitignoreEnsurer.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert str(tmp_path / ".gitignore") in out

    def test_main_help_prints_description(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-h"])
        with pytest.raises(SystemExit):
            GlobalGitignoreEnsurer.main()
        out = capsys.readouterr().out
        assert "\nEnsure .zolletta-metaskill/ is in the global ~/.gitignore." in out
