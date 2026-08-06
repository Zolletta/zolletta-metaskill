"""Tests for interface_segregation_scanner module."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.patterns.python.interface_segregation_scanner import (
    InterfaceSegregationScanner,
)


def _parse_class(source: str) -> ast.ClassDef:
    """Parse source and return the first ClassDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("No class found in source")  # pragma: no cover


def _parse_func(source: str) -> ast.FunctionDef:
    """Parse source and return the first FunctionDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise AssertionError("No FunctionDef found in source")  # pragma: no cover


class TestGetClassInfo:
    def test_parse_class_simple_class_returns_bar(self) -> None:
        node = _parse_class("class Foo:\n    def bar(self):\n        pass\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        assert info["name"] == "Foo"
        assert info["line"] == 1
        assert info["bases"] == []
        assert len(info["methods"]) == 1
        assert info["methods"][0]["name"] == "bar"

    def test_class_with_bases(self) -> None:
        node = _parse_class("class Foo(Bar, Baz):\n    pass\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        assert info["bases"] == ["Bar", "Baz"]

    def test_class_with_attribute_base(self) -> None:
        node = _parse_class("class Foo(abc.ABC):\n    pass\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        assert info["bases"] == ["ABC"]

    def test_class_with_async_method(self) -> None:
        node = _parse_class("class Foo:\n    async def bar(self):\n        pass\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        assert len(info["methods"]) == 1
        assert info["methods"][0]["name"] == "bar"

    def test_class_with_multiple_methods(self) -> None:
        node = _parse_class(
            "class Foo:\n    def a(self):\n        pass\n    def b(self):\n        pass\n"
        )
        info = InterfaceSegregationScanner._get_class_info(node)
        assert len(info["methods"]) == 2
        names = {m["name"] for m in info["methods"]}
        assert names == {"a", "b"}

    def test_class_with_non_method_body(self) -> None:
        node = _parse_class("class Foo:\n    x = 1\n    y = 2\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        assert info["methods"] == []

    def test_method_info_fields(self) -> None:
        node = _parse_class("class Foo:\n    def bar(self):\n        pass\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        m = info["methods"][0]
        assert "line" in m
        assert "raises_not_implemented" in m
        assert "returns_none" in m


class TestRaisesNotImplemented:
    def test_parse_func_raises_call_returns_true(self) -> None:
        func = _parse_func("def foo(self):\n    raise NotImplementedError()\n")
        assert InterfaceSegregationScanner._raises_not_implemented(func) is True

    def test_parse_func_raises_name_returns_true(self) -> None:
        func = _parse_func("def foo(self):\n    raise NotImplementedError\n")
        assert InterfaceSegregationScanner._raises_not_implemented(func) is True

    def test_parse_func_no_raise_returns_false(self) -> None:
        func = _parse_func("def foo(self):\n    return 1\n")
        assert InterfaceSegregationScanner._raises_not_implemented(func) is False

    def test_raises_other_exception(self) -> None:
        func = _parse_func("def foo(self):\n    raise ValueError()\n")
        assert InterfaceSegregationScanner._raises_not_implemented(func) is False

    def test_raises_in_nested(self) -> None:
        func = _parse_func("def foo(self):\n    if True:\n        raise NotImplementedError()\n")
        assert InterfaceSegregationScanner._raises_not_implemented(func) is True

    def test_raise_without_exc(self) -> None:
        func = _parse_func("def foo(self):\n    raise\n")
        assert InterfaceSegregationScanner._raises_not_implemented(func) is False


class TestReturnsNoneOnly:
    def test_parse_func_pass_only_returns_true(self) -> None:
        func = _parse_func("def foo(self):\n    pass\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is True

    def test_parse_func_return_none_returns_true(self) -> None:
        func = _parse_func("def foo(self):\n    return None\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is True

    def test_parse_func_return_bare_returns_true(self) -> None:
        func = _parse_func("def foo(self):\n    return\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is True

    def test_parse_func_return_value_returns_false(self) -> None:
        func = _parse_func("def foo(self):\n    return 1\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is False

    def test_docstring_then_pass(self) -> None:
        func = _parse_func('def foo(self):\n    """Doc."""\n    pass\n')
        assert InterfaceSegregationScanner._returns_none_only(func) is True

    def test_docstring_then_return_none(self) -> None:
        func = _parse_func('def foo(self):\n    """Doc."""\n    return None\n')
        assert InterfaceSegregationScanner._returns_none_only(func) is True

    def test_parse_func_multiple_statements_returns_false(self) -> None:
        func = _parse_func("def foo(self):\n    x = 1\n    return None\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is False

    def test_parse_func_real_body_returns_false(self) -> None:
        func = _parse_func("def foo(self):\n    x = 1\n    y = 2\n    return x + y\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is False

    def test_empty_body_not_stub(self) -> None:
        func = _parse_func("def foo(self):\n    x = 1\n")
        assert InterfaceSegregationScanner._returns_none_only(func) is False


class TestIsProtocolOrAbc:
    def test_is_protocol_or_abc_protocol_returns_true(self) -> None:
        info = {"bases": ["Protocol"]}
        assert InterfaceSegregationScanner._is_protocol_or_abc(info) is True

    def test_is_protocol_or_abc_abc_returns_true(self) -> None:
        info = {"bases": ["ABC"]}
        assert InterfaceSegregationScanner._is_protocol_or_abc(info) is True

    def test_not_protocol_or_abc(self) -> None:
        info = {"bases": ["Foo"]}
        assert InterfaceSegregationScanner._is_protocol_or_abc(info) is False

    def test_is_protocol_or_abc_empty_bases_returns_false(self) -> None:
        info: dict[str, Any] = {"bases": []}
        assert InterfaceSegregationScanner._is_protocol_or_abc(info) is False

    def test_multiple_bases_with_protocol(self) -> None:
        info = {"bases": ["Foo", "Protocol"]}
        assert InterfaceSegregationScanner._is_protocol_or_abc(info) is True


class TestMain:
    def test_main_no_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_fat_interface(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(6))
        (src / "mod.py").write_text(f"class BigProtocol(Protocol):\n{methods}\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "BigProtocol" in out
        assert "Fat interfaces" in out

    def test_main_stub_violation(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class MyProto(Protocol):\n"
            "    def needed(self): pass\n"
            "    def not_needed(self): pass\n"
            "class MyImpl(MyProto):\n"
            "    def needed(self):\n        return 1\n"
            "    def not_needed(self):\n        raise NotImplementedError()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--min-methods", "2"])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "not_needed" in out

    def test_main_strict_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(6))
        (src / "mod.py").write_text(f"class BigProtocol(Protocol):\n{methods}\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strict"])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out

    def test_readouterr_main_skip_contains_skipped(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "src", "--skip"])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = InterfaceSegregationScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_min_methods_threshold(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(3))
        (src / "mod.py").write_text(f"class SmallProto(Protocol):\n{methods}\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--min-methods", "5"])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fat interfaces: none" in out

    def test_main_skips_pycache(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        pycache = src / "__pycache__"
        pycache.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(6))
        (pycache / "mod.py").write_text(f"class BigProtocol(Protocol):\n{methods}\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fat interfaces: none" in out

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def (:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = InterfaceSegregationScanner.main()
        assert rc == 0

    def test_main_report_only_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(6))
        (src / "mod.py").write_text(f"class BigProtocol(Protocol):\n{methods}\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = InterfaceSegregationScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "report-only" in out
