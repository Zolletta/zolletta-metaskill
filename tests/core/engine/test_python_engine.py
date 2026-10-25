"""Comprehensive tests for :class:`PythonEngine`."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.core.engine.language_engine import LanguageEngine
from zolletta_metaskill.core.engine.python_engine import PythonEngine
from zolletta_metaskill.core.structs import ClassInfo, MethodInfo, ModuleInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, source: str) -> Path:
    """Write *source* to *tmp_path*/*name* and return the path."""
    p = tmp_path / name
    p.write_text(source, encoding="utf-8")
    return p


def _classes(info: ModuleInfo) -> dict[str, ClassInfo]:
    return {c.name: c for c in info.classes}


def _functions(info: ModuleInfo) -> dict[str, MethodInfo]:
    return {f.name: f for f in info.functions}


class TestPythonEngine:
    # --- Protocol conformance ---

    def test_is_language_engine(self) -> None:
        assert isinstance(PythonEngine(), LanguageEngine)

    def test_pythonengine_language_property_returns_python(self) -> None:
        assert PythonEngine().language == "python"

    # --- parse_module — classes ---

    def test_simple_class_with_methods(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    def bar(self):\n        pass\n    def baz(self):\n        pass\n",
        )
        info = PythonEngine().parse_module(path)
        classes = _classes(info)
        assert "Foo" in classes
        cls = classes["Foo"]
        assert cls.bases == []
        assert cls.is_abstract is False
        assert cls.is_test_class is False
        assert {m.name for m in cls.methods} == {"bar", "baz"}

    def test_class_with_bases(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "class Bar(Foo, Mixin):\n    pass\n")
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Bar"]
        assert cls.bases == ["Foo", "Mixin"]

    def test_abstract_class_abc(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "class Base(ABC):\n    pass\n")
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Base"]
        assert cls.is_abstract is True

    def test_abstract_class_protocol(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "class Proto(Protocol):\n    pass\n")
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Proto"]
        assert cls.is_abstract is True

    def test_write_test_class_returns_true(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "class TestSomething:\n    pass\n")
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["TestSomething"]
        assert cls.is_test_class is True

    def test_class_with_instance_attributes(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def __init__(self):\n"
            "        self.x = 1\n"
            "        self.y = 2\n"
            "    def set_z(self):\n"
            "        self.z = 3\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        assert cls.attributes == ["x", "y", "z"]

    def test_class_method_with_local_variable_assignment(self, tmp_path: Path) -> None:
        """Local variable assignments inside methods are not self attributes."""
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    def bar(self):\n        local = 1\n        self.value = local\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        # Only self.value is an attribute; local is not.
        assert cls.attributes == ["value"]

    def test_class_with_static_method(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    @staticmethod\n    def helper(a):\n        return a\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        m = next(meth for meth in cls.methods if meth.name == "helper")
        assert m.is_static is True
        assert m.params == ["a"]

    def test_class_with_private_method(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def _private(self):\n"
            "        pass\n"
            "    def public(self):\n"
            "        pass\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        priv = next(m for m in cls.methods if m.name == "_private")
        pub = next(m for m in cls.methods if m.name == "public")
        assert priv.is_public is False
        assert pub.is_public is True

    def test_classmethod_is_not_static(self, tmp_path: Path) -> None:
        """A ``@classmethod`` decorator is a Name but not ``staticmethod``."""
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    @classmethod\n    def make(cls):\n        pass\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        m = next(meth for meth in cls.methods if meth.name == "make")
        assert m.is_static is False

    def test_class_attributes_after_class_level_assignment(self, tmp_path: Path) -> None:
        """A class-level constant must not stop ``self.x`` attribute collection."""
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    CONST = 1\n    def __init__(self):\n        self.x = 1\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        assert cls.attributes == ["x"]

    def test_class_attributes_deduplicated(self, tmp_path: Path) -> None:
        """The same ``self.x`` assigned in two methods is reported once."""
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def __init__(self):\n"
            "        self.x = 1\n"
            "    def reset(self):\n"
            "        self.x = 0\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        assert cls.attributes == ["x"]

    def test_class_with_async_method(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    async def fetch(self):\n        pass\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        assert any(m.name == "fetch" for m in cls.methods)

    def test_class_with_return_type_annotation(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    def bar(self) -> int:\n        return 1\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        m = next(meth for meth in cls.methods if meth.name == "bar")
        assert m.return_type == "int"

    def test_class_with_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    def bar(self):\n        raise ValueError('bad')\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        m = next(meth for meth in cls.methods if meth.name == "bar")
        assert m.raises == ["ValueError"]

    def test_class_with_bare_raise(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n    def bar(self):\n        raise ValueError\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        m = next(meth for meth in cls.methods if meth.name == "bar")
        assert m.raises == ["ValueError"]

    def test_class_lineno_and_end_lineno(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "\n\nclass Foo:\n    def bar(self):\n        pass\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        assert cls.lineno == 3
        assert cls.end_lineno == 5

    # --- parse_module — functions ---

    def test_module_level_function(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def foo(a, b):\n    return a + b\n")
        info = PythonEngine().parse_module(path)
        funcs = _functions(info)
        assert "foo" in funcs
        assert funcs["foo"].params == ["a", "b"]

    def test_function_excludes_self_and_cls(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "def foo(self, cls, x):\n    pass\n",
        )
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.params == ["x"]

    def test_function_counts_posonly_and_kwonly_params(self, tmp_path: Path) -> None:
        """Posonlyargs and kwonlyargs count toward params (PLR0913 parity)."""
        path = _write(tmp_path, "mod.py", "def foo(a, /, b, *, c, d):\n    pass\n")
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.params == ["a", "b", "c", "d"]

    def test_function_excludes_vararg_and_kwarg(self, tmp_path: Path) -> None:
        """*args/** kwargs are variadics, not counted parameters."""
        path = _write(tmp_path, "mod.py", "def foo(a, *args, b, **kwargs):\n    pass\n")
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.params == ["a", "b"]

    def test_method_excludes_self_and_cls_among_kwonly(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def bar(self, a, *, b):\n"
            "        pass\n"
            "    @classmethod\n"
            "    def make(cls, x, *, y):\n"
            "        pass\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        bar = next(m for m in cls.methods if m.name == "bar")
        make = next(m for m in cls.methods if m.name == "make")
        assert bar.params == ["a", "b"]
        assert make.params == ["x", "y"]

    def test_function_with_return_type(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def foo() -> str:\n    return 'hi'\n")
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.return_type == "str"

    def test_function_that_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "def foo():\n    raise RuntimeError('boom')\n",
        )
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.raises == ["RuntimeError"]

    def test_write_private_function_returns_false(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def _helper():\n    pass\n")
        info = PythonEngine().parse_module(path)
        f = _functions(info)["_helper"]
        assert f.is_public is False

    def test_write_async_function_contains_fetch(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "async def fetch():\n    pass\n")
        info = PythonEngine().parse_module(path)
        assert "fetch" in _functions(info)

    def test_function_no_return_annotation(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def foo():\n    pass\n")
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.return_type is None

    def test_function_multiple_raises_dedup(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "def foo():\n    raise ValueError('a')\n    raise ValueError('b')\n",
        )
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.raises == ["ValueError"]

    # --- parse_module — imports ---

    def test_write_import_simple_returns_false(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "import os\n")
        info = PythonEngine().parse_module(path)
        imp = info.imports[0]
        assert imp.module == "os"
        assert imp.names == ["os"]
        assert imp.is_relative is False

    def test_write_import_dotted_returns_single_item(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "import os.path\n")
        info = PythonEngine().parse_module(path)
        imp = info.imports[0]
        assert imp.module == "os.path"
        assert imp.names == ["os.path"]

    def test_from_import_multiple(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "from os import path, getenv\n")
        info = PythonEngine().parse_module(path)
        imp = info.imports[0]
        assert imp.module == "os"
        assert imp.names == ["path", "getenv"]
        assert imp.is_relative is False

    def test_relative_import_dot(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "from . import foo\n")
        info = PythonEngine().parse_module(path)
        imp = info.imports[0]
        assert imp.is_relative is True
        assert imp.module == ""
        assert imp.names == ["foo"]

    def test_relative_import_double_dot(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "from ..foo import bar\n")
        info = PythonEngine().parse_module(path)
        imp = info.imports[0]
        assert imp.is_relative is True
        assert imp.module == "foo"
        assert imp.names == ["bar"]

    def test_write_import_lineno_returns_3(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "\n\nimport os\n")
        info = PythonEngine().parse_module(path)
        assert info.imports[0].lineno == 3

    # --- parse_module — __all__ ---

    def test_write_all_exports_returns_multiple_items(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", '__all__ = ["Foo", "Bar"]\n')
        info = PythonEngine().parse_module(path)
        assert info.all_exports == ["Foo", "Bar"]

    def test_no_all_exports(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.all_exports is None

    def test_all_exports_tuple_not_collected(self, tmp_path: Path) -> None:
        """A tuple ``__all__`` is not recognised (only lists are)."""
        path = _write(tmp_path, "mod.py", '__all__ = ("Foo", "Bar")\n')
        info = PythonEngine().parse_module(path)
        assert info.all_exports is None

    def test_all_exports_non_string_element_skipped(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", '__all__ = ["Foo", other_name]\n')
        info = PythonEngine().parse_module(path)
        assert info.all_exports == ["Foo"]

    def test_non_all_list_assignment_is_not_exports(self, tmp_path: Path) -> None:
        """``x = [1]`` has a Name target but is not ``__all__``."""
        path = _write(tmp_path, "mod.py", "x = [1]\n")
        info = PythonEngine().parse_module(path)
        assert info.all_exports is None

    # --- parse_module — docstring ---

    def test_module_with_docstring(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", '"""Module doc."""\n\nx = 1\n')
        info = PythonEngine().parse_module(path)
        assert info.docstring == "Module doc."

    def test_module_without_docstring(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.docstring is None

    def test_module_expression_first_statement_docstring_none(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", 'print("hi")\n\nx = 1\n')
        info = PythonEngine().parse_module(path)
        assert info.docstring is None

    # --- parse_module — syntax errors ---

    def test_write_syntax_error_returns_empty_list(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def foo(:\n    pass\n")
        info = PythonEngine().parse_module(path)
        assert info.has_syntax_error is True
        assert info.classes == []
        assert info.functions == []
        assert info.imports == []

    def test_syntax_error_preserves_path_and_language(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def foo(:\n    pass\n")
        info = PythonEngine().parse_module(path)
        assert info.path == path
        assert info.language == "python"

    def test_parse_module_nonexistent_file_returns_empty_list(self, tmp_path: Path) -> None:
        info = PythonEngine().parse_module(tmp_path / "nope.py")
        assert info.has_syntax_error is True
        assert info.classes == []

    def test_parse_module_missing_file_preserves_path_and_language(self, tmp_path: Path) -> None:
        path = tmp_path / "nope.py"
        info = PythonEngine().parse_module(path)
        assert info.path == path
        assert info.language == "python"

    # --- parse_module — edge cases ---

    def test_write_empty_file_returns_none(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "")
        info = PythonEngine().parse_module(path)
        assert info.has_syntax_error is False
        assert info.classes == []
        assert info.functions == []
        assert info.imports == []
        assert info.docstring is None

    def test_write_only_imports_returns_empty_list(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "import os\nfrom os import path\n")
        info = PythonEngine().parse_module(path)
        assert len(info.imports) == 2
        assert info.classes == []
        assert info.functions == []

    def test_write_only_class_returns_empty_list(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "class Foo:\n    pass\n")
        info = PythonEngine().parse_module(path)
        assert len(info.classes) == 1
        assert info.functions == []
        assert info.imports == []

    # --- file_extensions / test_file_glob ---

    def test_file_extensions_file_extensions_returns_single_item(self) -> None:
        assert PythonEngine().file_extensions() == [".py"]

    # --- ModuleInfo basics ---

    def test_write_language_field_returns_path(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.language == "python"
        assert info.path == path

    def test_has_syntax_error_false_on_valid(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.has_syntax_error is False

    # --- dataclass detection ---

    def test_dataclass_fields_collected_returns_true(self, tmp_path: Path) -> None:
        src = (
            "from dataclasses import dataclass, field\n\n"
            "@dataclass(frozen=True)\n"
            "class Point:\n"
            "    x: int\n"
            "    y: int = 0\n"
            "    tags: list = field(default_factory=list)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        info = PythonEngine().parse_module(path)
        cls = info.classes[0]
        assert cls.is_dataclass is True
        assert cls.dataclass_fields == ["x", "y", "tags"]

    def test_bare_dataclass_decorator_detected(self, tmp_path: Path) -> None:
        src = "from dataclasses import dataclass\n\n@dataclass\nclass A:\n    a: int\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is True
        assert cls.dataclass_fields == ["a"]

    def test_plain_class_is_dataclass_false(self, tmp_path: Path) -> None:
        src = "class Plain:\n    x = 1\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is False
        assert cls.dataclass_fields == []

    def test_qualified_dataclass_decorator_detected(self, tmp_path: Path) -> None:
        src = "import dataclasses\n\n@dataclasses.dataclass\nclass A:\n    a: int\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is True
        assert cls.dataclass_fields == ["a"]

    def test_qualified_dataclass_call_detected(self, tmp_path: Path) -> None:
        src = "import dataclasses\n\n@dataclasses.dataclass(frozen=True)\nclass A:\n    a: int\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is True
        assert cls.dataclass_fields == ["a"]

    def test_attribute_decorator_not_dataclass(self, tmp_path: Path) -> None:
        """``@attr.s`` is an Attribute decorator whose attr is not ``dataclass``."""
        src = "import attr\n\n@attr.s\nclass A:\n    a: int\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is False

    def test_call_decorator_name_not_dataclass(self, tmp_path: Path) -> None:
        """``@register()`` calls a Name that is not ``dataclass``."""
        src = "@register()\nclass A:\n    a: int\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is False

    def test_call_decorator_attribute_not_dataclass(self, tmp_path: Path) -> None:
        """``@mod.register()`` calls an Attribute that is not ``dataclass``."""
        src = "import mod\n\n@mod.register()\nclass A:\n    a: int\n"
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is False

    def test_dataclass_fields_exclude_plain_assignments(self, tmp_path: Path) -> None:
        """Only annotated names are dataclass fields — ``CONST = 1`` is not."""
        src = (
            "from dataclasses import dataclass\n\n@dataclass\nclass A:\n    x: int\n    CONST = 1\n"
        )
        path = _write(tmp_path, "mod.py", src)
        cls = PythonEngine().parse_module(path).classes[0]
        assert cls.is_dataclass is True
        assert cls.dataclass_fields == ["x"]
