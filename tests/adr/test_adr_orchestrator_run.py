"""Tests for ADROrchestrator.run() and ADROrchestrator.main()."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator

from .conftest import write_adr


def write_settings(tmp_path: Path) -> None:
    """Write a minimal settings.json into ``tmp_path/.zolletta-metaskill``."""
    meta = tmp_path / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "settings.json").write_text(
        json.dumps({"documentation": {"dir": "docs", "adrs": "adr"}})
    )


class TestADROrchestratorRun:
    """Tests for ADROrchestrator.run() — delegates to ADRCLI.run()."""

    def test_run_with_valid_adrs_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        monkeypatch.chdir(tmp_path)
        rc = ADROrchestrator.run([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 new" in out

    def test_run_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        monkeypatch.chdir(tmp_path)
        rc = ADROrchestrator.run([])
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err

    def test_run_with_none_argv_uses_sys_argv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When argv is None, ADRCLI.run reads from sys.argv."""
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = ADROrchestrator.run(None)
        assert rc == 0


class TestMain:
    """Tests for ADROrchestrator.main()."""

    def test_main_with_adrs_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = ADROrchestrator.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 new" in out

    def test_main_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = ADROrchestrator.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err
