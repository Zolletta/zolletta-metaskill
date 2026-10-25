"""Tests for ADRClient — argument parsing and report formatting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_client import ADRClient
from zolletta_metaskill.adr.structs.distill_report import DistillReport

from .conftest import write_adr


def write_settings(tmp_path: Path, adrs: str | None = "adr") -> None:
    """Write a minimal settings.json into ``tmp_path/.zolletta-metaskill``."""
    meta = tmp_path / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "settings.json").write_text(
        json.dumps({"documentation": {"dir": "docs", "adrs": adrs}})
    )


class TestADRClient:
    # --- Tests for ADRClient.build_parser. ---

    def test_build_parser_returns_parser_with_defaults(self) -> None:
        """build_parser returns a parser with default values."""
        parser = ADRClient.build_parser()
        args = parser.parse_args([])
        assert args.json is False

    def test_build_parser_accepts_json_flag(self) -> None:
        """build_parser parses the --json flag."""
        parser = ADRClient.build_parser()
        args = parser.parse_args(["--json"])
        assert args.json is True

    # --- Tests for ADRClient.format_report. ---

    def test_format_report_json_returns_json_string(self) -> None:
        """format_report returns JSON when as_json=True."""
        report = DistillReport(new=["a.md"], has_adrs=True)
        result = ADRClient.format_report(report, as_json=True)
        data = json.loads(result)
        assert data["new"] == ["a.md"]
        assert data["has_adrs"] is True

    def test_format_report_plain_with_adrs_returns_summary(self) -> None:
        """format_report returns plain text summary when adrs exist."""
        report = DistillReport(new=["a.md"], stale=["b.md"], removed=["c.md"], has_adrs=True)
        result = ADRClient.format_report(report, as_json=False)
        assert "1 new" in result
        assert "1 stale" in result
        assert "1 removed" in result

    def test_format_report_plain_lead_ins_appends_warning(self) -> None:
        """format_report names the ADRs whose directive looks like a lead-in."""
        report = DistillReport(has_adrs=True, lead_ins=["ADR-0006", "ADR-0015"])
        result = ADRClient.format_report(report, as_json=False)
        assert "ADR-0006" in result
        assert "ADR-0015" in result
        assert "lead-in" in result

    def test_format_report_plain_without_lead_ins_has_no_warning(self) -> None:
        """format_report omits the warning when every directive is a sentence."""
        report = DistillReport(new=["a.md"], has_adrs=True)
        result = ADRClient.format_report(report, as_json=False)
        assert "lead-in" not in result

    def test_format_report_json_includes_lead_ins(self) -> None:
        """format_report carries lead_ins through to JSON output."""
        report = DistillReport(has_adrs=True, lead_ins=["ADR-0006"])
        data = json.loads(ADRClient.format_report(report, as_json=True))
        assert data["lead_ins"] == ["ADR-0006"]

    def test_format_report_plain_no_adrs_returns_no_adrs_message(self) -> None:
        """format_report returns 'no ADRs found' when has_adrs is False."""
        report = DistillReport(has_adrs=False)
        result = ADRClient.format_report(report, as_json=False)
        assert result == "ADR distiller: no ADRs found"

    def test_format_report_plain_with_dropped_keeps_summary(self) -> None:
        """The dropped count is appended to the counts line, not a replacement."""
        report = DistillReport(new=["a.md"], has_adrs=True, dropped=["ADR-0001"])
        result = ADRClient.format_report(report, as_json=False)
        assert result == "ADR distiller: 1 new, 0 stale, 0 removed, 1 dropped"

    def test_format_report_plain_with_lead_ins_keeps_summary(self) -> None:
        """The lead-in warning is appended to the counts line, not a replacement."""
        report = DistillReport(has_adrs=True, lead_ins=["ADR-0006", "ADR-0015"])
        result = ADRClient.format_report(report, as_json=False)
        assert result.startswith("ADR distiller: 0 new, 0 stale, 0 removed")
        assert result.endswith("rather than a decision: ADR-0006, ADR-0015")

    # --- Tests for ADRClient.missing_docs_error. ---

    def test_missing_docs_error_plain_returns_error_message(self) -> None:
        """missing_docs_error returns plain text error."""
        result = ADRClient.missing_docs_error(Path("/tmp/nope"), as_json=False)
        assert "/tmp/nope" in result
        assert "not a directory" in result

    def test_missing_docs_error_json_returns_json_dict(self) -> None:
        """missing_docs_error returns JSON with empty fields."""
        result = ADRClient.missing_docs_error(Path("/tmp/nope"), as_json=True)
        data = json.loads(result)
        assert data["new"] == []
        assert data["has_adrs"] is False

    def test_missing_docs_error_json_has_exact_keys(self) -> None:
        result = ADRClient.missing_docs_error(Path("/tmp/nope"), as_json=True)
        data = json.loads(result)
        assert set(data) == {"new", "stale", "removed", "dropped", "lead_ins", "has_adrs"}
        assert data["stale"] == []
        assert data["removed"] == []
        assert data["dropped"] == []
        assert data["lead_ins"] == []

    # --- Tests for ADRClient.run. ---

    def test_run_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run returns 1 when documentation.dir does not exist."""
        monkeypatch.chdir(tmp_path)
        rc = ADRClient.run([])
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
        rc = ADRClient.run(["--json"])
        assert rc == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["has_adrs"] is False

    def test_run_missing_docs_error_names_docs_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The error message names the configured docs dir, not a placeholder."""
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        (meta / "settings.json").write_text(json.dumps({"documentation": {"dir": "handbook"}}))
        monkeypatch.chdir(tmp_path)
        rc = ADRClient.run([])
        assert rc == 1
        assert "handbook" in capsys.readouterr().err

    def test_run_uses_configured_docs_dir_not_default(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A missing configured dir must fail even when ./docs exists."""
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        (meta / "settings.json").write_text(json.dumps({"documentation": {"dir": "no_such_docs"}}))
        (tmp_path / "docs").mkdir()
        monkeypatch.chdir(tmp_path)
        rc = ADRClient.run([])
        assert rc == 1
        assert "no_such_docs" in capsys.readouterr().err

    def test_run_writes_cache_under_configured_runs_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The mtime cache lands under ``runs_dir``, not the default."""
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        (meta / "settings.json").write_text(
            json.dumps(
                {
                    "runs_dir": "custom_runs",
                    "documentation": {"dir": "docs", "adrs": None},
                }
            )
        )
        (tmp_path / "docs").mkdir()
        monkeypatch.chdir(tmp_path)
        rc = ADRClient.run([])
        assert rc == 0
        assert (tmp_path / "custom_runs" / "adr-cache.json").exists()

    # --- Tests for the CLI main() function. ---

    def _run(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        argv: list[str],
    ) -> int:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return ADRClient.main()

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

    def test_format_report_plain_with_dropped_appends_count(self) -> None:
        report = DistillReport(has_adrs=True, dropped=["ADR-0001"])
        assert "1 dropped" in ADRClient.format_report(report, as_json=False)
