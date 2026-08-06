"""Tests for the ClassInfo dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from zolletta_metaskill.core.structs import ClassInfo, MethodInfo


class TestClassInfo:
    """Tests for the ClassInfo dataclass."""

    def test_classinfo_minimal_construction_returns_false(self) -> None:
        """ClassInfo can be constructed with only required fields."""
        c = ClassInfo(name="Foo", lineno=1, end_lineno=10)
        assert c.name == "Foo"
        assert c.lineno == 1
        assert c.end_lineno == 10
        assert c.methods == []
        assert c.bases == []
        assert c.attributes == []
        assert c.is_abstract is False
        assert c.is_test_class is False

    def test_methodinfo_full_construction_returns_true(self) -> None:
        """ClassInfo accepts all fields."""
        m = MethodInfo(name="method", lineno=2, end_lineno=3)
        c = ClassInfo(
            name="Bar",
            lineno=1,
            end_lineno=20,
            methods=[m],
            bases=["Base"],
            attributes=["x", "y"],
            is_abstract=True,
            is_test_class=True,
        )
        assert c.methods == [m]
        assert c.bases == ["Base"]
        assert c.attributes == ["x", "y"]
        assert c.is_abstract is True
        assert c.is_test_class is True

    def test_classinfo_frozen_raises_frozeninstanceerror(self) -> None:
        """ClassInfo is immutable."""
        c = ClassInfo(name="Foo", lineno=1, end_lineno=10)
        with pytest.raises(FrozenInstanceError):
            setattr(c, "name", "Bar")

    def test_default_lists_are_independent(self) -> None:
        """Each instance gets its own default list."""
        c1 = ClassInfo(name="A", lineno=1, end_lineno=2)
        c2 = ClassInfo(name="B", lineno=3, end_lineno=4)
        c1.methods.append(MethodInfo(name="m", lineno=1, end_lineno=1))
        assert c2.methods == []
