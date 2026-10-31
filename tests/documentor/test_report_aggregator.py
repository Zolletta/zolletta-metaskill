"""Tests for report_aggregator.py."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import zolletta_metaskill.documentor.report_aggregator as report_aggregator_module
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
        assert ReportAggregator.read_quality_cache(cache_dir) == {
            "missing": True,
            "name": "quality",
            "summary": {},
            "issues": [],
        }
        assert ReportAggregator.read_api_doc_cache(cache_dir) == {
            "missing": True,
            "name": "api_doc",
            "summary": {},
            "issues": [],
        }
        assert ReportAggregator.read_link_cache(cache_dir) == {
            "missing": True,
            "name": "links",
            "summary": {},
            "issues": [],
        }

    def test_read_quality_cache_invalid_json_returns_missing(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "quality.json").write_text("not json")
        assert ReportAggregator.read_quality_cache(cache_dir) == {
            "missing": True,
            "name": "quality",
            "summary": {},
            "issues": [],
        }

    def test_read_api_doc_cache_invalid_json_returns_missing(self, tmp_path: Path) -> None:
        """An unparsable api doc cache degrades to a missing record."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "api_doc_validator.json").write_text("{not json")
        assert ReportAggregator.read_api_doc_cache(cache_dir) == {
            "missing": True,
            "name": "api_doc",
            "summary": {},
            "issues": [],
        }

    def test_read_link_cache_invalid_json_returns_missing(self, tmp_path: Path) -> None:
        """An unparsable link cache degrades to a missing record."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "link_checker.json").write_text("][")
        assert ReportAggregator.read_link_cache(cache_dir) == {
            "missing": True,
            "name": "links",
            "summary": {},
            "issues": [],
        }

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
        assert data["repository"] == "/repo"
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
        lines = report.splitlines()
        assert "Missing sections: quality, api_doc" in lines
        assert lines[lines.index("Missing sections: quality, api_doc") + 1] == ""
        assert "## Links" in lines
        assert "## Staleness + Drift" not in lines
        assert "## API Documentation" not in lines

    def test_aggregate_repository_defaults_to_cwd(self, tmp_path: Path) -> None:
        """A quality cache without a repository key falls back to the cwd."""
        cache_dir = tmp_path / "cache"
        self._write(cache_dir, "quality.json", {"summary": {}})
        data = json.loads(ReportAggregator.aggregate(cache_dir, as_json=True))
        assert data["repository"] == os.path.abspath(".")

    def test_aggregate_scan_date_uses_utc_and_iso_format(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The scan timestamp comes from a UTC clock and keeps the ISO shape."""
        captured: dict[str, Any] = {}

        class _FakeDatetime:
            @staticmethod
            def now(tz: Any = None) -> datetime:
                captured["tz"] = tz
                return datetime(2026, 1, 1, tzinfo=UTC)

        monkeypatch.setattr(report_aggregator_module, "datetime", _FakeDatetime)
        data = json.loads(ReportAggregator.aggregate(tmp_path / "cache", as_json=True))
        assert captured["tz"] is UTC
        assert data["scan_date"] == "2026-01-01T00:00:00Z"

    def test_aggregate_as_json_dumps_with_stable_options(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The JSON report is dumped with indent=2 and default=str."""
        captured: dict[str, Any] = {}

        def _spy_dumps(data: Any, **kwargs: Any) -> str:
            captured.update(kwargs)
            return json.dumps(data, **kwargs)

        fake_json = SimpleNamespace(
            dumps=_spy_dumps,
            loads=json.loads,
            JSONDecodeError=json.JSONDecodeError,
        )
        monkeypatch.setattr(report_aggregator_module, "json", fake_json)
        ReportAggregator.aggregate(tmp_path / "cache", as_json=True)
        assert captured == {"indent": 2, "default": str}

    # --- _summarize ---

    def test_summarize_empty_records_default_to_zero(self) -> None:
        assert ReportAggregator._summarize({}, {}, {}) == {
            "aggregate_score": None,
            "aggregate_label": None,
            "total_docs": 0,
            "total_drift_issues": 0,
            "api_doc_issues": 0,
            "api_doc_suggestions": 0,
            "total_links": 0,
            "broken_links": 0,
            "duplicate_anchors": 0,
            "missing_sections": [],
        }

    # --- _format_markdown ---

    def _report_data(
        self,
        summary: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
        api_doc: dict[str, Any] | None = None,
        links: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "repository": "repo",
            "scan_date": "2026-01-01T00:00:00Z",
            "sections": {
                "quality": quality if quality is not None else {"missing": True},
                "api_doc": api_doc if api_doc is not None else {"missing": True},
                "links": links if links is not None else {"missing": True},
            },
            "summary": summary if summary is not None else {},
        }

    def test_format_markdown_score_without_label_uses_unknown(self) -> None:
        text = ReportAggregator._format_markdown(
            self._report_data(summary={"aggregate_score": 5.0})
        )
        assert "Aggregate quality score: 5.0/100 (unknown)" in text.splitlines()

    def test_format_markdown_empty_summary_renders_zero_counts(self) -> None:
        lines = ReportAggregator._format_markdown(self._report_data()).splitlines()
        assert "Documents reviewed:        0" in lines
        assert "Drift issues:              0" in lines
        assert "API doc issues:            0" in lines
        assert "API doc suggestions:       0" in lines
        assert "Links checked:             0" in lines
        assert "Broken links:              0" in lines
        assert "Duplicate anchors:         0" in lines

    def test_format_markdown_all_missing_ends_with_blank_line(self) -> None:
        text = ReportAggregator._format_markdown(
            self._report_data(summary={"missing_sections": ["quality", "api_doc", "links"]})
        )
        lines = text.splitlines()
        assert "Missing sections: quality, api_doc, links" in lines
        assert text.endswith("\n")

    def test_format_markdown_missing_sections_omit_blocks(self) -> None:
        lines = ReportAggregator._format_markdown(self._report_data()).splitlines()
        assert "## Staleness + Drift" not in lines
        assert "## API Documentation" not in lines
        assert "## Links" not in lines

    def test_format_markdown_staleness_section_renders_defaults(self) -> None:
        text = ReportAggregator._format_markdown(
            self._report_data(quality={"summary": {}, "documents": []})
        )
        lines = text.splitlines()
        assert "## Staleness + Drift" in lines
        assert "Aggregate score: n/a/100 (unknown)" in lines
        assert "Documents: 0" in lines
        assert "Drifted docs: 0" in lines
        assert "Total drift issues: 0" in lines

    def test_format_markdown_documents_truncates_list_at_five(self) -> None:
        docs = [{"file": f"d{i}.md", "total_score": i, "label": "fresh"} for i in range(7)]
        text = ReportAggregator._format_markdown(
            self._report_data(quality={"summary": {}, "documents": docs})
        )
        doc_lines = [line for line in text.splitlines() if line.startswith("- ")]
        assert doc_lines == [f"- d{i}.md: {i} (fresh)" for i in range(5)]

    def test_format_markdown_api_doc_section_renders_defaults(self) -> None:
        text = ReportAggregator._format_markdown(self._report_data(api_doc={}))
        lines = text.splitlines()
        assert "## API Documentation" in lines
        assert "Source signatures: 0" in lines
        assert "Documented items: 0" in lines
        assert "Issues: 0" in lines
        assert "Undocumented items: 0" in lines

    def test_format_markdown_links_section_renders_values(self) -> None:
        text = ReportAggregator._format_markdown(
            self._report_data(links={"summary": {"skipped": 7}})
        )
        lines = text.splitlines()
        assert "## Links" in lines
        assert "Total links: 0" in lines
        assert "Valid: 0" in lines
        assert "Broken: 0" in lines
        assert "Skipped: 7" in lines
        assert "Duplicate anchors: 0" in lines

    def test_format_markdown_links_section_renders_defaults(self) -> None:
        text = ReportAggregator._format_markdown(self._report_data(links={}))
        lines = text.splitlines()
        assert "## Links" in lines
        assert "Total links: 0" in lines
        assert "Valid: 0" in lines
        assert "Broken: 0" in lines
        assert "Skipped: 0" in lines
        assert "Duplicate anchors: 0" in lines

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
