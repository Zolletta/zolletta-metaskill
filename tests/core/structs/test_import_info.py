"""Tests for the ImportInfo dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from zolletta_metaskill.core.structs import ImportInfo


class TestImportInfo:
    """Tests for the ImportInfo dataclass."""

    def test_importinfo_minimal_construction_returns_false(self) -> None:
        """ImportInfo can be constructed with only the module name."""
        imp = ImportInfo(module="os.path")
        assert imp.module == "os.path"
        assert imp.names == []
        assert imp.lineno == 0
        assert imp.is_relative is False

    def test_importinfo_full_construction_returns_true(self) -> None:
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

    def test_importinfo_frozen_raises_frozeninstanceerror(self) -> None:
        """ImportInfo is immutable."""
        imp = ImportInfo(module="os")
        with pytest.raises(FrozenInstanceError):
            setattr(imp, "module", "sys")
