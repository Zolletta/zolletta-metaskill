"""Tests for scan_class_metrics module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.common.models import Finding
from zolletta_metaskill.patterns.scan_class_metrics import (
    main,
    scan_file,
    scan_module,
)


class TestScanFile:
    def test_file_with_class(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    def bar(self):\n        self.x = 1\n")
        results = scan_file(f)
        assert len(results) == 1
        r = results[0]
        assert isinstance(r, Finding)
        assert r.file == str(f)
        assert r.line == 1
        assert r.category == "class_metrics"
        assert "class=Foo" in r.description
        assert "lines=3" in r.description
        assert "methods=1" in r.description
        assert "public=1" in r.description
        assert "attrs=1" in r.description
        assert "start=1" in r.description
        assert "end=3" in r.description

    def test_file_with_private_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Foo:\n    def _private(self):\n        pass\n"
            "    def public(self):\n        pass\n"
        )
        results = scan_file(f)
        assert len(results) == 1
        assert "methods=2" in results[0].description
        assert "public=1" in results[0].description

    def test_file_with_async_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    async def bar(self):\n        pass\n")
        results = scan_file(f)
        assert len(results) == 1
        assert "methods=1" in results[0].description

    def test_file_with_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        results = scan_file(f)
        assert len(results) == 2
        names = set()
        for r in results:
            # Extract class name from description "class=NAME ..."
            assert "class=" in r.description
            part = r.description.split("class=")[1].split(" ")[0]
            names.add(part)
        assert names == {"Foo", "Bar"}

    def test_file_with_nested_class(self, tmp_path: Path) -> None:
        """ModuleInfo only contains top-level classes, not nested ones."""
        f = tmp_path / "mod.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        results = scan_file(f)
        # Only the top-level class is reported (ModuleInfo limitation)
        assert len(results) == 1
        assert "class=Outer" in results[0].description

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


class TestScanModule:
    def test_returns_findings(self, tmp_path: Path) -> None:
        from zolletta_metaskill.common.models import ClassInfo, MethodInfo, ModuleInfo

        f = tmp_path / "mod.py"
        module = ModuleInfo(
            path=f,
            language="python",
            classes=[
                ClassInfo(
                    name="Foo",
                    lineno=1,
                    end_lineno=3,
                    methods=[MethodInfo(name="bar", lineno=2, end_lineno=3)],
                ),
            ],
        )
        results = scan_module(module)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].category == "class_metrics"


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
