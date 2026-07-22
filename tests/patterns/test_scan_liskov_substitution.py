"""Tests for scan_liskov_substitution module."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.patterns.scan_liskov_substitution import (
    _check_lsp_violations,
    _get_classes,
    _get_method_signature,
    _get_raised_exceptions,
    _get_return_annotation,
    _is_stub_body,
    main,
)


def _parse_func(source: str) -> ast.FunctionDef:
    """Parse source and return the first FunctionDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise AssertionError("No function found in source")


def _parse_class(source: str) -> ast.ClassDef:
    """Parse source and return the first ClassDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("No class found in source")


def _parse_module(source: str) -> ast.Module:
    """Parse source into a Module AST."""
    return ast.parse(source)


class TestGetMethodSignature:
    def test_simple_method(self) -> None:
        func = _parse_func("class C:\n    def foo(self, a, b):\n        pass\n")
        sig = _get_method_signature(func)
        assert sig["name"] == "foo"
        assert sig["pos_args"] == ["a", "b"]
        assert sig["required_count"] == 2
        assert sig["defaults_count"] == 0
        assert sig["has_vararg"] is False
        assert sig["has_kwarg"] is False
        assert sig["returns_annotation"] is None

    def test_method_with_defaults(self) -> None:
        func = _parse_func("class C:\n    def foo(self, a, b=1):\n        pass\n")
        sig = _get_method_signature(func)
        assert sig["pos_args"] == ["a", "b"]
        assert sig["required_count"] == 1
        assert sig["defaults_count"] == 1

    def test_method_with_vararg_kwarg(self) -> None:
        func = _parse_func("class C:\n    def foo(self, a, *args, **kwargs):\n        pass\n")
        sig = _get_method_signature(func)
        assert sig["pos_args"] == ["a"]
        assert sig["has_vararg"] is True
        assert sig["has_kwarg"] is True

    def test_method_with_return_annotation(self) -> None:
        func = _parse_func("class C:\n    def foo(self) -> int:\n        return 1\n")
        sig = _get_method_signature(func)
        assert sig["returns_annotation"] == "int"

    def test_method_no_args(self) -> None:
        func = _parse_func("class C:\n    def foo(self):\n        pass\n")
        sig = _get_method_signature(func)
        assert sig["pos_args"] == []
        assert sig["required_count"] == 0

    def test_async_method(self) -> None:
        tree = ast.parse("class C:\n    async def foo(self, a):\n        pass\n")
        func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                func = node
                break
        assert func is not None
        sig = _get_method_signature(func)
        assert sig["name"] == "foo"
        assert sig["pos_args"] == ["a"]

    def test_line_number(self) -> None:
        func = _parse_func("class C:\n\n\n    def foo(self):\n        pass\n")
        sig = _get_method_signature(func)
        assert sig["line"] == 4


class TestGetReturnAnnotation:
    def test_no_annotation(self) -> None:
        func = _parse_func("def foo():\n    pass\n")
        assert _get_return_annotation(func) is None

    def test_simple_annotation(self) -> None:
        func = _parse_func("def foo() -> str:\n    return 'x'\n")
        assert _get_return_annotation(func) == "str"

    def test_complex_annotation(self) -> None:
        func = _parse_func("def foo() -> list[int]:\n    return [1]\n")
        assert _get_return_annotation(func) == "list[int]"

    def test_none_annotation(self) -> None:
        func = _parse_func("def foo() -> None:\n    pass\n")
        assert _get_return_annotation(func) == "None"


class TestGetRaisedExceptions:
    def test_no_raises(self) -> None:
        func = _parse_func("def foo():\n    return 1\n")
        assert _get_raised_exceptions(func) == set()

    def test_raise_call(self) -> None:
        func = _parse_func("def foo():\n    raise ValueError('bad')\n")
        assert _get_raised_exceptions(func) == {"ValueError"}

    def test_raise_name(self) -> None:
        func = _parse_func("def foo():\n    exc = ValueError()\n    raise exc\n")
        assert _get_raised_exceptions(func) == {"exc"}

    def test_multiple_raises(self) -> None:
        func = _parse_func(
            "def foo():\n"
            "    raise ValueError('a')\n"
            "    raise TypeError('b')\n"
        )
        assert _get_raised_exceptions(func) == {"ValueError", "TypeError"}

    def test_reraise_no_exc(self) -> None:
        func = _parse_func("def foo():\n    try:\n        pass\n    except:\n        raise\n")
        # bare raise has exc=None, so nothing added
        assert _get_raised_exceptions(func) == set()

    def test_raise_in_nested_function(self) -> None:
        func = _parse_func(
            "def foo():\n"
            "    def inner():\n"
            "        raise KeyError('x')\n"
            "    inner()\n"
        )
        # ast.walk descends into nested functions
        assert _get_raised_exceptions(func) == {"KeyError"}


class TestIsStubBody:
    def test_pass_body(self) -> None:
        func = _parse_func("def foo(self):\n    pass\n")
        assert _is_stub_body(func) is True

    def test_return_none(self) -> None:
        func = _parse_func("def foo(self):\n    return\n")
        assert _is_stub_body(func) is True

    def test_return_none_constant(self) -> None:
        func = _parse_func("def foo(self):\n    return None\n")
        assert _is_stub_body(func) is True

    def test_ellipsis_body(self) -> None:
        func = _parse_func("def foo(self):\n    ...\n")
        assert _is_stub_body(func) is True

    def test_docstring_then_pass(self) -> None:
        func = _parse_func('def foo(self):\n    """doc."""\n    pass\n')
        assert _is_stub_body(func) is True

    def test_real_body(self) -> None:
        func = _parse_func("def foo(self):\n    x = 1\n    return x\n")
        assert _is_stub_body(func) is False

    def test_return_value(self) -> None:
        func = _parse_func("def foo(self):\n    return 42\n")
        assert _is_stub_body(func) is False

    def test_docstring_then_real_body(self) -> None:
        func = _parse_func('def foo(self):\n    """doc."""\n    return 42\n')
        assert _is_stub_body(func) is False

    def test_multiple_statements(self) -> None:
        func = _parse_func("def foo(self):\n    pass\n    pass\n")
        assert _is_stub_body(func) is False


class TestGetClasses:
    def test_simple_class(self) -> None:
        tree = _parse_module("class Foo:\n    def bar(self):\n        pass\n")
        classes = _get_classes(tree)
        assert "Foo" in classes
        assert classes["Foo"]["name"] == "Foo"
        assert classes["Foo"]["bases"] == []
        assert "bar" in classes["Foo"]["methods"]

    def test_class_with_name_base(self) -> None:
        tree = _parse_module("class Dog(Animal):\n    pass\n")
        classes = _get_classes(tree)
        assert classes["Dog"]["bases"] == ["Animal"]

    def test_class_with_attribute_base(self) -> None:
        tree = _parse_module("class Dog(animals.Animal):\n    pass\n")
        classes = _get_classes(tree)
        assert classes["Dog"]["bases"] == ["Animal"]

    def test_multiple_bases(self) -> None:
        tree = _parse_module("class Dog(Animal, Creature):\n    pass\n")
        classes = _get_classes(tree)
        assert classes["Dog"]["bases"] == ["Animal", "Creature"]

    def test_multiple_classes(self) -> None:
        tree = _parse_module("class A:\n    pass\nclass B:\n    pass\n")
        classes = _get_classes(tree)
        assert set(classes.keys()) == {"A", "B"}

    def test_no_classes(self) -> None:
        tree = _parse_module("x = 1\n")
        assert _get_classes(tree) == {}

    def test_nested_class(self) -> None:
        tree = _parse_module("class Outer:\n    class Inner:\n        pass\n")
        classes = _get_classes(tree)
        assert "Outer" in classes
        assert "Inner" in classes

    def test_method_info(self) -> None:
        tree = _parse_module(
            "class Foo:\n"
            "    def bar(self, a):\n"
            "        raise ValueError()\n"
        )
        classes = _get_classes(tree)
        method = classes["Foo"]["methods"]["bar"]
        assert method["sig"]["pos_args"] == ["a"]
        assert method["raised"] == {"ValueError"}
        assert method["is_stub"] is False
        assert method["node"] is not None


class TestCheckLspViolations:
    def test_no_override_no_violation(self) -> None:
        parent = {
            "name": "P",
            "methods": {"foo": {"sig": {"required_count": 0}, "raised": set(), "is_stub": False}},
        }
        child = {"name": "C", "methods": {}}
        assert _check_lsp_violations(parent, child) == []

    def test_extra_required_params(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 2, "pos_args": ["a", "b"], "has_vararg": False,
                            "line": 5},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "extra_required_params" in types

    def test_fewer_params(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 2, "pos_args": ["a", "b"], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False,
                            "line": 5},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "fewer_params" in types

    def test_fewer_params_with_vararg_ok(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 2, "pos_args": ["a", "b"], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": True,
                            "line": 5},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "fewer_params" not in types

    def test_new_exceptions(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 1},
                    "raised": {"ValueError"}, "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 5},
                    "raised": {"ValueError", "KeyError"}, "is_stub": False,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "new_exceptions" in types

    def test_broader_exceptions_allowed(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 5},
                    "raised": {"ValueError", "RuntimeError"}, "is_stub": False,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "new_exceptions" not in types

    def test_stub_override(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 5},
                    "raised": set(), "is_stub": True,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "stub_override" in types

    def test_stub_when_parent_also_stub_ok(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": True,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 5},
                    "raised": set(), "is_stub": True,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "stub_override" not in types

    def test_multiple_violations(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 2, "pos_args": ["a", "b"], "has_vararg": False,
                            "line": 5},
                    "raised": {"KeyError"}, "is_stub": True,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        types = {v["type"] for v in violations}
        assert types == {"extra_required_params", "new_exceptions", "stub_override"}

    def test_violation_has_correct_fields(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False,
                            "line": 1},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False,
                            "line": 10},
                    "raised": set(), "is_stub": False,
                }
            },
        }
        violations = _check_lsp_violations(parent, child)
        v = violations[0]
        assert v["class"] == "C"
        assert v["method"] == "foo"
        assert v["line"] == 10
        assert "detail" in v


class TestMain:
    def test_main_success_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_with_violations_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self):\n"
            "        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "stub_override" in out
        assert "report-only mode" in out

    def test_main_with_violations_strict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self):\n"
            "        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out

    def test_main_skip(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--skip"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def bar(:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_pycache_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        pycache = src / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "mod.py").write_text("class Foo:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = main()
        assert rc == 0

    def test_main_violation_output_contains_fix(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self, extra):\n"
            "        return 'woof'\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fix:" in out
        assert "extra_required_params" in out

    def test_main_new_exception_violation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self):\n"
            "        raise KeyError('x')\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "new_exceptions" in out

    def test_main_fewer_params_violation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self, volume):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self):\n"
            "        return 'woof'\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "fewer_params" in out
