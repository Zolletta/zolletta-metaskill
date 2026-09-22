"""Tests for ADRCLI — argument parsing and report formatting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_cli import ADRCLI
from zolletta_metaskill.adr.structs.distill_report import DistillReport

from .conftest import write_adr


def write_settings(tmp_path: Path, adrs: str | None = "adr") -> None:
    """Write a minimal settings.json into ``tmp_path/.zolletta-metaskill``."""
    meta = tmp_path / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "settings.json").write_text(
        json.dumps({"documentation": {"dir": "docs", "adrs": adrs}})
    )


class TestADRCLI:
    # --- Tests for ADRCLI.build_parser. ---

    def test_build_parser_returns_parser_with_defaults(self) -> None:
        """build_parser returns a parser with default values."""
        parser = ADRCLI.build_parser()
        args = parser.parse_args([])
        assert args.json is False

    def test_build_parser_accepts_json_flag(self) -> None:
        """build_parser parses the --json flag."""
        parser = ADRCLI.build_parser()
        args = parser.parse_args(["--json"])
        assert args.json is True

    # --- Tests for ADRCLI.format_report. ---

    def test_format_report_json_returns_json_string(self) -> None:
        """format_report returns JSON when as_json=True."""
        report = DistillReport(new=["a.md"], has_adrs=True)
        result = ADRCLI.format_report(report, as_json=True)
        data = json.loads(result)
        assert data["new"] == ["a.md"]
        assert data["has_adrs"] is True

    def test_format_report_plain_with_adrs_returns_summary(self) -> None:
        """format_report returns plain text summary when adrs exist."""
        report = DistillReport(new=["a.md"], stale=["b.md"], removed=["c.md"], has_adrs=True)
        result = ADRCLI.format_report(report, as_json=False)
        assert "1 new" in result
        assert "1 stale" in result
        assert "1 removed" in result

    def test_format_report_plain_no_adrs_returns_no_adrs_message(self) -> None:
        """format_report returns 'no ADRs found' when has_adrs is False."""
        report = DistillReport(has_adrs=False)
        result = ADRCLI.format_report(report, as_json=False)
        assert "no ADRs found" in result

    # --- Tests for ADRCLI.missing_docs_error. ---

    def test_missing_docs_error_plain_returns_error_message(self) -> None:
        """missing_docs_error returns plain text error."""
        result = ADRCLI.missing_docs_error(Path("/tmp/nope"), as_json=False)
        assert "/tmp/nope" in result
        assert "not a directory" in result

    def test_missing_docs_error_json_returns_json_dict(self) -> None:
        """missing_docs_error returns JSON with empty fields."""
        result = ADRCLI.missing_docs_error(Path("/tmp/nope"), as_json=True)
        data = json.loads(result)
        assert data["new"] == []
        assert data["has_adrs"] is False

    # --- Tests for ADRCLI.run. ---

    def test_run_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run returns 1 when documentation.dir does not exist."""
        monkeypatch.chdir(tmp_path)
        rc = ADRCLI.run([])
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err

    def test_run_with_nonexistent_docs_dir_json_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run returns 1 and prints JSON when docs dir missing and --json."""
        monkeypatch.chdir(tmp_path)
        rc = ADRCLI.run(["--json"])
        assert rc == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["has_adrs"] is False

    # --- Tests for the CLI main() function. ---

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
