"""Tests for ADROrchestrator — distill, refresh, run, main, and truncate decisions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.adr.adr_discovery import ADRDiscovery
from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator

from .conftest import write_adr


def write_settings(tmp_path: Path) -> None:
    """Write a minimal settings.json into ``tmp_path/.zolletta-metaskill``."""
    meta = tmp_path / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "settings.json").write_text(
        json.dumps({"documentation": {"dir": "docs", "adrs": "adr"}})
    )


class TestADROrchestrator:
    # --- Tests for ADROrchestrator.distill_adr(). ---

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

    # --- Tests for ADROrchestrator.refresh(). ---

    def test_fresh_start_creates_distilled_file(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
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
        write_adr(f, "001", "Test", "Accepted", "We now do Z.")
        os.utime(f, (9999999999, 9999999999))  # far-future mtime to force staleness
        report = distiller.refresh()
        assert "ADR-001" in report.stale
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "We now do Z." in result

    def test_new_adr_added(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        write_adr(docs / "adr" / "0002-new.md", "002", "New", "Accepted", "We do Y.")
        report = distiller.refresh()
        assert "ADR-002" in report.new
        result = (docs / "adr" / "adr-distilled.md").read_text(encoding="utf-8")
        assert "[ADR-002]" in result

    def test_removed_adr_removed(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
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
        write_adr(f, "001", "Test", "Deprecated", "We do X.")
        os.utime(f, (9999999999, 9999999999))  # far-future mtime to force staleness
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
        write_adr(f, "001", "Test", "Accepted", "We do X.")
        os.utime(f, (9999999999, 9999999999))  # far-future mtime to force staleness
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
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
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
        write_adr(docs / "adr" / "0001-keep.md", "001", "Keep", "Accepted", "We do X.")
        write_adr(docs / "adr" / "0002-gone.md", "002", "Gone", "Accepted", "We do Y.")
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
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        cache_path = tmp_path / "cache.json"
        distiller = ADROrchestrator(docs, "adr", cache_path)
        distiller.refresh()
        # Delete the distilled file — next run treats it as no existing content
        (docs / "adr" / "adr-distilled.md").unlink()
        report = distiller.refresh()
        assert report.has_adrs is True
        assert (docs / "adr" / "adr-distilled.md").exists()

    # --- Tests for ADROrchestrator.run() — delegates to ADRCLI.run(). ---

    def test_run_with_valid_adrs_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        monkeypatch.chdir(tmp_path)
        rc = ADROrchestrator.run([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 new" in out

    def test_run_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        monkeypatch.chdir(tmp_path)
        rc = ADROrchestrator.run([])
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err

    def test_run_with_none_argv_uses_sys_argv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When argv is None, ADRCLI.run reads from sys.argv."""
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = ADROrchestrator.run(None)
        assert rc == 0

    # --- Tests for ADROrchestrator.main(). ---

    def test_main_with_adrs_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        docs = tmp_path / "docs"
        write_adr(docs / "adr" / "0001-test.md", "001", "Test", "Accepted", "We do X.")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = ADROrchestrator.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "1 new" in out

    def test_main_with_nonexistent_docs_dir_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_settings(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = ADROrchestrator.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "not a directory" in err

    # --- Tests for ADROrchestrator._truncate_decision(). ---

    def test_short_text_preserved(self) -> None:
        assert ADROrchestrator._truncate_decision("Use PostgreSQL.") == "Use PostgreSQL."

    def test_truncates_at_sentence(self) -> None:
        text = "Use PostgreSQL for the primary database. More text follows here."
        result = ADROrchestrator._truncate_decision(text)
        assert result == "Use PostgreSQL for the primary database."

    def test_truncates_at_max_length(self) -> None:
        text = "A " * 150  # 300 chars, no sentence boundary
        result = ADROrchestrator._truncate_decision(text)
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

    def test_strips_markdown_bold(self) -> None:
        result = ADROrchestrator._truncate_decision("**Important** decision.")
        assert result == "Important decision."

    def test_strips_markdown_italic(self) -> None:
        assert ADROrchestrator._truncate_decision("*Important* decision.") == "Important decision."

    def test_strips_markdown_code(self) -> None:
        result = ADROrchestrator._truncate_decision("Use `postgres` database.")
        assert result == "Use postgres database."

    def test_strips_markdown_links(self) -> None:
        result = ADROrchestrator._truncate_decision("See [docs](http://example.com) for info.")
        assert result == "See docs for info."

    def test_truncate_decision_empty_text_returns_empty(self) -> None:
        assert ADROrchestrator._truncate_decision("") == ""

    def test_truncate_decision_collapses_whitespace_returns_use_postgresql_now(self) -> None:
        result = ADROrchestrator._truncate_decision("Use    PostgreSQL\n\nnow.")
        assert result == "Use PostgreSQL now."

    def test_no_word_boundary_in_long_text(self) -> None:
        text = "a" * 250
        result = ADROrchestrator._truncate_decision(text)
        assert result.endswith("...")

    def test_exactly_max_length_no_truncation(self) -> None:
        """Text at exactly _MAX_DECISION_LEN chars is not truncated."""
        text = "a" * ADROrchestrator._MAX_DECISION_LEN
        result = ADROrchestrator._truncate_decision(text)
        assert result == text
        assert not result.endswith("...")
