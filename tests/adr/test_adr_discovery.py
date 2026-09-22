"""Tests for ADRDiscovery — find files, extract metadata, and extract sections."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from zolletta_metaskill.adr.adr_discovery import ADRDiscovery

from .conftest import write_adr


class TestADRDiscovery:
    # --- Tests for ADRDiscovery._extract_metadata(). ---

    def test_extracts_all_fields(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        mtime = write_adr(f, "001", "Use Postgres", "Accepted", "We use PostgreSQL.")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        assert record.number == "001"
        assert record.title == "Use Postgres"
        assert record.status == "Accepted"
        assert record.decision_text == "We use PostgreSQL."
        assert record.file_path == f
        assert record.mtime == mtime

    def test_non_adr_file_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "notes.md"
        f.write_text("Just notes.\n", encoding="utf-8")
        assert ADRDiscovery._extract_metadata(f) is None

    def test_unreadable_file_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("# ADR-001: Test\n", encoding="utf-8")
        with patch("pathlib.Path.read_text", side_effect=OSError("nope")):
            assert ADRDiscovery._extract_metadata(f) is None

    def test_missing_status_section(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        f.write_text("# ADR-001: Test\n\n## Decision\n\nDo X.\n", encoding="utf-8")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        assert record.status == ""
        assert record.decision_text == "Do X."

    def test_missing_decision_section(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        f.write_text("# ADR-001: Test\n\n## Status\n\nAccepted\n", encoding="utf-8")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        assert record.status == "Accepted"
        assert record.decision_text == ""

    def test_heading_without_colon(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        f.write_text(
            "# ADR-001 Test Title\n\n## Status\n\nAccepted\n\n## Decision\n\nDo X.\n",
            encoding="utf-8",
        )
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        assert record.number == "001"

    def test_heading_with_space(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        f.write_text(
            "# ADR 001: Title\n\n## Status\n\nAccepted\n\n## Decision\n\nDo X.\n",
            encoding="utf-8",
        )
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        assert record.number == "001"

    def test_oserror_on_stat(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        write_adr(f, "001", "Test")
        with patch("pathlib.Path.stat", side_effect=OSError("nope")):
            record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        assert record.mtime == 0.0

    # --- Tests for ADRDiscovery._extract_section(). ---

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

    def test_extract_section_empty_section_returns_empty(self) -> None:
        content = "## Status\n\n## Decision\n\nDo X.\n"
        pattern = re.compile(
            r"^##\s+Status[ \t]*\n(.*?)(?=\n##\s|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        assert ADRDiscovery._extract_section(content, pattern) == ""

    # --- Tests for ADRDiscovery.find_files(). ---

    def test_finds_adrs_in_subdir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test")
        records = ADRDiscovery.find_files(docs, "adr")
        assert len(records) == 1
        assert records[0].number == "001"
        assert records[0].title == "Test"

    def test_finds_adrs_in_docs_root(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        write_adr(docs / "0001-test.md", "001", "Test")
        records = ADRDiscovery.find_files(docs, "")
        assert len(records) == 1

    def test_none_adrs_path_returns_empty(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        assert ADRDiscovery.find_files(docs, None) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        assert ADRDiscovery.find_files(docs, "adr") == []

    def test_excludes_distilled_file(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "adr").mkdir(parents=True)
        write_adr(docs / "adr" / "0001-test.md", "001", "Test")
        (docs / "adr" / "adr-distilled.md").write_text(
            "- [ADR-001](adr/0001-test.md) Test.\n", encoding="utf-8"
        )
        records = ADRDiscovery.find_files(docs, "")
        numbers = [r.number for r in records]
        assert "001" in numbers

    def test_multiple_adrs_sorted(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0003-c.md", "003", "C")
        write_adr(docs / "adr" / "0001-a.md", "001", "A")
        write_adr(docs / "adr" / "0002-b.md", "002", "B")
        records = ADRDiscovery.find_files(docs, "adr")
        assert [r.number for r in records] == ["001", "002", "003"]

    def test_non_adr_file_skipped(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "adr").mkdir(parents=True)
        write_adr(docs / "adr" / "0001-test.md", "001", "Test")
        (docs / "adr" / "notes.md").write_text("Just notes.\n", encoding="utf-8")
        records = ADRDiscovery.find_files(docs, "adr")
        assert len(records) == 1
