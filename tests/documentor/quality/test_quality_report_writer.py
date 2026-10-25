"""Tests for QualityReportWriter."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from zolletta_metaskill.documentor.quality import quality_report_writer
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


def _report_data_fixture(
    issues: list[dict[str, Any]] | None = None,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Minimal ``report_data`` dict feeding ``_format_markdown`` directly."""
    return {
        "repository": "repo",
        "scan_date": "2026-01-01T00:00:00Z",
        "summary": {
            "total_docs": len(documents or []),
            "aggregate_score": 50.0,
            "aggregate_label": "aging",
            "drifted_docs": 0,
            "total_issues": len(issues or []),
            "by_severity": {},
            "by_category": {},
            "by_fix_type": {},
        },
        "documents": documents or [],
        "issues": issues or [],
    }


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

    def test_generate_report_default_as_json_returns_markdown(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """Omitting as_json renders the text report, not JSON."""
        repo_path = tmp_path_factory.mktemp("repo")
        text = QualityReportWriter.generate_report(str(repo_path), [], [])
        assert text.splitlines()[0] == "Documentation Staleness + Drift Report"

    def test_generate_report_json_output_is_indented_and_str_defaulted(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """The JSON payload is indent=2 and default=str handles opaque values."""
        repo_path = tmp_path_factory.mktemp("repo")
        scores = [
            {
                "file": "a.md",
                "total_score": 50.0,
                "label": "aging",
                "dimensions": {},
                "generated": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ]
        json_out = QualityReportWriter.generate_report(str(repo_path), scores, [], as_json=True)
        assert json_out == json.dumps(json.loads(json_out), indent=2, default=str)

    # --- Report data ---

    def test_build_report_data_scan_date_is_utc_zulu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """scan_date is the current instant in UTC, rendered as Zulu ISO-8601."""
        captured: dict[str, Any] = {}

        class FrozenDateTime:
            """datetime stand-in returning a fixed instant, recording the tz argument."""

            @staticmethod
            def now(tz: Any = None) -> datetime:
                captured["tz"] = tz
                return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

        monkeypatch.setattr(quality_report_writer, "datetime", FrozenDateTime)
        data = QualityReportWriter._build_report_data("repo", [], [])
        assert captured["tz"] is UTC
        assert data["scan_date"] == "2026-01-01T12:00:00Z"

    def test_build_report_data_aggregate_score_rounds_to_one_decimal(self) -> None:
        """The aggregate score is rounded to exactly one decimal place."""
        scores = [
            {"file": "a.md", "total_score": 100.0, "label": "fresh", "dimensions": {}},
            {"file": "b.md", "total_score": 0.0, "label": "abandoned", "dimensions": {}},
            {"file": "c.md", "total_score": 0.0, "label": "abandoned", "dimensions": {}},
        ]
        data = QualityReportWriter._build_report_data("repo", scores, [])
        assert data["summary"]["aggregate_score"] == 33.3

    def test_build_report_data_summary_counts_defaults_and_repeats(self) -> None:
        """Severity/category/fix_type buckets count defaults and repeats exactly."""
        issues = [
            {
                "file": "a.md",
                "severity": "high",
                "category": "factual",
                "fix_type": "semi",
            },
            {
                "file": "b.md",
                "severity": "high",
                "category": "factual",
                "fix_type": "semi",
            },
            {"file": "c.md"},
            {"file": "d.md", "severity": "info"},
        ]
        data = QualityReportWriter._build_report_data("repo", [], issues)
        assert data["summary"]["drifted_docs"] == 3
        assert data["summary"]["total_issues"] == 4
        assert data["summary"]["by_severity"] == {"high": 2, "info": 2}
        assert data["summary"]["by_category"] == {"factual": 2, "unknown": 2}
        assert data["summary"]["by_fix_type"] == {"semi": 2, "manual": 2}

    # --- Markdown rendering ---

    def test_format_markdown_sorts_issues_by_severity_in_place(self) -> None:
        """_format_markdown reorders the issues list by severity rank."""
        issues = [
            {"file": "nosev.md", "description": "no severity"},
            {"file": "weird.md", "severity": "weird", "description": "unknown severity"},
            {"file": "info.md", "severity": "info", "description": "info"},
            {"file": "crit.md", "severity": "critical", "description": "critical"},
        ]
        report_data = _report_data_fixture(issues=issues)
        QualityReportWriter._format_markdown(report_data)
        assert [i["file"] for i in issues] == [
            "crit.md",
            "nosev.md",
            "info.md",
            "weird.md",
        ]

    def test_format_markdown_renders_every_present_severity_group(self) -> None:
        """Issues land under their severity group; a missing severity counts as info."""
        issues = [
            {"file": "crit.md", "severity": "critical", "description": "d"},
            {"file": "mid.md", "severity": "medium", "description": "d"},
            {"file": "info.md", "severity": "info", "description": "d"},
            {"file": "nosev.md", "description": "d"},
        ]
        text = QualityReportWriter._format_markdown(_report_data_fixture(issues=issues))
        lines = text.splitlines()
        assert "CRITICAL SEVERITY (1 issues):" in lines
        assert "MEDIUM SEVERITY (1 issues):" in lines
        assert "INFO SEVERITY (2 issues):" in lines

    def test_format_markdown_issue_fix_tags_and_category_default(self) -> None:
        """Fix tags map known fix types, fall back to [MANUAL], category to unknown."""
        issues = [
            {
                "file": "a.md",
                "severity": "low",
                "description": "auto fix",
                "fix_type": "auto",
                "category": "factual",
            },
            {"file": "b.md", "severity": "low", "description": "missing fix"},
            {
                "file": "c.md",
                "severity": "low",
                "description": "exotic fix",
                "fix_type": "exotic",
                "category": "temporal",
            },
        ]
        text = QualityReportWriter._format_markdown(_report_data_fixture(issues=issues))
        lines = text.splitlines()
        assert "    [AUTO] auto fix" in lines
        assert "    [MANUAL] missing fix" in lines
        assert "    [MANUAL] exotic fix" in lines
        assert "    Category: unknown" in lines

    def test_format_markdown_fix_type_summary_maps_labels(self) -> None:
        """The fix-type summary labels known types and passes unknowns through."""
        report_data = _report_data_fixture(
            issues=[{"file": "a.md", "severity": "low", "description": "d"}]
        )
        report_data["summary"]["by_fix_type"] = {"auto": 1, "exotic": 2}
        text = QualityReportWriter._format_markdown(report_data)
        lines = text.splitlines()
        assert "  Auto-fixable: 1" in lines
        assert "  exotic: 2" in lines

    def test_format_markdown_empty_issues_prints_all_clear(self) -> None:
        """An issue-free report prints the all-clear line and ends in a newline."""
        text = QualityReportWriter._format_markdown(_report_data_fixture())
        assert text.splitlines()[-1] == "No drift issues detected. All docs appear current."
        assert text.endswith("\n")

    def test_format_markdown_breakdown_limits_to_five_worst(self) -> None:
        """Only the five worst-scoring documents get a dimension breakdown."""
        documents = [
            {
                "file": f"f{i}.md",
                "total_score": float(i),
                "label": "x",
                "dimensions": {"d": {"score": 1.0, "weight": 0.5, "weighted": 0.5}},
            }
            for i in range(6)
        ]
        text = QualityReportWriter._format_markdown(_report_data_fixture(documents=documents))
        assert text.count("(score:") == 5

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
