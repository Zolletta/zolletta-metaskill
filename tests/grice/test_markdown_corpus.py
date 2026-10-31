"""Tests for markdown_corpus.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.markdown_corpus import MarkdownCorpus


class TestMarkdownCorpus:
    # --- headings and sections ---

    def test_parse_two_headings_splits_sections_at_each(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nIntro prose.\n\n## Step\n\nMore prose.\n"
        )
        assert features.headings == ("Title", "Step")
        assert features.heading_levels == (1, 2)
        assert features.section_count == 2

    def test_parse_two_headings_records_one_based_line_numbers(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nIntro prose.\n\n## Step\n\nMore prose.\n"
        )
        assert features.heading_lines == (1, 5)

    def test_parse_no_heading_keeps_one_pseudo_section(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "Just prose.\n\nAnd more.\n")
        assert features.headings == ()
        assert features.heading_levels == ()
        assert features.heading_lines == ()
        assert features.section_count == 1
        assert features.sections == ("Just prose.\n\nAnd more.",)

    def test_parse_two_sections_records_exact_section_bodies(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nIntro prose.\n\n## Step\n\nMore prose.\n"
        )
        assert features.sections == ("\nIntro prose.\n", "\nMore prose.")
        assert features.prose == "\nIntro prose.\n\n\nMore prose."

    def test_parse_prose_before_first_heading_joins_its_section(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "Loose prose.\n\n# Title\n\nBody.\n")
        assert features.headings == ("Title",)
        assert features.section_count == 1
        assert "Loose prose." in features.sections[0]
        assert "Body." in features.sections[0]

    def test_parse_trailing_hashes_are_stripped_from_heading_text(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "## Step ##\n\nBody.\n")
        assert features.headings == ("Step",)

    def test_parse_empty_document_yields_a_blank_section(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "")
        assert features.headings == ()
        assert features.sections == ("",)
        assert features.prose == ""

    # --- frontmatter ---

    def test_parse_leading_frontmatter_is_recorded(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "---\naudience: human\nstatus: stable\n---\n# Title\n"
        )
        assert features.frontmatter == "audience: human\nstatus: stable"

    def test_parse_frontmatter_keeps_heading_line_numbers_file_relative(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "---\naudience: human\nstatus: stable\n---\n# Title\n\nBody.\n"
        )
        assert features.heading_lines == (5,)

    def test_parse_frontmatter_is_excluded_from_prose(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "---\naudience: human\n---\n# Title\n\nBody.\n"
        )
        assert "audience" not in features.prose

    def test_parse_no_frontmatter_records_empty_frontmatter(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "Just prose.\n")
        assert features.frontmatter == ""

    def test_parse_empty_frontmatter_is_excluded_from_prose(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "---\n---\n# Title\n\nBody.\n")
        assert features.frontmatter == ""
        assert features.headings == ("Title",)
        assert features.prose == "\nBody."
        assert features.boilerplate_words == 0

    def test_parse_unterminated_frontmatter_is_treated_as_body(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "---\naudience: human\n\n# Title\n")
        assert features.frontmatter == ""
        assert features.headings == ("Title",)

    def test_parse_unterminated_frontmatter_keeps_heading_line_numbers(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "---\naudience: human\n\n# Title\n")
        assert features.heading_lines == (4,)

    # --- fenced code ---

    def test_parse_fenced_block_is_excluded_from_prose(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md",
            "# Title\n\nRun this.\n\n```python\nprint('hello')\n```\n\nThen stop.\n",
        )
        assert "print('hello')" not in features.prose
        assert "Run this." in features.prose
        assert "Then stop." in features.prose

    def test_parse_heading_after_fenced_block_is_still_found(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\n```python\nprint('hello')\n```\n\n## Step\n\nBody.\n"
        )
        assert features.headings == ("Title", "Step")
        assert features.heading_lines == (1, 7)

    # --- sentences ---

    def test_parse_terminated_sentences_splits_them(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "# Title\n\nOne. Two? Three!\n")
        assert features.sentences == ("One.", "Two?", "Three!")

    def test_parse_table_rows_are_not_sentences(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\n| Field | Type |\n|---|---|\n| path | str |\n"
        )
        assert features.sentences == ()

    def test_parse_empty_section_produces_no_sentence(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "")
        assert features.sections == ("",)
        assert features.sentences == ()

    def test_parse_two_character_sentence_is_kept(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "# Title\n\nGo\n")
        assert features.sentences == ("Go",)

    def test_parse_dropped_candidate_does_not_end_the_section(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "# Title\n\nOne. . Two.\n")
        assert features.sentences == ("One.", "Two.")

    # --- code spans ---

    def test_parse_inline_code_spans_are_collected_without_backticks(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nRun `make test` then `ruff`.\n"
        )
        assert features.code_spans == ("make test", "ruff")

    def test_parse_blank_code_span_is_dropped(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "# Title\n\nAn empty `` span.\n")
        assert features.code_spans == ()

    # --- boilerplate ---

    @pytest.mark.parametrize(
        ("line", "word_count"),
        [
            ("[![badge](https://img/b.svg)](https://example.com)", 1),
            ("---", 1),
            ("<!-- note -->", 3),
        ],
        ids=[
            "badge_line_counts_one_word",
            "rule_line_counts_one_word",
            "comment_line_counts_three_words",
        ],
    )
    def test_parse_boilerplate_lines_are_counted_as_words(self, line: str, word_count: int) -> None:
        features = MarkdownCorpus.parse("docs/index.md", f"# Title\n\n{line}\n\nBody.\n")
        assert features.boilerplate_words == word_count

    def test_parse_multiline_comment_is_excluded_from_prose(self) -> None:
        """A comment spanning several lines contributes no prose words."""
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nReal prose.\n<!-- hidden\nstill hidden\n-->\nMore prose.\n"
        )
        assert "hidden" not in features.prose
        assert "Real prose" in features.prose
        assert "More prose" in features.prose

    def test_parse_multiline_comment_counts_boilerplate_words(self) -> None:
        """Every word inside a multi-line comment region is boilerplate."""
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nBody.\n<!-- one two\nthree -->\nTail.\n"
        )
        # `<!--`, `one`, `two`, `three`, `-->` — the whole comment region.
        assert features.boilerplate_words == 5

    def test_parse_unterminated_comment_drops_remainder(self) -> None:
        """An unclosed comment swallows the rest of the file."""
        features = MarkdownCorpus.parse(
            "docs/index.md", "# Title\n\nReal prose.\n<!-- never closed\nstill hidden\n"
        )
        assert "hidden" not in features.prose
        assert "Real prose" in features.prose

    def test_parse_prose_only_document_has_no_boilerplate(self) -> None:
        features = MarkdownCorpus.parse("docs/index.md", "# Title\n\nBody prose here.\n")
        assert features.boilerplate_words == 0

    def test_parse_frontmatter_is_not_counted_as_boilerplate(self) -> None:
        features = MarkdownCorpus.parse(
            "docs/index.md", "---\naudience: human\n---\n# Title\n\nBody.\n"
        )
        assert features.boilerplate_words == 0
