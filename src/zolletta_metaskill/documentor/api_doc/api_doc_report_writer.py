"""APIDocReportWriter formats API documentation validation reports in text and JSON.

Separates report presentation from AST signature and doc parsing.
"""

from __future__ import annotations

import json
from typing import Any


class APIDocReportWriter:
    """Formats API documentation validation issues and suggestions into reports."""

    @staticmethod
    def generate_report(
        issues: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        source_count: int,
        doc_count: int,
        as_json: bool = False,
        suggest_coverage: bool = False,
    ) -> str:
        """Generate a validation report.

        Args:
            issues: Real drift issues (phantom docs, param mismatches, deprecations).
            suggestions: Undocumented items with priority classification.
            source_count: Total number of source items discovered.
            doc_count: Total number of documented items found.
            as_json: If True, return the report as a JSON string; otherwise return Markdown.
            suggest_coverage: If True, include prioritized documentation suggestions
                in the report. If False, only show a summary count of undocumented items.

        """
        report_data = APIDocReportWriter.generate_report_data(
            issues,
            suggestions,
            source_count,
            doc_count,
            suggest_coverage=suggest_coverage,
        )

        if as_json:
            return json.dumps(report_data, indent=2, default=str)

        sug_by_priority = APIDocReportWriter._count_by_priority(suggestions)
        lines = APIDocReportWriter._report_header(
            source_count, doc_count, issues, suggestions, sug_by_priority
        )
        APIDocReportWriter._report_issue_sections(lines, issues)
        if suggest_coverage and suggestions:
            APIDocReportWriter._report_suggestions(lines, suggestions)
        APIDocReportWriter._report_type_summary(lines, report_data["summary"]["by_type"])
        APIDocReportWriter._report_footer(lines, suggestions, sug_by_priority)

        return "\n".join(lines)

    @staticmethod
    def generate_report_data(
        issues: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        source_count: int,
        doc_count: int,
        suggest_coverage: bool = False,
    ) -> dict[str, Any]:
        """Return the JSON-serializable report data structure."""
        sug_by_priority = APIDocReportWriter._count_by_priority(suggestions)
        report_data = APIDocReportWriter._build_report_data(
            issues, suggestions, source_count, doc_count, sug_by_priority
        )
        if suggest_coverage:
            report_data["suggestions"] = suggestions
        return report_data

    @staticmethod
    def _count_by_priority(suggestions: list[dict[str, Any]]) -> dict[str, int]:
        """Count suggestions grouped by their priority classification."""
        by_priority: dict[str, int] = {}
        for s in suggestions:
            p = s.get("priority", "low")
            by_priority[p] = by_priority.get(p, 0) + 1
        return by_priority

    @staticmethod
    def _build_report_data(
        issues: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        source_count: int,
        doc_count: int,
        sug_by_priority: dict[str, int],
    ) -> dict[str, Any]:
        """Build the report data structure used by both output formats."""
        report_data: dict[str, Any] = {
            "summary": {
                "source_signatures": source_count,
                "documented_items": doc_count,
                "total_issues": len(issues),
                "undocumented_count": len(suggestions),
                "undocumented_by_priority": sug_by_priority,
                "by_type": {},
                "by_severity": {},
            },
            "issues": issues,
        }

        for issue in issues:
            itype = issue.get("type", "unknown")
            sev = issue.get("severity", "unknown")
            report_data["summary"]["by_type"][itype] = (
                report_data["summary"]["by_type"].get(itype, 0) + 1
            )
            report_data["summary"]["by_severity"][sev] = (
                report_data["summary"]["by_severity"].get(sev, 0) + 1
            )
        return report_data

    @staticmethod
    def _report_header(
        source_count: int,
        doc_count: int,
        issues: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        sug_by_priority: dict[str, int],
    ) -> list[str]:
        """Build the report header lines."""
        lines = [
            "API Documentation Validation Report",
            "=" * 60,
            f"Source signatures found: {source_count}",
            f"Documented items found:  {doc_count}",
            f"Issues found:            {len(issues)}",
            f"Undocumented items:      {len(suggestions)}",
        ]
        if sug_by_priority:
            parts = [f"{p}={c}" for p, c in sorted(sug_by_priority.items())]
            lines.append(f"  by priority:           {', '.join(parts)}")
        lines.append("")

        if not issues:
            lines.append("No drift issues found. API documentation matches source code.")
            lines.append("")
        return lines

    @staticmethod
    def _report_issue_sections(lines: list[str], issues: list[dict[str, Any]]) -> None:
        """Append per-severity issue sections to the report lines."""
        severity_order = ["high", "medium", "low"]
        for severity in severity_order:
            sev_issues = [i for i in issues if i.get("severity") == severity]
            if not sev_issues:
                continue
            lines.append(f"{severity.upper()} ({len(sev_issues)} issues):")
            lines.append("-" * 40)
            for issue in sev_issues:
                lines.append(f"  [{issue.get('type', 'unknown')}] {issue['description']}")
                if "source_file" in issue:
                    lines.append(
                        f"    Source: {issue['source_file']}:{issue.get('source_line', '?')}"
                    )
                if "doc_file" in issue:
                    lines.append(f"    Doc:    {issue['doc_file']}:{issue.get('doc_line', '?')}")
                lines.append("")
            lines.append("")

    @staticmethod
    def _report_suggestions(lines: list[str], suggestions: list[dict[str, Any]]) -> None:
        """Append the prioritized documentation-suggestions section."""
        lines.append("DOCUMENTATION SUGGESTIONS:")
        lines.append("-" * 40)
        priority_order = ["high", "medium", "low", "skip"]
        for priority in priority_order:
            pri_sugs = [s for s in suggestions if s.get("priority") == priority]
            if not pri_sugs:
                continue
            lines.append(f"  [{priority.upper()}] ({len(pri_sugs)} items):")
            for s in pri_sugs[:20]:
                lines.append(f"    {s['name']} ({s['kind']}) — {s['reason']}")
                lines.append(
                    f"      Source: {s.get('source_file', '?')}:{s.get('source_line', '?')}"
                )
            if len(pri_sugs) > 20:
                lines.append(f"    ... and {len(pri_sugs) - 20} more")
            lines.append("")
        lines.append("")

    @staticmethod
    def _report_type_summary(lines: list[str], by_type: dict[str, int]) -> None:
        """Append the issues-by-type summary section."""
        if not by_type:
            return
        lines.append("ISSUES BY TYPE:")
        lines.append("-" * 40)
        type_labels = {
            "documented_not_in_source": "Documented but not in source",
            "missing_param_in_docs": "Missing parameters in docs",
            "extra_param_in_docs": "Extra parameters in docs",
            "deprecated_still_documented": "Deprecated items still documented",
        }
        for itype, count in sorted(by_type.items()):
            label = type_labels.get(itype, itype)
            lines.append(f"  {label}: {count}")
        lines.append("")

    @staticmethod
    def _report_footer(
        lines: list[str],
        suggestions: list[dict[str, Any]],
        sug_by_priority: dict[str, int],
    ) -> None:
        """Append the undocumented-items summary footer."""
        lines.append(f"Undocumented items: {len(suggestions)} (not counted as issues)")
        if sug_by_priority:
            parts = [f"{p}={c}" for p, c in sorted(sug_by_priority.items())]
            lines.append(f"  by priority: {', '.join(parts)}")
        lines.append("  Use --suggest-coverage to see prioritized documentation suggestions.")
