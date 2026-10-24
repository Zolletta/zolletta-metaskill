"""Tests for the SourceSignature dataclass."""

from __future__ import annotations

from typing import Any

from zolletta_metaskill.documentor.structs.source_signature import SourceSignature


class TestSourceSignature:
    """Tests for the SourceSignature dataclass."""

    # --- construction ---

    def test_construction_with_defaults(self) -> None:
        """SourceSignature sets default values properly."""
        sig = SourceSignature(
            name="foo",
            kind="function",
            file_path="foo.py",
            line_number=10,
            parameters=[],
        )
        assert sig.name == "foo"
        assert sig.kind == "function"
        assert sig.file_path == "foo.py"
        assert sig.line_number == 10
        assert sig.parameters == []
        assert sig.return_annotation is None
        assert sig.decorators == []
        assert sig.docstring is None
        assert not sig.is_private
        assert sig.parent_class is None
        assert sig.qualified_name == "foo"
        assert not sig.is_deprecated

    def test_none_decorators_becomes_empty_list(self) -> None:
        """__post_init__ replaces an explicitly passed None decorators with an empty list.

        The kwargs go through a ``dict[str, Any]`` because passing ``None`` for a
        ``list[str]`` field is exactly what an untyped caller does at runtime, and
        the guard exists for that case. Going via the dict keeps the test honest
        without a type-checker suppression.
        """
        kwargs: dict[str, Any] = {
            "name": "foo",
            "kind": "function",
            "file_path": "foo.py",
            "line_number": 10,
            "parameters": [],
            "decorators": None,
        }
        sig = SourceSignature(**kwargs)
        assert sig.decorators == []
        assert not sig.is_deprecated

    # --- derived attributes ---

    def test_qualified_name_with_parent_class(self) -> None:
        """qualified_name includes parent class if present."""
        sig = SourceSignature(
            name="bar",
            kind="method",
            file_path="bar.py",
            line_number=20,
            parameters=[],
            parent_class="MyClass",
        )
        assert sig.qualified_name == "MyClass.bar"

    def test_source_signature_is_deprecated_when_decorator_present(self) -> None:
        """is_deprecated checks for 'deprecated' in decorators."""
        sig = SourceSignature(
            name="old",
            kind="function",
            file_path="old.py",
            line_number=30,
            parameters=[],
            decorators=["deprecated", "override"],
        )
        assert sig.is_deprecated

    # --- serialization ---

    def test_source_signature_to_dict_serializes_all_keys(self) -> None:
        """to_dict serializes all expected keys."""
        sig = SourceSignature(
            name="helper",
            kind="function",
            file_path="helper.py",
            line_number=40,
            parameters=[{"name": "x", "type": "int"}],
            return_annotation="str",
            decorators=["staticmethod"],
            docstring="Helpful.",
            is_private=True,
            parent_class="Worker",
        )
        d = sig.to_dict()
        assert d["name"] == "helper"
        assert d["qualified_name"] == "Worker.helper"
        assert d["kind"] == "function"
        assert d["file"] == "helper.py"
        assert d["line"] == 40
        assert d["parameters"] == [{"name": "x", "type": "int"}]
        assert d["return_annotation"] == "str"
        assert d["decorators"] == ["staticmethod"]
        assert d["is_private"] is True
        assert d["is_deprecated"] is False
