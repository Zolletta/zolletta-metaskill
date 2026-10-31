"""Tests for open_closed_scanner module."""

from __future__ import annotations

import ast
import json
import subprocess
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
    return OpenClosedScanner.main()


_LADDER_SRC = (
    "def f(x):\n"
    "    if isinstance(x, int):\n        pass\n"
    "    elif isinstance(x, str):\n        pass\n"
    "    elif isinstance(x, float):\n        pass\n"
)


class TestOpenClosedScanner:
    # --- IsTypeCheck ---

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

    # --- ContainsTypeCheck ---

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

    # --- CountTypeBranches ---

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

    def test_multi_statement_else_block_if_returns_1(self) -> None:
        """A nested if inside a multi-statement else is a separate chain, not an elif."""
        source = (
            "if isinstance(x, int):\n    pass\n"
            "else:\n"
            "    if isinstance(y, str):\n        pass\n"
            "    print(y)\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 1

    # --- syntax vocabulary is not a type ladder ---

    def test_ast_node_ladder_is_not_counted(self) -> None:
        """``ast.*`` is a closed grammar; a ladder over it is parser dispatch."""
        source = (
            "if isinstance(node, ast.ClassDef):\n    pass\n"
            "elif isinstance(node, ast.FunctionDef):\n    pass\n"
            "elif isinstance(node, ast.Import):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 0

    def test_ast_tuple_ladder_is_not_counted(self) -> None:
        source = (
            "if isinstance(node, ast.ClassDef):\n    pass\n"
            "elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):\n    pass\n"
            "elif isinstance(node, ast.Import):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 0

    def test_tree_sitter_type_string_ladder_is_not_counted(self) -> None:
        """``node.type`` names tree-sitter node types — a grammar, not application types."""
        source = (
            "if child.type == 'namespace_use_group':\n    pass\n"
            "elif child.type == 'namespace_use_clause':\n    pass\n"
            "elif child.type in ('name', 'qualified_name'):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 0

    def test_application_type_ladder_is_still_flagged(self) -> None:
        """The positive case: narrowing must not suppress a genuine ladder."""
        source = (
            "if isinstance(x, Dog):\n    pass\n"
            "elif isinstance(x, Cat):\n    pass\n"
            "elif isinstance(x, Bird):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 3

    def test_kind_ladder_is_still_flagged(self) -> None:
        """``.kind`` is a domain convention, so a ``.kind`` ladder stays a finding."""
        source = (
            "if issue.kind == 'critical':\n    pass\n"
            "elif issue.kind == 'high':\n    pass\n"
            "elif issue.kind == 'low':\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 3

    def test_mixed_ast_and_domain_operands_are_still_flagged(self) -> None:
        """A domain branch that merely mentions ``ast`` is still a domain branch."""
        source = (
            "if isinstance(n, ast.Call) and isinstance(n.value, Dog):\n    pass\n"
            "elif isinstance(n, ast.Name) and isinstance(n.ctx, Cat):\n    pass\n"
            "elif isinstance(n, ast.Constant) and isinstance(n.value, Bird):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 3

    def test_mixed_ladder_counts_only_the_domain_branch(self) -> None:
        source = (
            "if isinstance(n, ast.Call):\n    pass\n"
            "elif isinstance(n, Dog):\n    pass\n"
            "elif isinstance(n, Cat):\n    pass\n"
        )
        node = _parse_if(source)
        assert OpenClosedScanner._count_type_branches(node) == 2

    def test_scan_file_ignores_ast_ladder(self, tmp_path: Path) -> None:
        source = (
            "import ast\n\n\n"
            "def walk(node):\n"
            "    if isinstance(node, ast.ClassDef):\n        pass\n"
            "    elif isinstance(node, ast.FunctionDef):\n        pass\n"
            "    elif isinstance(node, ast.Import):\n        pass\n"
        )
        path = tmp_path / "walker.py"
        path.write_text(source)
        assert OpenClosedScanner.scan_file(path) == []

    def test_scan_file_reports_application_ladder(self, tmp_path: Path) -> None:
        source = (
            "def handle(x):\n"
            "    if isinstance(x, Dog):\n        pass\n"
            "    elif isinstance(x, Cat):\n        pass\n"
            "    elif isinstance(x, Bird):\n        pass\n"
        )
        path = tmp_path / "handler.py"
        path.write_text(source)
        violations = OpenClosedScanner.scan_file(path)
        assert [v["type"] for v in violations] == ["type_ladder"]

    # --- IsStringTypeDispatch ---

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

    # --- FindMatchOnType ---

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

    # --- ScanFile ---

    def test_type_ladder_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "def f(x):\n"
            "    if isinstance(x, int):\n        pass\n"
            "    elif isinstance(x, str):\n        pass\n"
            "    elif isinstance(x, float):\n        pass\n"
        )
        violations = OpenClosedScanner.scan_file(f)
        assert violations == [
            {
                "type": "type_ladder",
                "file": str(f),
                "line": 2,
                "branches": 3,
                "detail": "if/elif chain with 3 type-check branches",
            }
        ]

    def test_string_dispatch_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('def f(obj, t):\n    return builtins.getattr(obj, "method_" + t)\n')
        violations = OpenClosedScanner.scan_file(f)
        assert violations == [
            {
                "type": "string_dispatch",
                "file": str(f),
                "line": 2,
                "branches": 0,
                "detail": "getattr() with dynamic string — consider polymorphism",
            }
        ]

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
        assert violations == [
            {
                "type": "match_on_type",
                "file": str(f),
                "line": 2,
                "branches": 3,
                "detail": "match/case on type with 3 class patterns",
            }
        ]

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

    # --- Main ---

    def test_main_no_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def f(x):\n    return x + 1\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert (
            out
            == "\n".join(
                [
                    "=" * 70,
                    "OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT",
                    "=" * 70,
                    "",
                    "## OCP violations: none",
                    "",
                    "Result: all clear",
                ]
            )
            + "\n"
        )

    def test_main_with_violations_report_only(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_LADDER_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert (
            out
            == "\n".join(
                [
                    "=" * 70,
                    "OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT",
                    "=" * 70,
                    "",
                    "## OCP violations (1 found)",
                    "",
                    "  [type_ladder] if/elif chain with 3 type-check branches",
                    "    -> mod.py:2",
                    "    Fix: replace type branching with polymorphism (strategy pattern,",
                    "         plugin registry, or protocol-based dispatch)",
                    "",
                    "Result: OCP violations found (report-only mode)",
                ]
            )
            + "\n"
        )

    def test_main_check_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_ocp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert out == "Result: SKIPPED (check_ocp disabled in settings.json)\n"

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_ocp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report == {"skipped": True, "reason": "check_ocp disabled in settings.json"}

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert err == "Error: no configured source directories exist on disk\n"

    def test_main_min_branches_setting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``patterns.ocp_min_branches`` filters type ladders below the threshold."""
        _write_settings(tmp_path, python={"patterns": {"ocp_min_branches": 5}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_LADDER_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_LADDER_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        expected = {
            "directories": ["src"],
            "min_branches": 3,
            "violation_count": 1,
            "violations": [
                {
                    "type": "type_ladder",
                    "file": "mod.py",
                    "line": 2,
                    "branches": 3,
                    "detail": "if/elif chain with 3 type-check branches",
                }
            ],
        }
        assert rc == 0
        assert out == json.dumps(expected, indent=2) + "\n"

    def test_main_gitignored_dirs_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("src/ignored/\n")
        _write_settings(tmp_path)
        ignored = tmp_path / "src" / "ignored"
        ignored.mkdir(parents=True)
        (ignored / "mod.py").write_text(_LADDER_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_non_default_source_root_returns_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``python.paths.source`` comes from settings, not the ``["src"]`` default."""
        _write_settings(tmp_path, python={"paths": {"source": ["lib"]}})
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "mod.py").write_text(_LADDER_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert (
            out
            == "\n".join(
                [
                    "=" * 70,
                    "OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT",
                    "=" * 70,
                    "",
                    "## OCP violations (1 found)",
                    "",
                    "  [type_ladder] if/elif chain with 3 type-check branches",
                    "    -> mod.py:2",
                    "    Fix: replace type branching with polymorphism (strategy pattern,",
                    "         plugin registry, or protocol-based dispatch)",
                    "",
                    "Result: OCP violations found (report-only mode)",
                ]
            )
            + "\n"
        )

    # --- AST guard paths ---

    def test_is_string_collection_non_literal_node_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse("x", mode="eval").body
        assert OpenClosedScanner._is_string_collection(node) is False

    def test_is_syntax_vocabulary_non_isinstance_call_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse("foo(x)", mode="eval").body
        assert OpenClosedScanner._is_syntax_vocabulary(node) is False

    def test_is_syntax_vocabulary_name_node_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse("flag", mode="eval").body
        assert OpenClosedScanner._is_syntax_vocabulary(node) is False

    def test_match_with_few_class_cases_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "def f(x):\n    match x:\n        case int():\n            pass\n"
            "        case str():\n            pass\n"
        )
        violations = OpenClosedScanner.scan_file(f)
        assert [v for v in violations if v["type"] == "match_on_type"] == []

    def test_is_syntax_vocabulary_string_call_non_isinstance_false(self) -> None:
        import ast as _ast

        node = _ast.parse("isinstance()", mode="eval").body
        assert OpenClosedScanner._is_syntax_vocabulary(node) is False

    def test_is_syntax_class_mixed_tuple_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse("(ast.ClassDef, Dog)", mode="eval").body
        assert OpenClosedScanner._is_syntax_class(node) is False

    def test_is_syntax_class_empty_tuple_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse("()", mode="eval").body
        assert OpenClosedScanner._is_syntax_class(node) is False

    def test_is_string_collection_mixed_tuple_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse('("a", 1)', mode="eval").body
        assert OpenClosedScanner._is_string_collection(node) is False

    def test_is_string_collection_empty_tuple_returns_false(self) -> None:
        import ast as _ast

        node = _ast.parse("()", mode="eval").body
        assert OpenClosedScanner._is_string_collection(node) is False

    def test_is_syntax_vocabulary_all_syntax_boolop_returns_true(self) -> None:
        import ast as _ast

        node = _ast.parse("isinstance(n, ast.Call) and isinstance(n, ast.Name)", mode="eval").body
        assert OpenClosedScanner._is_syntax_vocabulary(node) is True

    def test_is_syntax_vocabulary_named_call_returns_false(self) -> None:
        """``foo(n, ast.Call)`` is a domain call — the func id must be ``isinstance``."""
        import ast as _ast

        node = _ast.parse("foo(n, ast.Call)", mode="eval").body
        assert OpenClosedScanner._is_syntax_vocabulary(node) is False
