"""LinkReportWriter formats link-check reports in Markdown and JSON."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from zolletta_metaskill.documentor.structs.link_info import LinkInfo


class LinkReportWriter:
    """Formats LinkChecker results into text or JSON reports."""

    @staticmethod
    def generate_report(
        all_links: list[LinkInfo],
        duplicate_anchors: dict[str, list[tuple[str, int]]],
        broken_only: bool = False,
        as_json: bool = False,
    ) -> str:
        """Generate a link check report."""
        report_data = LinkReportWriter.generate_report_data(
            all_links, duplicate_anchors, broken_only=broken_only
        )

        if as_json:
            # pragma: no mutate start — report_data holds only str/int/None, so `default` is
            # unreachable
            return json.dumps(report_data, indent=2, default=str)
            # pragma: no mutate end

        return LinkReportWriter._format_markdown(report_data)

    @staticmethod
    def generate_report_data(
        all_links: list[LinkInfo],
        duplicate_anchors: dict[str, list[tuple[str, int]]],
        broken_only: bool = False,
    ) -> dict[str, Any]:
        """Return the JSON-serializable link check report data."""
        broken = [lnk for lnk in all_links if lnk.is_valid is False]
        valid = [lnk for lnk in all_links if lnk.is_valid is True]
        skipped = [lnk for lnk in all_links if lnk.is_valid is None]

        report_data: dict[str, Any] = {
            "summary": {
                "total_links": len(all_links),
                "valid": len(valid),
                "broken": len(broken),
                "skipped": len(skipped),
                "duplicate_anchors": sum(len(v) for v in duplicate_anchors.values()),
            },
            "broken_links": [lnk.to_dict() for lnk in broken],
            "duplicate_anchors": {
                file: [{"anchor": anchor, "line": line} for anchor, line in dups]
                for file, dups in duplicate_anchors.items()
            },
        }

        if not broken_only:
            report_data["all_links"] = [lnk.to_dict() for lnk in all_links]

        return report_data

    @staticmethod
    def _format_markdown(report_data: dict[str, Any]) -> str:
        """Render the report data as Markdown."""
        summary = report_data["summary"]
        broken = report_data["broken_links"]
        duplicate_anchors = report_data["duplicate_anchors"]

        lines: list[str] = [
            "Link Check Report",
            "=" * 60,
            f"Total links:      {summary['total_links']}",
            f"Valid:            {summary['valid']}",
            f"Broken:           {summary['broken']}",
            f"Skipped:          {summary['skipped']}",
            f"Duplicate anchors: {summary['duplicate_anchors']}",
            "",
        ]

        if broken:
            LinkReportWriter._report_broken(lines, broken)
        if duplicate_anchors:
            LinkReportWriter._report_dups(lines, duplicate_anchors)
        if not broken and not duplicate_anchors:
            lines.append("No issues found. All links are valid.")

        LinkReportWriter._report_type_breakdown(lines, report_data)
        return "\n".join(lines)

    @staticmethod
    def _report_broken(lines: list[str], broken: list[dict[str, Any]]) -> None:
        """Append broken links section grouped by file."""
        lines.append("BROKEN LINKS:")
        lines.append("-" * 60)
        # pragma: no mutate start — writes go through setdefault, so the default factory is
        # unreachable
        by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # pragma: no mutate end
        for link in broken:
            by_file.setdefault(link.get("source_file", ""), []).append(link)

        for source_file, file_links in sorted(by_file.items()):
            lines.append(f"\n  {source_file}:")
            for link in sorted(file_links, key=lambda lnk: lnk.get("line", 0)):
                lines.append(
                    f"    Line {link.get('line')}: [{link.get('text')}]({link.get('target')})"
                )
                lines.append(f"      Error: {link.get('error')}")
        lines.append("")

    @staticmethod
    def _report_dups(lines: list[str], duplicate_anchors: dict[str, list[dict[str, int]]]) -> None:
        """Append duplicate anchors section."""
        lines.append("DUPLICATE ANCHORS:")
        lines.append("-" * 60)
        for file, dups in sorted(duplicate_anchors.items()):
            lines.append(f"\n  {file}:")
            for dup in dups:
                lines.append(f"    Line {dup['line']}: duplicate anchor '#{dup['anchor']}'")
        lines.append("")

    @staticmethod
    def _report_type_breakdown(lines: list[str], report_data: dict[str, Any]) -> None:
        """Append link type breakdown section."""
        all_links = report_data.get("all_links", report_data["broken_links"])
        type_counts: dict[str, int] = {}
        broken_type_counts: dict[str, int] = {}
        for link in all_links:
            ltype = link.get("type", "unknown")
            type_counts[ltype] = type_counts.get(ltype, 0) + 1
        for link in report_data["broken_links"]:
            ltype = link.get("type", "unknown")
            broken_type_counts[ltype] = broken_type_counts.get(ltype, 0) + 1

        lines.append("LINK TYPE BREAKDOWN:")
        lines.append("-" * 40)
        for ltype in sorted(type_counts.keys()):
            broken_count = broken_type_counts.get(ltype, 0)
            total = type_counts[ltype]
            lines.append(f"  {ltype:<25} {total:>4} total, {broken_count:>4} broken")
