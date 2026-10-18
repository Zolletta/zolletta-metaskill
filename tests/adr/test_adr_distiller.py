"""Tests for ADRDistiller (parse/write/update the distilled file)."""

from __future__ import annotations

from zolletta_metaskill.adr.adr_distiller import ADRDistiller


class TestADRDistiller:
    # --- Tests for ADRDistiller.parse_directives(). ---

    def test_parse_directives_returns_adr_001_use_postgres(self) -> None:
        content = (
            "# Header\n\n"
            "- [ADR-001](adr/001.md) Use Postgres.\n"
            "- [ADR-002](adr/002.md) Use Redis.\n"
        )
        result = ADRDistiller.parse_directives(content)
        assert "ADR-001" in result
        assert "ADR-002" in result
        assert result["ADR-001"] == "- [ADR-001](adr/001.md) Use Postgres."

    def test_ignores_non_directive_lines(self) -> None:
        content = "# Header\n\nSome text.\n\n- Not a directive.\n"
        result = ADRDistiller.parse_directives(content)
        assert result == {}

    def test_parse_directives_empty_content_returns_empty_dict(self) -> None:
        assert ADRDistiller.parse_directives("") == {}

    def test_parse_directives_none_content_returns_empty_dict(self) -> None:
        assert ADRDistiller.parse_directives(None) == {}

    # --- Tests for ADRDistiller.find_lead_ins(). ---

    def test_find_lead_ins_returns_adr_numbers_for_colon_terminated(self) -> None:
        lines = [
            "- [ADR-001](adr/001.md) Add a conditional mutation-testing sensor:",
            "- [ADR-002](adr/002.md) Use Postgres.",
        ]
        assert ADRDistiller.find_lead_ins(lines) == ["ADR-001"]

    def test_find_lead_ins_returns_empty_for_complete_sentences(self) -> None:
        lines = [
            "- [ADR-001](adr/001.md) Use Postgres.",
            "- [ADR-002](adr/002.md) Configuration is resolved once per run.",
        ]
        assert ADRDistiller.find_lead_ins(lines) == []

    def test_find_lead_ins_ignores_lines_that_are_not_directives(self) -> None:
        lines = ["# Header", "Some prose ending in a colon:", "", "---"]
        assert ADRDistiller.find_lead_ins(lines) == []

    def test_find_lead_ins_deduplicates_repeated_numbers(self) -> None:
        lines = [
            "- [ADR-001](a.md) First lead-in:",
            "- [ADR-001](b.md) Same ADR again:",
        ]
        assert ADRDistiller.find_lead_ins(lines) == ["ADR-001"]

    def test_find_lead_ins_tolerates_trailing_newline(self) -> None:
        lines = ["- [ADR-001](adr/001.md) A lead-in:\n"]
        assert ADRDistiller.find_lead_ins(lines) == ["ADR-001"]
