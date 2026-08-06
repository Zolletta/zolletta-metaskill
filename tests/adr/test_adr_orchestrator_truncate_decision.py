"""Tests for ADROrchestrator._truncate_decision()."""

from __future__ import annotations

from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator


class TestTruncateDecision:
    """Tests for ADROrchestrator._truncate_decision()."""

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
