"""Tests for source_signature_extractor.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

from zolletta_metaskill.documentor.api_doc.source_signature_extractor import (
    SourceSignatureExtractor,
)


class TestSourceSignatureExtractor:
    """SourceSignatureExtractor pulls signatures out of Python source."""

    # --- _annotation_to_str ---

    def test_annotation_to_str_none_input_returns_none(self) -> None:
        assert SourceSignatureExtractor._annotation_to_str(None) is None

    def test_annotation_to_str_simple_name_returns_str(self, tmp_path: Path) -> None:
        src = "def f(x: int) -> str: ...\n"
        p = tmp_path / "m.py"
        p.write_text(src)
        import ast

        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._annotation_to_str(func.args.args[0].annotation) == "int"
        assert SourceSignatureExtractor._annotation_to_str(func.returns) == "str"

    def test_annotation_to_str_subscript_annotation_returns_list_int(self, tmp_path: Path) -> None:
        import ast

        src = "def f(x: list[int]) -> dict[str, int]: ...\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert (
            SourceSignatureExtractor._annotation_to_str(func.args.args[0].annotation) == "list[int]"
        )

    def test_annotation_to_str_attribute_returns_typing_optional_int(self, tmp_path: Path) -> None:
        import ast

        src = "def f(x: typing.Optional[int]) -> None: ...\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert (
            SourceSignatureExtractor._annotation_to_str(func.args.args[0].annotation)
            == "typing.Optional[int]"
        )

    # --- _extract_decorator_names ---

    def test_extract_decorator_names_name_decorator_returns_single_item(self) -> None:
        import ast

        src = "@staticmethod\ndef f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._extract_decorator_names(func.decorator_list) == [
            "staticmethod"
        ]

    def test_extract_decorator_names_attribute_decorator_returns_single_item(self) -> None:
        import ast

        src = "@app.route\ndef f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._extract_decorator_names(func.decorator_list) == [
            "app.route"
        ]

    def test_call_decorator_name(self) -> None:
        import ast

        src = "@deprecated\ndef f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._extract_decorator_names(func.decorator_list) == [
            "deprecated"
        ]

    def test_call_decorator_attribute(self) -> None:
        import ast

        src = "@functools.wraps(f)\ndef g(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._extract_decorator_names(func.decorator_list) == [
            "functools.wraps"
        ]

    def test_call_decorator_with_name_func(self) -> None:
        import ast

        src = '@deprecated("1.0")\ndef old(): pass\n'
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._extract_decorator_names(func.decorator_list) == [
            "deprecated"
        ]

    def test_extract_decorator_names_empty_input_returns_empty_list(self) -> None:
        import ast

        src = "def f(): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert SourceSignatureExtractor._extract_decorator_names(func.decorator_list) == []

    # --- _extract_parameters ---

    def test_extract_parameters_simple_params_returns_b(self) -> None:
        import ast

        src = "def f(a, b): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert len(params) == 2
        assert params[0]["name"] == "a"
        assert params[0]["has_default"] is False
        assert params[1]["name"] == "b"

    def test_extract_parameters_self_skipped_returns_a(self) -> None:
        import ast

        src = "def f(self, a): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert len(params) == 1
        assert params[0]["name"] == "a"

    def test_extract_parameters_cls_skipped_returns_a(self) -> None:
        import ast

        src = "def f(cls, a): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert len(params) == 1
        assert params[0]["name"] == "a"

    def test_extract_parameters_default_values_returns_x(self) -> None:
        import ast

        src = "def f(a, b=10, c='x'): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert params[0]["has_default"] is False
        assert params[1]["has_default"] is True
        assert params[1]["default"] == "10"
        assert params[2]["has_default"] is True
        assert params[2]["default"] == "'x'"

    def test_extract_parameters_vararg_is_valid(self) -> None:
        import ast

        src = "def f(a, *args): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert any(p["name"] == "*args" for p in params)

    def test_extract_parameters_kwarg_is_valid(self) -> None:
        import ast

        src = "def f(a, **kwargs): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert any(p["name"] == "**kwargs" for p in params)

    def test_extract_parameters_kwonly_args_returns_false(self) -> None:
        import ast

        src = "def f(a, *, b=1, c): pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        kwonly = [p for p in params if p["name"] in ("b", "c")]
        assert len(kwonly) == 2
        b_param = next(p for p in kwonly if p["name"] == "b")
        assert b_param["has_default"] is True
        assert b_param["default"] == "1"
        c_param = next(p for p in kwonly if p["name"] == "c")
        assert c_param["has_default"] is False

    def test_extract_parameters_annotation_extracted_returns_int(self) -> None:
        import ast

        src = "def f(a: int) -> None: pass\n"
        tree = ast.parse(src)
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        params = SourceSignatureExtractor._extract_parameters(func)
        assert params[0]["annotation"] == "int"

    # --- extract_signatures ---

    def test_extract_signatures_extract_function_returns_doc(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text('"""Module."""\ndef foo(a, b=1):\n    """Doc."""\n    return a\n')
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        assert len(sigs) == 1
        assert sigs[0].name == "foo"
        assert sigs[0].kind == "function"
        assert sigs[0].docstring == "Doc."

    def test_extract_signatures_extract_method_returns_myclass(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("class MyClass:\n    def method(self, x):\n        return x\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        # Should find __init__? No, just method and class
        names = [s.name for s in sigs]
        assert "method" in names
        assert "MyClass" in names
        method = next(s for s in sigs if s.name == "method")
        assert method.kind == "method"
        assert method.parent_class == "MyClass"

    def test_extract_signatures_extract_class_excludes_value(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("class MyClass:\n    def __init__(self, a, b):\n        self.a = a\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        cls = next(s for s in sigs if s.name == "MyClass")
        assert cls.kind == "class"
        param_names = [p["name"] for p in cls.parameters]
        assert "a" in param_names
        assert "b" in param_names
        assert "self" not in param_names

    def test_private_excluded_by_default(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("def _private(): pass\ndef public(): pass\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        names = [s.name for s in sigs]
        assert "public" in names
        assert "_private" not in names

    def test_private_included_with_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("def _private(): pass\ndef public(): pass\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p), include_private=True)
        names = [s.name for s in sigs]
        assert "_private" in names
        assert "public" in names

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("def f(:\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        assert sigs == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        sigs = SourceSignatureExtractor.extract_signatures(str(tmp_path / "nonexistent.py"))
        assert sigs == []

    def test_extract_signatures_async_function_returns_aio(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("async def aio():\n    return 1\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        assert len(sigs) == 1
        assert sigs[0].name == "aio"

    def test_extract_signatures_decorators_extracted_returns_true(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("@deprecated\ndef old(): pass\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        assert sigs[0].decorators == ["deprecated"]
        assert sigs[0].is_deprecated is True

    def test_private_class_excluded_by_default(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("class _Private:\n    pass\nclass Public:\n    pass\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p))
        names = [s.name for s in sigs]
        assert "Public" in names
        assert "_Private" not in names

    def test_private_class_included_with_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "mod.py"
        p.write_text("class _Private:\n    pass\n")
        sigs = SourceSignatureExtractor.extract_signatures(str(p), include_private=True)
        names = [s.name for s in sigs]
        assert "_Private" in names

    # --- extract_all_signatures ---

    def test_extract_all_signatures_walks_directory_is_valid(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def foo(): pass\n")
        sub = src / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("def bar(): pass\n")
        all_sigs = SourceSignatureExtractor.extract_all_signatures(str(src))
        assert "a.py" in all_sigs
        assert "sub/b.py" in all_sigs
        assert any(s.name == "foo" for s in all_sigs["a.py"])
        assert any(s.name == "bar" for s in all_sigs["sub/b.py"])

    def test_extract_all_signatures_gitignored_pycache_is_skipped(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def foo(): pass\n")
        pycache = src / "__pycache__"
        pycache.mkdir()
        (pycache / "stub.py").write_text("def cached(): pass\n")
        (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

        all_sigs = SourceSignatureExtractor.extract_all_signatures(str(src))
        assert "a.py" in all_sigs
        # __pycache__ is excluded by git, which is now the one deciding
        assert not any("__pycache__" in k for k in all_sigs)

    def test_extract_all_signatures_empty_dir_returns_empty_dict(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        all_sigs = SourceSignatureExtractor.extract_all_signatures(str(src))
        assert all_sigs == {}

    def test_extract_all_signatures_relative_paths_returns_mod_py(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        all_sigs = SourceSignatureExtractor.extract_all_signatures(str(src))
        sig = all_sigs["mod.py"][0]
        assert sig.file_path == "mod.py"
