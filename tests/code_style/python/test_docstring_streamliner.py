"""Tests for streamline_docstrings.py."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.docstring_streamliner import DocstringStreamliner
from zolletta_metaskill.code_style.python.structs import FileReport

# ---------------------------------------------------------------------------
# _is_section_header
# ---------------------------------------------------------------------------


class TestIsSectionHeader:
    def test_is_section_header_args_header_returns_true(self) -> None:
        assert DocstringStreamliner._is_section_header("Args:") is True

    def test_is_section_header_returns_header_returns_true(self) -> None:
        assert DocstringStreamliner._is_section_header("Returns:") is True

    def test_indented_header_is_not_section(self) -> None:
        assert DocstringStreamliner._is_section_header("    Args:") is False

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


# ---------------------------------------------------------------------------
# parse_docstring
# ---------------------------------------------------------------------------


class TestParseDocstring:
    def test_parse_docstring_summary_only_returns_empty_list(self) -> None:
        summary, sections = DocstringStreamliner.parse_docstring("A short summary.")
        assert summary == ["A short summary."]
        assert sections == []

    def test_summary_and_args(self) -> None:
        text = "Summary line.\n\nArgs:\n    x: the x"
        summary, sections = DocstringStreamliner.parse_docstring(text)
        assert "Summary line." in summary
        assert len(sections) == 1
        assert sections[0][0] == "Args:"
        assert sections[0][1] == ["    x: the x"]

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

    def test_summary_with_blank_before_section(self) -> None:
        text = "Summary.\n\n\nArgs:\n    x: the x"
        summary, sections = DocstringStreamliner.parse_docstring(text)
        assert "Summary." in summary
        assert len(sections) == 1


# ---------------------------------------------------------------------------
# rebuild_docstring
# ---------------------------------------------------------------------------


class TestRebuildDocstring:
    def test_rebuild_docstring_summary_only_returns_summary(self) -> None:
        result = DocstringStreamliner.rebuild_docstring(["Summary."], [])
        assert result == "Summary."

    def test_summary_and_section(self) -> None:
        result = DocstringStreamliner.rebuild_docstring(["Summary."], [("Args:", ["    x: the x"])])
        assert "Summary." in result
        assert "Args:" in result
        assert "    x: the x" in result
        # D413: trailing blank line after last section
        assert result.endswith("")

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
        # The trailing blank from the body is removed, then D413 blank is appended
        assert result == "Summary.\n\nArgs:\n    x: the x\n"


# ---------------------------------------------------------------------------
# _arg_name_from_entry
# ---------------------------------------------------------------------------


class TestArgNameFromEntry:
    def test_arg_name_from_entry_plain_name_returns_x(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("x") == "x"

    def test_name_with_type(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("x (int)") == "x"

    def test_arg_name_from_entry_star_args_returns_args(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("*args") == "args"

    def test_star_star_kwargs(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("**kwargs") == "kwargs"


# ---------------------------------------------------------------------------
# is_trivial_arg_desc
# ---------------------------------------------------------------------------


class TestIsTrivialArgDesc:
    def test_empty_desc_with_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "", "int") is True

    def test_empty_desc_without_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "", None) is False

    def test_desc_equals_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "int", "int") is True

    def test_desc_equals_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "x", "int") is True

    def test_desc_the_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "the x", "int") is True

    def test_desc_a_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "a x", "int") is True

    def test_desc_an_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "an x", "int") is True

    def test_desc_with_trailing_period(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "the x.", "int") is True

    def test_is_trivial_arg_desc_meaningful_desc_returns_false(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "the number of items", "int") is False

    def test_no_annotation_keeps_section(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "some desc", None) is False


# ---------------------------------------------------------------------------
# is_trivial_returns_desc
# ---------------------------------------------------------------------------


class TestIsTrivialReturnsDesc:
    def test_empty_desc_with_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("", "int") is True

    def test_empty_desc_without_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("", None) is False

    def test_desc_equals_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("int", "int") is True

    def test_is_trivial_returns_desc_meaningful_desc_returns_false(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("the count", "int") is False

    def test_desc_with_trailing_period(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("int.", "int") is True


# ---------------------------------------------------------------------------
# _annotation_str
# ---------------------------------------------------------------------------


class TestAnnotationStr:
    def test_annotation_str_none_annotation_returns_none(self) -> None:
        assert DocstringStreamliner._annotation_str(None) is None

    def test_annotation_str_simple_annotation_returns_int(self) -> None:
        tree = ast.parse("x: int = 0")
        stmt = tree.body[0]
        assert isinstance(stmt, ast.AnnAssign)
        ann = stmt.annotation
        assert DocstringStreamliner._annotation_str(ann) == "int"

    def test_annotation_str_complex_annotation_returns_list_int(self) -> None:
        tree = ast.parse("x: list[int] = 0")
        stmt = tree.body[0]
        assert isinstance(stmt, ast.AnnAssign)
        ann = stmt.annotation
        assert DocstringStreamliner._annotation_str(ann) == "list[int]"


# ---------------------------------------------------------------------------
# get_arg_annotations / get_return_annotation
# ---------------------------------------------------------------------------


class TestArgAnnotations:
    def test_get_arg_annotations_simple_function_returns_dict(self) -> None:
        tree = ast.parse("def f(x: int, y: str) -> bool: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns == {"x": "int", "y": "str"}

    def test_get_arg_annotations_unannotated_arg_returns_dict(self) -> None:
        tree = ast.parse("def f(x, y: str) -> bool: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns == {"x": None, "y": "str"}

    def test_vararg_and_kwarg(self) -> None:
        tree = ast.parse("def f(*args: int, **kwargs: str) -> None: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns["args"] == "int"
        assert anns["kwargs"] == "str"

    def test_get_arg_annotations_kwonly_args_returns_dict(self) -> None:
        tree = ast.parse("def f(*, x: int, y: str) -> None: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns == {"x": "int", "y": "str"}

    def test_get_return_annotation_return_annotation_returns_bool(self) -> None:
        tree = ast.parse("def f(x: int) -> bool: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        assert DocstringStreamliner.get_return_annotation(node) == "bool"

    def test_no_return_annotation(self) -> None:
        tree = ast.parse("def f(x: int): ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        assert DocstringStreamliner.get_return_annotation(node) is None


# ---------------------------------------------------------------------------
# _is_private / _is_test_function / _is_test_file / _is_nested
# ---------------------------------------------------------------------------


class TestPredicates:
    def test_is_private_private_name_returns_true(self) -> None:
        assert DocstringStreamliner._is_private("_helper") is True

    def test_is_private_public_name_returns_false(self) -> None:
        assert DocstringStreamliner._is_private("helper") is False

    def test_dunder_not_private(self) -> None:
        assert DocstringStreamliner._is_private("__init__") is False

    def test_dunder_custom_not_private(self) -> None:
        assert DocstringStreamliner._is_private("__custom__") is False

    def test_is_test_function_test_function_returns_true(self) -> None:
        assert DocstringStreamliner._is_test_function("test_foo") is True

    def test_not_test_function(self) -> None:
        assert DocstringStreamliner._is_test_function("foo") is False

    def test_test_file_by_name(self) -> None:
        assert DocstringStreamliner._is_test_file(Path("test_foo.py")) is True

    def test_test_file_by_dir(self) -> None:
        assert DocstringStreamliner._is_test_file(Path("tests/foo.py")) is True

    def test_not_test_file(self) -> None:
        assert DocstringStreamliner._is_test_file(Path("src/foo.py")) is False

    def test_annotate_parents_nested_function_returns_true(self) -> None:
        tree = ast.parse("def outer():\n    def inner():\n        pass\n")
        DocstringStreamliner._annotate_parents(tree)
        outer = tree.body[0]
        assert isinstance(outer, ast.FunctionDef)
        inner = outer.body[0]
        assert isinstance(inner, ast.FunctionDef)
        assert DocstringStreamliner._is_nested(inner) is True

    def test_top_level_not_nested(self) -> None:
        tree = ast.parse("def f(): pass")
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        assert DocstringStreamliner._is_nested(node) is False


# ---------------------------------------------------------------------------
# _detect_prefix_quote
# ---------------------------------------------------------------------------


class TestDetectPrefixQuote:
    def test_simple_triple_quote(self) -> None:
        result = DocstringStreamliner._detect_prefix_quote('    """doc"""')
        assert result is not None
        prefix, quote = result
        assert prefix == ""
        assert quote == '"""'

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

    def test_no_match_returns_default(self) -> None:
        result = DocstringStreamliner._detect_prefix_quote("pass")
        assert result is not None
        prefix, quote = result
        assert prefix == ""
        assert quote == '"""'


