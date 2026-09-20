"""Tests for the CLI main() function."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_cli import ADRCLI

from .conftest import write_adr


def write_settings(tmp_path: Path, adrs: str | None = "adr") -> None:
    """Write a minimal settings.json into ``tmp_path/.zolletta-metaskill``."""
    meta = tmp_path / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "settings.json").write_text(
        json.dumps({"documentation": {"dir": "docs", "adrs": adrs}})
    )


class TestMain:
    """Tests for the CLI main() function."""

    def _run(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        argv: list[str],
    ) -> int:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return ADRCLI.main()

    def test_main_with_adrs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "1 new" in out

    def test_main_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["has_adrs"] is True
        assert "ADR-001" in data["new"]

    def test_main_no_adrs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_settings(tmp_path)
        (tmp_path / "docs").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "no ADRs" in out

    def test_main_no_adrs_plain(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_settings(tmp_path)
        (tmp_path / "docs").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "no ADRs" in out

    def test_main_empty_adrs_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty string adrs means ADRs are scattered in docs root."""
        write_settings(tmp_path, adrs="")
        docs = tmp_path / "docs"
        write_adr(docs / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["has_adrs"] is True

    def test_main_nonexistent_docs_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_settings(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "not a directory" in err

    def test_main_nonexistent_docs_dir_json(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_settings(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 1
        data = json.loads(out)
        assert data["has_adrs"] is False
