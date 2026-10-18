"""Tests for documentation_inventory.py."""

from __future__ import annotations

from zolletta_metaskill.documentor.structs import DocumentationInventory


class TestDocumentationInventory:
    # --- all_paths ---

    def test_inventory_all_paths_merges_both_groups_sorted(self) -> None:
        inventory = DocumentationInventory(
            documentation=("docs/b.md", "docs/a.md"),
            root_documents={"readme": "README.md"},
        )
        assert inventory.all_paths == ("README.md", "docs/a.md", "docs/b.md")

    def test_inventory_all_paths_drops_a_path_in_both_groups(self) -> None:
        inventory = DocumentationInventory(
            documentation=("README.md",),
            root_documents={"readme": "README.md"},
        )
        assert inventory.all_paths == ("README.md",)

    def test_inventory_all_paths_is_empty_without_any_group(self) -> None:
        assert DocumentationInventory().all_paths == ()

    # --- kind_of ---

    def test_inventory_kind_of_returns_the_root_document_kind(self) -> None:
        inventory = DocumentationInventory(
            root_documents={"readme": "README.md", "agents": "AGENTS.md"}
        )
        assert inventory.kind_of("AGENTS.md") == "agents"

    def test_inventory_kind_of_returns_none_for_a_docs_dir_file(self) -> None:
        inventory = DocumentationInventory(documentation=("docs/index.md",))
        assert inventory.kind_of("docs/index.md") is None

    def test_inventory_kind_of_returns_none_for_an_unknown_path(self) -> None:
        assert DocumentationInventory().kind_of("README.md") is None

    # --- defaults ---

    def test_inventory_skipped_reason_defaults_to_none(self) -> None:
        assert DocumentationInventory().skipped_reason is None

    def test_inventory_dict_defaults_are_not_shared_between_instances(self) -> None:
        assert (
            DocumentationInventory().root_documents is not DocumentationInventory().root_documents
        )
