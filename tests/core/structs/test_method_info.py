"""Tests for the MethodInfo dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from zolletta_metaskill.core.structs import MethodInfo


class TestMethodInfo:
    """Tests for the MethodInfo dataclass."""

    def test_methodinfo_minimal_construction_returns_empty_list(self) -> None:
        """MethodInfo can be constructed with only required fields."""
        m = MethodInfo(name="foo", lineno=1, end_lineno=5)
        assert m.name == "foo"
        assert m.lineno == 1
        assert m.end_lineno == 5
        assert m.params == []
        assert m.is_public is True
        assert m.is_static is False
        assert m.return_type is None
        assert m.raises == []

    def test_methodinfo_full_construction_returns_multiple_items(self) -> None:
        """MethodInfo accepts all fields."""
        m = MethodInfo(
            name="bar",
            lineno=10,
            end_lineno=20,
            params=["a", "b"],
            is_public=False,
            is_static=True,
            return_type="int",
            raises=["ValueError", "TypeError"],
        )
        assert m.name == "bar"
        assert m.params == ["a", "b"]
        assert m.is_public is False
        assert m.is_static is True
        assert m.return_type == "int"
        assert m.raises == ["ValueError", "TypeError"]

    def test_methodinfo_frozen_raises_frozeninstanceerror(self) -> None:
        """MethodInfo is immutable."""
        m = MethodInfo(name="foo", lineno=1, end_lineno=5)
        with pytest.raises(FrozenInstanceError):
            setattr(m, "name", "bar")

    def test_default_lists_are_independent(self) -> None:
        """Each instance gets its own default list (no shared mutable default)."""
        m1 = MethodInfo(name="a", lineno=1, end_lineno=2)
        m2 = MethodInfo(name="b", lineno=3, end_lineno=4)
        m1.params.append("x")
        assert m2.params == []

    def test_methodinfo_equality_returns_m2(self) -> None:
        """Two MethodInfos with the same fields are equal."""
        m1 = MethodInfo(name="foo", lineno=1, end_lineno=5)
        m2 = MethodInfo(name="foo", lineno=1, end_lineno=5)
        assert m1 == m2

    def test_methodinfo_inequality_succeeds(self) -> None:
        """MethodInfos with different fields are not equal."""
        m1 = MethodInfo(name="foo", lineno=1, end_lineno=5)
        m2 = MethodInfo(name="bar", lineno=1, end_lineno=5)
        assert m1 != m2
