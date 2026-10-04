"""ReportAggregator combines individual documentor cache files into one report."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


class ReportAggregator:
    """Reads documentor cache files and emits a unified Markdown or JSON report."""

    SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    @staticmethod
    def read_quality_cache(cache_dir: Path) -> dict[str, Any]:
        """Read the unified drift + quality quality cache file."""
        path = cache_dir / "quality.json"
        if not path.exists():
            return ReportAggregator._missing_record("quality")
        try:
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return ReportAggregator._missing_record("quality")

    @staticmethod
    def read_api_doc_cache(cache_dir: Path) -> dict[str, Any]:
        """Read the API doc validation cache file."""
        path = cache_dir / "api_doc_validator.json"
        if not path.exists():
            return ReportAggregator._missing_record("api_doc")
        try:
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return ReportAggregator._missing_record("api_doc")

    @staticmethod
    def read_link_cache(cache_dir: Path) -> dict[str, Any]:
        """Read the link checker cache file."""
        path = cache_dir / "link_checker.json"
        if not path.exists():
            return ReportAggregator._missing_record("links")
        try:
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return ReportAggregator._missing_record("links")

    @staticmethod
    def _missing_record(name: str) -> dict[str, Any]:
        """Return a placeholder record for a missing cache file."""
        return {
            "missing": True,
            "name": name,
            "summary": {},
            "issues": [],
        }

    @staticmethod
    def aggregate(cache_dir: Path, as_json: bool = False) -> str:
        """Combine all available documentor caches into a single report."""
        quality = ReportAggregator.read_quality_cache(cache_dir)
        api_doc = ReportAggregator.read_api_doc_cache(cache_dir)
        links = ReportAggregator.read_link_cache(cache_dir)

        report_data = {
            "repository": quality.get("repository", os.path.abspath(".")),
            "scan_date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sections": {
                "quality": quality,
                "api_doc": api_doc,
                "links": links,
            },
            "summary": ReportAggregator._summarize(quality, api_doc, links),
        }

        if as_json:
            return json.dumps(report_data, indent=2, default=str)
        return ReportAggregator._format_markdown(report_data)

    @staticmethod
    def _summarize(
        quality: dict[str, Any], api_doc: dict[str, Any], links: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a high-level summary across all sections."""
        quality_summary = quality.get("summary", {})
        api_doc_summary = api_doc.get("summary", {})
        links_summary = links.get("summary", {})

        return {
            "aggregate_score": quality_summary.get("aggregate_score"),
            "aggregate_label": quality_summary.get("aggregate_label"),
            "total_docs": quality_summary.get("total_docs", 0),
            "total_drift_issues": quality_summary.get("total_issues", 0),
            "api_doc_issues": api_doc_summary.get("total_issues", 0),
            "api_doc_suggestions": api_doc_summary.get("undocumented_count", 0),
            "total_links": links_summary.get("total_links", 0),
            "broken_links": links_summary.get("broken", 0),
            "duplicate_anchors": links_summary.get("duplicate_anchors", 0),
            "missing_sections": [
                name
                for name, record in [("quality", quality), ("api_doc", api_doc), ("links", links)]
                if record.get("missing")
            ],
        }

    @staticmethod
    def _format_markdown(report_data: dict[str, Any]) -> str:
        """Render the aggregated report data as Markdown."""
        summary = report_data["summary"]
        sections = report_data["sections"]
        lines: list[str] = [
            "Documentor Review Report",
            "=" * 60,
            f"Repository: {report_data['repository']}",
            f"Scan date:  {report_data['scan_date']}",
            "",
            "OVERVIEW",
            "-" * 40,
        ]

        score = summary.get("aggregate_score")
        if score is not None:
            label = summary.get("aggregate_label", "unknown")
            lines.append(f"Aggregate quality score: {score:.1f}/100 ({label})")
        lines.append(f"Documents reviewed:        {summary.get('total_docs', 0)}")
        lines.append(f"Drift issues:              {summary.get('total_drift_issues', 0)}")
        lines.append(f"API doc issues:            {summary.get('api_doc_issues', 0)}")
        lines.append(f"API doc suggestions:       {summary.get('api_doc_suggestions', 0)}")
        lines.append(f"Links checked:             {summary.get('total_links', 0)}")
        lines.append(f"Broken links:              {summary.get('broken_links', 0)}")
        lines.append(f"Duplicate anchors:         {summary.get('duplicate_anchors', 0)}")
        lines.append("")

        missing = summary.get("missing_sections", [])
        if missing:
            lines.append(f"Missing sections: {', '.join(missing)}")
            lines.append("")

        # Staleness section
        quality = sections["quality"]
        if not quality.get("missing"):
            lines.append("## Staleness + Drift")
            lines.append("")
            quality_summary = quality.get("summary", {})
            lines.append(
                f"Aggregate score: {quality_summary.get('aggregate_score', 'n/a')}/100 "
                f"({quality_summary.get('aggregate_label', 'unknown')})"
            )
            lines.append(f"Documents: {quality_summary.get('total_docs', 0)}")
            lines.append(f"Drifted docs: {quality_summary.get('drifted_docs', 0)}")
            lines.append(f"Total drift issues: {quality_summary.get('total_issues', 0)}")
            lines.append("")

            for doc in quality.get("documents", [])[:5]:
                lines.append(f"- {doc.get('file')}: {doc.get('total_score')} ({doc.get('label')})")
            lines.append("")

        # API doc section
        api_doc = sections["api_doc"]
        if not api_doc.get("missing"):
            lines.append("## API Documentation")
            lines.append("")
            api_summary = api_doc.get("summary", {})
            lines.append(f"Source signatures: {api_summary.get('source_signatures', 0)}")
            lines.append(f"Documented items: {api_summary.get('documented_items', 0)}")
            lines.append(f"Issues: {api_summary.get('total_issues', 0)}")
            lines.append(f"Undocumented items: {api_summary.get('undocumented_count', 0)}")
            lines.append("")

        # Links section
        links = sections["links"]
        if not links.get("missing"):
            lines.append("## Links")
            lines.append("")
            link_summary = links.get("summary", {})
            lines.append(f"Total links: {link_summary.get('total_links', 0)}")
            lines.append(f"Valid: {link_summary.get('valid', 0)}")
            lines.append(f"Broken: {link_summary.get('broken', 0)}")
            lines.append(f"Skipped: {link_summary.get('skipped', 0)}")
            lines.append(f"Duplicate anchors: {link_summary.get('duplicate_anchors', 0)}")
            lines.append("")

        return "\n".join(lines)
