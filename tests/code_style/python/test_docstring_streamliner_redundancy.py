"""Tests for DocstringStreamliner — split from TestDocstringStreamliner."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.docstring_streamliner import DocstringStreamliner
from zolletta_metaskill.code_style.python.structs import DocstringStripOptions


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {
            "code_style": {},
            "paths": {"source": ["src"], "tests": ["tests"], "package": "mypkg"},
        },
        "php": None,
    }
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


class TestDocstringStreamlinerRedundancy:
    """Tests for DocstringStreamliner (redundancy), split from TestDocstringStreamliner."""

    def _parse(self, source: str) -> ast.FunctionDef:
        tree = ast.parse(source)
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        return node

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return DocstringStreamliner.main()

    # --- Tests for DocstringStreamliner._analyze_function(). ---

    def test_redundant_args_removed(self) -> None:
        src = 'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.kind == "redundant"
        assert "Args" in finding.detail

    def test_redundant_returns_removed(self) -> None:
        src = 'def f(x: int) -> int:\n    """Summary.\n\nReturns:\n    int"""\n    return x\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert "Returns" in finding.detail

    def test_obsolete_docstring_removed(self) -> None:
        src = (
            'def f(x: int) -> int:\n    """\nArgs:\n    x: int\n'
            'Returns:\n    int"""\n    return x\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.remove is True

    def test_strip_tests_not_test_file(self) -> None:
        src = 'def test_foo(x: int) -> None:\n    """Test foo."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("src/foo.py"), DocstringStripOptions(False, True, False, False)
        )
        assert finding is None

    def test_strip_obvious_init(self) -> None:
        src = (
            'class C:\n    def __init__(self, x: int) -> None:\n        """Init."""\n        pass\n'
        )
        tree = ast.parse(src)
        DocstringStreamliner._annotate_parents(tree)
        cls = tree.body[0]
        assert isinstance(cls, ast.ClassDef)
        init_node = cls.body[0]
        assert isinstance(init_node, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            init_node, Path("f.py"), DocstringStripOptions(False, False, False, True)
        )
        assert finding is not None
        assert finding.kind == "obvious_init"

    def test_strip_obvious_init_not_obvious(self) -> None:
        src = 'class C:\n    def __init__(self, x) -> None:\n        """Init."""\n        pass\n'
        tree = ast.parse(src)
        DocstringStreamliner._annotate_parents(tree)
        cls = tree.body[0]
        assert isinstance(cls, ast.ClassDef)
        init_node = cls.body[0]
        assert isinstance(init_node, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            init_node, Path("f.py"), DocstringStripOptions(False, False, False, True)
        )
        assert finding is None

    def test_strip_private_finding_fields_exact(self) -> None:
        src = 'def _helper(x: int) -> None:\n    """A helper."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(True, False, False, False)
        )
        assert finding is not None
        assert finding.line == 1
        assert finding.kind == "private"
        assert finding.detail == "_helper() — private"
        assert finding.node is node
        assert finding.new_text is None
        assert finding.remove is True

    def test_strip_tests_finding_fields_exact(self) -> None:
        src = 'def test_foo(x: int) -> None:\n    """Test foo."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("test_foo.py"), DocstringStripOptions(False, True, False, False)
        )
        assert finding is not None
        assert finding.line == 1
        assert finding.kind == "test"
        assert finding.detail == "test_foo() — test function"
        assert finding.node is node
        assert finding.new_text is None
        assert finding.remove is True

    def test_strip_nested_finding_fields_exact(self) -> None:
        src = 'def outer():\n    def inner():\n        """Nested."""\n        pass\n'
        tree = ast.parse(src)
        DocstringStreamliner._annotate_parents(tree)
        outer = tree.body[0]
        assert isinstance(outer, ast.FunctionDef)
        inner = outer.body[0]
        assert isinstance(inner, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            inner, Path("f.py"), DocstringStripOptions(False, False, True, False)
        )
        assert finding is not None
        assert finding.line == 2
        assert finding.kind == "nested"
        assert finding.detail == "inner() — nested function"
        assert finding.node is inner
        assert finding.new_text is None
        assert finding.remove is True

    def test_strip_obvious_init_finding_fields_exact(self) -> None:
        src = (
            'class C:\n    def __init__(self, x: int) -> None:\n        """Init."""\n        pass\n'
        )
        tree = ast.parse(src)
        DocstringStreamliner._annotate_parents(tree)
        cls = tree.body[0]
        assert isinstance(cls, ast.ClassDef)
        init_node = cls.body[0]
        assert isinstance(init_node, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            init_node, Path("f.py"), DocstringStripOptions(False, False, False, True)
        )
        assert finding is not None
        assert finding.line == 2
        assert finding.kind == "obvious_init"
        assert finding.detail == "__init__ — all params have type annotations"
        assert finding.node is init_node
        assert finding.new_text is None
        assert finding.remove is True

    def test_redundant_args_and_returns_finding_exact(self) -> None:
        src = (
            'def f(x: int) -> int:\n    """Summary.\n\nArgs:\n    x: int\n'
            '\nReturns:\n    int"""\n    return x\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.line == 1
        assert finding.kind == "redundant"
        assert finding.detail == "removed redundant section(s): Args, Returns"
        assert finding.node is node
        assert finding.new_text == "Summary."
        assert finding.remove is False

    def test_returns_before_args_both_removed_finding_exact(self) -> None:
        src = (
            'def f(x: int) -> int:\n    """Summary.\n\nReturns:\n    int\n'
            '\nArgs:\n    x: int"""\n    return x\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.detail == "removed redundant section(s): Returns, Args"
        assert finding.new_text == "Summary."

    def test_arguments_header_redundant_removed(self) -> None:
        src = 'def f(x: int) -> None:\n    """Summary.\n\nArguments:\n    x: int"""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.detail == "removed redundant section(s): Args"
        assert finding.new_text == "Summary."

    def test_parameters_header_redundant_removed(self) -> None:
        src = 'def f(x: int) -> None:\n    """Summary.\n\nParameters:\n    x: int"""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.detail == "removed redundant section(s): Args"
        assert finding.new_text == "Summary."

    def test_meaningful_returns_section_kept(self) -> None:
        src = (
            'def f(x: int) -> int:\n    """Summary.\n\nReturns:\n'
            '    the computed count"""\n    return x\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is None

    # --- Tests for DocstringStreamliner.process_file(). ---

    def test_strip_private_in_file(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text('def _helper() -> None:\n    """Helper."""\n    pass\n', encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(True, False, False, False)
        )
        assert len(report.findings) == 1
        assert report.findings[0].kind == "private"

    # --- Tests for DocstringStreamliner.apply_edits(). ---

    def test_remove_redundant_args(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = 'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Args:" not in result
        assert "Summary." in result
        assert result == 'def f(x: int) -> None:\n    """Summary."""\n    pass\n'

    def test_apply_edits_single_quoted_docstring_exact(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = "def f(x: int) -> None:\n    '''Summary.\n\nArgs:\n    x: int'''\n    pass\n"
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert result == "def f(x: int) -> None:\n    '''Summary.'''\n    pass\n"

    def test_apply_edits_two_findings_bottom_up_exact(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = (
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
            "\n"
            'def g(y: str) -> None:\n    """Doc.\n\nArgs:\n    y: str"""\n    pass\n'
        )
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        assert len(report.findings) == 2
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert result == (
            'def f(x: int) -> None:\n    """Summary."""\n    pass\n'
            "\n"
            'def g(y: str) -> None:\n    """Doc."""\n    pass\n'
        )

    def test_remove_obsolete_docstring_with_pass(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = 'def f(x: int) -> int:\n    """\nArgs:\n    x: int\nReturns:\n    int"""\n'
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "pass" in result
        assert result == "def f(x: int) -> int:\n    pass\n"

    def test_remove_obsolete_docstring_with_other_stmts(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = (
            'def f(x: int) -> int:\n    """\nArgs:\n    x: int\n'
            'Returns:\n    int"""\n    return x\n'
        )
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "return x" in result
        assert result == "def f(x: int) -> int:\n    return x\n"

    def test_strip_private_apply(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = 'def _helper() -> None:\n    """Helper."""\n    pass\n'
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(True, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Helper" not in result
        assert result == "def _helper() -> None:\n    pass\n"

    def test_remove_docstring_strips_trailing_blank(self, tmp_path: Path) -> None:
        """When a docstring is removed and a blank line follows, the blank is also removed."""
        src = tmp_path / "mod.py"
        original = (
            'def f(x: int) -> int:\n    """\nArgs:\n    x: int\n'
            'Returns:\n    int"""\n\n    return x\n'
        )
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Args:" not in result
        assert "return x" in result
        assert "\n\n\n" not in result
        assert result == "def f(x: int) -> int:\n    return x\n"

    def test_replace_docstring_no_trailing_newline(self, tmp_path: Path) -> None:
        """When the last docstring line has no trailing newline, the replacement preserves it."""
        src = tmp_path / "mod.py"
        original = 'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""'
        src.write_bytes(original.encode("utf-8"))
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Args:" not in result
        assert "Summary." in result
        assert not result.endswith("\n")
        assert result == 'def f(x: int) -> None:\n    """Summary."""'

    # --- Tests for DocstringStreamliner.main(). ---

    def test_strip_private_setting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"docstring_strip_private": True}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def _helper() -> None:\n    """Helper."""\n    pass\n', encoding="utf-8"
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Private" in out

    def test_strip_tests_setting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"docstring_strip_tests": True}})
        src = tmp_path / "src"
        tests = src / "tests"
        tests.mkdir(parents=True)
        (tests / "test_mod.py").write_text(
            'def test_foo() -> None:\n    """Test foo."""\n    pass\n', encoding="utf-8"
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Test function" in out

    def test_strip_nested_setting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"docstring_strip_nested": True}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def outer():\n    def inner():\n        """Nested."""\n        pass\n    pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Nested" in out

    def test_strip_obvious_init_setting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"docstring_strip_obvious_init": True}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class C:\n    def __init__(self, x: int) -> None:\n"
            '        """Init."""\n        pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "obvious" in out.lower()
