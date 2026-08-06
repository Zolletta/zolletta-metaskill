"""Tests for open_closed_scanner module."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import cast

import pytest

from zolletta_metaskill.patterns.python.open_closed_scanner import (
    OpenClosedScanner,
)


def _parse(source: str) -> ast.Module:
    return ast.parse(source)


def _parse_if(source: str) -> ast.If:
    tree = _parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            return node
    raise AssertionError("No If found")  # pragma: no cover


def _parse_call(source: str) -> ast.Call:
    tree = _parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            return node
    raise AssertionError("No Call found")  # pragma: no cover


def _parse_match(source: str) -> ast.Match:
    tree = _parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Match):
            return node
    raise AssertionError("No Match found")  # pragma: no cover


class TestIsTypeCheck:
    def test_parse_call_isinstance_call_returns_true(self) -> None:
        node = _parse_call("isinstance(x, int)")
        assert OpenClosedScanner._is_type_check(node) is True

    def test_parse_call_type_call_returns_true(self) -> None:
        node = _parse_call("type(x)")
        assert OpenClosedScanner._is_type_check(node) is True

    def test_parse_type_compare_returns_true(self) -> None:
        tree = _parse("type(obj) == SomeClass")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                assert OpenClosedScanner._is_type_check(node) is True
                return
        raise AssertionError("No Compare found")  # pragma: no cover

    def test_class_name_compare(self) -> None:
        tree = _parse("obj.__class__.__name__ == 'Foo'")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                assert OpenClosedScanner._is_type_check(node) is True
                return
        raise AssertionError("No Compare found")  # pragma: no cover

    def test_type_attr_compare(self) -> None:
        tree = _parse("obj.type == 'foo'")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                assert OpenClosedScanner._is_type_check(node) is True
                return
        raise AssertionError("No Compare found")  # pragma: no cover

    def test_kind_attr_compare(self) -> None:
        tree = _parse("obj.kind == 'foo'")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                assert OpenClosedScanner._is_type_check(node) is True
                return
        raise AssertionError("No Compare found")  # pragma: no cover

    def test_class_attr_compare(self) -> None:
        tree = _parse("obj.__class__ == Foo")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                assert OpenClosedScanner._is_type_check(node) is True
                return
        raise AssertionError("No Compare found")  # pragma: no cover

    def test_non_type_compare(self) -> None:
        tree = _parse("x == 5")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                assert OpenClosedScanner._is_type_check(node) is False
                return
        raise AssertionError("No Compare found")  # pragma: no cover

    def test_non_type_call(self) -> None:
        node = _parse_call("len(x)")
        assert OpenClosedScanner._is_type_check(node) is False

    def test_parse_other_node_returns_false(self) -> None:
        tree = _parse("x = 1")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                assert OpenClosedScanner._is_type_check(node) is False
                return
        raise AssertionError("No Assign found")  # pragma: no cover


class TestContainsTypeCheck:
    def test_bool_op_with_type_check(self) -> None:
        tree = _parse("isinstance(x, int) and x > 0")
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp):
                assert OpenClosedScanner._contains_type_check(node) is True
                return
        raise AssertionError("No BoolOp found")  # pragma: no cover

    def test_bool_op_without_type_check(self) -> None:
        tree = _parse("x > 0 and y > 0")
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp):
                assert OpenClosedScanner._contains_type_check(node) is False
                return
        raise AssertionError("No BoolOp found")  # pragma: no cover

    def test_non_bool_op(self) -> None:
        node = _parse_call("isinstance(x, int)")
        assert OpenClosedScanner._contains_type_check(node) is True

    def test_nested_bool_op(self) -> None:
        tree = _parse("(isinstance(x, int) or isinstance(x, str)) and x > 0")
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp):
                assert OpenClosedScanner._contains_type_check(node) is True
                return
        raise AssertionError("No BoolOp found")  # pragma: no cover


class TestCountTypeBranches:
    def test_three_isinstance_branches(self) -> None:
        source = (
            "if isinstance(x, int):\n    pass\n"
            "elif isinstance(x, str):\n    pass\n"
            "elif isinstance(x, float):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 3

    def test_parse_if_two_branches_returns_2(self) -> None:
        source = "if isinstance(x, int):\n    pass\nelif isinstance(x, str):\n    pass\n"
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 2

    def test_parse_if_one_branch_returns_1(self) -> None:
        source = "if isinstance(x, int):\n    pass\n"
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 1

    def test_parse_if_with_else_returns_3(self) -> None:
        source = (
            "if isinstance(x, int):\n    pass\n"
            "elif isinstance(x, str):\n    pass\n"
            "elif isinstance(x, float):\n    pass\n"
            "else:\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 3

    def test_non_type_branches(self) -> None:
        source = "if x > 0:\n    pass\nelif x < 0:\n    pass\nelif x == 0:\n    pass\n"
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 0


class TestIsStringTypeDispatch:
    def test_getattr_with_concat(self) -> None:
        node = _parse_call('builtins.getattr(obj, "method_" + type_name)')
        assert OpenClosedScanner._is_string_type_dispatch(node) is True

    def test_getattr_with_fstring(self) -> None:
        node = _parse_call('builtins.getattr(obj, f"method_{type_name}")')
        assert OpenClosedScanner._is_string_type_dispatch(node) is True

    def test_getattr_without_concat(self) -> None:
        node = _parse_call('builtins.getattr(obj, "method_name")')
        assert OpenClosedScanner._is_string_type_dispatch(node) is False

    def test_non_getattr_call(self) -> None:
        node = _parse_call("len(x)")
        assert OpenClosedScanner._is_string_type_dispatch(node) is False

    def test_attribute_call_not_getattr(self) -> None:
        """Attribute call where attr is not 'getattr' (e.g. obj.method(...))."""
        node = _parse_call('obj.method("method_" + t)')
        assert OpenClosedScanner._is_string_type_dispatch(node) is False

    def test_getattr_with_one_arg(self) -> None:
        node = _parse_call("builtins.getattr(obj)")
        assert OpenClosedScanner._is_string_type_dispatch(node) is False

    def test_non_call_node(self) -> None:
        tree = _parse("x = 1")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                assert OpenClosedScanner._is_string_type_dispatch(cast("ast.Call", node)) is False
                return
        raise AssertionError("No Assign found")  # pragma: no cover


class TestFindMatchOnType:
    def test_match_on_class(self) -> None:
        source = "match x:\n    case int():\n        pass\n    case str():\n        pass\n"
        node = _parse_match(source)
        assert OpenClosedScanner._find_match_on_type(node) is True

    def test_match_on_value(self) -> None:
        source = "match x:\n    case 1:\n        pass\n    case 2:\n        pass\n"
        node = _parse_match(source)
        assert OpenClosedScanner._find_match_on_type(node) is False

    def test_parse_match_mixed_match_returns_true(self) -> None:
        source = "match x:\n    case int():\n        pass\n    case 1:\n        pass\n"
        node = _parse_match(source)
        assert OpenClosedScanner._find_match_on_type(node) is True


class TestScanFile:
    def test_type_ladder_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
            "    elif isinstance(x, float):\n        pass\n"
        )
        violations = OpenClosedScanner.scan_file(f)
        ladders = [v for v in violations if v["type"] == "type_ladder"]
        assert len(ladders) == 1
        assert ladders[0]["branches"] == 3

    def test_string_dispatch_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('def f(obj, t):\n    return builtins.getattr(obj, "method_" + t)\n')
        violations = OpenClosedScanner.scan_file(f)
        dispatches = [v for v in violations if v["type"] == "string_dispatch"]
        assert len(dispatches) == 1

    def test_match_on_type_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "def f(x):\n"
            "    match x:\n"
            "        case int():\n            pass\n"
            "        case str():\n            pass\n"
            "        case float():\n            pass\n"
        )
        violations = OpenClosedScanner.scan_file(f)
        matches = [v for v in violations if v["type"] == "match_on_type"]
        assert len(matches) == 1
        assert matches[0]["branches"] == 3

    def test_scan_file_no_violations_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("def f(x):\n    return x + 1\n")
        violations = OpenClosedScanner.scan_file(f)
        assert violations == []

    def test_scan_file_syntax_error_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def f(:\n")
        violations = OpenClosedScanner.scan_file(f)
        assert violations == []

    def test_scan_file_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        violations = OpenClosedScanner.scan_file(f)
        assert violations == []

    def test_two_branch_no_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
        )
        violations = OpenClosedScanner.scan_file(f)
        ladders = [v for v in violations if v["type"] == "type_ladder"]
        assert len(ladders) == 0


class TestMain:
    def test_main_no_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def f(x):\n    return x + 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = OpenClosedScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_with_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
            "    elif isinstance(x, float):\n        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = OpenClosedScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "type_ladder" in out
        assert "report-only" in out

    def test_main_strict_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
            "    elif isinstance(x, float):\n        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strict"])
        rc = OpenClosedScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out

    def test_readouterr_main_skip_contains_skipped(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "src", "--skip"])
        rc = OpenClosedScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = OpenClosedScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_min_branches_filter(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
            "    elif isinstance(x, float):\n        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--min-branches", "5"])
        rc = OpenClosedScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def f(x):\n    return x\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OpenClosedScanner.main()
        assert rc == 0

    def test_main_skips_pycache(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        pycache = src / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.py").write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
            "    elif isinstance(x, float):\n        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = OpenClosedScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