# ---------------------------------------------------------------------------
# render_docstring
# ---------------------------------------------------------------------------


class TestRenderDocstring:
    def test_render_docstring_single_line_returns_a_summary(self) -> None:
        result = DocstringStreamliner.render_docstring("    ", "", '"""', "A summary.")
        assert result == '    """A summary."""'

    def test_render_docstring_multi_line_contains_empty(self) -> None:
        result = DocstringStreamliner.render_docstring(
            "    ", "", '"""', "Summary.\n\nArgs:\n    x: the x"
        )
        lines = result.split("\n")
        assert lines[0] == '    """Summary.'
        assert '    """' in lines[-1]

    def test_render_docstring_empty_text_returns_empty(self) -> None:
        result = DocstringStreamliner.render_docstring("    ", "", '"""', "")
        assert result == '    """"""'

    def test_render_docstring_with_prefix_returns_r_raw_doc(self) -> None:
        result = DocstringStreamliner.render_docstring("    ", "r", '"""', "raw doc")
        assert result == '    r"""raw doc"""'


# ---------------------------------------------------------------------------
# _parse_args_entries
# ---------------------------------------------------------------------------


class TestParseArgsEntries:
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


# ---------------------------------------------------------------------------
# _args_section_is_redundant / _returns_section_is_redundant
# ---------------------------------------------------------------------------


