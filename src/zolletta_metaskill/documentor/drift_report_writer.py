"""DriftReportWriter formats documentation drift reports in Markdown and JSON.

Separates report presentation from drift analysis.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any


class DriftReportWriter:
    """Formats documentation drift findings into text or JSON reports."""

    SEVERITY_ORDER: dict[str, int] = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4,
    }

    @staticmethod
    def generate_report(
        repo_path: str,
        all_issues: list[dict[str, Any]],
        doc_files: list[str],
        as_json: bool = False,
    ) -> str:
        """Generate a drift report."""
        all_issues.sort(
            key=lambda x: DriftReportWriter.SEVERITY_ORDER.get(x.get("severity", "info"), 99)
        )

        drifted_files = {i["file"] for i in all_issues if i["severity"] != "info"}

        report_data: dict[str, Any] = {
            "repository": os.path.abspath(repo_path),
            "scan_date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": {
                "total_docs": len(doc_files),
                "drifted_docs": len(drifted_files),
                "total_issues": len(all_issues),
                "by_severity": {},
                "by_category": {},
                "by_fix_type": {},
            },
            "issues": all_issues,
        }

        for issue in all_issues:
            sev = issue.get("severity", "info")
            cat = issue.get("category", "unknown")
            fix = issue.get("fix_type", "manual")
            report_data["summary"]["by_severity"][sev] = (
                report_data["summary"]["by_severity"].get(sev, 0) + 1
            )
            report_data["summary"]["by_category"][cat] = (
                report_data["summary"]["by_category"].get(cat, 0) + 1
            )
            report_data["summary"]["by_fix_type"][fix] = (
                report_data["summary"]["by_fix_type"].get(fix, 0) + 1
            )

        if as_json:
            return json.dumps(report_data, indent=2, default=str)

        lines: list[str] = [
            "Documentation Drift Report",
            "=" * 60,
            f"Repository: {os.path.abspath(repo_path)}",
            f"Scan date:  {report_data['scan_date']}",
            f"Docs found: {len(doc_files)}",
            f"Drifted:    {len(drifted_files)}",
            f"Issues:     {len(all_issues)}",
            "",
        ]

        severity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for issue in all_issues:
            severity_groups[issue["severity"]].append(issue)

        for severity in ["critical", "high", "medium", "low", "info"]:
            group = severity_groups.get(severity, [])
            if not group:
                continue
            lines.append(f"{severity.upper()} SEVERITY ({len(group)} issues):")
            lines.append("-" * 40)
            for issue in group:
                fix_tag = {"auto": "[AUTO]", "semi": "[SEMI]", "manual": "[MANUAL]"}.get(
                    issue.get("fix_type", "manual"), "[MANUAL]"
                )
                lines.append(f"  {issue['file']}")
                lines.append(f"    {fix_tag} {issue['description']}")
                lines.append(f"    Category: {issue.get('category', 'unknown')}")
                lines.append("")
            lines.append("")

        lines.append("FIX TYPE SUMMARY:")
        lines.append("-" * 40)
        for fix_type, count in sorted(report_data["summary"]["by_fix_type"].items()):
            label = {
                "auto": "Auto-fixable",
                "semi": "Semi-automated",
                "manual": "Manual review",
            }.get(fix_type, fix_type)
            lines.append(f"  {label}: {count}")
        lines.append("")

        if not all_issues:
            lines.append("No documentation drift detected. All docs appear current.")

        return "\n".join(lines)
