"""Fenced-code handling shared by the documentor tools.

Two tools need the same thing and were each doing it with an inline boolean:
``link_checker`` to skip fenced blocks while collecting links, and
``doc_code_mapper`` to skip them while collecting references. They agreed by
coincidence, not by construction — which is why a ``markdown`` block
*illustrating* a link became a real reference in one tool and was correctly
ignored in the other.

One helper makes the agreement structural: if a fence rule ever changes, both
call sites change together.
"""

from __future__ import annotations

from pathlib import Path


class FencedContent:
    """Fenced-code awareness for markdown text.

    Handles ``` fences and only ``` fences. Indented four-space blocks are
    deliberately out of scope: neither caller tracked them, and adding the
    capability to one side only would recreate exactly the disagreement this
    class exists to remove.

    Known limitation: fence *length* is not tracked, so a ```` ```` ```` block
    containing an inner ``` run would toggle state twice. No such block exists
    in this repository today. If one is ever added, CommonMark's rule — a fence
    closes only on a run at least as long as the one that opened it — has to be
    implemented here and in both callers together.
    """

    FENCE = "```"

    @staticmethod
    def is_fence(line: str) -> bool:
        """Return True when *line* opens or closes a fenced block."""
        return line.strip().startswith(FencedContent.FENCE)

    @staticmethod
    def strip_fences(content: str) -> str:
        """Return *content* with fenced blocks removed.

        Fence lines themselves are dropped too, so the remaining text can be
        searched with plain regexes without a fence ever leaking through.

        Args:
            content: Raw markdown text.

        Returns:
            The text outside every ``` fenced block, original line structure
            preserved so reported line numbers still line up.

        """
        kept: list[str] = []
        in_fence = False
        for line in content.splitlines():
            if FencedContent.is_fence(line):
                in_fence = not in_fence
                continue
            if not in_fence:
                kept.append(line)
        return "\n".join(kept)

    @staticmethod
    def strip_fences_from_file(path: str | Path) -> str:
        """Return the fenced-free text of *path*, or "" when it cannot be read."""
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""
        return FencedContent.strip_fences(content)
