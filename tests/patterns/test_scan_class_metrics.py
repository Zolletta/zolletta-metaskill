"""Tests for scan_class_metrics module."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.patterns.scan_class_metrics import (
    _count_self_attrs,
    _get_class_end,
    main,
    scan_file,
)


def _parse_class(source: str) -> ast.ClassDef:
    """Parse source and return the first ClassDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("No class found in source")


class TestGetClassEnd:
    def test_simple_class(self) -> None:
        node = _parse_class("class Foo:\n    pass\n")
        assert _get_class_end(node) == 2

    def test_class_with_methods(self) -> None:
        source = (
            "class Foo:\n    def bar(self):\n        return 1\n"
            "    def baz(self):\n        return 2\n"
        )
        node = _parse_class(source)
        assert _get_class_end(node) == 5

    def test_class_with_nested_class(self) -> None:
        source = "class Outer:\n    class Inner:\n        pass\n"
        node = _parse_class(source)
        assert _get_class_end(node) == 3

    def test_class_with_decorators(self) -> None:
        source = "class Foo:\n    x = 1\n    y = 2\n    z = 3\n"
        node = _parse_class(source)
        assert _get_class_end(node) == 4


class TestCountSelfAttrs:
    def test_no_attrs(self) -> None:
        node = _parse_class("class Foo:\n    def bar(self):\n        pass\n")
        assert _count_self_attrs(node) == 0

    def test_single_attr(self) -> None:
        node = _parse_class("class Foo:\n    def bar(self):\n        self.x = 1\n")
        assert _count_self_attrs(node) == 1

    def test_multiple_distinct_attrs(self) -> None:
        source = (
            "class Foo:\n    def bar(self):\n        self.x = 1\n"
            "        self.y = 2\n        self.z = 3\n"
        )
        node = _parse_class(source)
        assert _count_self_attrs(node) == 3

    def test_duplicate_attrs_counted_once(self) -> None:
        source = (
            "class Foo:\n    def bar(self):\n        self.x = 1\n"
            "    def baz(self):\n        self.x = 2\n"
        )
        node = _parse_class(source)
        assert _count_self_attrs(node) == 1

    def test_attr_access_not_assignment(self) -> None:
        source = "class Foo:\n    def bar(self):\n        return self.value + self.other\n"
        node = _parse_class(source)
        assert _count_self_attrs(node) == 2

    def test_non_self_attrs_ignored(self) -> None:
        source = "class Foo:\n    def bar(self, other):\n        other.x = 1\n        self.y = 2\n"
        node = _parse_class(source)
        assert _count_self_attrs(node) == 1


class TestScanFile:
    def test_file_with_class(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    def bar(self):\n        self.x = 1\n")
        results = scan_file(f)
        assert len(results) == 1
        r = results[0]
        assert r["class"] == "Foo"
        assert r["file"] == str(f)
        assert r["lines"] == 3
        assert r["methods"] == 1
        assert r["public"] == 1
        assert r["attrs"] == 1
        assert r["start"] == 1
        assert r["end"] == 3

    def test_file_with_private_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Foo:\n    def _private(self):\n        pass\n"
            "    def public(self):\n        pass\n"
        )
        results = scan_file(f)
        assert len(results) == 1
        assert results[0]["methods"] == 2
        assert results[0]["public"] == 1

    def test_file_with_async_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    async def bar(self):\n        pass\n")
        results = scan_file(f)
        assert len(results) == 1
        assert results[0]["methods"] == 1

    def test_file_with_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        results = scan_file(f)
        assert len(results) == 2
        names = {r["class"] for r in results}
        assert names == {"Foo", "Bar"}

    def test_file_with_nested_class(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        results = scan_file(f)
        assert len(results) == 2

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        results = scan_file(f)
        assert results == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def bar(:\n")
        results = scan_file(f)
        assert results == []

    def test_file_with_no_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    return 1\n")
        results = scan_file(f)
        assert results == []


class TestMain:
    def test_main_success(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class BigClass:\n"
            + "    def method(self):\n        pass\n" * 20
            + "class Small:\n    pass\n"
        )
        monkeypatch.setattr(
            sys, "argv",
            ["prog", str(src), "--top", "10", "--min-lines", "5"],
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "LINES" in out
        assert "BigClass" in out

    def test_main_no_classes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "No classes found" in err

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_min_lines_filter(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Small:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--min-lines", "100"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Small" not in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n" * 20)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = main()
        assert rc == 0

    def test_main_top_limit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        content = ""
        for i in range(5):
            content += (
                f"class Class{i}:\n"
                + "    def m(self):\n        pass\n" * 20 + "\n"
            )
        (src / "mod.py").write_text(content)
        monkeypatch.setattr(
            sys, "argv",
            ["prog", str(src), "--top", "2", "--min-lines", "5"],
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        # Only 2 classes should appear
        count = out.count("Class")
        assert count <= 2
