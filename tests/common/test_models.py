"""Tests for zolletta_metaskill.common.models — dataclass construction and immutability."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from zolletta_metaskill.common.models import (
    ClassInfo,
    Finding,
    ImportInfo,
    MethodInfo,
    ModuleInfo,
)


class TestMethodInfo:
    """Tests for the MethodInfo dataclass."""

    def test_minimal_construction(self) -> None:
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

    def test_full_construction(self) -> None:
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

    def test_frozen(self) -> None:
        """MethodInfo is immutable."""
        m = MethodInfo(name="foo", lineno=1, end_lineno=5)
        with pytest.raises(FrozenInstanceError):
            m.name = "bar"  # type: ignore[misc]

    def test_default_lists_are_independent(self) -> None:
        """Each instance gets its own default list (no shared mutable default)."""
        m1 = MethodInfo(name="a", lineno=1, end_lineno=2)
        m2 = MethodInfo(name="b", lineno=3, end_lineno=4)
        m1.params.append("x")
        assert m2.params == []

    def test_equality(self) -> None:
        """Two MethodInfos with the same fields are equal."""
        m1 = MethodInfo(name="foo", lineno=1, end_lineno=5)
        m2 = MethodInfo(name="foo", lineno=1, end_lineno=5)
        assert m1 == m2

    def test_inequality(self) -> None:
        """MethodInfos with different fields are not equal."""
        m1 = MethodInfo(name="foo", lineno=1, end_lineno=5)
        m2 = MethodInfo(name="bar", lineno=1, end_lineno=5)
        assert m1 != m2


class TestClassInfo:
    """Tests for the ClassInfo dataclass."""

    def test_minimal_construction(self) -> None:
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

    def test_full_construction(self) -> None:
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

    def test_frozen(self) -> None:
        """ClassInfo is immutable."""
        c = ClassInfo(name="Foo", lineno=1, end_lineno=10)
        with pytest.raises(FrozenInstanceError):
            c.name = "Bar"  # type: ignore[misc]

    def test_default_lists_are_independent(self) -> None:
        """Each instance gets its own default list."""
        c1 = ClassInfo(name="A", lineno=1, end_lineno=2)
        c2 = ClassInfo(name="B", lineno=3, end_lineno=4)
        c1.methods.append(MethodInfo(name="m", lineno=1, end_lineno=1))
        assert c2.methods == []


class TestImportInfo:
    """Tests for the ImportInfo dataclass."""

    def test_minimal_construction(self) -> None:
        """ImportInfo can be constructed with only the module name."""
        imp = ImportInfo(module="os.path")
        assert imp.module == "os.path"
        assert imp.names == []
        assert imp.lineno == 0
        assert imp.is_relative is False

    def test_full_construction(self) -> None:
        """ImportInfo accepts all fields."""
        imp = ImportInfo(
            module="os",
            names=["path", "getenv"],
            lineno=5,
            is_relative=True,
        )
        assert imp.names == ["path", "getenv"]
        assert imp.lineno == 5
        assert imp.is_relative is True

    def test_frozen(self) -> None:
        """ImportInfo is immutable."""
        imp = ImportInfo(module="os")
        with pytest.raises(FrozenInstanceError):
            imp.module = "sys"  # type: ignore[misc]


class TestModuleInfo:
    """Tests for the ModuleInfo dataclass."""

    def test_minimal_construction(self) -> None:
        """ModuleInfo can be constructed with only path and language."""
        mi = ModuleInfo(path=Path("/tmp/foo.py"), language="python")
        assert mi.path == Path("/tmp/foo.py")
        assert mi.language == "python"
        assert mi.classes == []
        assert mi.imports == []
        assert mi.functions == []
        assert mi.all_exports is None
        assert mi.docstring is None
        assert mi.has_syntax_error is False

    def test_full_construction(self) -> None:
        """ModuleInfo accepts all fields."""
        cls = ClassInfo(name="Foo", lineno=1, end_lineno=10)
        imp = ImportInfo(module="os", lineno=1)
        fn = MethodInfo(name="main", lineno=1, end_lineno=5)
        mi = ModuleInfo(
            path=Path("/tmp/foo.py"),
            language="python",
            classes=[cls],
            imports=[imp],
            functions=[fn],
            all_exports=["Foo"],
            docstring="A module.",
            has_syntax_error=False,
        )
        assert mi.classes == [cls]
        assert mi.imports == [imp]
        assert mi.functions == [fn]
        assert mi.all_exports == ["Foo"]
        assert mi.docstring == "A module."
        assert mi.has_syntax_error is False

    def test_frozen(self) -> None:
        """ModuleInfo is immutable."""
        mi = ModuleInfo(path=Path("/tmp/foo.py"), language="python")
        with pytest.raises(FrozenInstanceError):
            mi.language = "php"  # type: ignore[misc]

    def test_default_lists_are_independent(self) -> None:
        """Each instance gets its own default list."""
        mi1 = ModuleInfo(path=Path("/a.py"), language="python")
        mi2 = ModuleInfo(path=Path("/b.py"), language="python")
        mi1.classes.append(ClassInfo(name="A", lineno=1, end_lineno=2))
        assert mi2.classes == []


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

    def test_frozen(self) -> None:
        """Finding is immutable."""
        f = Finding(
            file="/tmp/foo.py",
            line=10,
            category="naming",
            severity="high",
            description="Bad name.",
        )
        with pytest.raises(FrozenInstanceError):
            f.line = 20  # type: ignore[misc]

    def test_equality(self) -> None:
        """Two Findings with the same fields are equal."""
        f1 = Finding(file="a.py", line=1, category="x", severity="low", description="d")
        f2 = Finding(file="a.py", line=1, category="x", severity="low", description="d")
        assert f1 == f2
