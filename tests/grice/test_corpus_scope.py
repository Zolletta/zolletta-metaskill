"""Tests for corpus_scope.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.corpus_scope import CorpusScope


class TestCorpusScope:
    # --- is_adr ---

    @pytest.mark.parametrize(
        "path",
        [
            "docs/current/security/adr/ADR-001.md",
            "docs/maintainers/adr/0001-x.md",
            "docs/old/v3.x/security/adr/ADR-002.md",
            "docs/explanation/adrs/0001.md",
            "docs/ADR/0001.md",
        ],
        ids=[
            "adr_nested_in_current_is_excluded",
            "adr_in_maintainers_is_excluded",
            "adr_deep_in_old_is_excluded",
            "adrs_plural_is_excluded",
            "adr_uppercase_dir_is_excluded",
        ],
    )
    def test_is_adr_directory_named_adr_returns_true(self, path: str) -> None:
        assert CorpusScope.is_adr(path, None) is True

    @pytest.mark.parametrize(
        "path",
        ["docs/adr.md", "docs/explanation/documentation/adr.md", "docs/adrian/x.md", "README.md"],
        ids=[
            "file_named_adr_is_kept",
            "nested_file_named_adr_is_kept",
            "dir_with_adr_prefix_is_kept",
            "root_document_is_kept",
        ],
    )
    def test_is_adr_non_adr_directory_returns_false(self, path: str) -> None:
        assert CorpusScope.is_adr(path, None) is False

    def test_is_adr_inside_configured_dir_returns_true(self) -> None:
        assert CorpusScope.is_adr("docs/decisions/0001.md", "docs/decisions") is True

    def test_is_adr_sibling_of_configured_dir_returns_false(self) -> None:
        assert CorpusScope.is_adr("docs/decisions-old/0001.md", "docs/decisions") is False

    # --- split ---

    def test_split_configured_and_named_dirs_excludes_both(self) -> None:
        settings = {"documentation": {"dir": "docs", "adrs": "decisions"}}
        paths = ("README.md", "docs/decisions/1.md", "docs/a/adr/2.md", "docs/a/guide.md")
        assert CorpusScope.split(paths, settings) == (
            ("README.md", "docs/a/guide.md"),
            ("docs/decisions/1.md", "docs/a/adr/2.md"),
        )

    @pytest.mark.parametrize(
        "adrs",
        ["", ".", "./", None],
        ids=[
            "empty_adrs_excludes_nothing",
            "dot_adrs_excludes_nothing",
            "dot_slash_adrs_excludes_nothing",
            "null_adrs_excludes_nothing",
        ],
    )
    def test_split_adrs_naming_the_docs_root_keeps_the_corpus(self, adrs: str | None) -> None:
        settings = {"documentation": {"dir": "docs", "adrs": adrs}}
        paths = ("docs/0001-x.md", "docs/guide.md")
        assert CorpusScope.split(paths, settings) == (paths, ())

    def test_split_nested_configured_dir_is_normalised(self) -> None:
        settings = {"documentation": {"dir": "./docs/", "adrs": "explanation/adr/architecture/"}}
        paths = ("docs/explanation/adr/architecture/0001.md", "docs/explanation/x.md")
        assert CorpusScope.split(paths, settings)[1] == (
            "docs/explanation/adr/architecture/0001.md",
        )
