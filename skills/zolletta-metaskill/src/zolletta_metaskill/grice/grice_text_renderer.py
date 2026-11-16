"""GriceTextRenderer — lay out a GriceReport as the scanner's markdown output."""

from __future__ import annotations

from zolletta_metaskill.grice.defect_catalog import DefectCatalog
from zolletta_metaskill.grice.diagnosis_engine import DiagnosisEngine
from zolletta_metaskill.grice.structs.diagnosis import Diagnosis
from zolletta_metaskill.grice.structs.grice_report import GriceReport
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores


class GriceTextRenderer:
    """Render the report sections in English, in the order the subcommand uses.

    The text is a reading aid for whoever runs the scanner by hand; the
    subcommand builds ``reports/grice.md`` from the JSON payload, in the
    invocation language. Both carry the same numbers.
    """

    NONE = "*None.*"
    HEADER = "| Document | Quantity | Quality | Relation | Manner | Index |"
    RULE = "|---|---|---|---|---|---|---|"

    @staticmethod
    def render(report: GriceReport) -> str:
        """Return the whole report as markdown.

        Args:
            report: The scanned corpus.

        Returns:
            The markdown text, ending with a newline.

        """
        lines = [
            "# Grice Documentation Analysis",
            "",
            f"- **Corpus:** {report.corpus_size} document(s)",
            f"- **ADR files excluded:** {len(report.excluded_adrs)}",
            f"- **Corpus median (`grice_index`):** {GriceTextRenderer.cell(report.corpus_median)}",
        ]
        if report.disabled_metrics:
            lines.append(f"- **Disabled metrics:** {', '.join(report.disabled_metrics)}")
        lines += GriceTextRenderer._summary(report)
        lines += GriceTextRenderer._defects(report)
        lines += GriceTextRenderer._outliers(report)
        lines += GriceTextRenderer._benchmarks(report)
        lines += GriceTextRenderer._documents(report)
        lines += ["", "## Notes", ""] + [f"- {note}" for note in report.notes]
        return "\n".join(lines) + "\n"

    @staticmethod
    def cell(value: float | None) -> str:
        """Format an index for a table cell.

        Args:
            value: The index, or ``None``.

        Returns:
            The value to one decimal, or an em dash when nothing was measured.

        """
        return "—" if value is None else f"{value:.1f}"

    @staticmethod
    def _summary(report: GriceReport) -> list[str]:
        """Return the Executive Summary section.

        Args:
            report: The scanned corpus.

        Returns:
            The section's lines, one table row per group plus the corpus total.

        """
        lines = [
            "",
            "## Executive Summary",
            "",
            "| Group | Docs | Median index | Outliers | Defects |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| `{group.name}` | {group.documents} | {GriceTextRenderer.cell(group.median_index)} "
            f"| {group.outliers} | {group.defects} |"
            for group in report.groups
        ]
        lines.append(
            f"| **Corpus** | {report.corpus_size} | {GriceTextRenderer.cell(report.corpus_median)} "
            f"| {len(report.outliers)} | {len(report.defects)} |"
        )
        return lines

    @staticmethod
    def _defects(report: GriceReport) -> list[str]:
        """Return the Structural Defects section.

        Args:
            report: The scanned corpus.

        Returns:
            The heading-skip table and the deduplicated broken-link table.

        """
        skips = [d for d in report.defects if d.kind == DefectCatalog.HEADING_SKIP]
        links = [d for d in report.defects if d.kind == DefectCatalog.BROKEN_LINK]
        lines = ["", "## 1. Structural Defects", "", "### Heading level skips", ""]
        if skips:
            lines += ["| ID | File | Line | Group | Problem |", "|---|---|---|---|---|"]
            lines += [
                f"| `{d.id}` | `{d.locations[0].file}` | {d.locations[0].line} "
                f"| `{d.locations[0].group}` | {d.description} |"
                for d in skips
            ]
        else:
            lines.append(GriceTextRenderer.NONE)
        lines += ["", "### Broken internal links and anchors", ""]
        if links:
            lines += ["| ID | Target | Count | Occurrences |", "|---|---|---|---|"]
            lines += [
                f"| `{d.id}` | `{d.target}` | {len(d.locations)} | "
                + ", ".join(f"`{loc.file}:{loc.line}`" for loc in d.locations)
                + " |"
                for d in links
            ]
        else:
            lines.append(GriceTextRenderer.NONE)
        return lines

    @staticmethod
    def _outliers(report: GriceReport) -> list[str]:
        """Return the outlier triage section, one table per group.

        Args:
            report: The scanned corpus.

        Returns:
            The section's lines; groups without outliers are left out.

        """
        threshold = f"{report.settings.outlier_threshold:g}"
        lines = ["", f"## 2. Outliers (`grice_index < {threshold}`)", ""]
        groups = [group for group in report.triage if group.outliers]
        if not groups:
            return [*lines, GriceTextRenderer.NONE]
        for group in groups:
            lines += [
                f"### `{group.name}`",
                "",
                f"{GriceTextRenderer.HEADER} Diagnosis & recommended action |",
                GriceTextRenderer.RULE,
            ]
            lines += [
                f"{GriceTextRenderer._scores_row(entry.scores)} "
                f"**{entry.diagnosis.summary}:** {entry.diagnosis.action} |"
                for entry in group.outliers
            ]
            lines.append("")
        return lines[:-1]

    @staticmethod
    def _benchmarks(report: GriceReport) -> list[str]:
        """Return the positive benchmarks section, one table per group.

        Args:
            report: The scanned corpus.

        Returns:
            The section's lines; groups without benchmarks are left out.

        """
        lines = ["", "## 3. Positive Benchmarks", ""]
        groups = [group for group in report.triage if group.benchmarks]
        if not groups:
            return [*lines, GriceTextRenderer.NONE]
        for group in groups:
            lines += [
                f"### `{group.name}`",
                "",
                f"{GriceTextRenderer.HEADER} Strength |",
                GriceTextRenderer.RULE,
            ]
            lines += [
                f"{GriceTextRenderer._scores_row(entry.scores)} "
                + "; ".join(
                    GriceTextRenderer._strength(entry.scores, strength)
                    for strength in entry.strengths
                )
                + " |"
                for entry in group.benchmarks
            ]
            lines.append("")
        return lines[:-1]

    @staticmethod
    def _scores_row(row: MaximScores) -> str:
        """Return the document, the four maxims and the index of a triage row.

        Args:
            row: The document's scores.

        Returns:
            The row's leading cells, ending with a ``|``.

        """
        cell = GriceTextRenderer.cell
        return (
            f"| `{row.path}` | {cell(row.quantity)} | {cell(row.quality)} "
            f"| {cell(row.relation)} | {cell(row.manner)} | **{cell(row.grice_index)}** |"
        )

    @staticmethod
    def _strength(row: MaximScores, strength: Diagnosis) -> str:
        """Return one won benchmark slot as text.

        Args:
            row: The benchmark's scores.
            strength: The slot's reading.

        Returns:
            ``**Balanced:** <summary>`` or ``**Top <Maxim> (<value>):** <summary>``.

        """
        if strength.code == "balanced" or strength.maxim is None:
            return f"**Balanced:** {strength.summary}"
        value = GriceTextRenderer.cell(DiagnosisEngine.measured(row).get(strength.maxim))
        return f"**Top {strength.maxim.capitalize()} ({value}):** {strength.summary}"

    @staticmethod
    def _documents(report: GriceReport) -> list[str]:
        """Return the full per-document table.

        Args:
            report: The scanned corpus.

        Returns:
            The section's lines, one row per document.

        """
        cell = GriceTextRenderer.cell
        lines = [
            "",
            "## Corpus",
            "",
            "| Document | Group | Quantity | Quality | Relation | Manner | Grice |",
            "|---|---|---|---|---|---|---|",
        ]
        return lines + [
            f"| `{row.path}` | `{row.group}` | {cell(row.quantity)} | {cell(row.quality)} "
            f"| {cell(row.relation)} | {cell(row.manner)} | {cell(row.grice_index)} |"
            for row in report.documents
        ]
