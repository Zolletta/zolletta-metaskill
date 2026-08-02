"""Tests for ADRDiscovery._extract_section()."""

from __future__ import annotations

import re

from zolletta_metaskill.adr.adr_discovery import ADRDiscovery


class TestExtractSection:
    """Tests for ADRDiscovery._extract_section()."""

    def test_extracts_first_line(self) -> None:
        content = "## Status\n\nAccepted\n\nMore text.\n\n## Decision\n\nDo X.\n"
        pattern = re.compile(
            r"^##\s+Status[ \t]*\n(.*?)(?=\n##\s|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        assert ADRDiscovery._extract_section(content, pattern) == "Accepted"

    def test_section_not_found(self) -> None:
        content = "## Other\n\nText.\n"
        pattern = re.compile(
            r"^##\s+Status[ \t]*\n(.*?)(?=\n##\s|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        assert ADRDiscovery._extract_section(content, pattern) == ""

    def test_empty_section(self) -> None:
        content = "## Status\n\n## Decision\n\nDo X.\n"
        pattern = re.compile(
            r"^##\s+Status[ \t]*\n(.*?)(?=\n##\s|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        assert ADRDiscovery._extract_section(content, pattern) == ""
