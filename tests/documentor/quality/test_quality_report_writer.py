"""Tests for QualityReportWriter."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from zolletta_metaskill.documentor.quality.quality_report_writer import (
    QualityReportWriter,
)


def _issue_report_fixture() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One scored document and two drift issues, one semi-fixable and one manual."""
    scores = [
        {
            "file": "README.md",
            "total_score": 70.0,
            "label": "good",
            "dimensions": {},
        }
    ]
    issues = [
        {
            "file": "README.md",
            "severity": "high",
            "category": "factual",
            "description": "Referenced source file changed",
            "fix_type": "semi",
        },
        {
            "file": "README.md",
            "severity": "low",
            "category": "temporal",
            "description": "Documentation not updated in 200 days",
            "fix_type": "manual",
        },
    ]
    return scores, issues


def _populated_scores_fixture() -> list[dict[str, Any]]:
    """Two scored documents with distinct labels for populated-report tests."""
    return [
        {
            "file": "docs/guide.md",
            "total_score": 85.0,
            "label": "acceptable",
            "dimensions": {
                "last_updated": {"score": 90.0, "weight": 0.2, "weighted": 18.0},
                "accuracy": {"score": 80.0, "weight": 0.15, "weighted": 12.0},
            },
        },
        {
            "file": "README.md",
            "total_score": 95.0,
            "label": "fresh",
            "dimensions": {
                "last_updated": {"score": 100.0, "weight": 0.2, "weighted": 20.0},
                "accuracy": {"score": 90.0, "weight": 0.15, "weighted": 13.5},
            },
        },
    ]


class TestQualityReportWriter:
    """Tests for QualityReportWriter report generation."""

    # --- Labels and Bars ---

    def test_get_label_mapping(self) -> None:
        """get_label maps score ranges to expected human-readable strings."""
        assert QualityReportWriter.get_label(95.0) == "fresh"
        assert QualityReportWriter.get_label(80.0) == "acceptable"
        assert QualityReportWriter.get_label(60.0) == "aging"
        assert QualityReportWriter.get_label(40.0) == "stale"
        assert QualityReportWriter.get_label(10.0) == "abandoned"
        assert QualityReportWriter.get_label(-5.0) == "unknown"

    def test_score_bar_fills_half_when_score_is_fifty(self) -> None:
        """_score_bar generates an ascii progress bar."""
        bar = QualityReportWriter._score_bar(50.0, width=10)
        assert bar == "[#####.....]"

    # --- Report Generation ---

    def test_generate_report_empty(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Empty score list returns report with zero aggregate."""
        repo_path = tmp_path_factory.mktemp("repo")
        text = QualityReportWriter.generate_report(str(repo_path), [], [], as_json=False)
        assert "Documentation Staleness + Drift Report" in text
        assert "Documents:       0" in text

        json_out = QualityReportWriter.generate_report(str(repo_path), [], [], as_json=True)
        data = json.loads(json_out)
        assert data["documents"] == []
        assert data["summary"]["total_docs"] == 0
        assert data["summary"]["aggregate_score"] == 0

    def test_generate_report_populated_text_and_json(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """Populated scores emit valid markdown table and structured JSON."""
        repo_path = tmp_path_factory.mktemp("repo")
        scores = _populated_scores_fixture()

        text = QualityReportWriter.generate_report(str(repo_path), scores, [], as_json=False)
        assert "Documentation Staleness + Drift Report" in text
        assert "docs/guide.md" in text
        assert "README.md" in text

        json_out = QualityReportWriter.generate_report(str(repo_path), scores, [], as_json=True)
        data = json.loads(json_out)
        assert data["summary"]["total_docs"] == 2
        assert data["summary"]["aggregate_score"] == 90.0
        assert data["summary"]["aggregate_label"] == "acceptable"

    def test_generate_report_with_issues(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Drift issues are grouped by severity and include fix-type tags."""
        repo_path = tmp_path_factory.mktemp("repo")
        scores, issues = _issue_report_fixture()
        text = QualityReportWriter.generate_report(str(repo_path), scores, issues, as_json=False)
        assert "HIGH SEVERITY" in text
        assert "[SEMI]" in text
        assert "FIX TYPE SUMMARY" in text

        json_out = QualityReportWriter.generate_report(str(repo_path), scores, issues, as_json=True)
        data = json.loads(json_out)
        assert data["summary"]["total_issues"] == 2
        assert data["summary"]["by_severity"]["high"] == 1
        assert data["summary"]["by_severity"]["low"] == 1

    # --- Text contract ---

    def test_generate_report_matches_committed_contract(
        self,
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The rendered report is a byte-for-byte contract that must not be loosened.

        A literal ``report_data`` pins the markdown renderer to its committed
        output, so a legitimate change is ``pytest --update-fixtures`` plus a
        reviewed diff — never a hand-edit or a weaker matcher. The trailing
        newline keeps the fixture POSIX-clean while matching the rendered text.
        """
        report_data: dict[str, Any] = {
            "repository": "repo",
            "scan_date": "2026-01-01T00:00:00Z",
            "summary": {
                "total_docs": 2,
                "aggregate_score": 77.5,
                "aggregate_label": "acceptable",
                "drifted_docs": 1,
                "total_issues": 2,
                "by_severity": {"high": 1, "low": 1},
                "by_category": {"factual": 1, "temporal": 1},
                "by_fix_type": {"manual": 1, "semi": 1},
            },
            "documents": [
                {
                    "file": "README.md",
                    "total_score": 70.0,
                    "label": "aging",
                    "dimensions": {
                        "temporal": {"score": 50.0, "weight": 0.20, "weighted": 10.0},
                    },
                },
                {
                    "file": "docs/guide.md",
                    "total_score": 85.0,
                    "label": "acceptable",
                    "dimensions": {
                        "factual": {"score": 90.0, "weight": 0.15, "weighted": 13.5},
                    },
                },
            ],
            "issues": [
                {
                    "file": "README.md",
                    "severity": "high",
                    "category": "factual",
                    "description": "Referenced source file changed",
                    "fix_type": "semi",
                },
                {
                    "file": "docs/guide.md",
                    "severity": "low",
                    "category": "temporal",
                    "description": "Documentation not updated in 200 days",
                    "fix_type": "manual",
                },
            ],
        }
        text = QualityReportWriter._format_markdown(report_data)
        text_contract("documentor/quality/quality_report_writer.txt", text + "\n")
