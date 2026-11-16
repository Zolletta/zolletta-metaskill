"""Tests for document_grouper.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.document_grouper import DocumentGrouper


class TestDocumentGrouper:
    # --- group_of ---

    @pytest.mark.parametrize(
        ("path", "docs_dir", "expected"),
        [
            (".backstage/docs/current/php/how-tos/x.md", ".backstage/docs", "current"),
            (".backstage/docs/old/v3.x/y.md", ".backstage/docs", "old"),
            (".backstage/docs/general/z.md", ".backstage/docs", "general"),
            (".backstage/docs/index.md", ".backstage/docs", "(root)"),
            ("README.md", ".backstage/docs", "(root)"),
            ("AGENTS.md", "docs", "(root)"),
            ("docs/guide/usage.md", "./docs/", "guide"),
            ("guide/usage.md", ".", "guide"),
            ("index.md", ".", "(root)"),
        ],
        ids=[
            "deep_file_takes_first_level_child",
            "old_is_an_ordinary_group",
            "shallow_child_is_its_own_group",
            "file_in_docs_dir_is_root",
            "root_readme_is_root",
            "root_agents_is_root",
            "docs_dir_is_normalised",
            "dot_docs_dir_groups_by_top_dir",
            "dot_docs_dir_top_file_is_root",
        ],
    )
    def test_group_of_path_returns_first_level_child_or_root(
        self, path: str, docs_dir: str, expected: str
    ) -> None:
        assert DocumentGrouper.group_of(path, docs_dir) == expected

    # --- order ---

    def test_order_repeated_groups_returns_sorted_with_root_last(self) -> None:
        groups = ["old", "(root)", "current", "old", "general"]
        assert DocumentGrouper.order(groups) == ("current", "general", "old", "(root)")
