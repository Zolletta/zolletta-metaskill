"""Tests for the LinkInfo dataclass."""

from __future__ import annotations

from zolletta_metaskill.documentor.structs.link_info import LinkInfo


class TestLinkInfo:
    """Tests for the LinkInfo dataclass."""

    def test_construction_and_defaults(self) -> None:
        """LinkInfo sets fields and default status properly."""
        info = LinkInfo(
            source_file="doc.md",
            line_number=12,
            link_text="Click here",
            link_target="https://example.com",
            link_type="external",
        )
        assert info.source_file == "doc.md"
        assert info.line_number == 12
        assert info.link_text == "Click here"
        assert info.link_target == "https://example.com"
        assert info.link_type == "external"
        assert info.is_valid is None
        assert info.error is None

    def test_to_dict(self) -> None:
        """to_dict serializes all expected keys."""
        info = LinkInfo(
            source_file="readme.md",
            line_number=5,
            link_text="Docs",
            link_target="docs/index.md",
            link_type="local_file",
        )
        info.is_valid = True
        d = info.to_dict()
        assert d["source_file"] == "readme.md"
        assert d["line"] == 5
        assert d["text"] == "Docs"
        assert d["target"] == "docs/index.md"
        assert d["type"] == "local_file"
        assert d["valid"] is True
        assert d["error"] is None
