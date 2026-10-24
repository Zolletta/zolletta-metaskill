"""Tests for DocstringStreamliner — split from TestDocstringStreamliner."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.docstring_report_writer import DocstringReportWriter
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


class TestDocstringStreamlinerPredicates:
    """Tests for DocstringStreamliner (predicates), split from TestDocstringStreamliner."""

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

    # --- Tests for DocstringStreamliner._is_section_header(). ---

    def test_is_section_header_args_header_returns_true(self) -> None:
        assert DocstringStreamliner._is_section_header("Args:") is True

    def test_is_section_header_returns_header_returns_true(self) -> None:
        assert DocstringStreamliner._is_section_header("Returns:") is True

    def test_is_section_header_no_colon_returns_false(self) -> None:
        assert DocstringStreamliner._is_section_header("Args") is False

    def test_is_section_header_unknown_section_returns_false(self) -> None:
        assert DocstringStreamliner._is_section_header("Foo:") is False

    def test_is_section_header_case_insensitive_returns_true(self) -> None:
        assert DocstringStreamliner._is_section_header("ARGS:") is True

    def test_is_section_header_empty_line_returns_false(self) -> None:
        assert DocstringStreamliner._is_section_header("") is False

    def test_is_section_header_tab_indented_returns_false(self) -> None:
        assert DocstringStreamliner._is_section_header("\tArgs:") is False

    # --- Tests for DocstringStreamliner._arg_name_from_entry(). ---

    def test_name_with_type(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("x (int)") == "x"

    # --- Tests for DocstringStreamliner.is_trivial_arg_desc(). ---

    def test_is_trivial_arg_desc_meaningful_desc_returns_false(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "the number of items", "int") is False

    # --- Tests for DocstringStreamliner.is_trivial_returns_desc(). ---

    def test_is_trivial_returns_desc_meaningful_desc_returns_false(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("the count", "int") is False

    # --- Tests for DocstringStreamliner._is_private(). ---

    def test_is_private_private_name_returns_true(self) -> None:
        assert DocstringStreamliner._is_private("_helper") is True

    def test_is_private_public_name_returns_false(self) -> None:
        assert DocstringStreamliner._is_private("helper") is False

    # --- Tests for DocstringStreamliner._is_test_function(). ---

    def test_is_test_function_test_function_returns_true(self) -> None:
        assert DocstringStreamliner._is_test_function("test_foo") is True

    def test_not_test_function(self) -> None:
        assert DocstringStreamliner._is_test_function("foo") is False

    # --- Tests for DocstringStreamliner._is_test_file(). ---

    def test_test_file_by_name(self) -> None:
        assert DocstringStreamliner._is_test_file(Path("test_foo.py")) is True

    def test_test_file_by_dir(self) -> None:
        assert DocstringStreamliner._is_test_file(Path("tests/foo.py")) is True

    def test_not_test_file(self) -> None:
        assert DocstringStreamliner._is_test_file(Path("src/foo.py")) is False

    # --- Tests for DocstringStreamliner._is_nested(). ---

    def test_top_level_not_nested(self) -> None:
        tree = ast.parse("def f(): pass")
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        assert DocstringStreamliner._is_nested(node) is False

    # --- Tests for DocstringStreamliner._returns_section_is_redundant(). ---

    def test_trivial_equals_annotation(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["int"], "int") is True

    # --- Tests for DocstringStreamliner._analyze_function(). ---

    def test_protected_sections_kept(self) -> None:
        src = (
            'def f(x: int) -> int:\n    """Summary.\n\nArgs:\n    x: int\n'
            '\nRaises:\n    ValueError: bad"""\n    return x\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert "Args" in finding.detail
        assert "Raises" not in finding.detail

    # --- Tests for DocstringStreamliner.process_file(). ---

    def test_file_with_findings(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        assert len(report.findings) == 1
        assert report.findings[0].kind == "redundant"

    def test_file_no_findings(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text('def f(x: int) -> None:\n    """Summary."""\n    pass\n', encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        assert len(report.findings) == 0

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text("def f(:\n    pass\n", encoding="utf-8")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        assert len(report.findings) == 0

    def test_unicode_decode_error(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_bytes(b"\xff\xfe\x00def f(): pass\n")
        report = DocstringStreamliner.process_file(
            src, DocstringStripOptions(False, False, False, False)
        )
        assert len(report.findings) == 0

    # --- Tests for DocstringReportWriter._rel(). ---

    def test_rel_relative_path_returns_foo_py(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert DocstringReportWriter._rel(Path("src/foo.py").resolve()) == "src/foo.py"

    def test_rel_not_relative_returns_other_foo_py(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert DocstringReportWriter._rel(Path("/other/foo.py")) == "/other/foo.py"

    # --- Tests for DocstringStreamliner.main(). ---

    def test_missing_src_reports_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured Python source directories" in err

    def test_syntax_error_file_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("def f(:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0
