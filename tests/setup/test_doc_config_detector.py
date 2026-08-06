"""Tests for doc_config_detector.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.doc_config_detector import DocConfigDetector


def _write_settings(tmp_path: Path, doc_dir: str) -> None:
    """Write a settings.json with the given documentation.dir."""
    settings_dir = tmp_path / ".zolletta-metaskill"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text(
        json.dumps({"documentation": {"dir": doc_dir}}), encoding="utf-8"
    )


class TestDetectDocConfig:
    """Tests for DocConfigDetector.detect_doc_dir()."""

    def test_detect_doc_dir_from_settings_returns_value(self, tmp_path: Path) -> None:
        """detect_doc_dir reads documentation.dir from settings.json."""
        _write_settings(tmp_path, "custom-docs")
        assert DocConfigDetector.detect_doc_dir(tmp_path) == "custom-docs"

    def test_detect_doc_dir_default_when_no_settings(self, tmp_path: Path) -> None:
        """detect_doc_dir returns 'docs' when settings.json does not exist."""
        assert DocConfigDetector.detect_doc_dir(tmp_path) == "docs"

    def test_detect_doc_dir_default_when_key_missing(self, tmp_path: Path) -> None:
        """detect_doc_dir returns 'docs' when documentation.dir is missing."""
        settings_dir = tmp_path / ".zolletta-metaskill"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            json.dumps({"language": "en"}), encoding="utf-8"
        )
        assert DocConfigDetector.detect_doc_dir(tmp_path) == "docs"

    def test_detect_doc_dir_default_when_dir_is_null(self, tmp_path: Path) -> None:
        """detect_doc_dir returns 'docs' when documentation.dir is null."""
        settings_dir = tmp_path / ".zolletta-metaskill"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            json.dumps({"documentation": {"dir": None}}), encoding="utf-8"
        )
        assert DocConfigDetector.detect_doc_dir(tmp_path) == "docs"

    def test_detect_doc_dir_handles_invalid_json(self, tmp_path: Path) -> None:
        """detect_doc_dir returns 'docs' when settings.json is invalid JSON."""
        settings_dir = tmp_path / ".zolletta-metaskill"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text("not json", encoding="utf-8")
        assert DocConfigDetector.detect_doc_dir(tmp_path) == "docs"


class TestMain:
    """Tests for DocConfigDetector.main()."""

    def test_main_prints_docs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Main prints 'docs' when no settings.json exists."""
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = DocConfigDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "docs" in out

    def test_main_prints_from_settings(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Main prints the dir from settings.json."""
        _write_settings(tmp_path, "my-docs")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = DocConfigDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "my-docs" in out

    def test_main_default_directory(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Main prints 'docs' when run with no arguments."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.chdir(tmp_path)
        rc = DocConfigDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "docs" in out
