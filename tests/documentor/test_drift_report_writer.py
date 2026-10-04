"""Tests for DriftReportWriter."""

from __future__ import annotations

import json
from pathlib import Path

from zolletta_metaskill.documentor.drift_report_writer import DriftReportWriter


class TestDriftReportWriter:
    """Tests for DriftReportWriter formatting."""

    # --- Empty Report ---

    def test_generate_report_no_issues(self, tmp_path: Path) -> None:
        """Report with no issues emits success message or clean JSON."""
        text = DriftReportWriter.generate_report(str(tmp_path), [], ["doc.md"], as_json=False)
        assert "No documentation drift detected" in text

        json_out = DriftReportWriter.generate_report(str(tmp_path), [], ["doc.md"], as_json=True)
        data = json.loads(json_out)
        assert data["summary"]["total_issues"] == 0
        assert data["summary"]["drifted_docs"] == 0

    # --- Populated Report ---

    def test_generate_report_with_issues_text_and_json(self, tmp_path: Path) -> None:
        """Report with issues formats sections grouped by severity."""
        issues = [
            {
                "file": "docs/api.md",
                "severity": "high",
                "category": "factual",
                "description": "Function foo() removed",
                "fix_type": "manual",
            },
            {
                "file": "README.md",
                "severity": "info",
                "category": "temporal",
                "description": "Untracked doc",
                "fix_type": "auto",
            },
        ]
        docs = ["docs/api.md", "README.md"]
        text = DriftReportWriter.generate_report(str(tmp_path), issues, docs, as_json=False)
        assert "Documentation Drift Report" in text
        assert "HIGH SEVERITY (1 issues)" in text
        assert "docs/api.md" in text
        assert "[MANUAL] Function foo() removed" in text

        json_out = DriftReportWriter.generate_report(str(tmp_path), issues, docs, as_json=True)
        data = json.loads(json_out)
        assert data["summary"]["total_issues"] == 2
        assert data["summary"]["drifted_docs"] == 1
        assert data["summary"]["by_severity"]["high"] == 1
        assert data["summary"]["by_severity"]["info"] == 1
