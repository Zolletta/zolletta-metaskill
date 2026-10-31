"""Tests for APIDocReportWriter."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from zolletta_metaskill.documentor.api_doc.api_doc_report_writer import APIDocReportWriter
from zolletta_metaskill.documentor.structs import APIDocReportOptions


def _issues_and_suggestions_fixture() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One missing-parameter issue and one undocumented-function suggestion."""
    issues = [
        {
            "type": "missing_param_in_docs",
            "severity": "high",
            "description": "Parameter x missing from doc",
            "source_file": "src/foo.py",
            "source_line": 15,
        }
    ]
    suggestions = [
        {
            "name": "bar",
            "kind": "function",
            "reason": "Public function has no docstring",
            "priority": "high",
            "source_file": "src/bar.py",
            "source_line": 20,
        }
    ]
    return issues, suggestions


def _rich_fixture() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Issues and suggestions exercising every severity, priority, and default."""
    issues: list[dict[str, Any]] = [
        {
            "type": "missing_param_in_docs",
            "severity": "high",
            "description": "d-high-1",
            "source_file": "src/a.py",
            "source_line": 10,
            "doc_file": "docs/a.md",
            "doc_line": 20,
        },
        {
            "type": "documented_not_in_source",
            "severity": "high",
            "description": "d-high-2",
        },
        {
            "type": "extra_param_in_docs",
            "severity": "medium",
            "description": "d-med-1",
            "source_file": "src/b.py",
        },
        {"severity": "medium", "description": "d-med-2"},
        {
            "type": "deprecated_still_documented",
            "severity": "low",
            "description": "d-low-1",
            "doc_file": "docs/c.md",
        },
        {
            "type": "documented_not_in_source",
            "severity": "low",
            "description": "d-low-2",
        },
        {"type": "mystery", "description": "d-x"},
    ]
    suggestions: list[dict[str, Any]] = [
        {
            "name": "s-high",
            "kind": "function",
            "reason": "r-h",
            "priority": "high",
            "source_file": "src/s.py",
            "source_line": 5,
        },
        *[
            {
                "name": f"s-med-{i}",
                "kind": "class",
                "reason": "r-m",
                "priority": "medium",
                "source_file": f"src/m{i}.py",
                "source_line": i,
            }
            for i in range(21)
        ],
        *[
            {
                "name": f"s-low-{i}",
                "kind": "method",
                "reason": "r-l",
                "priority": "low",
                "source_file": f"src/l{i}.py",
                "source_line": i,
            }
            for i in range(20)
        ],
        {"name": "s-skip", "kind": "module", "reason": "r-s", "priority": "skip"},
        {"name": "s-nopri", "kind": "function", "reason": "r-n"},
    ]
    return issues, suggestions


class TestAPIDocReportWriter:
    """Tests for APIDocReportWriter formatting."""

    # --- Empty and Basic Reports ---

    def test_generate_report_no_issues(self) -> None:
        """Report with no issues prints clear message or valid empty json."""
        text = APIDocReportWriter.generate_report(
            [], [], APIDocReportOptions(10, 10, as_json=False)
        )
        assert "No drift issues found" in text

        json_out = APIDocReportWriter.generate_report(
            [], [], APIDocReportOptions(10, 10, as_json=True)
        )
        data = json.loads(json_out)
        assert data["summary"]["total_issues"] == 0
        assert data["summary"]["source_signatures"] == 10

    # --- Populated Reports ---

    def test_generate_report_with_issues_and_suggestions(self) -> None:
        """Report with issues and suggestions renders headers, sections, and summaries."""
        issues, suggestions = _issues_and_suggestions_fixture()
        text = APIDocReportWriter.generate_report(
            issues, suggestions, APIDocReportOptions(5, 4, as_json=False, suggest_coverage=True)
        )
        assert "API Documentation Validation Report" in text
        assert "HIGH (1 issues):" in text
        assert "DOCUMENTATION SUGGESTIONS:" in text
        assert "bar (function)" in text
        assert "ISSUES BY TYPE:" in text

        json_out = APIDocReportWriter.generate_report(
            issues, suggestions, APIDocReportOptions(5, 4, as_json=True, suggest_coverage=True)
        )
        data = json.loads(json_out)
        assert data["summary"]["total_issues"] == 1
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["name"] == "bar"

    # --- Text Output Contract ---

    def test_generate_report_matches_committed_contract(
        self,
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The rendered report is a byte-for-byte contract.

        The comparison is exact on purpose and must not be loosened to a
        substring or regex check: a legitimate change to the rendered report is
        ``pytest --update-fixtures`` followed by a reviewed diff. The trailing
        newline keeps the committed fixture a POSIX text file.

        """
        issues, suggestions = _issues_and_suggestions_fixture()
        report = APIDocReportWriter.generate_report(
            issues, suggestions, APIDocReportOptions(5, 4, as_json=False, suggest_coverage=True)
        )
        text_contract("documentor/api_doc/api_doc_report_writer.txt", f"{report}\n")

    # --- Exact Output ---

    def test_generate_report_empty_input_exact_lines(self) -> None:
        """The no-issues report is asserted line-for-line."""
        report = APIDocReportWriter.generate_report(
            [], [], APIDocReportOptions(10, 10, as_json=False)
        )
        assert report.splitlines() == [
            "API Documentation Validation Report",
            "=" * 60,
            "Source signatures found: 10",
            "Documented items found:  10",
            "Issues found:            0",
            "Undocumented items:      0",
            "",
            "No drift issues found. API documentation matches source code.",
            "",
            "Undocumented items: 0 (not counted as issues)",
            "  Use --suggest-coverage to see prioritized documentation suggestions.",
        ]

    def test_generate_report_missing_medium_severity_still_renders_low(self) -> None:
        """A gap in the severity order does not stop later severity sections."""
        issues = [
            {"type": "missing_param_in_docs", "severity": "high", "description": "d-high"},
            {"type": "extra_param_in_docs", "severity": "low", "description": "d-low"},
        ]
        report = APIDocReportWriter.generate_report(
            issues, [], APIDocReportOptions(3, 2, as_json=False)
        )
        assert report.splitlines() == [
            "API Documentation Validation Report",
            "=" * 60,
            "Source signatures found: 3",
            "Documented items found:  2",
            "Issues found:            2",
            "Undocumented items:      0",
            "",
            "HIGH (1 issues):",
            "-" * 40,
            "  [missing_param_in_docs] d-high",
            "",
            "",
            "LOW (1 issues):",
            "-" * 40,
            "  [extra_param_in_docs] d-low",
            "",
            "",
            "ISSUES BY TYPE:",
            "-" * 40,
            "  Extra parameters in docs: 1",
            "  Missing parameters in docs: 1",
            "",
            "Undocumented items: 0 (not counted as issues)",
            "  Use --suggest-coverage to see prioritized documentation suggestions.",
        ]

    def test_generate_report_rich_fixture_exact_lines(self) -> None:
        """Every branch of the text renderer is asserted line-for-line."""
        issues, suggestions = _rich_fixture()
        report = APIDocReportWriter.generate_report(
            issues, suggestions, APIDocReportOptions(7, 6, as_json=False, suggest_coverage=True)
        )
        expected = [
            "API Documentation Validation Report",
            "=" * 60,
            "Source signatures found: 7",
            "Documented items found:  6",
            "Issues found:            7",
            "Undocumented items:      44",
            "  by priority:           high=1, low=21, medium=21, skip=1",
            "",
            "HIGH (2 issues):",
            "-" * 40,
            "  [missing_param_in_docs] d-high-1",
            "    Source: src/a.py:10",
            "    Doc:    docs/a.md:20",
            "",
            "  [documented_not_in_source] d-high-2",
            "",
            "",
            "MEDIUM (2 issues):",
            "-" * 40,
            "  [extra_param_in_docs] d-med-1",
            "    Source: src/b.py:?",
            "",
            "  [unknown] d-med-2",
            "",
            "",
            "LOW (2 issues):",
            "-" * 40,
            "  [deprecated_still_documented] d-low-1",
            "    Doc:    docs/c.md:?",
            "",
            "  [documented_not_in_source] d-low-2",
            "",
            "",
            "DOCUMENTATION SUGGESTIONS:",
            "-" * 40,
            "  [HIGH] (1 items):",
            "    s-high (function) — r-h",
            "      Source: src/s.py:5",
            "",
            "  [MEDIUM] (21 items):",
            *[
                line
                for i in range(20)
                for line in (
                    f"    s-med-{i} (class) — r-m",
                    f"      Source: src/m{i}.py:{i}",
                )
            ],
            "    ... and 1 more",
            "",
            "  [LOW] (20 items):",
            *[
                line
                for i in range(20)
                for line in (
                    f"    s-low-{i} (method) — r-l",
                    f"      Source: src/l{i}.py:{i}",
                )
            ],
            "",
            "  [SKIP] (1 items):",
            "    s-skip (module) — r-s",
            "      Source: ?:?",
            "",
            "",
            "ISSUES BY TYPE:",
            "-" * 40,
            "  Deprecated items still documented: 1",
            "  Documented but not in source: 2",
            "  Extra parameters in docs: 1",
            "  Missing parameters in docs: 1",
            "  mystery: 1",
            "  unknown: 1",
            "",
            "Undocumented items: 44 (not counted as issues)",
            "  by priority: high=1, low=21, medium=21, skip=1",
            "  Use --suggest-coverage to see prioritized documentation suggestions.",
        ]
        assert report.splitlines() == expected

    def test_generate_report_data_rich_fixture_exact_dict(self) -> None:
        """The report data structure is asserted as a whole dict."""
        issues, suggestions = _rich_fixture()
        data = APIDocReportWriter.generate_report_data(
            issues, suggestions, APIDocReportOptions(7, 6, suggest_coverage=True)
        )
        assert data == {
            "summary": {
                "source_signatures": 7,
                "documented_items": 6,
                "total_issues": 7,
                "undocumented_count": 44,
                "undocumented_by_priority": {
                    "high": 1,
                    "medium": 21,
                    "low": 21,
                    "skip": 1,
                },
                "by_type": {
                    "missing_param_in_docs": 1,
                    "documented_not_in_source": 2,
                    "extra_param_in_docs": 1,
                    "deprecated_still_documented": 1,
                    "unknown": 1,
                    "mystery": 1,
                },
                "by_severity": {"high": 2, "medium": 2, "low": 2, "unknown": 1},
            },
            "issues": issues,
            "suggestions": suggestions,
        }

        without_suggestions = APIDocReportWriter.generate_report_data(
            issues, suggestions, APIDocReportOptions(7, 6, suggest_coverage=False)
        )
        assert "suggestions" not in without_suggestions
        assert without_suggestions["summary"] == data["summary"]

    def test_generate_report_json_output_exact_string(self) -> None:
        """JSON output is a two-space-indented dump that stringifies odd values."""
        issues = [
            {
                "type": "missing_param_in_docs",
                "severity": "high",
                "description": "d",
                "odd": Path("p"),
            }
        ]
        json_out = APIDocReportWriter.generate_report(
            issues, [], APIDocReportOptions(5, 4, as_json=True)
        )
        expected = {
            "summary": {
                "source_signatures": 5,
                "documented_items": 4,
                "total_issues": 1,
                "undocumented_count": 0,
                "undocumented_by_priority": {},
                "by_type": {"missing_param_in_docs": 1},
                "by_severity": {"high": 1},
            },
            "issues": [
                {
                    "type": "missing_param_in_docs",
                    "severity": "high",
                    "description": "d",
                    "odd": "p",
                }
            ],
        }
        assert json_out == json.dumps(expected, indent=2, default=str)
