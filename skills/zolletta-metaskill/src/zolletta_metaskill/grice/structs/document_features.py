"""DocumentFeatures — the parsed shape of one documentation file."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentFeatures:
    """Everything the four maxim scorers need from one markdown file.

    Parsed once and passed to every scorer, so a file is read and split a
    single time. Each maxim asks a different question of the same shape — how
    long the sections are, whether the headings match their bodies, how the
    sentences read — and every one of those questions is answered from this
    struct rather than from a re-read of the file.

    Attributes:
        path: Repository-relative path, used as the report row key.
        prose: The document body with frontmatter and fenced code removed.
        frontmatter: The leading ``---`` block, or ``""`` when absent.
        sections: Section bodies, one per heading; text before the first
            heading is section zero so no prose is silently dropped.
        sentences: Sentences extracted from :attr:`sections`.
        headings: Heading texts in document order, without the ``#`` markers.
        heading_levels: Heading depths (1-6), positionally aligned with
            :attr:`headings`.
        heading_lines: 1-based line numbers of the headings, positionally
            aligned with :attr:`headings`.
        code_spans: Inline code spans, backticks stripped.
        boilerplate_words: Words on badge, image, comment, rule and
            frontmatter lines — material that carries no prose of its own.

    """

    path: str
    prose: str
    frontmatter: str
    sections: tuple[str, ...]
    sentences: tuple[str, ...]
    headings: tuple[str, ...]
    heading_levels: tuple[int, ...]
    heading_lines: tuple[int, ...]
    code_spans: tuple[str, ...]
    boilerplate_words: int

    @property
    def word_count(self) -> int:
        """Return the number of whitespace-separated words in the prose.

        Returns:
            The word count, or ``0`` for a frontmatter-only document.

        """
        return len(self.prose.split())

    @property
    def section_count(self) -> int:
        """Return how many section bodies the document has.

        Returns:
            The section count; always at least one for a non-empty body.

        """
        return len(self.sections)

    @property
    def sentence_count(self) -> int:
        """Return how many sentences the scorer extracted.

        Returns:
            The sentence count.

        """
        return len(self.sentences)

    @property
    def words_per_section(self) -> float:
        """Return the mean section length in words.

        Returns:
            Words divided by sections, or ``0.0`` when there are no sections.

        """
        if not self.sections:
            return 0.0
        return self.word_count / len(self.sections)
