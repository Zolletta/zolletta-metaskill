"""QualityReportWriter formats the unified staleness + drift report."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any


class QualityReportWriter:
    """Formats documentation staleness scores and drift issues into reports."""

    SCORE_LABELS: dict[tuple[float, float], str] = {
        (90, 100): "fresh",
        (75, 90): "acceptable",
        (50, 75): "aging",
        (25, 50): "stale",
        (-1, 25): "abandoned",
    }

    SEVERITY_ORDER: dict[str, int] = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4,
    }

    @staticmethod
    def get_label(score: float) -> str:
        """Return a human-readable label for a staleness score."""
        for (low, high), label in QualityReportWriter.SCORE_LABELS.items():
            if low < score <= high:
                return label
        return "unknown"

    @staticmethod
    def generate_report(
        repo_path: str,
        scores: list[dict[str, Any]],
        issues: list[dict[str, Any]],
        as_json: bool = False,
    ) -> str:
        """Generate a unified staleness + drift report."""
        report_data = QualityReportWriter._build_report_data(repo_path, scores, issues)
        if as_json:
            return json.dumps(report_data, indent=2, default=str)
        return QualityReportWriter._format_markdown(report_data)

    @staticmethod
    def _build_report_data(
        repo_path: str, scores: list[dict[str, Any]], issues: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build the JSON-serializable report data structure."""
        drifted_files = {i["file"] for i in issues if i.get("severity") != "info"}
        aggregate = sum(s["total_score"] for s in scores) / len(scores) if scores else 0.0

        report_data: dict[str, Any] = {
            "repository": os.path.abspath(repo_path),
            "scan_date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": {
                "total_docs": len(scores),
                "aggregate_score": round(aggregate, 1),
                "aggregate_label": QualityReportWriter.get_label(aggregate),
                "drifted_docs": len(drifted_files),
                "total_issues": len(issues),
                "by_severity": {},
                "by_category": {},
                "by_fix_type": {},
            },
            "documents": scores,
            "issues": issues,
        }

        for issue in issues:
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

        return report_data

    @staticmethod
    def _format_markdown(report_data: dict[str, Any]) -> str:
        """Render the report data as Markdown."""
        summary = report_data["summary"]
        scores = report_data["documents"]
        issues = report_data["issues"]

        lines: list[str] = [
            "Documentation Staleness + Drift Report",
            "=" * 60,
            f"Repository: {report_data['repository']}",
            f"Scan date:  {report_data['scan_date']}",
            (
                f"Aggregate Score: {summary['aggregate_score']:.1f}/100 "
                f"({summary['aggregate_label']})"
            ),
            f"Documents:       {summary['total_docs']}",
            f"Drifted docs:    {summary['drifted_docs']}",
            f"Total issues:    {summary['total_issues']}",
            "",
        ]

        if scores:
            sorted_scores = sorted(scores, key=lambda s: s["total_score"])
            lines.append(f"{'File':<45} {'Score':>6} {'Label':>12}")
            lines.append("-" * 65)
            for s in sorted_scores:
                lines.append(f"{s['file']:<45} {s['total_score']:>5.1f} {s['label']:>12}")
            lines.append("")

            lines.append("DIMENSION BREAKDOWN (worst scoring files):")
            lines.append("-" * 60)
            for s in sorted_scores[:5]:
                lines.append(f"\n  {s['file']} (score: {s['total_score']:.1f})")
                for dim_name, dim_data in s["dimensions"].items():
                    bar = QualityReportWriter._score_bar(dim_data["score"])
                    lines.append(
                        f"    {dim_name:<25} {dim_data['score']:>5.1f} "
                        f"(x{dim_data['weight']:.2f} = {dim_data['weighted']:>5.1f}) {bar}"
                    )
            lines.append("")

        if issues:
            # pragma: no mutate start — the unknown-severity sentinel only has to outrank every
            # known rank, so 99 vs 100 is unobservable; the ordering itself is asserted by tests
            issues.sort(
                key=lambda x: QualityReportWriter.SEVERITY_ORDER.get(x.get("severity", "info"), 99)
            )
            # pragma: no mutate end
            severity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for issue in issues:
                severity_groups[issue.get("severity", "info")].append(issue)

            lines.append("DRIFT ISSUES:")
            lines.append("-" * 60)
            for severity in ["critical", "high", "medium", "low", "info"]:
                group = severity_groups.get(severity, [])  # pragma: no mutate — None is falsy too
                if not group:
                    continue
                lines.append(f"{severity.upper()} SEVERITY ({len(group)} issues):")
                lines.append("-" * 40)
                for issue in group:
                    # pragma: no mutate start — a renamed "manual" key or a missing fix_type still
                    # resolves through the "[MANUAL]" fallback, so those mutants are unobservable
                    fix_tag = {"auto": "[AUTO]", "semi": "[SEMI]", "manual": "[MANUAL]"}.get(
                        issue.get("fix_type", "manual"), "[MANUAL]"
                    )
                    # pragma: no mutate end
                    lines.append(f"  {issue['file']}")
                    lines.append(f"    {fix_tag} {issue['description']}")
                    lines.append(f"    Category: {issue.get('category', 'unknown')}")
                    lines.append("")
                lines.append("")

            lines.append("FIX TYPE SUMMARY:")
            lines.append("-" * 40)
            for fix_type, count in sorted(summary["by_fix_type"].items()):
                label = {
                    "auto": "Auto-fixable",
                    "semi": "Semi-automated",
                    "manual": "Manual review",
                }.get(fix_type, fix_type)
                lines.append(f"  {label}: {count}")
            lines.append("")
        else:
            lines.append("No drift issues detected. All docs appear current.")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _score_bar(score: float, width: int = 20) -> str:
        """Generate a simple ASCII bar for a score."""
        filled = int(score / 100 * width)
        return "[" + "#" * filled + "." * (width - filled) + "]"
