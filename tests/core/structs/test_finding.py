"""Tests for the Finding dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from zolletta_metaskill.core.structs import Finding


class TestFinding:
    """Tests for the Finding dataclass."""

    def test_construction_with_defaults(self) -> None:
        """Finding uses default fix_type when not specified."""
        f = Finding(
            file="/tmp/foo.py",
            line=10,
            category="naming",
            severity="high",
            description="Bad name.",
        )
        assert f.file == "/tmp/foo.py"
        assert f.line == 10
        assert f.category == "naming"
        assert f.severity == "high"
        assert f.description == "Bad name."
        assert f.fix_type == "manual"

    def test_construction_with_fix_type(self) -> None:
        """Finding accepts a custom fix_type."""
        f = Finding(
            file="/tmp/foo.py",
            line=10,
            category="naming",
            severity="high",
            description="Bad name.",
            fix_type="auto",
        )
        assert f.fix_type == "auto"

    def test_finding_frozen_raises_frozeninstanceerror(self) -> None:
        """Finding is immutable."""
        f = Finding(
            file="/tmp/foo.py",
            line=10,
            category="naming",
            severity="high",
            description="Bad name.",
        )
        with pytest.raises(FrozenInstanceError):
            setattr(f, "line", 20)

    def test_finding_equality_returns_f2(self) -> None:
        """Two Findings with the same fields are equal."""
        f1 = Finding(file="a.py", line=1, category="x", severity="low", description="d")
        f2 = Finding(file="a.py", line=1, category="x", severity="low", description="d")
        assert f1 == f2
