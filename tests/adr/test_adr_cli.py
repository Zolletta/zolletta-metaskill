"""Tests for ADRCLI — argument parsing and report formatting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_cli import ADRCLI
from zolletta_metaskill.adr.structs.distill_report import DistillReport


class TestADRCLIBuildParser:
    """Tests for ADRCLI.build_parser."""

    def test_build_parser_returns_parser_with_defaults(self) -> None:
        """build_parser returns a parser with default values."""
        parser = ADRCLI.build_parser()
        args = parser.parse_args([])
        assert args.docs_dir == "docs"
        assert args.adrs_path is None
        assert args.cache_dir == ".zolletta-metaskill"
        assert args.json is False

    def test_build_parser_accepts_all_args_returns_parsed(self) -> None:
        """build_parser parses all CLI arguments."""
        parser = ADRCLI.build_parser()
        args = parser.parse_args(["--docs-dir", "/tmp/docs", "--adrs-path", "adr", "--json"])
        assert args.docs_dir == "/tmp/docs"
        assert args.adrs_path == "adr"
        assert args.json is True


class TestADRCLIFormatReport:
    """Tests for ADRCLI.format_report."""

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


class TestADRCLIMissingDocsError:
    """Tests for ADRCLI.missing_docs_error."""

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


class TestADRCLIRun:
    """Tests for ADRCLI.run."""

    def test_run_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Run returns 1 when docs-dir does not exist."""
        rc = ADRCLI.run(["--docs-dir", str(tmp_path / "nope"), "--adrs-path", "adr"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err

    def test_run_with_nonexistent_docs_dir_json_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Run returns 1 and prints JSON when docs-dir missing and --json."""
        rc = ADRCLI.run(["--docs-dir", str(tmp_path / "nope"), "--adrs-path", "adr", "--json"])
        assert rc == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["has_adrs"] is False
