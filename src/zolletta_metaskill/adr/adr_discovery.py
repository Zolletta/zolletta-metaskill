"""ADR file discovery and metadata extraction."""

from __future__ import annotations

import re
from pathlib import Path

from zolletta_metaskill.adr.structs.adr_record import ADRRecord


class ADRDiscovery:
    """Find ADR files and extract metadata from each."""

    _ADR_HEADING_RE = re.compile(r"^(#+)\s+ADR[-\s]?(\d+)\s*:?\s*(.*)", re.MULTILINE)
    _STATUS_HEADING_RE = re.compile(
        r"^##\s+Status[ \t]*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL
    )
    _DECISION_HEADING_RE = re.compile(
        r"^##\s+Decision[ \t]*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL
    )
    _DISTILLED_FILENAME = "adr-distilled.md"

    @staticmethod
    def find_files(
        docs_dir: Path,
        adrs_path: str | None,
    ) -> list[ADRRecord]:
        """Scan for ADR files and extract metadata from each.

        Args:
            docs_dir: Path to the project's documentation directory.
            adrs_path: Relative path within *docs_dir* where ADRs live
                (e.g. ``"adr"``), ``""`` if scattered in docs root, or
                ``None`` if no ADRs were detected.

        Returns:
            A list of :class:`ADRRecord` objects, one per ADR file found.
            Non-matching files are skipped.

        """
        if adrs_path is None:
            return []

        search_dir = docs_dir / adrs_path if adrs_path else docs_dir

        if not search_dir.is_dir():
            return []

        records: list[ADRRecord] = []
        for f in sorted(search_dir.rglob("*.md")):
            if f.name == ADRDiscovery._DISTILLED_FILENAME:
                continue
            record = ADRDiscovery._extract_metadata(f)
            if record is not None:
                records.append(record)
        return records

    @staticmethod
    def _extract_metadata(file_path: Path) -> ADRRecord | None:
        """Extract ADR metadata from a single file.

        Returns ``None`` if the file does not contain an ADR heading.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        heading_match = ADRDiscovery._ADR_HEADING_RE.search(content)
        if heading_match is None:
            return None

        number = heading_match.group(2)
        title = heading_match.group(3).strip()

        status = ADRDiscovery._extract_section(content, ADRDiscovery._STATUS_HEADING_RE)
        decision_text = ADRDiscovery._extract_section(content, ADRDiscovery._DECISION_HEADING_RE)

        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            mtime = 0.0

        return ADRRecord(
            number=number,
            title=title,
            status=status,
            decision_text=decision_text,
            file_path=file_path,
            mtime=mtime,
        )

    @staticmethod
    def _extract_section(content: str, pattern: re.Pattern[str]) -> str:
        """Extract the first non-empty line from a markdown section.

        Args:
            content: The full file content.
            pattern: A compiled regex with one capture group for the
                section body (between the heading and the next ``##``).

        Returns:
            The first non-empty line of the section, stripped, or an
            empty string if the section is not found.

        """
        match = pattern.search(content)
        if match is None:
            return ""
        body = match.group(1)
        for line in body.splitlines():
            line = line.strip()
            if line:
                return line
        return ""
