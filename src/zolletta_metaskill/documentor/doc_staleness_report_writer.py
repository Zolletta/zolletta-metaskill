"""DocStalenessReportWriter formats staleness reports in Markdown and JSON.

Separates report presentation from staleness calculation.
"""

from __future__ import annotations

import json
from typing import Any


class DocStalenessReportWriter:
    """Formats documentation staleness scores into text or JSON reports."""

    SCORE_LABELS: dict[tuple[float, float], str] = {
        (90, 100): "fresh",
        (75, 90): "acceptable",
        (50, 75): "aging",
        (25, 50): "stale",
        (-1, 25): "abandoned",
    }

    @staticmethod
    def get_label(score: float) -> str:
        """Return a human-readable label for a staleness score."""
        for (low, high), label in DocStalenessReportWriter.SCORE_LABELS.items():
            if low < score <= high:
                return label
        return "unknown"

    @staticmethod
    def generate_report(scores: list[dict[str, Any]], as_json: bool = False) -> str:
        """Generate a staleness report from scored documents."""
        if not scores:
            if as_json:
                return json.dumps({"documents": [], "aggregate_score": 0}, indent=2)
            return "No documentation files found to score."

        aggregate = sum(s["total_score"] for s in scores) / len(scores)

        report_data = {
            "aggregate_score": round(aggregate, 1),
            "aggregate_label": DocStalenessReportWriter.get_label(aggregate),
            "total_documents": len(scores),
            "documents": scores,
        }

        if as_json:
            return json.dumps(report_data, indent=2, default=str)

        lines: list[str] = [
            "Documentation Staleness Report",
            "=" * 60,
            (
                f"Aggregate Score: {aggregate:.1f}/100 "
                f"({DocStalenessReportWriter.get_label(aggregate)})"
            ),
            f"Documents Scored: {len(scores)}",
            "",
        ]

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
                bar = DocStalenessReportWriter._score_bar(dim_data["score"])
                lines.append(
                    f"    {dim_name:<25} {dim_data['score']:>5.1f} "
                    f"(x{dim_data['weight']:.2f} = {dim_data['weighted']:>5.1f}) {bar}"
                )

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _score_bar(score: float, width: int = 20) -> str:
        """Generate a simple ASCII bar for a score."""
        filled = int(score / 100 * width)
        return "[" + "#" * filled + "." * (width - filled) + "]"
