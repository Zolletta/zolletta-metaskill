"""Tests for interface_segregation_scanner module."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections.abc import Callable
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


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {
            "patterns": {},
            "paths": {"source": ["src"], "tests": ["tests"], "package": "mypkg"},
        },
        "php": None,
    }
    python_overrides = overrides.pop("python", None)
    if isinstance(python_overrides, dict):
        base_python = settings["python"]
        assert isinstance(base_python, dict)
        for key, value in python_overrides.items():
            if isinstance(value, dict) and isinstance(base_python.get(key), dict):
                base_python[key].update(value)
            else:
                base_python[key] = value
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def test_write_settings_replaces_non_dict_python_value(tmp_path: Path) -> None:
    """A non-dict ``python`` override value replaces the base value."""
    path = _write_settings(tmp_path, python={"tools": "none"})
    written = json.loads(path.read_text())
    python = written["python"]
    assert isinstance(python, dict)
    assert python["tools"] == "none"


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Chdir into tmp_path and run main() with *argv*."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    return InterfaceSegregationScanner.main()


def _fat_protocol_src(count: int = 6, name: str = "BigProtocol") -> str:
    methods = "\n".join(f"    def m{i}(self): pass" for i in range(count))
    return f"class {name}(Protocol):\n{methods}\n"


class TestInterfaceSegregationScanner:
    # --- GetClassInfo ---

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

    def test_class_with_subscript_base(self) -> None:
        node = _parse_class("class Foo(Generic[T]):\n    pass\n")
        info = InterfaceSegregationScanner._get_class_info(node)
        assert info["bases"] == []

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

    # --- RaisesNotImplemented ---

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

    # --- ReturnsNoneOnly ---

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

    # --- IsProtocolOrAbc ---

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

    # --- Main ---

    def test_stubs_for_protocol_fully_implemented_returns_empty(self) -> None:
        proto_info = {"methods": [{"name": "a"}, {"name": "b"}]}
        implementers = {"Proto": ["Impl"]}
        all_classes = {
            "Impl": {
                "file": "x.py",
                "methods": [
                    {
                        "name": "a",
                        "line": 1,
                        "raises_not_implemented": False,
                        "returns_none": False,
                    }
                ],
            }
        }
        assert (
            InterfaceSegregationScanner._stubs_for_protocol(
                "Proto", proto_info, implementers, all_classes
            )
            == []
        )

    def test_main_no_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "## Fat interfaces: none (threshold: 5 methods)" in out.splitlines()
        assert "## Implementers stubbing interface methods: none" in out.splitlines()
        assert "Result: all clear" in out.splitlines()

    def test_main_fat_interface(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_fat_protocol_src())
        rc = _run(tmp_path, monkeypatch, ["prog"])
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
        _write_settings(tmp_path, python={"patterns": {"isp_min_methods": 2}})
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
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "not_needed" in out
        assert "report-only" in out

    def test_main_check_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_isp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Result: SKIPPED (check_isp disabled in settings.json)" in out.splitlines()

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_isp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report == {"skipped": True, "reason": "check_isp disabled in settings.json"}

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert err.splitlines() == ["Error: no configured source directories exist on disk"]

    def test_main_min_methods_setting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``patterns.isp_min_methods`` filters protocols below the threshold."""
        _write_settings(tmp_path, python={"patterns": {"isp_min_methods": 5}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_fat_protocol_src(count=3, name="SmallProto"))
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fat interfaces: none" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_fat_protocol_src())
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] == 1
        assert report["fat_interfaces"][0]["name"] == "BigProtocol"
        assert report["min_methods"] == 5
        assert report["directories"] == ["src"]

    def test_main_json_stub_violations_exact_fields(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The JSON report spells out every stub-violation field verbatim."""
        _write_settings(tmp_path, python={"patterns": {"isp_min_methods": 2}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class MyProto(Protocol):\n"  # line 1
            "    def a(self): pass\n"  # line 2
            "    def b(self): pass\n"  # line 3
            "class MyImpl(MyProto):\n"  # line 4
            "    def a(self):\n"  # line 5
            "        raise NotImplementedError()\n"
            "    def b(self):\n"  # line 7
            "        pass\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["min_methods"] == 2
        assert report["fat_interfaces"] == [
            {
                "name": "MyProto",
                "file": "mod.py",
                "line": 1,
                "method_count": 2,
                "methods": ["a", "b"],
            }
        ]
        assert report["stub_violations"] == [
            {
                "protocol": "MyProto",
                "implementer": "MyImpl",
                "method": "a",
                "file": "mod.py",
                "line": 5,
                "issue": "raises NotImplementedError",
            },
            {
                "protocol": "MyProto",
                "implementer": "MyImpl",
                "method": "b",
                "file": "mod.py",
                "line": 7,
                "issue": "stub (pass/return None)",
            },
        ]
        assert report["violation_count"] == 3

    def test_main_text_forwards_stub_violations_to_emit_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() forwards the detected stub violations to ``_emit_text``."""
        _write_settings(tmp_path, python={"patterns": {"isp_min_methods": 2}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class MyProto(Protocol):\n"
            "    def a(self): pass\n"
            "    def b(self): pass\n"
            "class MyImpl(MyProto):\n"
            "    def a(self):\n"
            "        raise NotImplementedError()\n"
            "    def b(self):\n"
            "        pass\n"
        )
        captured: dict[str, Any] = {}

        def _spy(
            min_methods: int,
            fat_interfaces: list[dict[str, Any]],
            stub_violations: list[dict[str, Any]],
            implementers: dict[str, list[str]],
        ) -> None:
            captured["stub_violations"] = stub_violations

        monkeypatch.setattr(InterfaceSegregationScanner, "_emit_text", staticmethod(_spy))
        rc = _run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0
        assert captured["stub_violations"] == [
            {
                "protocol": "MyProto",
                "implementer": "MyImpl",
                "method": "a",
                "file": "mod.py",
                "line": 5,
                "issue": "raises NotImplementedError",
            },
            {
                "protocol": "MyProto",
                "implementer": "MyImpl",
                "method": "b",
                "file": "mod.py",
                "line": 7,
                "issue": "stub (pass/return None)",
            },
        ]

    def test_main_gitignored_dirs_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("src/ignored/\n")
        _write_settings(tmp_path)
        ignored = tmp_path / "src" / "ignored"
        ignored.mkdir(parents=True)
        (ignored / "mod.py").write_text(_fat_protocol_src())
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fat interfaces: none" in out

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def (:\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    # --- MinMethods ---

    def test_min_methods_configured_value_returns_it(self) -> None:
        settings = {"python": {"patterns": {"isp_min_methods": 2}}}
        assert InterfaceSegregationScanner._min_methods(settings, {"python"}) == 2

    def test_min_methods_bool_setting_returns_default(self) -> None:
        """A boolean ``isp_min_methods`` is not an int and falls back to 5."""
        settings = {"python": {"patterns": {"isp_min_methods": True}}}
        assert InterfaceSegregationScanner._min_methods(settings, {"python"}) == 5

    # --- CollectClasses ---

    def test_collect_classes_syntax_error_continues_to_next_file(self, tmp_path: Path) -> None:
        """A syntax-error file is skipped, not fatal — later files still scan."""
        (tmp_path / "a_bad.py").write_text("class Foo:\n    def (:\n")
        (tmp_path / "z_good.py").write_text("class Good(Protocol):\n    def a(self): pass\n")
        assert InterfaceSegregationScanner._collect_classes([tmp_path]) == {
            "Good": {
                "name": "Good",
                "line": 1,
                "bases": ["Protocol"],
                "methods": [
                    {
                        "name": "a",
                        "line": 2,
                        "raises_not_implemented": False,
                        "returns_none": True,
                    }
                ],
                "file": "z_good.py",
            }
        }

    # --- DetectViolations ---

    def test_detect_violations_method_count_at_threshold_is_fat(self) -> None:
        """A protocol with exactly ``min_methods`` methods is fat (``>=``)."""
        all_classes = {
            "P": {
                "name": "P",
                "line": 1,
                "file": "p.py",
                "bases": ["Protocol"],
                "methods": [{"name": "a"}, {"name": "b"}],
            }
        }
        fat, stubs = InterfaceSegregationScanner._detect_violations(all_classes, {}, 2)
        assert fat == [
            {
                "name": "P",
                "file": "p.py",
                "line": 1,
                "method_count": 2,
                "methods": ["a", "b"],
            }
        ]
        assert stubs == []

    # --- EmitText ---

    def test_emit_text_stub_only_violations_reports_violations(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Violations in either list alone still print the violations result."""
        InterfaceSegregationScanner._emit_text(
            5,
            [],
            [
                {
                    "protocol": "P",
                    "implementer": "I",
                    "method": "m",
                    "file": "f.py",
                    "line": 1,
                    "issue": "stub (pass/return None)",
                }
            ],
            {},
        )
        out = capsys.readouterr().out
        assert "Result: ISP violations found (report-only mode)" in out.splitlines()

    def test_emit_text_no_violations_reports_all_clear(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        InterfaceSegregationScanner._emit_text(5, [], [], {})
        out = capsys.readouterr().out
        assert "Result: all clear" in out.splitlines()

    # --- EmitFatInterfaces ---

    def test_emit_fat_interfaces_multiple_implementers_joined(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        InterfaceSegregationScanner._emit_fat_interfaces(
            [{"name": "P", "file": "p.py", "line": 1, "method_count": 6, "methods": ["m"]}],
            5,
            {"P": ["Alpha", "Beta"]},
        )
        out = capsys.readouterr().out
        assert "    Implementers: Alpha, Beta" in out.splitlines()

    # --- EmitStubViolations ---

    def test_emit_stub_violations_empty_reports_none(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        InterfaceSegregationScanner._emit_stub_violations([])
        out = capsys.readouterr().out
        assert "## Implementers stubbing interface methods: none" in out.splitlines()

    # --- Text Output Contract ---

    def test_emit_text_matches_committed_contract(
        self,
        capsys: pytest.CaptureFixture[str],
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The captured text report is a byte-for-byte contract.

        The comparison is exact on purpose and must not be loosened to a
        substring or regex check: a legitimate change to the rendered report is
        ``pytest --update-fixtures`` followed by a reviewed diff.

        """
        fat_interfaces = [
            {
                "name": "BigProtocol",
                "file": "pkg/mod.py",
                "line": 3,
                "method_count": 6,
                "methods": ["m0", "m1", "m2", "m3", "m4", "m5"],
            }
        ]
        stub_violations = [
            {
                "protocol": "BigProtocol",
                "implementer": "PartialImpl",
                "method": "m0",
                "file": "pkg/impl.py",
                "line": 12,
                "issue": "raises NotImplementedError",
            }
        ]
        InterfaceSegregationScanner._emit_text(
            5, fat_interfaces, stub_violations, {"BigProtocol": ["PartialImpl"]}
        )
        text_contract(
            "patterns/python/interface_segregation_scanner.txt",
            capsys.readouterr().out,
        )
