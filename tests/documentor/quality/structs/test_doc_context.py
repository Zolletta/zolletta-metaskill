"""Tests for doc_context.py."""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pytest

from zolletta_metaskill.documentor.quality.structs.doc_context import DocContext


class TestDocContext:
    # --- file_parent_dir: the derived field ---

    def test_file_parent_dir_nested_doc_returns_containing_folder(self) -> None:
        ctx = DocContext(file_rel_path="docs/explanation/adr/0015-standard-script-cli.md")
        assert ctx.file_parent_dir == "docs/explanation/adr"

    def test_file_parent_dir_shallow_doc_returns_folder(self) -> None:
        ctx = DocContext(file_rel_path="docs/reference/settings-schema.md")
        assert ctx.file_parent_dir == "docs/reference"

    def test_file_parent_dir_root_doc_returns_empty_string(self) -> None:
        """dirname('README.md') is '' — not '.'. Callers use os.path.join."""
        ctx = DocContext(file_rel_path="README.md")
        assert ctx.file_parent_dir == ""

    def test_file_parent_dir_empty_parent_joins_correctly(self) -> None:
        ctx = DocContext(file_rel_path="README.md")
        assert os.path.join("/repo", ctx.file_parent_dir, "src") == "/repo/src"

    def test_file_parent_dir_is_not_stored_so_cannot_drift(self) -> None:
        """The field is derived, so a mismatched parent is unrepresentable."""
        ctx = DocContext(file_rel_path="docs/reference/tools.md")
        assert "file_parent_dir" not in {f.name for f in dataclasses.fields(ctx)}
        assert isinstance(DocContext.file_parent_dir, property)

    def test_file_parent_dir_recomputes_when_path_changes(self) -> None:
        """A frozen dataclass cannot change it — assert the derivation is live."""
        ctx = DocContext(file_rel_path="a/b/c.md")
        assert ctx.file_parent_dir == os.path.dirname("a/b/c.md")

    # --- Construction ---

    def test_file_rel_path_only_gets_defaults(self) -> None:
        ctx = DocContext(file_rel_path="docs/x.md")
        assert ctx.file_rel_path == "docs/x.md"
        assert ctx.refs == {}
        assert ctx.since_date == ""
        assert ctx.associated_code_dirs == ()

    def test_all_fields_are_stored(self) -> None:
        ctx = DocContext(
            file_rel_path="docs/x.md",
            refs={"files": ["a.py"], "functions": set()},
            since_date="2026-01-01",
            associated_code_dirs=("src",),
        )
        assert ctx.refs["files"] == ["a.py"]
        assert ctx.since_date == "2026-01-01"
        assert ctx.associated_code_dirs == ("src",)

    # --- Immutability ---

    def test_doc_context_assign_field_when_frozen_raises(self) -> None:
        ctx = DocContext(file_rel_path="docs/x.md")
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(ctx, "file_rel_path", "other.md")

    def test_refs_default_is_not_shared_between_instances(self) -> None:
        """A mutable default on a frozen dataclass would leak across instances."""
        first = DocContext(file_rel_path="a.md")
        second = DocContext(file_rel_path="b.md")
        assert first.refs is not second.refs
        first.refs["files"] = ["leaked.py"]
        assert second.refs == {}

    # --- Relationship to the docs root ---

    def test_file_parent_dir_differs_from_documentation_dir(self) -> None:
        """Why the naming matters: the two are two levels apart here.

        ``documentation.dir`` is 'docs'; the parent of a doc inside
        docs/explanation/adr/ is 'docs/explanation/adr'. Conflating them would
        make reference resolution look in the wrong place.
        """
        documentation_dir = Path("docs")
        ctx = DocContext(file_rel_path="docs/explanation/adr/0015-standard-script-cli.md")
        assert ctx.file_parent_dir != str(documentation_dir)
        assert Path(ctx.file_parent_dir).is_relative_to(documentation_dir)
