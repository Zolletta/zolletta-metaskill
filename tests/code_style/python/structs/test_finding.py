"""Tests for Finding data model."""

from __future__ import annotations

import ast
from pathlib import Path

from zolletta_metaskill.code_style.python.structs.finding import Finding


class TestFindingCreation:
    """Tests for Finding dataclass creation and field access."""

    def test_finding_with_required_fields_returns_finding(self) -> None:
        """Finding stores all required fields correctly."""
        node = ast.parse("x = 1").body[0]
        finding = Finding(
            file=Path("/tmp/foo.py"),
            line=10,
            kind="redundant_args",
            detail="Args section is redundant",
            node=node,
        )
        assert finding.file == Path("/tmp/foo.py")
        assert finding.line == 10
        assert finding.kind == "redundant_args"
        assert finding.detail == "Args section is redundant"
        assert finding.node is node
        assert finding.new_text is None
        assert finding.remove is False

    def test_finding_with_new_text_returns_new_text(self) -> None:
        """Finding accepts new_text for streamlined docstrings."""
        node = ast.parse("x = 1").body[0]
        finding = Finding(
            file=Path("/tmp/foo.py"),
            line=5,
            kind="redundant_returns",
            detail="Returns section is redundant",
            node=node,
            new_text='"""Summary."""',
        )
        assert finding.new_text == '"""Summary."""'

    def test_finding_with_remove_true_returns_remove(self) -> None:
        """Finding accepts remove=True to mark docstring for deletion."""
        node = ast.parse("x = 1").body[0]
        finding = Finding(
            file=Path("/tmp/foo.py"),
            line=3,
            kind="obsolete",
            detail="Docstring is obsolete",
            node=node,
            remove=True,
        )
        assert finding.remove is True
