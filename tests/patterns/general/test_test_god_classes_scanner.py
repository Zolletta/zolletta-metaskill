"""Tests for test_god_classes_scanner module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.patterns.general.test_god_classes_scanner import TestGodClassesScanner


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {
            "patterns": {},
            "paths": {"source": ["src"], "tests": ["tests"], "package": "mypkg"},
        },
        "php": None,
    }
    python_overrides = overrides.pop("python", None)
    if isinstance(python_overrides, dict):
        base_python = settings["python"]
        assert isinstance(base_python, dict)
        for key, value in python_overrides.items():
            if isinstance(value, dict) and isinstance(base_python.get(key), dict):
                base_python[key].update(value)
            else:
                base_python[key] = value
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def test_write_settings_replaces_non_dict_python_value(tmp_path: Path) -> None:
    """A non-dict ``python`` override value replaces the base value."""
    path = _write_settings(tmp_path, python={"tools": "none"})
    written = json.loads(path.read_text())
    python = written["python"]
    assert isinstance(python, dict)
    assert python["tools"] == "none"


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Chdir into tmp_path and run main() with *argv*."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    return TestGodClassesScanner.main()


class TestTestGodClassesScanner:
    # --- ScanFile ---

    def test_file_with_test_class(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text(
            "class TestFoo:\n    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
        )
        results = TestGodClassesScanner.scan_file(f)
        assert len(results) == 1
        r = results[0]
        assert isinstance(r, Finding)
        assert r.file == str(f)
        assert r.line == 1
        assert r.category == "test_god_class"
        assert "class=TestFoo" in r.description
        assert "lines=5" in r.description
        assert "methods=2" in r.description
        assert "method_names=test_a,test_b" in r.description
        assert "start=1" in r.description
        assert "end=5" in r.description

    def test_file_with_async_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class TestFoo:\n    async def test_async(self):\n        pass\n")
        results = TestGodClassesScanner.scan_file(f)
        assert len(results) == 1
        assert "methods=1" in results[0].description

    def test_file_with_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class TestFoo:\n    pass\nclass TestBar:\n    pass\n")
        results = TestGodClassesScanner.scan_file(f)
        assert len(results) == 2
        names = set()
        for r in results:
            assert "class=" in r.description
            part = r.description.split("class=")[1].split(" ")[0]
            names.add(part)
        assert names == {"TestFoo", "TestBar"}

    def test_scan_file_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        results = TestGodClassesScanner.scan_file(f)
        assert results == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class TestFoo:\n    def (:\n")
        results = TestGodClassesScanner.scan_file(f)
        assert results == []

    def test_file_with_no_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("def test_func():\n    pass\n")
        results = TestGodClassesScanner.scan_file(f)
        assert results == []

    def test_non_python_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.txt"
        f.write_text("not python")
        results = TestGodClassesScanner.scan_file(f)
        assert results == []

    def test_file_with_non_test_class(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mod.py"
        f.write_text("class Helper:\n    def helper_method(self):\n        pass\n")
        results = TestGodClassesScanner.scan_file(f)
        assert len(results) == 1
        assert "class=Helper" in results[0].description
        assert "method_names=helper_method" in results[0].description

    def test_scan_file_nested_class_contains_class_testouter(self, tmp_path: Path) -> None:
        """ModuleInfo only contains top-level classes, not nested ones."""
        f = tmp_path / "test_mod.py"
        f.write_text("class TestOuter:\n    class Inner:\n        pass\n")
        results = TestGodClassesScanner.scan_file(f)
        # Only the top-level class is reported (ModuleInfo limitation)
        assert len(results) == 1
        assert "class=TestOuter" in results[0].description

    # --- ScanModule ---

    def test_moduleinfo_returns_findings_returns_test_god_class(self, tmp_path: Path) -> None:
        from zolletta_metaskill.core.structs import ClassInfo, MethodInfo, ModuleInfo

        f = tmp_path / "test_mod.py"
        module = ModuleInfo(
            path=f,
            language="python",
            classes=[
                ClassInfo(
                    name="TestFoo",
                    lineno=1,
                    end_lineno=5,
                    methods=[
                        MethodInfo(name="test_a", lineno=2, end_lineno=3),
                        MethodInfo(name="test_b", lineno=4, end_lineno=5),
                    ],
                ),
            ],
        )
        results = TestGodClassesScanner.scan_module(module)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].category == "test_god_class"

    # --- Main ---

    def test_main_success_contains_testbig(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text(
            "class TestBig:\n" + "    def test_m(self):\n        pass\n" * 10
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "LINES" in out
        assert "TestBig" in out

    def test_main_show_methods(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text(
            "class TestFoo:\n    def test_a(self):\n        pass\n"
            "    def test_b(self):\n        pass\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--show-methods"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_a" in out
        assert "test_b" in out

    def test_main_no_classes(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("x = 1\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 0
        assert "No test classes found" in err

    def test_main_missing_test_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured test directories" in err

    def test_main_check_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_test_god_classes": False}})
        (tmp_path / "tests").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0
        assert "SKIPPED" in capsys.readouterr().out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_test_god_classes": False}})
        (tmp_path / "tests").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_top_limit_setting(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"test_god_classes_top": 2}})
        tests = tmp_path / "tests"
        tests.mkdir()
        content = ""
        for i in range(5):
            content += (
                f"class TestClass{i}:\n" + "    def test_m(self):\n        pass\n" * 10 + "\n"
            )
        (tests / "test_mod.py").write_text(content)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert out.count("TestClass") <= 2

    def test_main_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("class TestFoo:\n    def test_a(self):\n        pass\n")
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["total_classes"] == 1
        assert report["classes"][0]["class"] == "TestFoo"
        assert report["classes"][0]["method_names"] == ["test_a"]
        assert report["directories"] == ["tests"]

    def test_main_sorted_by_lines(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text(
            "class TestSmall:\n    def test_a(self):\n        pass\n"
            "class TestBig:\n" + "    def test_m(self):\n        pass\n" * 20
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert out.index("TestBig") < out.index("TestSmall")

    def test_main_gitignored_files_skipped(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("tests/ignored/\n")
        _write_settings(tmp_path)
        ignored = tmp_path / "tests" / "ignored"
        ignored.mkdir(parents=True)
        (ignored / "test_mod.py").write_text("class TestHidden:\n    pass\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 0
        assert "No test classes found" in err
