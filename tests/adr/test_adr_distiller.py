"""Tests for ADRDistiller (parse/write/update the distilled file)."""

from __future__ import annotations

from pathlib import Path

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

    def test_find_lead_ins_trailing_space_after_colon_returns_empty(self) -> None:
        lines = ["- [ADR-001](adr/001.md) A lead-in: \n"]
        assert ADRDistiller.find_lead_ins(lines) == []

    def test_find_lead_ins_leading_newline_returns_empty(self) -> None:
        lines = ["\n- [ADR-001](adr/001.md) A lead-in:"]
        assert ADRDistiller.find_lead_ins(lines) == []

    def test_find_lead_ins_directive_ending_in_x_returns_empty(self) -> None:
        lines = ["- [ADR-001](adr/001.md) Rule:X\n"]
        assert ADRDistiller.find_lead_ins(lines) == []

    # --- Tests for ADRDistiller.is_lead_in(). ---

    def test_is_lead_in_colon_terminated_directive_returns_true(self) -> None:
        assert ADRDistiller.is_lead_in("- [ADR-001](adr/001.md) A lead-in:") is True

    def test_is_lead_in_trailing_space_after_colon_returns_false(self) -> None:
        assert ADRDistiller.is_lead_in("- [ADR-001](adr/001.md) A lead-in: \n") is False

    def test_is_lead_in_leading_newline_returns_false(self) -> None:
        assert ADRDistiller.is_lead_in("\n- [ADR-001](adr/001.md) A lead-in:") is False

    def test_is_lead_in_directive_ending_in_x_returns_false(self) -> None:
        assert ADRDistiller.is_lead_in("- [ADR-001](adr/001.md) Rule:X\n") is False

    # --- Tests for ADRDistiller.update_in_place(). ---

    def test_update_in_place_stale_directives_writes_exact_content(self, tmp_path: Path) -> None:
        existing = (
            "# Head\n"
            "- [ADR-001](a.md) old text\n"
            "- [ADR-002](b.md) remove me\n"
            "- [ADR-003](c.md) keep me\n"
            "- [ADR-004](d.md) stale"
        )
        target = tmp_path / "adr-distilled.md"
        target.write_text(existing)
        ADRDistiller.update_in_place(
            target,
            existing,
            {
                "ADR-001": "- [ADR-001](a.md) new text",
                "ADR-004": "- [ADR-004](d.md) fresh",
            },
            ["ADR-002"],
        )
        assert target.read_text() == (
            "# Head\n- [ADR-001](a.md) new text\n- [ADR-003](c.md) keep me\n- [ADR-004](d.md) fresh"
        )

    # --- Tests for ADRDistiller.write(). ---

    def test_write_new_file_writes_exact_content(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "adr-distilled.md"
        ADRDistiller.write(
            target,
            [
                "- [ADR-001](a.md) Use Postgres.",
                "- [ADR-002](b.md) Use Redis.",
            ],
        )
        assert target.read_text() == (
            "---\n"
            "audience: ai\n"
            "status: generated\n"
            'description: "Auto-generated architectural directives distilled from Accepted ADRs."\n'
            "---\n\n"
            "# adr-distilled.md — Architectural Directives\n\n"
            "> Auto-generated from the project's ADRs by the adr-distiller.\n"
            "> Do not edit directly — edit the source ADRs and re-run "
            "`/zolletta-metaskill adr-distiller` or `/zolletta-metaskill review`.\n"
            "> Each directive links to its source ADR for full context. "
            "Only Accepted decisions are included.\n\n"
            "- [ADR-001](a.md) Use Postgres.\n"
            "- [ADR-002](b.md) Use Redis.\n"
        )

    # --- Tests for ADRDistiller.write_placeholder(). ---

    def test_write_placeholder_new_file_writes_exact_content(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "adr-distilled.md"
        ADRDistiller.write_placeholder(target)
        assert target.read_text() == (
            "---\n"
            "audience: ai\n"
            "status: generated\n"
            'description: "Auto-generated placeholder written when no Accepted ADRs are found."\n'
            "---\n\n"
            "# adr-distilled.md — Architectural Directives\n\n"
            "No Architecture Decision Records (ADRs) were found in this "
            "project's documentation.\n\n"
            "ADRs capture the context, decision, and consequences of "
            "significant architectural choices.\n"
            "See https://adr.github.io/ for guidance on the ADR format.\n\n"
            "To start using ADRs:\n"
            "1. Create an `adr/` directory under your documentation folder\n"
            "2. Write your first ADR following the format described in the "
            "project's documentation standards\n"
            "3. Re-run `/zolletta-metaskill setup` to detect and distill them\n"
        )
