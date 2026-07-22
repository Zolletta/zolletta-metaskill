"""Comprehensive tests for api_doc_validator.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.documentor.api_doc_validator import (
    SourceSignature,
    _annotation_to_str,
    _classify_undocumented,
    _extract_decorator_names,
    _extract_parameters,
    extract_all_documented_items,
    extract_all_signatures,
    extract_documented_items,
    extract_signatures,
    generate_report,
    main,
    validate_api_docs,
)

# ---------------------------------------------------------------------------
# SourceSignature
# ---------------------------------------------------------------------------


class TestSourceSignature:
    def test_basic_construction(self) -> None:
        sig = SourceSignature(
            name="foo",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
        )
        assert sig.name == "foo"
        assert sig.kind == "function"
        assert sig.decorators == []
        assert sig.is_private is False
        assert sig.parent_class is None
        assert sig.qualified_name == "foo"
        assert sig.is_deprecated is False

    def test_qualified_name_with_parent(self) -> None:
        sig = SourceSignature(
            name="method",
            kind="method",
            file_path="mod.py",
            line_number=5,
            parameters=[],
            parent_class="MyClass",
        )
        assert sig.qualified_name == "MyClass.method"

    def test_is_deprecated_decorator(self) -> None:
        sig = SourceSignature(
            name="old",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
            decorators=["deprecated"],
        )
        assert sig.is_deprecated is True

    def test_is_deprecated_case_insensitive(self) -> None:
        sig = SourceSignature(
            name="old",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
            decorators=["DeprecatED"],
        )
        assert sig.is_deprecated is True

    def test_is_deprecated_no_decorator(self) -> None:
        sig = SourceSignature(
            name="ok",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
            decorators=["staticmethod"],
        )
        assert sig.is_deprecated is False

    def test_to_dict(self) -> None:
        sig = SourceSignature(
            name="foo",
            kind="function",
            file_path="mod.py",
            line_number=10,
            parameters=[{"name": "x"}],
            return_annotation="int",
            decorators=["staticmethod"],
            is_private=True,
            parent_class="Cls",
        )
        d = sig.to_dict()
        assert d["name"] == "foo"
        assert d["qualified_name"] == "Cls.foo"
        assert d["kind"] == "function"
        assert d["line"] == 10
        assert d["parameters"] == [{"name": "x"}]
        assert d["return_annotation"] == "int"
        assert d["is_private"] is True
        assert d["is_deprecated"] is False


# ---------------------------------------------------------------------------
# _annotation_to_str
# ---------------------------------------------------------------------------


class TestAnnotationToStr:
    def test_none(self) -> None:
        assert _annotation_to_str(None) is None

    def test_simple_name(self, tmp_path: Path) -> None:
        src = "def f(x: int) -> str: ...\n"
        p = tmp_path / "m.py"
        p.write_text(src)
        import ast

        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _annotation_to_str(func.args.args[0].annotation) == "int"
        assert _annotation_to_str(func.returns) == "str"

    def test_subscript_annotation(self, tmp_path: Path) -> None:
        import ast

        src = "def f(x: list[int]) -> dict[str, int]: ...\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _annotation_to_str(func.args.args[0].annotation) == "list[int]"

    def test_attribute_annotation(self, tmp_path: Path) -> None:
        import ast

        src = "def f(x: typing.Optional[int]) -> None: ...\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _annotation_to_str(func.args.args[0].annotation) == "typing.Optional[int]"


# ---------------------------------------------------------------------------
# _extract_decorator_names
# ---------------------------------------------------------------------------


class TestExtractDecoratorNames:
    def test_name_decorator(self) -> None:
        import ast

        src = "@staticmethod\ndef f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _extract_decorator_names(func.decorator_list) == ["staticmethod"]

    def test_attribute_decorator(self) -> None:
        import ast

        src = "@app.route\ndef f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _extract_decorator_names(func.decorator_list) == ["app.route"]

    def test_call_decorator_name(self) -> None:
        import ast

        src = "@deprecated\ndef f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _extract_decorator_names(func.decorator_list) == ["deprecated"]

    def test_call_decorator_attribute(self) -> None:
        import ast

        src = "@functools.wraps(f)\ndef g(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _extract_decorator_names(func.decorator_list) == ["functools.wraps"]

    def test_empty(self) -> None:
        import ast

        src = "def f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert _extract_decorator_names(func.decorator_list) == []


# ---------------------------------------------------------------------------
# _extract_parameters
# ---------------------------------------------------------------------------


class TestExtractParameters:
    def test_simple_params(self) -> None:
        import ast

        src = "def f(a, b): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert len(params) == 2
        assert params[0]["name"] == "a"
        assert params[0]["has_default"] is False
        assert params[1]["name"] == "b"

    def test_self_skipped(self) -> None:
        import ast

        src = "def f(self, a): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert len(params) == 1
        assert params[0]["name"] == "a"

    def test_cls_skipped(self) -> None:
        import ast

        src = "def f(cls, a): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert len(params) == 1
        assert params[0]["name"] == "a"

    def test_default_values(self) -> None:
        import ast

        src = "def f(a, b=10, c='x'): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert params[0]["has_default"] is False
        assert params[1]["has_default"] is True
        assert params[1]["default"] == "10"
        assert params[2]["has_default"] is True
        assert params[2]["default"] == "'x'"

    def test_vararg(self) -> None:
        import ast

        src = "def f(a, *args): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert any(p["name"] == "*args" for p in params)

    def test_kwarg(self) -> None:
        import ast

        src = "def f(a, **kwargs): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert any(p["name"] == "**kwargs" for p in params)

    def test_kwonly_args(self) -> None:
        import ast

        src = "def f(a, *, b=1, c): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        kwonly = [p for p in params if p["name"] in ("b", "c")]
        assert len(kwonly) == 2
        b_param = next(p for p in kwonly if p["name"] == "b")
        assert b_param["has_default"] is True
        assert b_param["default"] == "1"
        c_param = next(p for p in kwonly if p["name"] == "c")
        assert c_param["has_default"] is False

    def test_annotation_extracted(self) -> None:
        import ast

        src = "def f(a: int) -> None: pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = _extract_parameters(func)
        assert params[0]["annotation"] == "int"


# ---------------------------------------------------------------------------
# extract_signatures
# ---------------------------------------------------------------------------


class TestExtractSignatures:
    def test_extract_function(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text('"""Module."""\ndef foo(a, b=1):\n    """Doc."""\n    return a\n')
        sigs = extract_signatures(str(p))
        assert len(sigs) == 1
        assert sigs[0].name == "foo"
        assert sigs[0].kind == "function"
        assert sigs[0].docstring == "Doc."

    def test_extract_method(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("class MyClass:\n    def method(self, x):\n        return x\n")
        sigs = extract_signatures(str(p))
        # Should find __init__? No, just method and class
        names = [s.name for s in sigs]
        assert "method" in names
        assert "MyClass" in names
        method = next(s for s in sigs if s.name == "method")
        assert method.kind == "method"
        assert method.parent_class == "MyClass"

    def test_extract_class(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("class MyClass:\n    def __init__(self, a, b):\n        self.a = a\n")
        sigs = extract_signatures(str(p))
        cls = next(s for s in sigs if s.name == "MyClass")
        assert cls.kind == "class"
        param_names = [p["name"] for p in cls.parameters]
        assert "a" in param_names
        assert "b" in param_names
        assert "self" not in param_names

    def test_private_excluded_by_default(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("def _private(): pass\ndef public(): pass\n")
        sigs = extract_signatures(str(p))
        names = [s.name for s in sigs]
        assert "public" in names
        assert "_private" not in names

    def test_private_included_with_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("def _private(): pass\ndef public(): pass\n")
        sigs = extract_signatures(str(p), include_private=True)
        names = [s.name for s in sigs]
        assert "_private" in names
        assert "public" in names

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("def f(:\n")
        sigs = extract_signatures(str(p))
        assert sigs == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        sigs = extract_signatures(str(tmp_path / "nonexistent.py"))
        assert sigs == []

    def test_async_function(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("async def aio():\n    return 1\n")
        sigs = extract_signatures(str(p))
        assert len(sigs) == 1
        assert sigs[0].name == "aio"

    def test_decorators_extracted(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("@deprecated\ndef old(): pass\n")
        sigs = extract_signatures(str(p))
        assert sigs[0].decorators == ["deprecated"]
        assert sigs[0].is_deprecated is True


# ---------------------------------------------------------------------------
# extract_all_signatures
# ---------------------------------------------------------------------------


class TestExtractAllSignatures:
    def test_walks_directory(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def foo(): pass\n")
        sub = src / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("def bar(): pass\n")
        all_sigs = extract_all_signatures(str(src))
        assert "a.py" in all_sigs
        assert "sub/b.py" in all_sigs
        assert any(s.name == "foo" for s in all_sigs["a.py"])
        assert any(s.name == "bar" for s in all_sigs["sub/b.py"])

    def test_skips_pycache(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def foo(): pass\n")
        pycache = src / "__pycache__"
        pycache.mkdir()
        (pycache / "a.cpython-312.pyc").write_text("garbage")
        all_sigs = extract_all_signatures(str(src))
        assert "a.py" in all_sigs
        # __pycache__ files should be skipped
        assert not any("__pycache__" in k for k in all_sigs)

    def test_empty_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        all_sigs = extract_all_signatures(str(src))
        assert all_sigs == {}

    def test_relative_paths(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        all_sigs = extract_all_signatures(str(src))
        sig = all_sigs["mod.py"][0]
        assert sig.file_path == "mod.py"


# ---------------------------------------------------------------------------
# extract_documented_items
# ---------------------------------------------------------------------------


class TestExtractDocumentedItems:
    def test_heading_function(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n\nSome description.\n")
        items = extract_documented_items(str(p))
        assert "foo" in items
        assert items["foo"]["kind"] == "function"

    def test_heading_function_with_params(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo(a, b)`\n\nDescription.\n")
        items = extract_documented_items(str(p))
        assert "foo" in items

    def test_inline_function(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(x, y)` for details.\n")
        items = extract_documented_items(str(p))
        assert "bar" in items
        param_names = [p["name"] for p in items["bar"]["parameters"]]
        assert "x" in param_names
        assert "y" in param_names

    def test_inline_function_skips_self_cls(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(self, x)` for details.\n")
        items = extract_documented_items(str(p))
        param_names = [p["name"] for p in items["bar"]["parameters"]]
        assert "self" not in param_names
        assert "x" in param_names

    def test_param_list(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n\n- `a` (int): first param\n- `b` (str): second param\n")
        items = extract_documented_items(str(p))
        assert "foo" in items
        param_names = [p["name"] for p in items["foo"]["parameters"]]
        assert "a" in param_names
        assert "b" in param_names

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        items = extract_documented_items(str(tmp_path / "nope.md"))
        assert items == {}

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.md"
        p.write_text("")
        items = extract_documented_items(str(p))
        assert items == {}


# ---------------------------------------------------------------------------
# extract_all_documented_items
# ---------------------------------------------------------------------------


class TestExtractAllDocumentedItems:
    def test_single_file(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n")
        items = extract_all_documented_items(str(p))
        assert "foo" in items

    def test_directory_non_recursive(self, tmp_path: Path) -> None:
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.md").write_text("### `foo()`\n")
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("### `bar()`\n")
        items = extract_all_documented_items(str(d), recursive=False)
        assert "foo" in items
        assert "bar" not in items

    def test_directory_recursive(self, tmp_path: Path) -> None:
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.md").write_text("### `foo()`\n")
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("### `bar()`\n")
        items = extract_all_documented_items(str(d), recursive=True)
        assert "foo" in items
        assert "bar" in items

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        items = extract_all_documented_items(str(tmp_path / "nope"))
        assert items == {}


# ---------------------------------------------------------------------------
# validate_api_docs
# ---------------------------------------------------------------------------


class TestValidateApiDocs:
    def test_documented_not_in_source(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "phantom": {"name": "phantom", "line": 1, "kind": "function", "file": "api.md"}
        }
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "documented_not_in_source" for i in issues)

    def test_undocumented_suggestion(self) -> None:
        sig = SourceSignature("undoc", "function", "mod.py", 1, [{"name": "a"}])
        source_sigs = {"mod.py": [sig]}
        documented: dict[str, dict] = {}
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert any(s["type"] == "undocumented" for s in suggestions)

    def test_missing_param_in_docs(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [{"name": "a"}, {"name": "b"}])
        source_sigs = {"mod.py": [sig]}
        documented = {"foo": {"name": "foo", "line": 1, "kind": "function", "file": "api.md",
                              "parameters": [{"name": "a"}]}}
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "missing_param_in_docs" and i["parameter"] == "b" for i in issues)

    def test_extra_param_in_docs(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [{"name": "a"}])
        source_sigs = {"mod.py": [sig]}
        documented = {"foo": {"name": "foo", "line": 1, "kind": "function", "file": "api.md",
                              "parameters": [{"name": "a"}, {"name": "ghost"}]}}
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "extra_param_in_docs" and i["parameter"] == "ghost" for i in issues)

    def test_deprecated_still_documented(self) -> None:
        sig = SourceSignature("old", "function", "mod.py", 1, [], decorators=["deprecated"])
        source_sigs = {"mod.py": [sig]}
        documented = {"old": {"name": "old", "line": 1, "kind": "function", "file": "api.md",
                              "parameters": []}}
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "deprecated_still_documented" for i in issues)

    def test_no_issues_when_matched(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [{"name": "a"}])
        source_sigs = {"mod.py": [sig]}
        documented = {"foo": {"name": "foo", "line": 1, "kind": "function", "file": "api.md",
                              "parameters": [{"name": "a"}]}}
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert issues == []

    def test_both_empty_params(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [])
        source_sigs = {"mod.py": [sig]}
        documented = {"foo": {"name": "foo", "line": 1, "kind": "function", "file": "api.md",
                              "parameters": []}}
        issues, suggestions = validate_api_docs(source_sigs, documented)
        assert issues == []


# ---------------------------------------------------------------------------
# _classify_undocumented
# ---------------------------------------------------------------------------


class TestClassifyUndocumented:
    def test_init_py_skip(self) -> None:
        sig = SourceSignature("foo", "function", "__init__.py", 1, [])
        priority, reason = _classify_undocumented(sig)
        assert priority == "skip"

    def test_dataclass_skip(self) -> None:
        sig = SourceSignature("MyData", "class", "mod.py", 1, [], decorators=["dataclass"])
        priority, reason = _classify_undocumented(sig)
        assert priority == "skip"

    def test_entry_point_high(self) -> None:
        sig = SourceSignature("main", "function", "mod.py", 1, [])
        priority, reason = _classify_undocumented(sig)
        assert priority == "high"

    def test_protocol_high(self) -> None:
        sig = SourceSignature("MyProto", "class", "mod.py", 1, [], decorators=["runtime_checkable"])
        priority, reason = _classify_undocumented(sig)
        assert priority == "high"

    def test_complex_class_high(self) -> None:
        sig = SourceSignature("BigClass", "class", "mod.py", 1,
                              [{"name": f"p{i}"} for i in range(5)])
        priority, reason = _classify_undocumented(sig)
        assert priority == "high"

    def test_complex_function_medium(self) -> None:
        sig = SourceSignature("complex", "function", "mod.py", 1,
                              [{"name": f"p{i}"} for i in range(4)])
        priority, reason = _classify_undocumented(sig)
        assert priority == "medium"

    def test_simple_class_medium(self) -> None:
        sig = SourceSignature("Simple", "class", "mod.py", 1, [{"name": "a"}])
        priority, reason = _classify_undocumented(sig)
        assert priority == "medium"

    def test_simple_function_low(self) -> None:
        sig = SourceSignature("simple", "function", "mod.py", 1, [{"name": "a"}])
        priority, reason = _classify_undocumented(sig)
        assert priority == "low"

    def test_method_low(self) -> None:
        sig = SourceSignature("meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="C")
        priority, reason = _classify_undocumented(sig)
        assert priority == "low"

    def test_default_low(self) -> None:
        sig = SourceSignature(
            "weird", "other", "mod.py", 1,
            [{"name": "a"}, {"name": "b"}, {"name": "c"}],
        )
        priority, reason = _classify_undocumented(sig)
        assert priority == "low"


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_json_output(self) -> None:
        issues = [{"type": "documented_not_in_source", "severity": "high", "description": "test"}]
        report = generate_report(issues, [], 5, 3, as_json=True)
        data = json.loads(report)
        assert data["summary"]["total_issues"] == 1
        assert data["summary"]["source_signatures"] == 5
        assert data["summary"]["documented_items"] == 3

    def test_text_output_no_issues(self) -> None:
        report = generate_report([], [], 5, 3, as_json=False)
        assert "No drift issues found" in report
        assert "Source signatures found: 5" in report

    def test_text_output_with_issues(self) -> None:
        issues = [{"type": "documented_not_in_source", "severity": "high", "description": "test",
                   "source_file": "mod.py", "source_line": 10}]
        report = generate_report(issues, [], 5, 3, as_json=False)
        assert "HIGH" in report
        assert "test" in report

    def test_suggest_coverage(self) -> None:
        suggestions = [{"type": "undocumented", "priority": "high", "name": "foo",
                        "kind": "function", "reason": "entry point", "description": "desc"}]
        report = generate_report([], suggestions, 5, 3, suggest_coverage=True)
        assert "DOCUMENTATION SUGGESTIONS" in report
        assert "foo" in report

    def test_suggest_coverage_capped(self) -> None:
        suggestions = [
            {"type": "undocumented", "priority": "low", "name": f"f{i}",
             "kind": "function", "reason": "simple", "description": "desc"}
            for i in range(25)
        ]
        report = generate_report([], suggestions, 5, 3, suggest_coverage=True)
        assert "more" in report

    def test_issues_by_type_section(self) -> None:
        issues = [{"type": "documented_not_in_source", "severity": "high", "description": "test"}]
        report = generate_report(issues, [], 5, 3, as_json=False)
        assert "ISSUES BY TYPE" in report


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_source_not_found(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(
            sys, "argv",
            ["api_doc_validator.py", str(tmp_path / "nope"), str(tmp_path)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2

    def test_main_doc_not_found(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        monkeypatch.setattr(
            sys, "argv",
            ["api_doc_validator.py", str(src), str(tmp_path / "nope.md")],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2

    def test_main_directory_source(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `foo()`\n")
        monkeypatch.setattr(
            sys, "argv", ["api_doc_validator.py", str(src), str(docs)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "API Documentation Validation Report" in out

    def test_main_single_file_source(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "mod.py"
        src.write_text("def foo(): pass\n")
        docs = tmp_path / "api.md"
        docs.write_text("### `foo()`\n")
        monkeypatch.setattr(
            sys, "argv", ["api_doc_validator.py", str(src), str(docs)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_json_output(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "api.md"
        docs.write_text("### `foo()`\n")
        monkeypatch.setattr(
            sys, "argv",
            ["api_doc_validator.py", str(src), str(docs), "--json"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "summary" in data

    def test_main_recursive(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        sub = docs / "sub"
        sub.mkdir()
        (sub / "api.md").write_text("### `foo()`\n")
        monkeypatch.setattr(
            sys, "argv",
            ["api_doc_validator.py", str(src), str(docs), "--recursive"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_include_private(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def _private(): pass\ndef foo(): pass\n")
        docs = tmp_path / "api.md"
        docs.write_text("### `foo()`\n")
        monkeypatch.setattr(
            sys, "argv",
            ["api_doc_validator.py", str(src), str(docs), "--include-private"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_suggest_coverage(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def main(): pass\n")
        docs = tmp_path / "api.md"
        docs.write_text("Nothing here.\n")
        monkeypatch.setattr(
            sys, "argv",
            ["api_doc_validator.py", str(src), str(docs), "--suggest-coverage"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "DOCUMENTATION SUGGESTIONS" in out

    def test_main_high_severity_exit_1(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "api.md"
        docs.write_text("### `phantom()`\n")
        monkeypatch.setattr(
            sys, "argv", ["api_doc_validator.py", str(src), str(docs)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_main_non_python_source(
        self, monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "data.txt"
        src.write_text("not python")
        docs = tmp_path / "api.md"
        docs.write_text("### `foo()`\n")
        monkeypatch.setattr(
            sys, "argv", ["api_doc_validator.py", str(src), str(docs)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2
