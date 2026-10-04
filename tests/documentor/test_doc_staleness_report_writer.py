"""Tests for DocStalenessReportWriter."""

from __future__ import annotations

import json

from zolletta_metaskill.documentor.doc_staleness_report_writer import (
    DocStalenessReportWriter,
)


class TestDocStalenessReportWriter:
    """Tests for DocStalenessReportWriter report generation."""

    # --- Labels and Bars ---

    def test_get_label_mapping(self) -> None:
        """get_label maps score ranges to expected human-readable strings."""
        assert DocStalenessReportWriter.get_label(95.0) == "fresh"
        assert DocStalenessReportWriter.get_label(80.0) == "acceptable"
        assert DocStalenessReportWriter.get_label(60.0) == "aging"
        assert DocStalenessReportWriter.get_label(40.0) == "stale"
        assert DocStalenessReportWriter.get_label(10.0) == "abandoned"
        assert DocStalenessReportWriter.get_label(-5.0) == "unknown"

    def test_score_bar(self) -> None:
        """_score_bar generates an ascii progress bar."""
        bar = DocStalenessReportWriter._score_bar(50.0, width=10)
        assert bar == "[#####.....]"

    # --- Report Generation ---

    def test_generate_report_empty(self) -> None:
        """Empty score list returns informational message or empty json."""
        text = DocStalenessReportWriter.generate_report([], as_json=False)
        assert "No documentation files found" in text

        json_out = DocStalenessReportWriter.generate_report([], as_json=True)
        data = json.loads(json_out)
        assert data["documents"] == []
        assert data["aggregate_score"] == 0

    def test_generate_report_populated_text_and_json(self) -> None:
        """Populated scores emit valid markdown table and structured JSON."""
        scores = [
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

        text = DocStalenessReportWriter.generate_report(scores, as_json=False)
        assert "Documentation Staleness Report" in text
        assert "docs/guide.md" in text
        assert "README.md" in text

        json_out = DocStalenessReportWriter.generate_report(scores, as_json=True)
        data = json.loads(json_out)
        assert data["total_documents"] == 2
        assert data["aggregate_score"] == 90.0
        assert data["aggregate_label"] == "acceptable"
