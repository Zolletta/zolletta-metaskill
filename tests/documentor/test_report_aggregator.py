"""Tests for report_aggregator.py."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from zolletta_metaskill.documentor.report_aggregator import ReportAggregator


class TestReportAggregator:
    def _write(self, cache_dir: Path, name: str, data: dict[str, Any]) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / name).write_text(json.dumps(data))

    def _full_caches(self, cache_dir: Path) -> None:
        self._write(
            cache_dir,
            "quality.json",
            {
                "repository": "/repo",
                "summary": {
                    "aggregate_score": 72.5,
                    "aggregate_label": "acceptable",
                    "total_docs": 4,
                    "total_issues": 3,
                    "drifted_docs": 2,
                },
                "documents": [{"file": "README.md", "total_score": 80.0, "label": "fresh"}],
            },
        )
        self._write(
            cache_dir,
            "api_doc_validator.json",
            {
                "summary": {
                    "source_signatures": 10,
                    "documented_items": 8,
                    "total_issues": 2,
                    "undocumented_count": 3,
                },
                "issues": [],
            },
        )
        self._write(
            cache_dir,
            "link_checker.json",
            {
                "summary": {
                    "total_links": 20,
                    "valid": 18,
                    "broken": 2,
                    "skipped": 0,
                    "duplicate_anchors": 1,
                },
                "issues": [],
            },
        )

    # --- read_*_cache ---

    def test_read_caches_missing_files_return_missing_records(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        quality = ReportAggregator.read_quality_cache(cache_dir)
        api_doc = ReportAggregator.read_api_doc_cache(cache_dir)
        links = ReportAggregator.read_link_cache(cache_dir)
        assert quality["missing"] is True and quality["name"] == "quality"
        assert api_doc["missing"] is True and api_doc["name"] == "api_doc"
        assert links["missing"] is True and links["name"] == "links"

    def test_read_quality_cache_invalid_json_returns_missing(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "quality.json").write_text("not json")
        assert ReportAggregator.read_quality_cache(cache_dir)["missing"] is True

    def test_read_api_doc_cache_invalid_json_returns_missing(self, tmp_path: Path) -> None:
        """An unparsable api doc cache degrades to a missing record."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "api_doc_validator.json").write_text("{not json")
        record = ReportAggregator.read_api_doc_cache(cache_dir)
        assert record["missing"] is True and record["name"] == "api_doc"

    def test_read_link_cache_invalid_json_returns_missing(self, tmp_path: Path) -> None:
        """An unparsable link cache degrades to a missing record."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "link_checker.json").write_text("][")
        record = ReportAggregator.read_link_cache(cache_dir)
        assert record["missing"] is True and record["name"] == "links"

    def test_read_caches_unreadable_files_return_missing(self, tmp_path: Path) -> None:
        """Unreadable cache files are reported as missing rather than raising."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "quality.json").mkdir()
        (cache_dir / "api_doc_validator.json").mkdir()
        (cache_dir / "link_checker.json").mkdir()
        assert ReportAggregator.read_quality_cache(cache_dir)["missing"] is True
        assert ReportAggregator.read_api_doc_cache(cache_dir)["missing"] is True
        assert ReportAggregator.read_link_cache(cache_dir)["missing"] is True

    def test_read_caches_valid_files_return_data(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        self._full_caches(cache_dir)
        assert ReportAggregator.read_quality_cache(cache_dir)["summary"]["aggregate_score"] == 72.5
        assert ReportAggregator.read_api_doc_cache(cache_dir)["summary"]["total_issues"] == 2
        assert ReportAggregator.read_link_cache(cache_dir)["summary"]["broken"] == 2

    # --- aggregate ---

    def test_aggregate_all_missing_lists_missing_sections(self, tmp_path: Path) -> None:
        data = json.loads(ReportAggregator.aggregate(tmp_path / "cache", as_json=True))
        assert sorted(data["summary"]["missing_sections"]) == [
            "api_doc",
            "links",
            "quality",
        ]

    def test_aggregate_json_contains_all_sections_and_summary(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        self._full_caches(cache_dir)
        data = json.loads(ReportAggregator.aggregate(cache_dir, as_json=True))
        assert set(data["sections"]) == {"quality", "api_doc", "links"}
        summary = data["summary"]
        assert summary["aggregate_score"] == 72.5
        assert summary["aggregate_label"] == "acceptable"
        assert summary["total_docs"] == 4
        assert summary["total_drift_issues"] == 3
        assert summary["api_doc_issues"] == 2
        assert summary["api_doc_suggestions"] == 3
        assert summary["total_links"] == 20
        assert summary["broken_links"] == 2
        assert summary["duplicate_anchors"] == 1
        assert summary["missing_sections"] == []

    def test_aggregate_markdown_renders_sections(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        self._full_caches(cache_dir)
        report = ReportAggregator.aggregate(cache_dir)
        assert "Documentor Review Report" in report
        assert "Aggregate quality score: 72.5/100 (acceptable)" in report
        assert "## Staleness + Drift" in report
        assert "## API Documentation" in report
        assert "## Links" in report
        assert "Missing sections" not in report

    def test_aggregate_markdown_shows_missing_sections(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        self._write(cache_dir, "link_checker.json", {"summary": {}, "issues": []})
        report = ReportAggregator.aggregate(cache_dir)
        assert "Missing sections: quality, api_doc" in report
        assert "## Links" in report
        assert "## Staleness + Drift" not in report

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
            "sections": {
                "quality": {
                    "summary": {
                        "aggregate_score": 72.5,
                        "aggregate_label": "acceptable",
                        "total_docs": 4,
                        "drifted_docs": 2,
                        "total_issues": 3,
                    },
                    "documents": [{"file": "README.md", "total_score": 80.0, "label": "fresh"}],
                },
                "api_doc": {
                    "summary": {
                        "source_signatures": 10,
                        "documented_items": 8,
                        "total_issues": 2,
                        "undocumented_count": 3,
                    },
                },
                "links": {
                    "summary": {
                        "total_links": 20,
                        "valid": 18,
                        "broken": 2,
                        "skipped": 0,
                        "duplicate_anchors": 1,
                    },
                },
            },
            "summary": {
                "aggregate_score": 72.5,
                "aggregate_label": "acceptable",
                "total_docs": 4,
                "total_drift_issues": 3,
                "api_doc_issues": 2,
                "api_doc_suggestions": 3,
                "total_links": 20,
                "broken_links": 2,
                "duplicate_anchors": 1,
                "missing_sections": [],
            },
        }
        text = ReportAggregator._format_markdown(report_data)
        text_contract("documentor/report_aggregator.txt", text + "\n")
