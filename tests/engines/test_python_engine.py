"""Comprehensive tests for :class:`PythonEngine`."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.common.language_engine import LanguageEngine
from zolletta_metaskill.common.models import ClassInfo, MethodInfo, ModuleInfo
from zolletta_metaskill.engines.python_engine import PythonEngine

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


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_is_language_engine(self) -> None:
        assert isinstance(PythonEngine(), LanguageEngine)

    def test_language_property(self) -> None:
        assert PythonEngine().language == "python"


# ---------------------------------------------------------------------------
# parse_module — classes
# ---------------------------------------------------------------------------


class TestParseClasses:
    def test_simple_class_with_methods(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def bar(self):\n"
            "        pass\n"
            "    def baz(self):\n"
            "        pass\n",
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

    def test_test_class(self, tmp_path: Path) -> None:
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

    def test_class_with_static_method(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    @staticmethod\n"
            "    def helper(a):\n"
            "        return a\n",
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

    def test_class_with_async_method(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    async def fetch(self):\n"
            "        pass\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        assert any(m.name == "fetch" for m in cls.methods)

    def test_class_with_return_type_annotation(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def bar(self) -> int:\n"
            "        return 1\n",
        )
        info = PythonEngine().parse_module(path)
        cls = _classes(info)["Foo"]
        m = next(meth for meth in cls.methods if meth.name == "bar")
        assert m.return_type == "int"

    def test_class_with_raises(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "mod.py",
            "class Foo:\n"
            "    def bar(self):\n"
            "        raise ValueError('bad')\n",
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
        assert cls.end_lineno >= cls.lineno


# ---------------------------------------------------------------------------
# parse_module — functions
# ---------------------------------------------------------------------------


class TestParseFunctions:
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

    def test_private_function(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def _helper():\n    pass\n")
        info = PythonEngine().parse_module(path)
        f = _functions(info)["_helper"]
        assert f.is_public is False

    def test_async_function(self, tmp_path: Path) -> None:
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
            "def foo():\n"
            "    raise ValueError('a')\n"
            "    raise ValueError('b')\n",
        )
        info = PythonEngine().parse_module(path)
        f = _functions(info)["foo"]
        assert f.raises == ["ValueError"]


# ---------------------------------------------------------------------------
# parse_module — imports
# ---------------------------------------------------------------------------


class TestParseImports:
    def test_import_simple(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "import os\n")
        info = PythonEngine().parse_module(path)
        imp = info.imports[0]
        assert imp.module == "os"
        assert imp.names == ["os"]
        assert imp.is_relative is False

    def test_import_dotted(self, tmp_path: Path) -> None:
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

    def test_import_lineno(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "\n\nimport os\n")
        info = PythonEngine().parse_module(path)
        assert info.imports[0].lineno == 3


# ---------------------------------------------------------------------------
# parse_module — __all__
# ---------------------------------------------------------------------------


class TestAllExports:
    def test_all_exports(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", '__all__ = ["Foo", "Bar"]\n')
        info = PythonEngine().parse_module(path)
        assert info.all_exports == ["Foo", "Bar"]

    def test_no_all_exports(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.all_exports is None


# ---------------------------------------------------------------------------
# parse_module — docstring
# ---------------------------------------------------------------------------


class TestDocstring:
    def test_module_with_docstring(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", '"""Module doc."""\n\nx = 1\n')
        info = PythonEngine().parse_module(path)
        assert info.docstring == "Module doc."

    def test_module_without_docstring(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.docstring is None


# ---------------------------------------------------------------------------
# parse_module — syntax errors
# ---------------------------------------------------------------------------


class TestSyntaxErrors:
    def test_syntax_error(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "def foo(:\n    pass\n")
        info = PythonEngine().parse_module(path)
        assert info.has_syntax_error is True
        assert info.classes == []
        assert info.functions == []
        assert info.imports == []

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        info = PythonEngine().parse_module(tmp_path / "nope.py")
        assert info.has_syntax_error is True
        assert info.classes == []


# ---------------------------------------------------------------------------
# parse_module — edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_file(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "")
        info = PythonEngine().parse_module(path)
        assert info.has_syntax_error is False
        assert info.classes == []
        assert info.functions == []
        assert info.imports == []
        assert info.docstring is None

    def test_only_imports(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "import os\nfrom os import path\n")
        info = PythonEngine().parse_module(path)
        assert len(info.imports) == 2
        assert info.classes == []
        assert info.functions == []

    def test_only_class(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "class Foo:\n    pass\n")
        info = PythonEngine().parse_module(path)
        assert len(info.classes) == 1
        assert info.functions == []
        assert info.imports == []


# ---------------------------------------------------------------------------
# is_test_file
# ---------------------------------------------------------------------------


class TestIsTestFile:
    def test_test_prefix(self, tmp_path: Path) -> None:
        assert PythonEngine().is_test_file(tmp_path / "test_foo.py") is True

    def test_in_tests_dir(self) -> None:
        assert PythonEngine().is_test_file(Path("/proj/tests/foo.py")) is True

    def test_regular_source(self) -> None:
        assert PythonEngine().is_test_file(Path("/proj/src/foo.py")) is False


# ---------------------------------------------------------------------------
# is_source_file
# ---------------------------------------------------------------------------


class TestIsSourceFile:
    def test_py_file(self) -> None:
        assert PythonEngine().is_source_file(Path("foo.py")) is True

    def test_php_file(self) -> None:
        assert PythonEngine().is_source_file(Path("foo.php")) is False


# ---------------------------------------------------------------------------
# file_extensions / test_file_pattern
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_file_extensions(self) -> None:
        assert PythonEngine().file_extensions() == [".py"]

    def test_test_file_pattern(self) -> None:
        assert PythonEngine().test_file_pattern() == "test_*.py"


# ---------------------------------------------------------------------------
# ModuleInfo basics
# ---------------------------------------------------------------------------


class TestModuleInfo:
    def test_language_field(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.language == "python"
        assert info.path == path

    def test_has_syntax_error_false_on_valid(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "mod.py", "x = 1\n")
        info = PythonEngine().parse_module(path)
        assert info.has_syntax_error is False
