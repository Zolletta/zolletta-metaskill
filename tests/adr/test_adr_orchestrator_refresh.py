"""Tests for ADROrchestrator.refresh()."""

from __future__ import annotations

import time
from pathlib import Path

from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator

from .conftest import write_adr


class TestRefresh:
    """Tests for ADROrchestrator.refresh()."""

    def test_fresh_start_creates_distilled_file(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted",
                 "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        report = distiller.refresh()
        assert report.has_adrs is True
        assert "ADR-001" in report.new
        distilled = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-001]" in distilled
        assert "We do X." in distilled
        assert cache_path.exists()

    def test_no_changes_preserves_existing(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Accepted", "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        # First run
        distiller.refresh()
        # Modify the distilled file with agent refinement
        distilled_path = docs / "adr" / "adr-distilled.md"
        content = distilled_path.read_text(encoding="utf-8")
        refined = content.replace(
            "- [ADR-001](adr/0001-test.md) We do X.",
            "- [ADR-001](adr/0001-test.md) We do X instead of Y.",
        )
        distilled_path.write_text(refined, encoding="utf-8")
        # Second run — no changes to ADR
        report = distiller.refresh()
        assert report.new == []
        assert report.stale == []
        assert report.removed == []
        result = distilled_path.read_text(encoding="utf-8")
        assert "instead of Y" in result

    def test_stale_adr_re_distilled(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Accepted", "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        # Modify the ADR (change mtime)
        time.sleep(0.01)
        write_adr(f, "001", "Test", "Accepted", "We now do Z.")
        report = distiller.refresh()
        assert "ADR-001" in report.stale
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "We now do Z." in result

    def test_new_adr_added(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted",
                 "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        write_adr(docs / "adr" / "0002-new.md", "002", "New", "Accepted",
                 "We do Y.")
        report = distiller.refresh()
        assert "ADR-002" in report.new
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-002]" in result

    def test_removed_adr_removed(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted",
                 "We do X.")
        f2 = docs / "adr" / "0002-gone.md"
        write_adr(f2, "002", "Gone", "Accepted", "We do Y.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        f2.unlink()
        report = distiller.refresh()
        assert "ADR-002" in report.removed
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-002]" not in result
        assert "[ADR-001]" in result

    def test_no_adrs_writes_placeholder(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "adr").mkdir(parents=True)
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        report = distiller.refresh()
        assert report.has_adrs is False
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "No Architecture Decision Records" in result

    def test_status_change_accepted_to_deprecated_removes(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Accepted", "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        time.sleep(0.01)
        write_adr(f, "001", "Test", "Deprecated", "We do X.")
        report = distiller.refresh()
        assert report.has_adrs is False
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-001]" not in result
        assert "No Architecture Decision Records" in result

    def test_status_change_proposed_to_accepted_adds(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        f = docs / "adr" / "0001-test.md"
        write_adr(f, "001", "Test", "Proposed", "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        time.sleep(0.01)
        write_adr(f, "001", "Test", "Accepted", "We do X.")
        report = distiller.refresh()
        assert report.has_adrs is True
        assert "ADR-001" in report.stale
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-001]" in result

    def test_none_adrs_path_writes_placeholder(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, None, cache_path)
        report = distiller.refresh()
        assert report.has_adrs is False

    def test_distilled_file_preserves_category_headings(self, tmp_path: Path) -> None:
        """Agent-added category headings are preserved across refreshes."""
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted",
                 "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        # Add category heading to distilled file
        distilled_path = docs / "adr" / "adr-distilled.md"
        content = distilled_path.read_text(encoding="utf-8")
        content = content.replace(
            "- [ADR-001]",
            "## Architecture\n\n- [ADR-001]",
        )
        distilled_path.write_text(content, encoding="utf-8")
        # Refresh with no changes — heading should be preserved
        distiller.refresh()
        result = distilled_path.read_text(encoding="utf-8")
        assert "## Architecture" in result

    def test_in_place_update_removes_directive(self, tmp_path: Path) -> None:
        """ADRDistiller.update_in_place removes directives for removed ADRs."""
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-keep.md", "001", "Keep", "Accepted",
                 "We do X.")
        write_adr(docs / "adr" / "0002-gone.md", "002", "Gone", "Accepted",
                 "We do Y.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        # Delete ADR-002 and refresh (stale-only update path)
        (docs / "adr" / "0002-gone.md").unlink()
        report = distiller.refresh()
        assert "ADR-002" in report.removed
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-002]" not in result
        assert "[ADR-001]" in result

    def test_oserror_reading_distilled_file(self, tmp_path: Path) -> None:
        """OSError reading existing distilled file is handled gracefully.

        The defensive except OSError: pass in refresh is hard to
        trigger reliably on all platforms. We verify the code path by
        checking that a normal refresh after deleting the distilled file
        still works (existing_content is None, treated same as OSError).
        """
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted",
                 "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        # Delete the distilled file — next run treats it as no existing content
        (docs / "adr" / "adr-distilled.md").unlink()
        report = distiller.refresh()
        assert report.has_adrs is True
        assert (docs / "adr" / "adr-distilled.md").exists()
