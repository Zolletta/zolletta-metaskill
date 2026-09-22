"""Tests for class_metrics_scanner module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.patterns.general.class_metrics_scanner import ClassMetricsScanner


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
    return ClassMetricsScanner.main()


class TestClassMetricsScanner:
    # --- ScanFile ---

    def test_file_with_class(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    def bar(self):\n        self.x = 1\n")
        results = ClassMetricsScanner.scan_file(f)
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
        results = ClassMetricsScanner.scan_file(f)
        assert len(results) == 1
        assert "methods=2" in results[0].description
        assert "public=1" in results[0].description

    def test_file_with_async_methods(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    async def bar(self):\n        pass\n")
        results = ClassMetricsScanner.scan_file(f)
        assert len(results) == 1
        assert "methods=1" in results[0].description

    def test_file_with_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        results = ClassMetricsScanner.scan_file(f)
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
        results = ClassMetricsScanner.scan_file(f)
        # Only the top-level class is reported (ModuleInfo limitation)
        assert len(results) == 1
        assert "class=Outer" in results[0].description

    def test_scan_file_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        results = ClassMetricsScanner.scan_file(f)
        assert results == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def bar(:\n")
        results = ClassMetricsScanner.scan_file(f)
        assert results == []

    def test_file_with_no_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    return 1\n")
        results = ClassMetricsScanner.scan_file(f)
        assert results == []

    def test_non_python_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.txt"
        f.write_text("not python")
        results = ClassMetricsScanner.scan_file(f)
        assert results == []

    # --- ScanModule ---

    def test_moduleinfo_returns_findings_returns_class_metrics(self, tmp_path: Path) -> None:
        from zolletta_metaskill.core.structs import ClassInfo, MethodInfo, ModuleInfo

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
        results = ClassMetricsScanner.scan_module(module)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].category == "class_metrics"

    # --- Main ---

    def test_main_success_contains_bigclass(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"class_metrics_min_lines": 5}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class BigClass:\n"
            + "    def method(self):\n        pass\n" * 20
            + "class Small:\n    pass\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "LINES" in out
        assert "BigClass" in out

    def test_main_no_classes(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 0
        assert "No classes found" in err

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_check_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_class_metrics": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0
        assert "SKIPPED" in capsys.readouterr().out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_class_metrics": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_min_lines_setting(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"class_metrics_min_lines": 100}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Small:\n    pass\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Small" not in out

    def test_main_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"class_metrics_min_lines": 5}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class BigClass:\n" + "    def method(self):\n        pass\n" * 20
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["total_classes"] == 1
        assert report["classes"][0]["class"] == "BigClass"
        assert report["min_lines"] == 5
        assert report["top"] == 30
        assert report["directories"] == ["src"]

    def test_main_top_limit_setting(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(
            tmp_path,
            python={"patterns": {"class_metrics_top": 2, "class_metrics_min_lines": 5}},
        )
        src = tmp_path / "src"
        src.mkdir()
        content = ""
        for i in range(5):
            content += f"class Class{i}:\n" + "    def m(self):\n        pass\n" * 20 + "\n"
        (src / "mod.py").write_text(content)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        count = out.count("Class")
        assert count <= 2

    def test_main_gitignored_files_skipped(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("src/ignored/\n")
        _write_settings(tmp_path)
        ignored = tmp_path / "src" / "ignored"
        ignored.mkdir(parents=True)
        (ignored / "mod.py").write_text("class Hidden:\n    pass\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 0
        assert "No classes found" in err
