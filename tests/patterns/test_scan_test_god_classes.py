"""Tests for scan_test_god_classes module."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.patterns.scan_test_god_classes import (
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
        node = _parse_class("class TestFoo:\n    pass\n")
        assert _get_class_end(node) == 2

    def test_class_with_methods(self) -> None:
        source = (
            "class TestFoo:\n    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
        )
        node = _parse_class(source)
        assert _get_class_end(node) == 5

    def test_class_with_nested_class(self) -> None:
        source = "class TestOuter:\n    class Inner:\n        pass\n"
        node = _parse_class(source)
        assert _get_class_end(node) == 3


class TestScanFile:
    def test_file_with_test_class(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text(
            "class TestFoo:\n    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
        )
        results = scan_file(f)
        assert len(results) == 1
        r = results[0]
        assert r["class"] == "TestFoo"
        assert r["file"] == str(f)
        assert r["lines"] == 5
        assert r["methods"] == 2
        assert r["method_names"] == ["test_a", "test_b"]
        assert r["start"] == 1
        assert r["end"] == 5

    def test_file_with_async_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class TestFoo:\n    async def test_async(self):\n        pass\n")
        results = scan_file(f)
        assert len(results) == 1
        assert results[0]["methods"] == 1

    def test_file_with_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class TestFoo:\n    pass\nclass TestBar:\n    pass\n")
        results = scan_file(f)
        assert len(results) == 2
        names = {r["class"] for r in results}
        assert names == {"TestFoo", "TestBar"}

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        results = scan_file(f)
        assert results == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class TestFoo:\n    def (:\n")
        results = scan_file(f)
        assert results == []

    def test_file_with_no_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("def test_func():\n    pass\n")
        results = scan_file(f)
        assert results == []

    def test_file_with_non_test_class(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class Helper:\n    def helper_method(self):\n        pass\n")
        results = scan_file(f)
        assert len(results) == 1
        assert results[0]["class"] == "Helper"
        assert results[0]["method_names"] == ["helper_method"]

    def test_nested_class(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class TestOuter:\n    class Inner:\n        pass\n")
        results = scan_file(f)
        assert len(results) == 2


class TestMain:
    def test_main_success(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text(
            "class TestBig:\n" + "    def test_m(self):\n        pass\n" * 10
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tests), "--top", "10"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "LINES" in out
        assert "TestBig" in out

    def test_main_show_methods(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text(
            "class TestFoo:\n    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tests), "--show-methods"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_a" in out
        assert "test_b" in out

    def test_main_no_classes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("x = 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(tests)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "No test classes found" in err

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_top_limit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        content = ""
        for i in range(5):
            content += (
                f"class TestClass{i}:\n"
                + "    def test_m(self):\n        pass\n" * 10 + "\n"
            )
        (tests / "test_mod.py").write_text(content)
        monkeypatch.setattr(sys, "argv", ["prog", str(tests), "--top", "2"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert out.count("TestClass") <= 2

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("class TestFoo:\n    def test_a(self):\n        pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = main()
        assert rc == 0

    def test_main_sorted_by_lines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text(
            "class TestSmall:\n    def test_a(self):\n        pass\n"
            "class TestBig:\n"
            + "    def test_m(self):\n        pass\n" * 20
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tests)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert out.index("TestBig") < out.index("TestSmall")
