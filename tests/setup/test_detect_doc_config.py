"""Tests for detect_doc_config.py."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.setup.detect_doc_config import detect_doc_dir


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
