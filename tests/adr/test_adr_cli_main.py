"""Tests for the CLI main() function."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_cli import main

from .conftest import write_adr


class TestMain:
    """Tests for the CLI main() function."""

    def test_main_with_adrs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(docs),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
            ],
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "1 new" in out

    def test_main_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(docs),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
                "--json",
            ],
        )
        rc = main()
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
        docs = tmp_path / "docs"
        docs.mkdir()
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(docs),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
            ],
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "no ADRs" in out

    def test_main_no_adrs_plain(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(docs),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
            ],
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "no ADRs" in out

    def test_main_empty_adrs_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty string adrs-path means ADRs are scattered in docs root."""
        docs = tmp_path / "docs"
        write_adr(docs / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(docs),
                "--adrs-path",
                "",
                "--cache-dir",
                str(cache_dir),
                "--json",
            ],
        )
        rc = main()
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
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(tmp_path / "nope"),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
            ],
        )
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "not a directory" in err

    def test_main_nonexistent_docs_dir_json(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cache_dir = tmp_path / ".zolletta-metaskill"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--docs-dir",
                str(tmp_path / "nope"),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
                "--json",
            ],
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        data = json.loads(out)
        assert data["has_adrs"] is False
