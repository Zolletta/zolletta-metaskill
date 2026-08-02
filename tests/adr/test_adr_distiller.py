"""Tests for ADRDistiller (parse/write/update the distilled file)."""

from __future__ import annotations

from zolletta_metaskill.adr.adr_distiller import ADRDistiller


class TestParseDirectives:
    """Tests for ADRDistiller.parse_directives()."""

    def test_parses_directives(self) -> None:
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

    def test_empty_content(self) -> None:
        assert ADRDistiller.parse_directives("") == {}

    def test_none_content(self) -> None:
        assert ADRDistiller.parse_directives(None) == {}
