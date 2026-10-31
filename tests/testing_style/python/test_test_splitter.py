"""Tests for test_splitter module."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.testing_style.python.structs import SplitPlan
from zolletta_metaskill.testing_style.python.test_splitter import (
    TestSplitter,
)


def _parse_class(source: str) -> ast.ClassDef:
    """Parse source and return the first ClassDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("No class found in source")  # pragma: no cover


def _parse_module(source: str) -> ast.Module:
    """Parse source into a Module AST."""
    return ast.parse(source)


def _make_method(name: str) -> ast.FunctionDef:
    """Create a simple test method AST node."""
    return _parse_func(f"def {name}(self):\n    pass\n")


def _parse_func(source: str) -> ast.FunctionDef:
    """Parse source and return the first FunctionDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise AssertionError("No function found in source")  # pragma: no cover


class TestTestSplitter:
    # --- LoadMapping ---

    def test_none_returns_empty(self) -> None:
        assert TestSplitter._load_mapping(None) == {}

    def test_empty_string_returns_empty(self) -> None:
        assert TestSplitter._load_mapping("") == {}

    def test_load_mapping_inline_json_returns_dict(self) -> None:
        result = TestSplitter._load_mapping('{"cache": "Cache"}')
        assert result == {"cache": "Cache"}

    def test_load_mapping_file_path_returns_dict(self, tmp_path: Path) -> None:
        f = tmp_path / "mapping.json"
        f.write_text(json.dumps({"cache": "Cache", "extract": "Extractor"}))
        result = TestSplitter._load_mapping(str(f))
        assert result == {"cache": "Cache", "extract": "Extractor"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            TestSplitter._load_mapping("not json")

    # --- GetTestMethods ---

    def test_returns_test_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
            "    def helper(self):\n        pass\n"
        )
        methods = TestSplitter._get_test_methods(cls)
        assert len(methods) == 2
        assert {m.name for m in methods} == {"test_a", "test_b"}

    def test_no_test_methods(self) -> None:
        cls = _parse_class("class TestFoo:\n    def helper(self):\n        pass\n")
        assert TestSplitter._get_test_methods(cls) == []

    def test_async_test_methods(self) -> None:
        cls = _parse_class("class TestFoo:\n    async def test_a(self):\n        pass\n")
        methods = TestSplitter._get_test_methods(cls)
        assert len(methods) == 1
        assert methods[0].name == "test_a"

    def test_parse_class_empty_class_returns_empty_list(self) -> None:
        cls = _parse_class("class TestFoo:\n    pass\n")
        assert TestSplitter._get_test_methods(cls) == []

    # --- GetSharedMethods ---

    def test_returns_non_test_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    def test_a(self):\n        pass\n"
            "    def setup(self):\n        pass\n"
            "    def helper(self):\n        pass\n"
        )
        methods = TestSplitter._get_shared_methods(cls)
        assert len(methods) == 2
        assert {m.name for m in methods} == {"setup", "helper"}

    def test_no_shared_methods(self) -> None:
        cls = _parse_class("class TestFoo:\n    def test_a(self):\n        pass\n")
        assert TestSplitter._get_shared_methods(cls) == []

    def test_async_shared_methods(self) -> None:
        cls = _parse_class("class TestFoo:\n    async def setup(self):\n        pass\n")
        methods = TestSplitter._get_shared_methods(cls)
        assert len(methods) == 1

    # --- AutoDerivePrefixes ---

    def test_auto_derive_prefixes_simple_prefixes_returns_dict(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            _make_method("test_cache_get"),
            _make_method("test_cache_set"),
            _make_method("test_extract_defaults"),
        ]
        groups = TestSplitter._auto_derive_prefixes(methods)
        assert groups == {
            "cache": ["test_cache_get", "test_cache_set"],
            "extract": ["test_extract_defaults"],
        }

    def test_auto_derive_prefixes_single_token_returns_dict(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            _make_method("test_cache"),
            _make_method("test_extract"),
        ]
        groups = TestSplitter._auto_derive_prefixes(methods)
        assert groups == {"cache": ["test_cache"], "extract": ["test_extract"]}

    def test_auto_derive_prefixes_empty_methods_returns_empty_dict(self) -> None:
        assert TestSplitter._auto_derive_prefixes([]) == {}

    def test_preserves_method_names(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            _make_method("test_cache_get"),
            _make_method("test_cache_set"),
        ]
        groups = TestSplitter._auto_derive_prefixes(methods)
        assert "test_cache_get" in groups["cache"]
        assert "test_cache_set" in groups["cache"]

    # --- GroupMethods ---

    def test_groups_by_prefix(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            _make_method("test_cache_get"),
            _make_method("test_cache_set"),
            _make_method("test_extract_defaults"),
        ]
        mapping = {"cache": "Cache", "extract": "Extractor"}
        groups = TestSplitter._group_methods(methods, mapping)
        assert "Cache" in groups
        assert "Extractor" in groups
        assert len(groups["Cache"]) == 2
        assert len(groups["Extractor"]) == 1

    def test_group_methods_unmatched_methods_returns_test_unknown_thing(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            _make_method("test_cache_get"),
            _make_method("test_unknown_thing"),
        ]
        mapping = {"cache": "Cache"}
        groups = TestSplitter._group_methods(methods, mapping)
        assert "_unmatched" in groups
        assert len(groups["_unmatched"]) == 1
        assert groups["_unmatched"][0].name == "test_unknown_thing"

    def test_longest_prefix_match(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            _make_method("test_extract_defaults"),
        ]
        mapping = {"extract": "Extractor", "extract_defaults": "DefaultsExtractor"}
        groups = TestSplitter._group_methods(methods, mapping)
        assert "DefaultsExtractor" in groups
        assert len(groups["DefaultsExtractor"]) == 1

    def test_exact_prefix_match(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [_make_method("test_cache")]
        mapping = {"cache": "Cache"}
        groups = TestSplitter._group_methods(methods, mapping)
        assert "Cache" in groups
        assert len(groups["Cache"]) == 1

    def test_group_methods_empty_mapping_returns_1(self) -> None:
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [_make_method("test_cache_get")]
        groups = TestSplitter._group_methods(methods, {})
        assert "_unmatched" in groups
        assert len(groups["_unmatched"]) == 1

    def test_group_methods_empty_methods_returns_empty_dict(self) -> None:
        groups = TestSplitter._group_methods([], {"cache": "Cache"})
        assert groups == {}

    # --- UnparseNode ---

    def test_parse_func_simple_function_contains_return_1(self) -> None:
        func = _parse_func("def foo():\n    return 1\n")
        result = TestSplitter._unparse_node(func)
        assert "def foo():" in result
        assert "return 1" in result

    def test_parse_class_class_contains_class_foo(self) -> None:
        cls = _parse_class("class Foo:\n    pass\n")
        result = TestSplitter._unparse_node(cls)
        assert "class Foo:" in result

    # --- IndentBlock ---

    def test_indent_block_single_line_returns_x_1(self) -> None:
        assert TestSplitter._indent_block("x = 1") == "    x = 1"

    def test_indent_block_multiple_lines_returns_x_1_y_2(self) -> None:
        result = TestSplitter._indent_block("x = 1\ny = 2")
        assert result == "    x = 1\n    y = 2"

    def test_empty_line_preserved(self) -> None:
        result = TestSplitter._indent_block("x = 1\n\ny = 2")
        assert result == "    x = 1\n\n    y = 2"

    def test_indent_block_custom_indent_returns_x_1(self) -> None:
        assert TestSplitter._indent_block("x = 1", indent="  ") == "  x = 1"

    # --- BuildSplitFile ---

    def test_with_module_docstring(self) -> None:
        module = _parse_module(
            '"""Original docstring."""\n'
            "import pytest\n"
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    def test_cache_get(self):\n        pass\n")
        test_methods = TestSplitter._get_test_methods(cls)
        result = TestSplitter._build_split_file(
            _plan(module, cls, test_methods, [], "TestOriginal"), "Cache"
        )
        assert "split from TestOriginal" in result
        assert "Original docstring" in result

    def test_without_module_docstring(self) -> None:
        module = _parse_module(
            "import pytest\nclass TestOriginal:\n    def test_cache_get(self):\n        pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    def test_cache_get(self):\n        pass\n")
        test_methods = TestSplitter._get_test_methods(cls)
        result = TestSplitter._build_split_file(
            _plan(module, cls, test_methods, [], "TestOriginal"), "Cache"
        )
        assert "Tests for Cache" in result

    def test_parse_module_copies_imports_contains_from_foo_import_bar(self) -> None:
        module = _parse_module(
            "import pytest\nfrom foo import bar\nclass TestOriginal:\n    pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = TestSplitter._build_split_file(_plan(module, cls, [], [], "TestOriginal"), "Cache")
        assert "import pytest" in result
        assert "from foo import bar" in result

    def test_parse_module_copies_pytestmark_contains_pytestmark(self) -> None:
        module = _parse_module(
            "import pytest\npytestmark = pytest.mark.xfail\nclass TestOriginal:\n    pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = TestSplitter._build_split_file(_plan(module, cls, [], [], "TestOriginal"), "Cache")
        assert "pytestmark" in result

    def test_parse_module_non_pytestmark_assignment_ignored(self) -> None:
        module = _parse_module("LIMIT = 10\nclass TestOriginal:\n    pass\n")
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = TestSplitter._build_split_file(_plan(module, cls, [], [], "TestOriginal"), "Cache")
        assert "LIMIT" not in result

    def test_new_class_name(self) -> None:
        module = _parse_module("class TestOriginal:\n    pass\n")
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = TestSplitter._build_split_file(_plan(module, cls, [], [], "TestOriginal"), "Cache")
        assert "class TestCache:" in result

    def test_includes_shared_methods(self) -> None:
        module = _parse_module(
            "class TestOriginal:\n"
            "    def setup(self):\n        pass\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        cls = _parse_class(
            "class TestOriginal:\n"
            "    def setup(self):\n        pass\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        test_methods = TestSplitter._get_test_methods(cls)
        shared = TestSplitter._get_shared_methods(cls)
        result = TestSplitter._build_split_file(
            _plan(module, cls, test_methods, shared, "TestOriginal"), "Cache"
        )
        assert "def setup" in result
        assert "def test_cache_get" in result

    def test_includes_test_methods(self) -> None:
        module = _parse_module(
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
            "    def test_cache_set(self):\n        pass\n"
        )
        cls = _parse_class(
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
            "    def test_cache_set(self):\n        pass\n"
        )
        test_methods = TestSplitter._get_test_methods(cls)
        result = TestSplitter._build_split_file(
            _plan(module, cls, test_methods, [], "TestOriginal"), "Cache"
        )
        assert "def test_cache_get" in result
        assert "def test_cache_set" in result

    def test_parse_module_class_docstring_contains_long_string(self) -> None:
        module = _parse_module("class TestOriginal:\n    pass\n")
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = TestSplitter._build_split_file(_plan(module, cls, [], [], "TestOriginal"), "Cache")
        assert "Tests for Cache, split from TestOriginal" in result

    def test_build_split_file_full_layout_exact_lines(self) -> None:
        module = _parse_module(
            '"""Docstring."""\n'
            "import pytest\n"
            "from foo import bar\n"
            "pytestmark = pytest.mark.xfail\n"
            "class TestOriginal:\n"
            "    def setup(self):\n        self.x = 1\n"
            "    def test_cache_get(self):\n        assert True\n"
        )
        cls = _parse_class(
            "class TestOriginal:\n"
            "    def setup(self):\n        self.x = 1\n"
            "    def test_cache_get(self):\n        assert True\n"
        )
        test_methods = TestSplitter._get_test_methods(cls)
        shared = TestSplitter._get_shared_methods(cls)
        result = TestSplitter._build_split_file(
            _plan(module, cls, test_methods, shared, "TestOriginal"), "Cache"
        )
        assert result.splitlines() == [
            '"""Docstring. — split from TestOriginal."""',
            "",
            "import pytest",
            "from foo import bar",
            "",
            "pytestmark = pytest.mark.xfail",
            "",
            "class TestCache:",
            '    """Tests for Cache, split from TestOriginal."""',
            "",
            "    def setup(self):",
            "        self.x = 1",
            "",
            "    def test_cache_get(self):",
            "        assert True",
        ]

    def test_build_split_file_no_docstring_exact_lines(self) -> None:
        module = _parse_module(
            "import pytest\nclass TestOriginal:\n    def test_cache_get(self):\n        pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    def test_cache_get(self):\n        pass\n")
        test_methods = TestSplitter._get_test_methods(cls)
        result = TestSplitter._build_split_file(
            _plan(module, cls, test_methods, [], "TestOriginal"), "Cache"
        )
        assert result.splitlines() == [
            '"""Tests for Cache — split from TestOriginal."""',
            "",
            "import pytest",
            "",
            "class TestCache:",
            '    """Tests for Cache, split from TestOriginal."""',
            "",
            "    def test_cache_get(self):",
            "        pass",
        ]

    # --- EmitAutoMapping ---

    def test_emit_auto_mapping_text_output_exact_lines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        f.write_text(
            "class TestGodClass:\n"
            "    def setup(self):\n        pass\n"
            "    def test_cache_a(self):\n        pass\n"
            "    def test_cache_b(self):\n        pass\n"
            "    def test_cache_c(self):\n        pass\n"
            "    def test_cache_d(self):\n        pass\n"
            "    def test_extract_x(self):\n        pass\n"
            "    def test_extract_y(self):\n        pass\n"
            "    def test_extract_z(self):\n        pass\n"
            "    def test_foo(self):\n        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert out.splitlines() == [
            "=" * 70,
            "TEST SPLITTER — test_god.py",
            "=" * 70,
            "",
            "Class: TestGodClass",
            "Test methods: 8",
            "Shared methods (fixtures/helpers): 1",
            "",
            "No --mapping provided. Auto-deriving prefixes from method names:",
            "  cache: 4 methods -> ['test_cache_a', 'test_cache_b', 'test_cache_c']...",
            "  extract: 3 methods -> ['test_extract_x', 'test_extract_y', 'test_extract_z']",
            "  foo: 1 methods -> ['test_foo']",
            "",
            'Use --mapping \'{"prefix": "SutClass", ...}\' to specify SUT names.',
            "Example:",
            '  --mapping \'{"cache": "Cache", "extract": "Extract", "foo": "Foo"}\'',
            "",
            "Re-run with --mapping to split. Use --dry-run to preview first.",
        ]

    # --- EmitProposedSplit ---

    def test_emit_proposed_split_text_output_exact_lines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        f.write_text(
            "class TestGodClass:\n"
            "    def setup(self):\n        pass\n"
            "    def test_cache_get(self):\n        pass\n"
            "    def test_unknown_thing(self):\n        pass\n"
        )
        mapping = '{"cache": "Cache"}'
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping, "--dry-run"])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert out.splitlines() == [
            "=" * 70,
            "TEST SPLITTER — test_god.py",
            "=" * 70,
            "",
            "Class: TestGodClass",
            "Test methods: 2",
            "Shared methods (fixtures/helpers): 1",
            "",
            "Proposed split (2 groups):",
            "",
            "  Cache -> TestCache (1 methods):",
            "    test_cache_get",
            "",
            "  _unmatched (1 methods):",
            "    test_unknown_thing",
            "    (No prefix matched — review and add to mapping)",
            "",
            "⚠  1 methods unmatched. Add their prefixes to --mapping",
            "   or they will be placed in a separate _unmatched test file.",
            "",
            "--dry-run: no files written.",
        ]

    # --- EmitWritten ---

    def test_emit_written_text_output_exact_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        TestSplitter._emit_written(
            False, Path("test_god.py"), Path("out"), ["test_cache.py", "test_extractor.py"], {}
        )
        assert capsys.readouterr().out.splitlines() == [
            "",
            "Writing split files to: out/",
            "  test_cache.py",
            "  test_extractor.py",
            "",
            "Done. 2 files written to out/",
            "Review the split files, then move them to replace the original.",
            "Original file test_god.py was NOT modified.",
        ]

    def test_emit_written_json_output_exact_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = {"test_file": "test_god.py"}
        TestSplitter._emit_written(
            True, Path("test_god.py"), Path("out"), ["test_cache.py"], result
        )
        expected = {
            "test_file": "test_god.py",
            "out_dir": "out",
            "written": ["test_cache.py"],
        }
        assert result == expected
        assert capsys.readouterr().out == json.dumps(expected, indent=2) + "\n"

    # --- WriteSplitFiles ---

    def test_write_split_files_empty_groups_writes_only_named_file(self, tmp_path: Path) -> None:
        tree = _parse_module("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        cls = _parse_class("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        written = TestSplitter._write_split_files(
            tree, cls, {"Cache": [], "_unmatched": []}, [], tmp_path
        )
        assert written == ["test_cache.py"]
        assert (tmp_path / "test_cache.py").exists()
        assert not (tmp_path / "test_unmatched.py").exists()

    def test_write_split_files_empty_unmatched_writes_later_group(self, tmp_path: Path) -> None:
        tree = _parse_module("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        cls = _parse_class("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {
            "_unmatched": [],
            "cache": [_make_method("test_cache_get")],
        }
        written = TestSplitter._write_split_files(tree, cls, groups, [], tmp_path)
        assert written == ["test_cache.py"]
        assert (tmp_path / "test_cache.py").exists()

    def test_write_split_files_unmatched_with_methods_writes_file(self, tmp_path: Path) -> None:
        tree = _parse_module("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        cls = _parse_class("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {
            "Cache": [_make_method("test_cache_get")],
            "_unmatched": [_make_method("test_unknown_thing")],
        }
        written = TestSplitter._write_split_files(tree, cls, groups, [], tmp_path)
        assert written == ["test_cache.py", "test_unmatched.py"]
        assert (tmp_path / "test_unmatched.py").exists()

    def test_write_split_files_build_call_exact_plan_and_sut(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tree = _parse_module("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        cls = _parse_class("class TestGodClass:\n    def test_cache_get(self):\n        pass\n")
        method = _make_method("test_cache_get")
        shared = _parse_func("def setup(self):\n    pass\n")
        calls: list[tuple[SplitPlan, str]] = []

        def _spy(plan: SplitPlan, sut: str) -> str:
            calls.append((plan, sut))
            return "SPLIT CONTENT"

        monkeypatch.setattr(TestSplitter, "_build_split_file", staticmethod(_spy))
        written = TestSplitter._write_split_files(
            tree, cls, {"Cache": [method]}, [shared], tmp_path
        )
        assert written == ["test_cache.py"]
        assert (tmp_path / "test_cache.py").read_text() == "SPLIT CONTENT"
        assert len(calls) == 1
        plan, sut = calls[0]
        assert sut == "Cache"
        assert plan.original_module is tree
        assert plan.class_node is cls
        assert plan.test_methods == (method,)
        assert plan.shared_methods == (shared,)
        assert plan.original_class_name == "TestGodClass"

    # --- Main ---

    def _write_test_file(self, path: Path) -> None:
        """Write a sample test file with multiple SUT prefixes."""
        path.write_text(
            '"""Test module docstring."""\n'
            "import pytest\n"
            "class TestGodClass:\n"
            "    def setup(self):\n        self.x = 1\n"
            "    def test_cache_get(self):\n        assert True\n"
            "    def test_cache_set(self):\n        assert True\n"
            "    def test_extract_defaults(self):\n        assert True\n"
        )

    def test_main_nonexistent_file(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/file.py"])
        rc = TestSplitter.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_syntax_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def(:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = TestSplitter.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "failed to parse" in err

    def test_main_no_test_class(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = TestSplitter.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert err == f"Error: no test class found in {f}\n"

    def test_main_class_not_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "mod.py"
        self._write_test_file(f)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--class", "NonExistent"])
        rc = TestSplitter.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert err == f"Error: no test class 'NonExistent' found in {f}\n"

    def test_main_class_with_no_test_methods(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class TestEmpty:\n    def helper(self):\n        pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--class", "TestEmpty"])
        rc = TestSplitter.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no test methods" in err

    def test_main_auto_derive_no_mapping(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Auto-deriving" in out
        assert "--mapping" in out

    def test_main_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping, "--dry-run"])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "no files written" in out
        assert "Cache" in out

    def test_main_writes_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        out_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        assert rc == 0
        assert "Done" in out
        assert (out_dir / "test_cache.py").exists()
        assert (out_dir / "test_extractor.py").exists()
        cache_content = (out_dir / "test_cache.py").read_text()
        assert "class TestCache:" in cache_content
        assert "def test_cache_get" in cache_content
        assert f"Original file {f} was NOT modified." in out.splitlines()

    def test_main_unmatched_methods(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        f.write_text(
            "class TestGodClass:\n"
            "    def test_cache_get(self):\n        pass\n"
            "    def test_unknown_thing(self):\n        pass\n"
        )
        mapping = '{"cache": "Cache"}'
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping, "--dry-run"])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "_unmatched" in out
        assert "unmatched" in out

    def test_main_mapping_from_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps({"cache": "Cache", "extract": "Extractor"}))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", str(mapping_file)])
        rc = TestSplitter.main()
        out_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        assert rc == 0
        assert (out_dir / "test_cache.py").exists()

    def test_main_default_output_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        expected_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        assert expected_dir.exists()
        assert "test_god" in out

    def test_main_writes_shared_methods(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping])
        rc = TestSplitter.main()
        out_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        assert rc == 0
        cache_content = (out_dir / "test_cache.py").read_text()
        assert "def setup" in cache_content

    def test_main_empty_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = TestSplitter.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no test class" in err

    def test_main_proposed_split_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping, "--dry-run"])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Proposed split" in out
        assert "Test methods:" in out
        assert "Shared methods" in out

    def test_main_specific_class(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        f.write_text(
            "class TestFirst:\n"
            "    def test_a(self):\n        pass\n"
            "class TestGodClass:\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        mapping = '{"cache": "Cache"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                str(f),
                "--mapping",
                mapping,
                "--class",
                "TestGodClass",
            ],
        )
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        out_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        assert rc == 0
        assert "TestGodClass" in out
        assert (out_dir / "test_cache.py").exists()

    def test_main_json_auto_derive(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--json"])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        expected = {
            "test_file": str(f),
            "class": "TestGodClass",
            "test_methods": 3,
            "shared_methods": 1,
            "auto_prefixes": {
                "cache": ["test_cache_get", "test_cache_set"],
                "extract": ["test_extract_defaults"],
            },
            "proposed_mapping": {"cache": "Cache", "extract": "Extract"},
        }
        assert json.loads(out) == expected
        assert out == json.dumps(expected, indent=2) + "\n"

    def test_main_json_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["prog", str(f), "--mapping", mapping, "--dry-run", "--json"]
        )
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        expected = {
            "test_file": str(f),
            "class": "TestGodClass",
            "test_methods": 3,
            "shared_methods": 1,
            "groups": {
                "Cache": ["test_cache_get", "test_cache_set"],
                "Extractor": ["test_extract_defaults"],
            },
            "dry_run": True,
        }
        assert json.loads(out) == expected
        assert out == json.dumps(expected, indent=2) + "\n"

    def test_main_json_writes_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping, "--json"])
        rc = TestSplitter.main()
        out = capsys.readouterr().out
        assert rc == 0
        out_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        expected = {
            "test_file": str(f),
            "class": "TestGodClass",
            "test_methods": 3,
            "shared_methods": 1,
            "groups": {
                "Cache": ["test_cache_get", "test_cache_set"],
                "Extractor": ["test_extract_defaults"],
            },
            "out_dir": ".zolletta-metaskill/test_split/test_god",
            "written": ["test_cache.py", "test_extractor.py"],
        }
        assert json.loads(out) == expected
        assert out == json.dumps(expected, indent=2) + "\n"
        assert (out_dir / "test_cache.py").exists()

    def test_main_custom_runs_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        (meta / "settings.json").write_text(
            json.dumps({"language": "python", "runs_dir": "out_runs"})
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping])
        rc = TestSplitter.main()
        assert rc == 0
        assert (tmp_path / "out_runs" / "test_split" / "test_god" / "test_cache.py").exists()

    def test_main_existing_out_dir_returns_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        out_dir = tmp_path / ".zolletta-metaskill" / "test_split" / "test_god"
        out_dir.mkdir(parents=True)
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--mapping", mapping])
        rc = TestSplitter.main()
        assert rc == 0
        assert (out_dir / "test_cache.py").exists()

    def test_main_emit_auto_mapping_receives_exact_plan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        calls: list[tuple[bool, Path, SplitPlan, dict[str, object]]] = []

        def _spy(
            json_mode: bool, test_file: Path, plan: SplitPlan, result: dict[str, object]
        ) -> None:
            calls.append((json_mode, test_file, plan, result))

        monkeypatch.setattr(TestSplitter, "_emit_auto_mapping", staticmethod(_spy))
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = TestSplitter.main()
        assert rc == 0
        assert len(calls) == 1
        json_mode, test_file, plan, result = calls[0]
        assert json_mode is False
        assert test_file == f
        assert result == {
            "test_file": str(f),
            "class": "TestGodClass",
            "test_methods": 3,
            "shared_methods": 1,
        }
        assert isinstance(plan.original_module, ast.Module)
        assert ast.dump(plan.original_module) == ast.dump(ast.parse(f.read_text()))
        assert plan.class_node.name == "TestGodClass"
        assert [m.name for m in plan.test_methods] == [
            "test_cache_get",
            "test_cache_set",
            "test_extract_defaults",
        ]
        assert [m.name for m in plan.shared_methods] == ["setup"]
        assert plan.original_class_name == "TestGodClass"


def _plan(
    module: ast.Module,
    class_node: ast.ClassDef,
    test_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    shared_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    original_class_name: str,
) -> SplitPlan:
    """Build the SplitPlan that TestSplitter's private helpers now take."""
    return SplitPlan(
        original_module=module,
        class_node=class_node,
        test_methods=tuple(test_methods),
        shared_methods=tuple(shared_methods),
        original_class_name=original_class_name,
    )
