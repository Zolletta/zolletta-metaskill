"""Tests for DocstringStreamliner — split from TestDocstringStreamliner."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.docstring_report_writer import DocstringReportWriter
from zolletta_metaskill.code_style.python.docstring_streamliner import DocstringStreamliner
from zolletta_metaskill.code_style.python.structs import DocstringStripOptions, FileReport


class TestDocstringStreamlinerRendering:
    """Tests for DocstringStreamliner (rendering), split from TestDocstringStreamliner."""

    # --- Tests for DocstringStreamliner.parse_docstring(). ---

    def test_summary_and_args(self) -> None:
        text = "Summary line.\n\nArgs:\n    x: the x"
        summary, sections = DocstringStreamliner.parse_docstring(text)
        assert "Summary line." in summary
        assert len(sections) == 1
        assert sections[0][0] == "Args:"
        assert sections[0][1] == ["    x: the x"]

    def test_summary_with_blank_before_section(self) -> None:
        text = "Summary.\n\n\nArgs:\n    x: the x"
        summary, sections = DocstringStreamliner.parse_docstring(text)
        assert "Summary." in summary
        assert len(sections) == 1

    # --- Tests for DocstringStreamliner.rebuild_docstring(). ---

    def test_rebuild_docstring_summary_only_returns_summary(self) -> None:
        result = DocstringStreamliner.rebuild_docstring(["Summary."], [])
        assert result == "Summary."

    def test_summary_and_section(self) -> None:
        result = DocstringStreamliner.rebuild_docstring(["Summary."], [("Args:", ["    x: the x"])])
        assert "Summary." in result
        assert "Args:" in result
        assert "    x: the x" in result
        assert result.endswith("")

    # --- Tests for DocstringStreamliner._arg_name_from_entry(). ---

    def test_star_star_kwargs(self) -> None:
        assert DocstringStreamliner._arg_name_from_entry("**kwargs") == "kwargs"

    # --- Tests for DocstringStreamliner.is_trivial_arg_desc(). ---

    def test_desc_equals_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "x", "int") is True

    def test_desc_the_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "the x", "int") is True

    def test_desc_a_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "a x", "int") is True

    def test_desc_an_arg_name(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "an x", "int") is True

    # --- Tests for DocstringStreamliner.is_trivial_returns_desc(). ---

    def test_returns_empty_desc_with_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("", "int") is True

    def test_returns_empty_desc_without_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("", None) is False

    def test_returns_desc_equals_annotation(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("int", "int") is True

    def test_returns_desc_with_trailing_period(self) -> None:
        assert DocstringStreamliner.is_trivial_returns_desc("int.", "int") is True

    # --- Tests for DocstringStreamliner._annotation_str(). ---

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

    # --- Tests for DocstringStreamliner.get_arg_annotations(). ---

    def test_vararg_and_kwarg(self) -> None:
        tree = ast.parse("def f(*args: int, **kwargs: str) -> None: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns["args"] == "int"
        assert anns["kwargs"] == "str"

    # --- Tests for DocstringStreamliner._is_private(). ---

    def test_dunder_not_private(self) -> None:
        assert DocstringStreamliner._is_private("__init__") is False

    def test_dunder_custom_not_private(self) -> None:
        assert DocstringStreamliner._is_private("__custom__") is False

    # --- Tests for DocstringStreamliner._annotate_parents() and _is_nested(). ---

    def test_annotate_parents_nested_function_returns_true(self) -> None:
        tree = ast.parse("def outer():\n    def inner():\n        pass\n")
        DocstringStreamliner._annotate_parents(tree)
        outer = tree.body[0]
        assert isinstance(outer, ast.FunctionDef)
        inner = outer.body[0]
        assert isinstance(inner, ast.FunctionDef)
        assert DocstringStreamliner._is_nested(inner) is True

    # --- Tests for DocstringStreamliner._detect_prefix_quote(). ---

    def test_simple_triple_quote(self) -> None:
        result = DocstringStreamliner._detect_prefix_quote('    """doc"""')
        assert result is not None
        prefix, quote = result
        assert prefix == ""
        assert quote == '"""'

    # --- Tests for DocstringStreamliner.render_docstring(). ---

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

    def test_render_docstring_leading_blank_line_renders_multiline(self) -> None:
        result = DocstringStreamliner.render_docstring("    ", "", '"""', "\nx")
        assert result == '    """\n    x\n    """'

    def test_render_docstring_three_lines_exact(self) -> None:
        result = DocstringStreamliner.render_docstring("    ", "", '"""', "a\nb\nc")
        assert result == '    """a\n    b\n    c\n    """'

    def test_render_docstring_blank_middle_line_exact(self) -> None:
        result = DocstringStreamliner.render_docstring("    ", "", '"""', "a\n\nb")
        assert result == '    """a\n\n    b\n    """'

    # --- Tests for DocstringStreamliner._returns_section_is_redundant(). ---

    def test_returns_section_is_redundant_trivial_empty_returns_true(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant([], "int") is True

    def test_returns_section_is_redundant_two_line_trivial_returns_true(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["int", ""], "int") is True

    def test_returns_section_is_redundant_meaningful_returns_false(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["the count"], "int") is False

    def test_returns_section_is_redundant_no_annotation_returns_false(self) -> None:
        assert DocstringStreamliner._returns_section_is_redundant(["some desc"], None) is False

    # --- Tests for DocstringStreamliner._analyze_function(). ---

    def test_annotate_parents_strip_nested_returns_nested(self) -> None:
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
        assert finding.kind == "nested"

    # --- Tests for DocstringReportWriter.print_report(). ---

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
            node, Path("src/mod.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        report = FileReport(path=Path("src/mod.py"), findings=[finding])
        total = DocstringReportWriter.print_report([report], apply_mode=False)
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
            node, Path("src/mod.py"), DocstringStripOptions(False, False, False, False)
        )
        assert finding is not None
        report = FileReport(path=Path("src/mod.py"), findings=[finding])
        total = DocstringReportWriter.print_report([report], apply_mode=True)
        captured = capsys.readouterr()
        assert total == 1
        assert "apply mode" in captured.out
