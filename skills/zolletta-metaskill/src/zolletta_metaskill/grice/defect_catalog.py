"""DefectCatalog — number every structural defect, broken links once per target."""

from __future__ import annotations

import posixpath
from collections.abc import Callable
from dataclasses import replace

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.quality_metrics import QualityMetrics
from zolletta_metaskill.grice.structs.defect_location import DefectLocation
from zolletta_metaskill.grice.structs.structural_defect import StructuralDefect


class DefectCatalog:
    """Turn the line-level findings into the report's ``G1``, ``G2``… defects.

    Every heading skip is its own defect. Broken links are grouped by the
    target they resolve to — relative to the linking file, anchor included —
    so the same missing page or anchor reached from many pages is listed
    once, with every occurrence kept. Defects are ordered by severity, then by
    their first occurrence, and only then numbered.
    """

    ID_PREFIX = "G"
    BROKEN_LINK = "broken_link"
    HEADING_SKIP = "heading_skip"
    SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")

    @staticmethod
    def build(
        link_findings: list[Finding],
        heading_findings: list[Finding],
        group_of: Callable[[str], str],
    ) -> tuple[StructuralDefect, ...]:
        """Return every defect, numbered.

        Args:
            link_findings: Broken internal link/anchor findings.
            heading_findings: Heading-level skip findings.
            group_of: Maps a document path to its presentation group.

        Returns:
            The defects in report order with progressive ids.

        """
        drafts = DefectCatalog._links(link_findings, group_of) + [
            StructuralDefect(
                id="",
                kind=DefectCatalog.HEADING_SKIP,
                severity=finding.severity,
                description=finding.description,
                target=None,
                locations=(DefectLocation(finding.file, finding.line, group_of(finding.file)),),
            )
            for finding in heading_findings
        ]
        drafts.sort(key=DefectCatalog._sort_key)
        return tuple(
            replace(defect, id=f"{DefectCatalog.ID_PREFIX}{number}")
            for number, defect in enumerate(drafts, start=1)
        )

    @staticmethod
    def resolve_target(source: str, target: str) -> str:
        """Resolve a link *target* written in *source* to a repository path.

        Args:
            source: Repository-relative path of the linking document.
            target: The link target as written, anchor included.

        Returns:
            The normalised repository-relative target, ``#anchor`` kept; an
            anchor-only target resolves against *source* itself.

        """
        path, _, anchor = target.partition("#")
        if not path:
            resolved = source
        elif path.startswith("/"):
            resolved = posixpath.normpath(path.lstrip("/"))
        else:
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        return f"{resolved}#{anchor}" if anchor else resolved

    @staticmethod
    def _links(findings: list[Finding], group_of: Callable[[str], str]) -> list[StructuralDefect]:
        """Group broken-link findings by resolved target.

        Args:
            findings: Broken internal link/anchor findings.
            group_of: Maps a document path to its presentation group.

        Returns:
            One draft defect per target, ids not yet assigned.

        """
        by_target: dict[str, list[Finding]] = {}
        for finding in sorted(findings, key=lambda item: (item.file, item.line)):
            raw = QualityMetrics.link_target(finding.description)
            key = (
                DefectCatalog.resolve_target(finding.file, raw)
                if raw is not None
                else f"{finding.file}:{finding.line}"
            )
            by_target.setdefault(key, []).append(finding)
        return [
            StructuralDefect(
                id="",
                kind=DefectCatalog.BROKEN_LINK,
                severity=occurrences[0].severity,
                description=occurrences[0].description,
                target=target,
                locations=tuple(
                    DefectLocation(item.file, item.line, group_of(item.file))
                    for item in occurrences
                ),
            )
            for target, occurrences in by_target.items()
        ]

    @staticmethod
    def _sort_key(defect: StructuralDefect) -> tuple[int, str, int]:
        """Return the report-order key of *defect*.

        Args:
            defect: A draft defect.

        Returns:
            Severity rank, then the first occurrence's file and line.

        """
        order = DefectCatalog.SEVERITY_ORDER
        rank = order.index(defect.severity) if defect.severity in order else len(order)
        first = defect.locations[0]
        return rank, first.file, first.line
