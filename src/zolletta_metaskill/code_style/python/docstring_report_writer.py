"""DocstringReportWriter formats docstring streamlining reports in text and JSON.

Separates report presentation from docstring AST analysis and editing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zolletta_metaskill.code_style.python.structs import FileReport, Finding


class DocstringReportWriter:
    """Formats docstring streamlining results into console text or JSON reports."""

    KIND_LABELS: dict[str, str] = {
        "redundant": "Redundant Args/Returns sections",
        "private": "Private function docstrings (docstring_strip_private)",
        "test": "Test function docstrings (docstring_strip_tests)",
        "nested": "Nested function docstrings (docstring_strip_nested)",
        "obvious_init": "Obvious __init__ docstrings (docstring_strip_obvious_init)",
    }

    @staticmethod
    def _rel(path: Path) -> str:
        """Return path relative to current working directory if possible."""
        try:
            return str(path.relative_to(Path(".").resolve()))
        except ValueError:
            return str(path)

    @staticmethod
    def _findings_payload(reports: list[FileReport]) -> list[dict[str, Any]]:
        """Extract structured findings payload from file reports."""
        findings: list[dict[str, Any]] = []
        for report in reports:
            for f in report.findings:
                findings.append(
                    {
                        "file": DocstringReportWriter._rel(f.file),
                        "line": f.line,
                        "kind": f.kind,
                        "detail": f.detail,
                    }
                )
        return findings

    @staticmethod
    def json_report(reports: list[FileReport], directories: list[str], apply_mode: bool) -> int:
        """Print a JSON report. Return the total finding count."""
        findings = DocstringReportWriter._findings_payload(reports)
        result = {
            "directories": directories,
            "apply_mode": apply_mode,
            "findings": findings,
            "total": len(findings),
        }
        print(json.dumps(result, indent=2))
        return len(findings)

    @staticmethod
    def print_report(reports: list[FileReport], apply_mode: bool) -> int:
        """Print a human-readable report. Return the total finding count."""
        all_findings: list[Finding] = []
        for report in reports:
            all_findings.extend(report.findings)

        print("=" * 70)
        print("DOCSTRING STREAMLINE — REPORT")
        print("=" * 70)

        if not all_findings:
            print("\nResult: all clear\n")
            return 0

        by_kind: dict[str, list[Finding]] = {}
        for f in all_findings:
            by_kind.setdefault(f.kind, []).append(f)

        for kind, label in DocstringReportWriter.KIND_LABELS.items():
            items = by_kind.get(kind, [])
            if not items:
                continue
            print(f"\n## {label} ({len(items)} finding{'s' if len(items) != 1 else ''})\n")
            for f in items:
                print(f"  {DocstringReportWriter._rel(f.file)}:{f.line}")
                print(f"    {f.detail}")

        total = len(all_findings)
        print()
        if apply_mode:
            print(f"Result: {total} docstring(s) streamlined (apply mode)")
        else:
            print(f"Result: {total} finding(s) (dry-run mode). Use --apply to fix.")
        return total