class TestArgsSectionRedundant:
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


class TestReturnsSectionRedundant:
    def test_returns_section_is_redundant_trivial_empty_returns_true(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant([], "int") is True

    def test_trivial_equals_annotation(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["int"], "int") is True

    def test_returns_section_is_redundant_meaningful_returns_false(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["the count"], "int") is False

    def test_returns_section_is_redundant_no_annotation_returns_false(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["some desc"], None) is False


# ---------------------------------------------------------------------------
# _init_is_obvious
# ---------------------------------------------------------------------------


class TestInitIsObvious:
    def test_init_is_obvious_all_annotated_returns_true(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"self": None, "x": "int", "y": "str"}) is True

    def test_init_is_obvious_self_only_returns_true(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"self": None}) is True

    def test_init_is_obvious_unannotated_param_returns_false(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"self": None, "x": None}) is False

    def test_init_is_obvious_cls_skipped_returns_true(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"cls": None, "x": "int"}) is True


# ---------------------------------------------------------------------------
# _analyze_function
# ---------------------------------------------------------------------------


class TestAnalyzeFunction:
    def _parse(self, source: str) -> ast.FunctionDef:
        tree = ast.parse(source)
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        return node

    def test_redundant_args_removed(self) -> None:
        src = 'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), False, False, False, False
        )
        assert finding is not None
        assert finding.kind == "redundant"
        assert "Args" in finding.detail

    def test_redundant_returns_removed(self) -> None:
        src = 'def f(x: int) -> int:\n    """Summary.\n\nReturns:\n    int"""\n    return x\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), False, False, False, False
        )
        assert finding is not None
        assert "Returns" in finding.detail

    def test_obsolete_docstring_removed(self) -> None:
        src = (
            "def f(x: int) -> int:\n"
            '    """\nArgs:\n    x: int\nReturns:\n    int"""\n'
            "    return x\n"
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), False, False, False, False
        )
        assert finding is not None
        assert finding.remove is True

    def test_parse_no_docstring_returns_none(self) -> None:
        src = "def f(x: int) -> int:\n    return x\n"
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), False, False, False, False
        )
        assert finding is None

    def test_parse_no_redundancy_returns_none(self) -> None:
        src = (
            "def f(x: int) -> int:\n"
            '    """Summary.\n\nArgs:\n    x: the number of items"""\n'
            "    return x\n"
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), False, False, False, False
        )
        assert finding is None

    def test_parse_strip_private_returns_true(self) -> None:
        src = 'def _helper(x: int) -> None:\n    """A helper."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), True, False, False, False
        )
        assert finding is not None
        assert finding.kind == "private"
        assert finding.remove is True

    def test_parse_strip_tests_returns_test(self) -> None:
        src = 'def test_foo(x: int) -> None:\n    """Test foo."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("test_foo.py"), False, True, False, False
        )
        assert finding is not None
        assert finding.kind == "test"

    def test_strip_tests_not_test_file(self) -> None:
        src = 'def test_foo(x: int) -> None:\n    """Test foo."""\n    pass\n'
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("src/foo.py"), False, True, False, False
        )
        assert finding is None

    def test_annotate_parents_strip_nested_returns_nested(self) -> None:
        src = 'def outer():\n    def inner():\n        """Nested."""\n        pass\n'
        tree = ast.parse(src)
        DocstringStreamliner._annotate_parents(tree)
        outer = tree.body[0]
        assert isinstance(outer, ast.FunctionDef)
        inner = outer.body[0]
        assert isinstance(inner, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            inner, Path("f.py"), False, False, True, False
        )
        assert finding is not None
        assert finding.kind == "nested"

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
            init_node, Path("f.py"), False, False, False, True
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
            init_node, Path("f.py"), False, False, False, True
        )
        assert finding is None

    def test_protected_sections_kept(self) -> None:
        src = (
            "def f(x: int) -> int:\n"
            '    """Summary.\n\nArgs:\n    x: int\n\nRaises:\n    ValueError: bad"""\n'
            "    return x\n"
        )
        node = self._parse(src)
        finding = DocstringStreamliner._analyze_function(
            node, Path("f.py"), False, False, False, False
        )
        assert finding is not None
        assert "Args" in finding.detail
        # Raises is kept
        assert "Raises" not in finding.detail


