"""Tests for ADROrchestrator.run() and the module-level main()."""

from __future__ import annotations

from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator, main

from .conftest import write_adr


class TestADROrchestratorRun:
    """Tests for ADROrchestrator.run() — delegates to ADRCLI.run()."""

    def test_run_with_valid_adrs_returns_0(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_dir = tmp_path / "cache"
        rc = ADROrchestrator.run(
            [
                "--docs-dir",
                str(docs),
                "--adrs-path",
                "adr",
                "--cache-dir",
                str(cache_dir),
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 new" in out

    def test_run_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = ADROrchestrator.run(
            ["--docs-dir", str(tmp_path / "nope"), "--adrs-path", "adr"]
        )
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
        import sys

        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_dir = tmp_path / "cache"
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
        rc = ADROrchestrator.run(None)
        assert rc == 0


class TestMain:
    """Tests for the module-level main() function."""

    def test_main_with_adrs_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import sys

        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_dir = tmp_path / "cache"
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
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 new" in out

    def test_main_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import sys

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--docs-dir", str(tmp_path / "nope"), "--adrs-path", "adr"],
        )
        rc = main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err
