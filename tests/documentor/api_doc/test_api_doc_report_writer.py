"""Tests for APIDocReportWriter."""

from __future__ import annotations

import json
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
