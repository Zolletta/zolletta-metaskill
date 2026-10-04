"""Tests for DocstringReportWriter."""

from __future__ import annotations

import ast
from pathlib import Path

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
