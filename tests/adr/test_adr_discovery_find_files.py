"""Tests for ADRDiscovery.find_files()."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.adr.adr_discovery import ADRDiscovery

from .conftest import write_adr


class TestFindFiles:
    """Tests for ADRDiscovery.find_files()."""

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
