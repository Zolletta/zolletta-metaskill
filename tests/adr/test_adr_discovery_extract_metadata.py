"""Tests for ADRDiscovery._extract_metadata()."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from zolletta_metaskill.adr.adr_discovery import ADRDiscovery

from .conftest import write_adr


class TestExtractMetadata:
    """Tests for ADRDiscovery._extract_metadata()."""

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