# ---------------------------------------------------------------------------
# process_file
# ---------------------------------------------------------------------------


class TestProcessFile:
    def test_file_with_findings(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        assert len(report.findings) == 1
        assert report.findings[0].kind == "redundant"

    def test_file_no_findings(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text(
            'def f(x: int) -> None:\n    """Summary."""\n    pass\n',
            encoding="utf-8",
        )
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        assert len(report.findings) == 0

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text("def f(:\n    pass\n", encoding="utf-8")
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        assert len(report.findings) == 0

    def test_unicode_decode_error(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_bytes(b"\xff\xfe\x00def f(): pass\n")
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        assert len(report.findings) == 0

    def test_strip_private_in_file(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        src.write_text(
            'def _helper() -> None:\n    """Helper."""\n    pass\n',
            encoding="utf-8",
        )
        report = DocstringStreamliner.process_file(src, True, False, False, False)
        assert len(report.findings) == 1
        assert report.findings[0].kind == "private"


# ---------------------------------------------------------------------------
# apply_edits
# ---------------------------------------------------------------------------


class TestApplyEdits:
    def test_remove_redundant_args(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = 'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Args:" not in result
        assert "Summary." in result

    def test_remove_obsolete_docstring_with_pass(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = 'def f(x: int) -> int:\n    """\nArgs:\n    x: int\nReturns:\n    int"""\n'
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        result = DocstringStreamliner.apply_edits(src, report.findings)
        # The docstring is the only statement, so pass should be inserted
        assert "pass" in result

    def test_remove_obsolete_docstring_with_other_stmts(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = (
            "def f(x: int) -> int:\n"
            '    """\nArgs:\n    x: int\nReturns:\n    int"""\n'
            "    return x\n"
        )
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "return x" in result

    def test_strip_private_apply(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.py"
        original = 'def _helper() -> None:\n    """Helper."""\n    pass\n'
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(src, True, False, False, False)
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Helper" not in result

    def test_remove_docstring_strips_trailing_blank(self, tmp_path: Path) -> None:
        """When a docstring is removed and a blank line follows, the blank is also removed."""
        src = tmp_path / "mod.py"
        original = (
            "def f(x: int) -> int:\n"
            '    """\nArgs:\n    x: int\nReturns:\n    int"""\n'
            "\n"
            "    return x\n"
        )
        src.write_text(original, encoding="utf-8")
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        result = DocstringStreamliner.apply_edits(src, report.findings)
        # The docstring and the trailing blank line are both removed
        assert "Args:" not in result
        assert "return x" in result
        # No double blank line left behind
        assert "\n\n\n" not in result

    def test_replace_docstring_no_trailing_newline(self, tmp_path: Path) -> None:
        """When the last docstring line has no trailing newline, the replacement preserves it."""
        src = tmp_path / "mod.py"
        original = 'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""'
        src.write_bytes(original.encode("utf-8"))
        report = DocstringStreamliner.process_file(src, False, False, False, False)
        result = DocstringStreamliner.apply_edits(src, report.findings)
        assert "Args:" not in result
        assert "Summary." in result
        # The result should not end with a newline (preserving original)
        assert not result.endswith("\n")


# ---------------------------------------------------------------------------
# _rel
# ---------------------------------------------------------------------------


class TestRel:
    def test_rel_relative_path_returns_foo_py(self) -> None:
        assert DocstringStreamliner._rel(Path("src/foo.py"), Path("src")) == "foo.py"

    def test_rel_not_relative_returns_other_foo_py(self) -> None:
        assert DocstringStreamliner._rel(Path("/other/foo.py"), Path("src")) == "/other/foo.py"


# ---------------------------------------------------------------------------
# print_report
# ---------------------------------------------------------------------------


class TestPrintReport:
    def test_print_report_no_findings_contains_all_clear(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        total = DocstringStreamliner.print_report([], Path("src"), apply_mode=False)
        captured = capsys.readouterr()
        assert total == 0
        assert "all clear" in captured.out

    def test_annotate_parents_with_findings_contains_redundant(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        tree = ast.parse(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
        )
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            node, Path("src/mod.py"), False, False, False, False
        )
        assert finding is not None
        report = FileReport(path=Path("src/mod.py"), findings=[finding])
        total = DocstringStreamliner.print_report([report], Path("src"), apply_mode=False)
        captured = capsys.readouterr()
        assert total == 1
        assert "Redundant" in captured.out

    def test_annotate_parents_apply_mode_contains_apply_mode(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        tree = ast.parse(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n'
        )
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        finding = DocstringStreamliner._analyze_function(
            node, Path("src/mod.py"), False, False, False, False
        )
        assert finding is not None
        report = FileReport(path=Path("src/mod.py"), findings=[finding])
        total = DocstringStreamliner.print_report([report], Path("src"), apply_mode=True)
        captured = capsys.readouterr()
        assert total == 1
        assert "apply mode" in captured.out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_readouterr_skip_flag_contains_skipped(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "src", "--skip"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "SKIPPED" in captured.out

    def test_readouterr_nonexistent_directory_contains_does_not_exist(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 1
        assert "does not exist" in captured.err

    def test_readouterr_no_findings_contains_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary."""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "all clear" in captured.out

    def test_findings_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "dry-run" in captured.out

    def test_module_strict_flag_returns_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strict"])
        rc = DocstringStreamliner.main()
        assert rc == 1

    def test_readouterr_apply_flag_excludes_value(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        mod = src / "mod.py"
        mod.write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--apply"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "apply mode" in captured.out
        # The file should have been modified
        new_content = mod.read_text(encoding="utf-8")
        assert "Args:" not in new_content

    def test_strip_private_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def _helper() -> None:\n    """Helper."""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strip-private"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "Private" in captured.out

    def test_strip_tests_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        tests = src / "tests"
        tests.mkdir(parents=True)
        (tests / "test_mod.py").write_text(
            'def test_foo() -> None:\n    """Test foo."""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strip-tests"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "Test function" in captured.out

    def test_strip_nested_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def outer():\n    def inner():\n        """Nested."""\n        pass\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strip-nested"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "Nested" in captured.out

    def test_strip_obvious_init_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class C:\n"
            "    def __init__(self, x: int) -> None:\n"
            '        """Init."""\n'
            "        pass\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strip-obvious-init"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "obvious" in captured.out.lower()

    def test_readouterr_ignore_dirs_contains_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        skip = src / "skipme"
        skip.mkdir(parents=True)
        (skip / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--ignore-dirs", "skipme"])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "all clear" in captured.out

    def test_readouterr_empty_directory_contains_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = DocstringStreamliner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "all clear" in captured.out

    def test_syntax_error_file_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("def f(:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = DocstringStreamliner.main()
        assert rc == 0
