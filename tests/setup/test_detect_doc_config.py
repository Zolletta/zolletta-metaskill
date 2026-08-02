"""Tests for detect_doc_config.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.detect_doc_config import detect_doc_dir, main


class TestDetectDocConfig:
    """Tests for detect_doc_dir()."""

    def test_backstage_exists(self, tmp_path: Path) -> None:
        (tmp_path / ".backstage").mkdir()
        assert detect_doc_dir(tmp_path) == ".backstage"

    def test_docs_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        assert detect_doc_dir(tmp_path) == "docs"

    def test_default_when_neither_exists(self, tmp_path: Path) -> None:
        assert detect_doc_dir(tmp_path) == "docs"

    def test_backstage_takes_priority_over_docs(self, tmp_path: Path) -> None:
        (tmp_path / ".backstage").mkdir()
        (tmp_path / "docs").mkdir()
        assert detect_doc_dir(tmp_path) == ".backstage"

    def test_backstage_file_not_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".backstage").write_text("not a dir", encoding="utf-8")
        assert detect_doc_dir(tmp_path) == "docs"


class TestMain:
    """Tests for main()."""

    def test_main_prints_docs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "docs" in out

    def test_main_prints_backstage(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / ".backstage").mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert ".backstage" in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.chdir(tmp_path)
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "docs" in out
