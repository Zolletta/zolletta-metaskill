"""MarkdownCorpus — parse one markdown file into the shape the scorers read.

The four maxim scorers never see raw markdown. They see a
:class:`~zolletta_metaskill.grice.structs.document_features.DocumentFeatures`,
built once here, so the definition of "a section", "a sentence" and "inline
code" lives in exactly one place. Two scorers disagreeing about where a section
ends would produce two indices that cannot be compared, which defeats the whole
point of scoring a corpus relatively.

Fenced blocks are removed by the shared
:class:`~zolletta_metaskill.documentor.utils.fenced_content.FencedContent`
helper rather than by a second fence tracker here: prose metrics must not read
example code as prose, and the documentor tools already decided what a fence is.
"""

from __future__ import annotations

import re

from zolletta_metaskill.documentor.utils.fenced_content import FencedContent
from zolletta_metaskill.grice.structs.document_features import DocumentFeatures


class MarkdownCorpus:
    """Turn markdown source into a :class:`DocumentFeatures` value.

    The parse is line-oriented and single-pass: fence state, heading boundaries
    and boilerplate are all decided while walking the lines once, so heading
    line numbers stay true to the file even though fenced blocks are dropped
    from the prose.
    """

    HEADING = re.compile(r"^(#{1,6})\s+(\S.*?)\s*#*\s*$")
    CODE_SPAN = re.compile(r"`([^`\n]+)`")
    SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
    BADGE_LINE = re.compile(r"^\s*(?:\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\))\s*$")
    RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
    COMMENT_LINE = re.compile(r"^\s*<!--.*?(?:-->)?\s*$")
    FRONTMATTER = "---"

    @staticmethod
    def parse(path: str, text: str) -> DocumentFeatures:
        """Parse *text* into its feature shape.

        Args:
            path: Repository-relative path recorded on the result.
            text: Raw markdown source.

        Returns:
            The parsed features. A document with no headings yields one
            pseudo-section holding the whole body, because a body is a section
            even when nobody labelled it.

        """
        frontmatter, body, offset = MarkdownCorpus._split_frontmatter(text)
        headings, levels, numbers, sections = MarkdownCorpus._walk(body, offset)
        prose = "\n".join(sections)
        return DocumentFeatures(
            path=path,
            prose=prose,
            frontmatter=frontmatter,
            sections=sections,
            sentences=MarkdownCorpus._sentences(sections),
            headings=headings,
            heading_levels=levels,
            heading_lines=numbers,
            code_spans=tuple(
                span.strip() for span in MarkdownCorpus.CODE_SPAN.findall(prose) if span.strip()
            ),
            boilerplate_words=MarkdownCorpus._boilerplate_words(body),
        )

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[str, list[str], int]:
        """Split a leading ``---`` block off *text*.

        Args:
            text: Raw markdown source.

        Returns:
            The frontmatter text (``""`` when absent), the remaining lines, and
            how many lines the frontmatter consumed. The count is carried so
            heading line numbers keep pointing at the real file.

        """
        lines = text.splitlines()
        if not lines or lines[0].strip() != MarkdownCorpus.FRONTMATTER:
            return "", lines, 0
        for index in range(1, len(lines)):
            if lines[index].strip() == MarkdownCorpus.FRONTMATTER:
                return "\n".join(lines[1:index]), lines[index + 1 :], index + 1
        return "", lines, 0

    @staticmethod
    def _walk(
        lines: list[str], offset: int
    ) -> tuple[tuple[str, ...], tuple[int, ...], tuple[int, ...], tuple[str, ...]]:
        """Split *lines* into headings and their bodies in one pass.

        Args:
            lines: Body lines, frontmatter already removed.
            offset: How many lines preceded *lines*, so line numbers are
                file-relative rather than body-relative.

        Returns:
            Heading texts, heading levels, heading line numbers (1-based), and
            the body of each heading. Prose before the first heading joins that
            heading's body instead of forming a heading-less section, which is
            what keeps the two tuples the same length.

        """
        headings: list[str] = []
        levels: list[int] = []
        numbers: list[int] = []
        sections: list[str] = []
        current: list[str] = []
        in_fence = False  # pragma: no mutate — None is falsy like False, equivalent initial state
        for index, line in enumerate(lines):
            if FencedContent.is_fence(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = MarkdownCorpus.HEADING.match(line.strip())
            if match:
                # The first heading does not close a section: prose written
                # before it belongs to that heading's body, not to a
                # heading-less pseudo-section nobody wrote a title for.
                if headings:
                    sections.append("\n".join(current))
                    current = []
                headings.append(match.group(2).strip())
                levels.append(len(match.group(1)))
                numbers.append(offset + index + 1)
                continue
            current.append(line)
        if headings:
            sections.append("\n".join(current))
            return tuple(headings), tuple(levels), tuple(numbers), tuple(sections)
        return (), (), (), ("\n".join(current),)

    @staticmethod
    def _sentences(sections: tuple[str, ...]) -> tuple[str, ...]:
        """Split section bodies into sentences.

        Table rows are dropped: a row is a record, not a sentence, and counting
        its pipes as punctuation would distort every length metric. List
        markers are stripped so a bullet reads as the sentence it carries.

        Args:
            sections: Section bodies in document order.

        Returns:
            The sentences found, whitespace-trimmed, in document order.

        """
        sentences: list[str] = []
        for section in sections:
            for candidate in MarkdownCorpus.SENTENCE_BREAK.split(section):
                sentence = candidate.strip()
                if len(sentence) < 2 or sentence.startswith("|"):
                    continue
                sentences.append(sentence)
        return tuple(sentences)

    @staticmethod
    def _boilerplate_words(lines: list[str]) -> int:
        """Count the words on badge, rule and comment lines.

        Args:
            lines: Body lines, frontmatter already removed.

        Returns:
            The number of words that decorate the document rather than inform
            it. Frontmatter is excluded from both sides of the ratio, so it is
            not counted here either.

        """
        patterns = (
            MarkdownCorpus.BADGE_LINE,
            MarkdownCorpus.RULE,
            MarkdownCorpus.COMMENT_LINE,
        )
        return sum(
            len(line.split()) for line in lines if any(pattern.match(line) for pattern in patterns)
        )
