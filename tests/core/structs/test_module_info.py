"""Tests for the ModuleInfo dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from zolletta_metaskill.core.structs import ClassInfo, ImportInfo, MethodInfo, ModuleInfo


class TestModuleInfo:
    """Tests for the ModuleInfo dataclass."""

    def test_moduleinfo_minimal_construction_returns_false(self) -> None:
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

    def test_classinfo_full_construction_returns_false(self) -> None:
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

    def test_moduleinfo_frozen_raises_frozeninstanceerror(self) -> None:
        """ModuleInfo is immutable."""
        mi = ModuleInfo(path=Path("/tmp/foo.py"), language="python")
        with pytest.raises(FrozenInstanceError):
            setattr(mi, "language", "php")

    def test_default_lists_are_independent(self) -> None:
        """Each instance gets its own default list."""
        mi1 = ModuleInfo(path=Path("/a.py"), language="python")
        mi2 = ModuleInfo(path=Path("/b.py"), language="python")
        mi1.classes.append(ClassInfo(name="A", lineno=1, end_lineno=2))
        assert mi2.classes == []
