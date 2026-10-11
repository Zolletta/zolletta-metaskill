from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.documentor.utils.fenced_content import FencedContent


class TestFencedContent:
    """Tests for FencedContent."""

    # --- IsFence ---

    def test_backtick_fence_is_a_fence(self) -> None:
        assert FencedContent.is_fence("```python")

    def test_bare_fence_is_a_fence(self) -> None:
        assert FencedContent.is_fence("```")

    def test_closing_fence_is_a_fence(self) -> None:
        assert FencedContent.is_fence("```")

    def test_indented_fence_is_a_fence(self) -> None:
        assert FencedContent.is_fence("   ```")

    def test_prose_line_is_not_a_fence(self) -> None:
        assert not FencedContent.is_fence("Use ``` to fence a block.")

    def test_indented_code_block_is_not_a_fence(self) -> None:
        """Four-space blocks are explicitly out of scope for this helper."""
        assert not FencedContent.is_fence("    code = 1")

    def test_empty_line_is_not_a_fence(self) -> None:
        assert not FencedContent.is_fence("")

    # --- StripFences ---

    def test_removes_fenced_block(self) -> None:
        content = "before\n```markdown\n[broken](nope.md)\n```\nafter"
        assert FencedContent.strip_fences(content) == "before\nafter"

    def test_keeps_prose_around_a_fence(self) -> None:
        content = "See [ok](yes.md).\n```\n[nope](no.md)\n```\nSee [also](y.md)."
        result = FencedContent.strip_fences(content)
        assert "[ok](yes.md)" in result
        assert "[also](y.md)" in result
        assert "[nope](no.md)" not in result

    def test_preserves_line_count_of_prose(self) -> None:
        """Line numbers must survive so reports still point at the right line."""
        content = "one\ntwo\n```\nfour\n```\nsix\nseven"
        lines = FencedContent.strip_fences(content).splitlines()
        assert lines[0] == "one"
        assert lines[1] == "two"
        assert lines[-1] == "seven"

    def test_removes_multiple_blocks(self) -> None:
        content = "a\n```\nx\n```\nb\n```\ny\n```\nc"
        assert FencedContent.strip_fences(content) == "a\nb\nc"

    def test_fence_length_is_not_tracked(self) -> None:
        """Known limitation, recorded rather than hidden.

        A four-backtick fence containing an inner three-backtick run toggles
        state twice. No such block exists in this repository; if one appears,
        CommonMark's closing rule must be implemented here and in both callers
        together.
        """
        content = "a\n````\n```\nnested\n```\n````\nb"
        result = FencedContent.strip_fences(content)
        assert "nested" in result

    def test_unterminated_fence_drops_the_rest(self) -> None:
        content = "kept\n```\ndropped to end of file"
        assert FencedContent.strip_fences(content) == "kept"

    def test_text_without_fences_is_unchanged(self) -> None:
        content = "one\ntwo\nthree"
        assert FencedContent.strip_fences(content) == content

    def test_empty_content_is_empty(self) -> None:
        assert FencedContent.strip_fences("") == ""

    # --- StripFencesFromFile ---

    def test_reads_and_strips_a_file(self, tmp_path: Path) -> None:
        path = tmp_path / "doc.md"
        path.write_text("prose\n```\n[nope](x.md)\n```\n")
        result = FencedContent.strip_fences_from_file(path)
        assert "[nope](x.md)" not in result
        assert "prose" in result

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert FencedContent.strip_fences_from_file(tmp_path / "nope.md") == ""
