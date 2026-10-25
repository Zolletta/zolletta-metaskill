"""Tests for DocstringReportWriter."""

from __future__ import annotations

import ast
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.docstring_report_writer import (
    DocstringReportWriter,
)
from zolletta_metaskill.code_style.python.structs import FileReport, Finding


class TestDocstringReportWriter:
    """Tests for DocstringReportWriter formatting."""

    # --- Empty Report ---

    def test_empty_report_text(self, capsys: object) -> None:
        """Empty report emits all clear message."""
        total = DocstringReportWriter.print_report([], apply_mode=False)
        assert total == 0

    def test_empty_report_json(self, capsys: object) -> None:
        """Empty report in JSON returns 0 findings."""
        total = DocstringReportWriter.json_report([], ["src"], apply_mode=False)
        assert total == 0

    # --- Populated Report ---

    def test_populated_report_text(self) -> None:
        """Populated report prints findings grouped by kind."""
        finding = Finding(
            file=Path("src/a.py"),
            line=10,
            kind="redundant",
            detail="Redundant section",
            node=ast.Pass(),
            new_text='"""New."""',
        )
        report = FileReport(path=Path("src/a.py"), findings=[finding])
        total = DocstringReportWriter.print_report([report], apply_mode=False)
        assert total == 1

    def test_populated_report_json(self) -> None:
        """Populated report emits valid JSON findings payload."""
        finding = Finding(
            file=Path("src/b.py"),
            line=20,
            kind="private",
            detail="Private function docstring removed",
            node=ast.Pass(),
            remove=True,
        )
        report = FileReport(path=Path("src/b.py"), findings=[finding])
        total = DocstringReportWriter.json_report([report], ["src"], apply_mode=True)
        assert total == 1

    def test_json_report_findings_have_exact_keys(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Each finding object exposes exactly file/line/kind/detail."""
        finding = Finding(
            file=Path("src/b.py"),
            line=20,
            kind="private",
            detail="Private function docstring removed",
            node=ast.Pass(),
            remove=True,
        )
        report = FileReport(path=Path("src/b.py"), findings=[finding])
        DocstringReportWriter.json_report([report], ["src"], apply_mode=True)
        data = json.loads(capsys.readouterr().out)
        assert set(data["findings"][0]) == {"file", "line", "kind", "detail"}
        assert data["findings"][0]["line"] == 20
        assert data["findings"][0]["kind"] == "private"
        assert data["findings"][0]["detail"] == "Private function docstring removed"

    def test_json_report_output_is_indented(self, capsys: pytest.CaptureFixture[str]) -> None:
        DocstringReportWriter.json_report([], ["src"], apply_mode=False)
        out = capsys.readouterr().out
        assert '\n  "' in out

    def test_print_report_all_clear_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        DocstringReportWriter.print_report([], apply_mode=False)
        assert capsys.readouterr().out.endswith("Result: all clear\n\n")

    def test_print_report_pluralizes_findings(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A kind with several findings prints ``(N findings)`` with the plural s."""
        findings = [
            Finding(
                file=Path("src/a.py"),
                line=line,
                kind="redundant",
                detail="Redundant section",
                node=ast.Pass(),
            )
            for line in (4, 9)
        ]
        report = FileReport(path=Path("src/a.py"), findings=findings)
        DocstringReportWriter.print_report([report], apply_mode=False)
        assert "(2 findings)" in capsys.readouterr().out

    # --- text-output contract (tests.4) ---

    def test_print_report_matches_committed_contract(
        self, capsys: pytest.CaptureFixture[str], text_contract: Callable[[str, str], None]
    ) -> None:
        """The text report is a byte-for-byte contract that must not be loosened.

        The committed fixture is the full captured stdout; a legitimate change is
        ``pytest --update-fixtures`` plus a reviewed diff.
        """
        reports = [
            FileReport(
                path=Path("src/a.py"),
                findings=[
                    Finding(
                        file=Path("src/a.py"),
                        line=4,
                        kind="redundant",
                        detail="Redundant Args/Returns section",
                        node=ast.Pass(),
                    ),
                    Finding(
                        file=Path("src/a.py"),
                        line=9,
                        kind="private",
                        detail="Private function docstring",
                        node=ast.Pass(),
                        remove=True,
                    ),
                ],
            ),
            FileReport(
                path=Path("src/b.py"),
                findings=[
                    Finding(
                        file=Path("src/b.py"),
                        line=2,
                        kind="test",
                        detail="Test function docstring",
                        node=ast.Pass(),
                    ),
                ],
            ),
        ]
        total = DocstringReportWriter.print_report(reports, apply_mode=False)
        assert total == 3
        text_contract("code_style/python/docstring_report_writer.txt", capsys.readouterr().out)
