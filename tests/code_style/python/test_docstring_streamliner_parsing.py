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


class TestDocstringStreamlinerParsing:
    """Tests for DocstringStreamliner (parsing), split from TestDocstringStreamliner."""

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

    def test_indented_header_is_not_section(self) -> None:
        assert DocstringStreamliner._is_section_header("    Args:") is False

    # --- Tests for DocstringStreamliner.parse_docstring(). ---

    def test_parse_docstring_summary_only_returns_empty_list(self) -> None:
        summary, sections = DocstringStreamliner.parse_docstring("A short summary.")
        assert summary == ["A short summary."]
        assert sections == []

    def test_parse_docstring_multiple_sections_returns_returns(self) -> None:
        text = "Summary.\n\nArgs:\n    x: the x\n\nReturns:\n    the result"
        summary, sections = DocstringStreamliner.parse_docstring(text)
        assert len(sections) == 2
        assert sections[0][0] == "Args:"
        assert sections[1][0] == "Returns:"

    def test_trailing_blank_lines_stripped(self) -> None:
        text = "Summary.\n\nArgs:\n    x: the x\n\n\n"
        _, sections = DocstringStreamliner.parse_docstring(text)
        assert sections[0][1] == ["    x: the x"]

    def test_parse_docstring_empty_docstring_returns_empty_list(self) -> None:
        summary, sections = DocstringStreamliner.parse_docstring("")
        assert summary == [""]
        assert sections == []

    # --- Tests for DocstringStreamliner.rebuild_docstring(). ---

    def test_leading_blanks_stripped(self) -> None:
        result = DocstringStreamliner.rebuild_docstring(["", "", "Summary."], [])
        assert result == "Summary."

    def test_trailing_blanks_stripped(self) -> None:
        result = DocstringStreamliner.rebuild_docstring(["Summary.", "", ""], [])
        assert result == "Summary."

    def test_empty_summary_with_section(self) -> None:
        result = DocstringStreamliner.rebuild_docstring([""], [("Args:", ["    x: the x"])])
        assert result.startswith("Args:")

    def test_section_body_trailing_blank_stripped(self) -> None:
        """Trailing blank lines in a section body are stripped by the second while loop."""
        result = DocstringStreamliner.rebuild_docstring(
            ["Summary."], [("Args:", ["    x: the x", ""])]
        )
        assert "Summary." in result
        assert "Args:" in result
        assert "    x: the x" in result
        assert result == "Summary.\n\nArgs:\n    x: the x\n"

    # --- Tests for DocstringStreamliner._arg_name_from_entry(). ---

    def test_arg_name_from_entry_plain_name_returns_x(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("x") == "x"

    def test_arg_name_from_entry_star_args_returns_args(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("*args") == "args"

    # --- Tests for DocstringStreamliner.is_trivial_arg_desc(). ---

    def test_arg_empty_desc_with_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "", "int") is True

    def test_arg_empty_desc_without_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "", None) is False

    def test_arg_desc_equals_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "int", "int") is True

    def test_arg_desc_with_trailing_period(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "the x.", "int") is True

    # --- Tests for DocstringStreamliner._detect_prefix_quote(). ---

    def test_detect_prefix_quote_raw_prefix_returns_empty(self) -> None:
        result = DocstringStreamliner._detect_prefix_quote('    r"""doc"""')
        assert result is not None
        prefix, quote = result
        assert prefix == "r"
        assert quote == '"""'

    def test_detect_prefix_quote_single_quotes_returns_empty(self) -> None:
        result = DocstringStreamliner._detect_prefix_quote("    '''doc'''")
        assert result is not None
        prefix, quote = result
        assert quote == "'''"

    # --- Tests for DocstringStreamliner._parse_args_entries(). ---

    def test_parse_args_entries_single_entry_returns_single_item(self) -> None:
        entries = DocstringStreamliner._parse_args_entries(["    x: the x value"])
        assert entries == [("x", "the x value")]

    def test_parse_args_entries_multiple_entries_returns_2(self) -> None:
        body = ["    x: the x", "    y: the y"]
        entries = DocstringStreamliner._parse_args_entries(body)
        assert len(entries) == 2
        assert entries[0] == ("x", "the x")
        assert entries[1] == ("y", "the y")

    def test_entry_with_type_in_name(self) -> None:
        entries = DocstringStreamliner._parse_args_entries(["    x (int): the x"])
        assert entries[0][0] == "x (int)"

    def test_parse_args_entries_continuation_line_contains_second_line(self) -> None:
        body = ["    x: first line", "        second line"]
        entries = DocstringStreamliner._parse_args_entries(body)
        assert len(entries) == 1
        assert "second line" in entries[0][1]

    def test_parse_args_entries_empty_body_returns_empty_list(self) -> None:
        assert DocstringStreamliner._parse_args_entries([]) == []

    def test_blank_lines_between_entries(self) -> None:
        body = ["    x: the x", "", "    y: the y"]
        entries = DocstringStreamliner._parse_args_entries(body)
        assert len(entries) == 2

    def test_parse_args_entries_leading_blank_line_ignored(self) -> None:
        entries = DocstringStreamliner._parse_args_entries(["", "    x: the x"])
        assert entries == [("x", "the x")]

    def test_parse_args_entries_leading_continuation_without_entry_ignored(self) -> None:
        entries = DocstringStreamliner._parse_args_entries(["        stray", "    x: the x"])
        assert entries == [("x", "the x")]

    # --- Tests for DocstringStreamliner._args_section_is_redundant(). ---

    def test_args_section_is_redundant_all_trivial_returns_true(self) -> None:
        body = ["    x: int", "    y: str"]
        anns: dict[str, str | None] = {"x": "int", "y": "str"}
        assert DocstringStreamliner._args_section_is_redundant(body, anns) is True

    def test_args_section_is_redundant_self_skipped_returns_true(self) -> None:
        body = ["    self: ", "    x: int"]
        anns = {"self": None, "x": "int"}
        assert DocstringStreamliner._args_section_is_redundant(body, anns) is True

    def test_args_section_is_redundant_one_meaningful_returns_false(self) -> None:
        body = ["    x: the number of items"]
        anns: dict[str, str | None] = {"x": "int"}
        assert DocstringStreamliner._args_section_is_redundant(body, anns) is False

    def test_args_section_is_redundant_unannotated_arg_returns_false(self) -> None:
        body = ["    x: some desc"]
        anns: dict[str, str | None] = {"x": None}
        assert DocstringStreamliner._args_section_is_redundant(body, anns) is False

    def test_empty_args_section(self) -> None:
        assert DocstringStreamliner._args_section_is_redundant([], {}) is True

    # --- Tests for DocstringStreamliner._analyze_function(). ---

    def test_parse_no_docstring_returns_none(self) -> None:
        src = "def f(x: int) -> int:\n    return x\n"
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is None

    def test_parse_no_redundancy_returns_none(self) -> None:
        src = (
            'def f(x: int) -> int:\n    """Summary.\n\nArgs:\n'
            '    x: the number of items"""\n    return x\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is None

    def test_parse_strip_private_returns_true(self) -> None:
        src = 'def _helper(x: int) -> None:\n    """A helper."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(True, False, False, False)
        )
        assert finding is not None
        assert finding.kind == "private"
        assert finding.remove is True

    def test_parse_strip_tests_returns_test(self) -> None:
        src = 'def test_foo(x: int) -> None:\n    """Test foo."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("test_foo.py"), DocstringStripOptions(False, True, False, False)
        )
        assert finding is not None
        assert finding.kind == "test"

    # --- Tests for DocstringStreamliner._arg_name_from_entry(). ---

    def test_arg_name_from_entry_two_word_name_returns_both(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("x y") == "x y"

    def test_arg_name_from_entry_uppercase_initial_kept(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("Xabc") == "Xabc"

    # --- Tests for DocstringStreamliner._parse_args_entries(). ---

    def test_parse_args_entries_blank_line_inside_desc_returns_double_space(self) -> None:
        body = ["    x: first", "", "        second"]
        entries = DocstringStreamliner._parse_args_entries(body)
        assert entries == [("x", "first  second")]

    def test_parse_args_entries_continuation_with_colon_stays_in_desc(self) -> None:
        body = ["    x: first", "        note: cont"]
        entries = DocstringStreamliner._parse_args_entries(body)
        assert entries == [("x", "first note: cont")]

    def test_parse_args_entries_multiline_descs_returns_joined(self) -> None:
        body = ["    x: first", "        more", "    y: second", "        part"]
        entries = DocstringStreamliner._parse_args_entries(body)
        assert entries == [("x", "first more"), ("y", "second part")]

    def test_parse_args_entries_colon_in_desc_partitions_first(self) -> None:
        entries = DocstringStreamliner._parse_args_entries(["    x: a: b"])
        assert entries == [("x", "a: b")]

    # --- Tests for DocstringStreamliner._args_section_is_redundant(). ---

    def test_args_section_is_redundant_cls_skipped_returns_true(self) -> None:
        body = ["    cls: whatever", "    x: int"]
        anns: dict[str, str | None] = {"cls": None, "x": "int"}
        assert DocstringStreamliner._args_section_is_redundant(body, anns) is True

    def test_args_section_is_redundant_self_then_meaningful_returns_false(self) -> None:
        body = ["    self: whatever", "    x: the number of items"]
        anns: dict[str, str | None] = {"self": None, "x": "int"}
        assert DocstringStreamliner._args_section_is_redundant(body, anns) is False

    # --- Tests for DocstringStreamliner._analyze_function(). ---

    def test_parse_indented_docstring_redundant_args_removed(self) -> None:
        src = (
            'def f(x: int) -> None:\n    """Summary.\n\n    Args:\n'
            '        x: int\n    """\n    pass\n'
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        assert finding.kind == "redundant"
        assert "Args" in finding.detail

    # --- Tests for DocstringStreamliner.main(). ---

    def test_empty_directory_contains_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
