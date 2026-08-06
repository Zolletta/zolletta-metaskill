"""Tests for ADROrchestrator.distill_adr()."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.adr.adr_discovery import ADRDiscovery
from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator

from .conftest import write_adr


class TestDistillAdr:
    """Tests for ADROrchestrator.distill_adr()."""

    def test_accepted_adr_produces_directive(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-use-postgres.md"
        write_adr(
            f, "001", "Use Postgres", "Accepted", "We use PostgreSQL for the primary database."
        )
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        distiller = ADROrchestrator(docs, "adr", tmp_path / "cache.json")
        directive = distiller.distill_adr(record)
        assert directive is not None
        assert directive.startswith("- [ADR-001](adr/0001-use-postgres.md) ")
        assert "PostgreSQL" in directive

    def test_proposed_adr_excluded(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Proposed", "Maybe do X.")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        distiller = ADROrchestrator(docs, "adr", tmp_path / "cache.json")
        assert distiller.distill_adr(record) is None

    def test_deprecated_adr_excluded(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Deprecated", "We used to do X.")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        distiller = ADROrchestrator(docs, "adr", tmp_path / "cache.json")
        assert distiller.distill_adr(record) is None

    def test_superseded_adr_excluded(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Superseded", "Old decision.")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        distiller = ADROrchestrator(docs, "adr", tmp_path / "cache.json")
        assert distiller.distill_adr(record) is None

    def test_link_path_relative_to_docs_dir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "0001-test.md"
        write_adr(f, "001", "Test", "Accepted", "Do X.")
        record = ADRDiscovery._extract_metadata(f)
        assert record is not None
        distiller = ADROrchestrator(docs, "", tmp_path / "cache.json")
        directive = distiller.distill_adr(record)
        assert directive is not None
        assert "(0001-test.md)" in directive
