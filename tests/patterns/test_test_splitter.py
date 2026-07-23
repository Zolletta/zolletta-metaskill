"""Tests for test_splitter module."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.patterns.test_splitter import (
    _auto_derive_prefixes,
    _build_split_file,
    _get_shared_methods,
    _get_test_methods,
    _group_methods,
    _indent_block,
    _load_mapping,
    _pascal_to_snake,
    _snake_to_pascal,
    _unparse_node,
    main,
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


class TestPascalToSnake:
    def test_simple(self) -> None:
        assert _pascal_to_snake("Cache") == "cache"

    def test_multi_word(self) -> None:
        assert _pascal_to_snake("DefaultsExtractor") == "defaults_extractor"

    def test_single_char(self) -> None:
        assert _pascal_to_snake("A") == "a"

    def test_empty(self) -> None:
        assert _pascal_to_snake("") == ""

    def test_all_upper(self) -> None:
        assert _pascal_to_snake("ABC") == "a_b_c"


class TestSnakeToPascal:
    def test_simple(self) -> None:
        assert _snake_to_pascal("cache") == "Cache"

    def test_multi_word(self) -> None:
        assert _snake_to_pascal("defaults_extractor") == "DefaultsExtractor"

    def test_single_word(self) -> None:
        assert _snake_to_pascal("foo") == "Foo"

    def test_empty(self) -> None:
        assert _snake_to_pascal("") == ""


class TestLoadMapping:
    def test_none_returns_empty(self) -> None:
        assert _load_mapping(None) == {}

    def test_empty_string_returns_empty(self) -> None:
        assert _load_mapping("") == {}

    def test_inline_json(self) -> None:
        result = _load_mapping('{"cache": "Cache"}')
        assert result == {"cache": "Cache"}

    def test_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "mapping.json"
        f.write_text(json.dumps({"cache": "Cache", "extract": "Extractor"}))
        result = _load_mapping(str(f))
        assert result == {"cache": "Cache", "extract": "Extractor"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _load_mapping("not json")


class TestGetTestMethods:
    def test_returns_test_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
            "    def helper(self):\n        pass\n"
        )
        methods = _get_test_methods(cls)
        assert len(methods) == 2
        assert {m.name for m in methods} == {"test_a", "test_b"}

    def test_no_test_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    def helper(self):\n        pass\n"
        )
        assert _get_test_methods(cls) == []

    def test_async_test_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    async def test_a(self):\n        pass\n"
        )
        methods = _get_test_methods(cls)
        assert len(methods) == 1
        assert methods[0].name == "test_a"

    def test_empty_class(self) -> None:
        cls = _parse_class("class TestFoo:\n    pass\n")
        assert _get_test_methods(cls) == []


class TestGetSharedMethods:
    def test_returns_non_test_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    def test_a(self):\n        pass\n"
            "    def setup(self):\n        pass\n"
            "    def helper(self):\n        pass\n"
        )
        methods = _get_shared_methods(cls)
        assert len(methods) == 2
        assert {m.name for m in methods} == {"setup", "helper"}

    def test_no_shared_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    def test_a(self):\n        pass\n"
        )
        assert _get_shared_methods(cls) == []

    def test_async_shared_methods(self) -> None:
        cls = _parse_class(
            "class TestFoo:\n"
            "    async def setup(self):\n        pass\n"
        )
        methods = _get_shared_methods(cls)
        assert len(methods) == 1


class TestAutoDerivePrefixes:
    def test_simple_prefixes(self) -> None:
        methods = [_make_method("test_cache_get"), _make_method("test_cache_set"),
                   _make_method("test_extract_defaults")]
        groups = _auto_derive_prefixes(methods)
        assert groups == {"cache": ["test_cache_get", "test_cache_set"],
                          "extract": ["test_extract_defaults"]}

    def test_single_token(self) -> None:
        methods = [_make_method("test_cache"), _make_method("test_extract")]
        groups = _auto_derive_prefixes(methods)
        assert groups == {"cache": ["test_cache"], "extract": ["test_extract"]}

    def test_empty_methods(self) -> None:
        assert _auto_derive_prefixes([]) == {}

    def test_preserves_method_names(self) -> None:
        methods = [_make_method("test_cache_get"), _make_method("test_cache_set")]
        groups = _auto_derive_prefixes(methods)
        assert "test_cache_get" in groups["cache"]
        assert "test_cache_set" in groups["cache"]


class TestGroupMethods:
    def test_groups_by_prefix(self) -> None:
        methods = [_make_method("test_cache_get"), _make_method("test_cache_set"),
                   _make_method("test_extract_defaults")]
        mapping = {"cache": "Cache", "extract": "Extractor"}
        groups = _group_methods(methods, mapping)
        assert "Cache" in groups
        assert "Extractor" in groups
        assert len(groups["Cache"]) == 2
        assert len(groups["Extractor"]) == 1

    def test_unmatched_methods(self) -> None:
        methods = [_make_method("test_cache_get"), _make_method("test_unknown_thing")]
        mapping = {"cache": "Cache"}
        groups = _group_methods(methods, mapping)
        assert "_unmatched" in groups
        assert len(groups["_unmatched"]) == 1
        assert groups["_unmatched"][0].name == "test_unknown_thing"

    def test_longest_prefix_match(self) -> None:
        methods = [_make_method("test_extract_defaults")]
        mapping = {"extract": "Extractor", "extract_defaults": "DefaultsExtractor"}
        groups = _group_methods(methods, mapping)
        assert "DefaultsExtractor" in groups
        assert len(groups["DefaultsExtractor"]) == 1

    def test_exact_prefix_match(self) -> None:
        methods = [_make_method("test_cache")]
        mapping = {"cache": "Cache"}
        groups = _group_methods(methods, mapping)
        assert "Cache" in groups
        assert len(groups["Cache"]) == 1

    def test_empty_mapping(self) -> None:
        methods = [_make_method("test_cache_get")]
        groups = _group_methods(methods, {})
        assert "_unmatched" in groups
        assert len(groups["_unmatched"]) == 1

    def test_empty_methods(self) -> None:
        groups = _group_methods([], {"cache": "Cache"})
        assert groups == {}


class TestUnparseNode:
    def test_simple_function(self) -> None:
        func = _parse_func("def foo():\n    return 1\n")
        result = _unparse_node(func)
        assert "def foo():" in result
        assert "return 1" in result

    def test_class(self) -> None:
        cls = _parse_class("class Foo:\n    pass\n")
        result = _unparse_node(cls)
        assert "class Foo:" in result


class TestIndentBlock:
    def test_single_line(self) -> None:
        assert _indent_block("x = 1") == "    x = 1"

    def test_multiple_lines(self) -> None:
        result = _indent_block("x = 1\ny = 2")
        assert result == "    x = 1\n    y = 2"

    def test_empty_line_preserved(self) -> None:
        result = _indent_block("x = 1\n\ny = 2")
        assert result == "    x = 1\n\n    y = 2"

    def test_custom_indent(self) -> None:
        assert _indent_block("x = 1", indent="  ") == "  x = 1"


class TestBuildSplitFile:
    def test_with_module_docstring(self) -> None:
        module = _parse_module(
            '"""Original docstring."""\n'
            "import pytest\n"
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        cls = _parse_class(
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        test_methods = _get_test_methods(cls)
        result = _build_split_file(module, cls, "Cache", test_methods, [], "TestOriginal")
        assert "split from TestOriginal" in result
        assert "Original docstring" in result

    def test_without_module_docstring(self) -> None:
        module = _parse_module(
            "import pytest\n"
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        cls = _parse_class(
            "class TestOriginal:\n"
            "    def test_cache_get(self):\n        pass\n"
        )
        test_methods = _get_test_methods(cls)
        result = _build_split_file(module, cls, "Cache", test_methods, [], "TestOriginal")
        assert "Tests for Cache" in result

    def test_copies_imports(self) -> None:
        module = _parse_module(
            "import pytest\n"
            "from foo import bar\n"
            "class TestOriginal:\n    pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = _build_split_file(module, cls, "Cache", [], [], "TestOriginal")
        assert "import pytest" in result
        assert "from foo import bar" in result

    def test_copies_pytestmark(self) -> None:
        module = _parse_module(
            "import pytest\n"
            "pytestmark = pytest.mark.xfail\n"
            "class TestOriginal:\n    pass\n"
        )
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = _build_split_file(module, cls, "Cache", [], [], "TestOriginal")
        assert "pytestmark" in result

    def test_new_class_name(self) -> None:
        module = _parse_module("class TestOriginal:\n    pass\n")
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = _build_split_file(module, cls, "Cache", [], [], "TestOriginal")
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
        test_methods = _get_test_methods(cls)
        shared = _get_shared_methods(cls)
        result = _build_split_file(module, cls, "Cache", test_methods, shared, "TestOriginal")
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
        test_methods = _get_test_methods(cls)
        result = _build_split_file(module, cls, "Cache", test_methods, [], "TestOriginal")
        assert "def test_cache_get" in result
        assert "def test_cache_set" in result

    def test_class_docstring(self) -> None:
        module = _parse_module("class TestOriginal:\n    pass\n")
        cls = _parse_class("class TestOriginal:\n    pass\n")
        result = _build_split_file(module, cls, "Cache", [], [], "TestOriginal")
        assert "Tests for Cache, split from TestOriginal" in result


class TestMain:
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
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_syntax_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def(:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "failed to parse" in err

    def test_main_no_test_class(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no test class" in err

    def test_main_class_not_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "mod.py"
        self._write_test_file(f)
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--class", "NonExistent"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "NonExistent" in err

    def test_main_class_with_no_test_methods(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class TestEmpty:\n    def helper(self):\n        pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(f), "--class", "TestEmpty"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no test methods" in err

    def test_main_auto_derive_no_mapping(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = main()
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
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "no files written" in out
        assert "Cache" in out

    def test_main_writes_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "test_god.py"
        self._write_test_file(f)
        out_dir = tmp_path / "output"
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.setattr(sys, "argv",
                            ["prog", str(f), "--mapping", mapping, "--out", str(out_dir)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Done" in out
        assert (out_dir / "test_cache.py").exists()
        assert (out_dir / "test_extractor.py").exists()
        cache_content = (out_dir / "test_cache.py").read_text()
        assert "class TestCache:" in cache_content
        assert "def test_cache_get" in cache_content

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
        monkeypatch.setattr(sys, "argv",
                            ["prog", str(f), "--mapping", mapping, "--dry-run"])
        rc = main()
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
        out_dir = tmp_path / "output"
        monkeypatch.setattr(sys, "argv",
                            ["prog", str(f), "--mapping", str(mapping_file), "--out", str(out_dir)])
        rc = main()
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
        rc = main()
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
        out_dir = tmp_path / "output"
        mapping = '{"cache": "Cache", "extract": "Extractor"}'
        monkeypatch.setattr(sys, "argv",
                            ["prog", str(f), "--mapping", mapping, "--out", str(out_dir)])
        rc = main()
        assert rc == 0
        cache_content = (out_dir / "test_cache.py").read_text()
        assert "def setup" in cache_content

    def test_main_empty_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        rc = main()
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
        rc = main()
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
        out_dir = tmp_path / "output"
        monkeypatch.setattr(sys, "argv",
                            ["prog", str(f), "--mapping", mapping, "--out", str(out_dir),
                             "--class", "TestGodClass"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "TestGodClass" in out
        assert (out_dir / "test_cache.py").exists()
