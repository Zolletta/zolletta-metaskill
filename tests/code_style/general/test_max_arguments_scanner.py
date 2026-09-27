"""Tests for max_arguments_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.max_arguments_scanner import (
    MaxArgumentsScanner,
)
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.engine.python_engine import PythonEngine
from zolletta_metaskill.core.structs import ClassInfo, Finding, MethodInfo, ModuleInfo

TS_PHP_AVAILABLE = PHPEngine._have_tree_sitter_php()


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {"code_style": {}},
        "php": None,
    }
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def _git_init(root: Path) -> None:
    """Initialise a git repo at *root* so gitignore rules apply."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def _write(path: Path, source: str) -> Path:
    """Write *source* to *path* and return it."""
    path.write_text(source)
    return path


def _function(name: str, params: int, lineno: int = 1) -> MethodInfo:
    """Build a :class:`MethodInfo` with *params* declared parameters."""
    return MethodInfo(
        name=name,
        lineno=lineno,
        end_lineno=lineno + 1,
        params=[f"p{i}" for i in range(params)],
    )


class TestMaxArgumentsScanner:
    # --- Tests for MaxArgumentsScanner.resolve_extensions(). ---

    def test_python_language_returns_py(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="python")
        assert MaxArgumentsScanner.resolve_extensions(settings) == {".py"}

    def test_php_language_returns_php(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="php", python=None, php={"code_style": {}})
        assert MaxArgumentsScanner.resolve_extensions(settings) == {".php"}

    def test_polyglot_settings_scans_all_configured_languages(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="python", php={"code_style": {}})
        assert MaxArgumentsScanner.resolve_extensions(settings) == {".py", ".php"}

    def test_missing_settings_falls_back_to_all_engines(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert MaxArgumentsScanner.resolve_extensions(missing) == {".py", ".php"}

    def test_unknown_language_falls_back_to_all_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = _write_settings(tmp_path, language="go", python=None)
        result = MaxArgumentsScanner.resolve_extensions(settings)
        err = capsys.readouterr().err
        assert "no engine for language 'go'" in err
        assert result == {".py", ".php"}

    def test_invalid_json_falls_back(self, tmp_path: Path) -> None:
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        bad = meta / "settings.json"
        bad.write_text("{ not json")
        assert MaxArgumentsScanner.resolve_extensions(bad) == {".py", ".php"}

    def test_disabled_language_not_scanned(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_max_arguments": False}},
            php={"code_style": {}},
        )
        assert MaxArgumentsScanner.resolve_extensions(settings) == {".php"}

    def test_all_languages_disabled_returns_empty(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_max_arguments": False}},
        )
        assert MaxArgumentsScanner.resolve_extensions(settings) == set()

    # --- Tests for MaxArgumentsScanner.resolve_max_args(). ---

    def test_reads_max_arguments_from_settings(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python={"code_style": {"max_arguments": 3}})
        assert MaxArgumentsScanner.resolve_max_args(settings) == 3

    def test_smallest_limit_wins_across_languages(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_arguments": 7}},
            php={"code_style": {"max_arguments": 4}},
        )
        assert MaxArgumentsScanner.resolve_max_args(settings) == 4

    def test_no_configured_limit_falls_back_to_default(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path)  # code_style is empty
        assert MaxArgumentsScanner.resolve_max_args(settings) == 5

    def test_missing_settings_falls_back_to_default(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert MaxArgumentsScanner.resolve_max_args(missing) == 5

    def test_language_field_without_section_falls_back(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python=None)
        assert MaxArgumentsScanner.resolve_max_args(settings) == 5

    def test_non_integer_limit_falls_back(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path, python={"code_style": {"max_arguments": "5"}}
        )
        assert MaxArgumentsScanner.resolve_max_args(settings) == 5

    def test_boolean_limit_falls_back(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path, python={"code_style": {"max_arguments": True}}
        )
        assert MaxArgumentsScanner.resolve_max_args(settings) == 5

    def test_disabled_language_limit_ignored(self, tmp_path: Path) -> None:
        """A disabled language's max_arguments does not lower the limit."""
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_arguments": 7}},
            php={
                "code_style": {"check_max_arguments": False, "max_arguments": 1}
            },
        )
        assert MaxArgumentsScanner.resolve_max_args(settings) == 7

    # --- Tests for MaxArgumentsScanner.scan_module(). ---

    def test_scan_module_function_over_limit(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "m.py",
            language="python",
            functions=[_function("too_many", 6, lineno=3)],
        )
        findings = MaxArgumentsScanner.scan_module(module, max_args=5)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "max_arguments"
        assert findings[0].severity == "medium"
        assert findings[0].fix_type == "manual"
        assert findings[0].line == 3
        assert "Function 'too_many' has 6 parameters (max 5)" in findings[0].description

    def test_scan_module_at_limit_passes(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "m.py",
            language="python",
            functions=[_function("ok", 5)],
        )
        assert MaxArgumentsScanner.scan_module(module, max_args=5) == []

    def test_scan_module_method_qualified_name(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "m.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Foo",
                    lineno=1,
                    end_lineno=5,
                    methods=[_function("bar", 7, lineno=2)],
                )
            ],
        )
        findings = MaxArgumentsScanner.scan_module(module, max_args=5)
        assert len(findings) == 1
        assert "Method 'Foo.bar' has 7 parameters (max 5)" in findings[0].description

    def test_scan_module_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "m.py", language="python", has_syntax_error=True
        )
        assert MaxArgumentsScanner.scan_module(module, max_args=5) == []

    # --- Tests for MaxArgumentsScanner.scan_file(). ---

    def test_scan_file_python_function(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        findings = MaxArgumentsScanner.scan_file(f, max_args=5)
        assert len(findings) == 1
        assert findings[0].file == str(f)
        assert "too_many" in findings[0].description

    def test_scan_file_keyword_only_params_counted(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path / "m.py", "def too_many(a, /, b, *, c, d, e, g):\n    pass\n"
        )
        findings = MaxArgumentsScanner.scan_file(f, max_args=5)
        assert len(findings) == 1
        assert "has 6 parameters" in findings[0].description

    def test_scan_file_variadic_params_not_counted(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "m.py", "def ok(a, *args, b, **kwargs):\n    pass\n")
        assert MaxArgumentsScanner.scan_file(f, max_args=5) == []

    def test_scan_file_unknown_extension_returns_empty(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "notes.txt", "def too_many(a, b, c, d, e, g): pass\n")
        assert MaxArgumentsScanner.scan_file(f, max_args=5) == []

    def test_scan_file_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "broken.py", "def foo(:\n    pass\n")
        assert MaxArgumentsScanner.scan_file(f, max_args=5) == []

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_scan_file_php_function(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path / "f.php",
            "<?php\nfunction tooMany($a, $b, $c, $d, $e, $g) {}\n",
        )
        findings = MaxArgumentsScanner.scan_file(f, max_args=5)
        assert len(findings) == 1
        assert "tooMany" in findings[0].description

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_scan_file_php_variadic_not_counted(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path / "f.php",
            "<?php\nfunction ok($a, $b, $c, $d, $e, ...$rest) {}\n",
        )
        assert MaxArgumentsScanner.scan_file(f, max_args=5) == []

    def test_scan_file_parse_failure_warns(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> ModuleInfo:
            raise OSError("unreadable")

        monkeypatch.setattr(PythonEngine, "parse_module", _fail)
        f = _write(tmp_path / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        assert MaxArgumentsScanner.scan_file(f, max_args=5) == []
        assert "Warning: could not parse" in capsys.readouterr().err

    def test_scan_file_import_error_warns(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A missing optional parser dependency degrades to a warning."""

        def _fail(*_args: object, **_kwargs: object) -> ModuleInfo:
            raise ImportError("tree-sitter-php is required")

        monkeypatch.setattr(PythonEngine, "parse_module", _fail)
        f = _write(tmp_path / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        assert MaxArgumentsScanner.scan_file(f, max_args=5) == []
        assert "Warning: could not parse" in capsys.readouterr().err

    # --- Tests for MaxArgumentsScanner.scan_directory(). ---

    def test_scans_only_matching_extension(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "a.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        _write(root / "b.php", "<?php\nfunction tooMany($a, $b, $c, $d, $e, $g) {}\n")
        findings = MaxArgumentsScanner.scan_directory(
            root, max_args=5, extensions={".py"}
        )
        assert len(findings) == 1
        assert findings[0].file == str(root / "a.py")

    def test_nested_directories_scanned(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        sub = root / "pkg" / "sub"
        sub.mkdir(parents=True)
        _write(sub / "deep.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        findings = MaxArgumentsScanner.scan_directory(
            root, max_args=5, extensions={".py"}
        )
        assert len(findings) == 1
        assert findings[0].file == str(sub / "deep.py")

    def test_gitignored_file_skipped(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "ignored.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        _write(root / "real.py", "def ok(a):\n    pass\n")
        findings = MaxArgumentsScanner.scan_directory(
            root, max_args=5, extensions={".py"}
        )
        assert findings == []

    def test_outside_git_repo_scans_everything(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        _write(vendor / "dep.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        findings = MaxArgumentsScanner.scan_directory(
            root, max_args=5, extensions={".py"}
        )
        assert len(findings) == 1

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        assert (
            MaxArgumentsScanner.scan_directory(root, max_args=5, extensions={".py"})
            == []
        )

    def test_max_args_resolved_from_settings(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python={"code_style": {"max_arguments": 2}})
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def three(a, b, c):\n    pass\n")
        findings = MaxArgumentsScanner.scan_directory(
            root, extensions={".py"}, settings_path=settings
        )
        assert len(findings) == 1

    def test_extensions_resolved_from_settings(self, tmp_path: Path) -> None:
        """Omitted extensions resolve from settings.json (python → .py)."""
        settings = _write_settings(tmp_path, language="python")
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        _write(root / "f.php", "<?php\nfunction tooMany($a, $b, $c, $d, $e, $g) {}\n")
        findings = MaxArgumentsScanner.scan_directory(root, settings_path=settings)
        assert len(findings) == 1
        assert findings[0].file == str(root / "m.py")

    def test_git_missing_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_git(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("git not installed")

        monkeypatch.setattr(subprocess, "run", _no_git)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        findings = MaxArgumentsScanner.scan_directory(
            root, max_args=5, extensions={".py"}
        )
        assert len(findings) == 1

    # --- Tests for MaxArgumentsScanner.main(). ---

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_max_arguments=false for every configured language → SKIPPED."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_max_arguments": False}})
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_max_arguments": False}})
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = MaxArgumentsScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured source directory on disk → usage error."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "ok.py", "def ok(a, b):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_violation_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "m.py" in out
        assert "too_many" in out
        assert "6 params" in out

    def test_main_method_qualified_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(
            root / "m.py",
            "class Foo:\n    def bar(self, a, b, c, d, e, g):\n        pass\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Foo.bar" in out

    def test_main_only_scans_configured_language(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, language="python")
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.php", "<?php\nfunction tooMany($a, $b, $c, $d, $e, $g) {}\n")
        _write(root / "ok.py", "def ok(a):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "m.php" not in out

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_main_php_project(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(
            tmp_path,
            language="php",
            python=None,
            php={"code_style": {"max_arguments": 5}},
        )
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "f.php", "<?php\nfunction tooMany($a, $b, $c, $d, $e, $g) {}\n")
        _write(root / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "f.php" in out
        assert "m.py" not in out

    def test_main_max_args_from_settings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The limit comes from settings.json max_arguments."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"max_arguments": 7}})
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def six(a, b, c, d, e, g):\n    pass\n")
        _write(root / "n.py", "def eight(a, b, c, d, e, g, h, i):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "max 7" in out
        assert "eight" in out
        assert "six" not in out

    def test_main_gitignored_files_not_scanned(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        (tmp_path / ".gitignore").write_text("vendor/\n")
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        _write(vendor / "dep.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        _write(root / "real.py", "def ok(a):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "dep.py" not in out

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        _write(root / "ok.py", "def ok(a):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        report = json.loads(out)
        assert report["scanned"] == 2
        assert report["max_arguments"] == 5
        assert report["violation_count"] == 1
        assert report["directories"] == ["src"]
        assert report["violations"] == [
            {
                "file": "src/m.py",
                "function": "too_many",
                "line": 1,
                "params": 6,
                "over": 1,
            }
        ]

    def test_main_json_violations_sorted_by_params_desc(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "medium.py", "def six(a, b, c, d, e, g):\n    pass\n")
        _write(root / "biggest.py", "def nine(a, b, c, d, e, g, h, i, j):\n    pass\n")
        _write(root / "small_over.py", "def six2(a, b, c, d, e, g):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = MaxArgumentsScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert [v["file"] for v in report["violations"]] == [
            "src/biggest.py",
            "src/medium.py",
            "src/small_over.py",
        ]

    def test_main_default_max_args_is_5(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "ok.py", "def five(a, b, c, d, e):\n    pass\n")
        _write(root / "long.py", "def six(a, b, c, d, e, g):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "six" in out
        assert "five" not in out

    def test_main_source_roots_from_settings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scan roots come from python.paths.source in settings.json."""
        monkeypatch.chdir(tmp_path)
        _write_settings(
            tmp_path,
            python={
                "paths": {"source": ["lib"], "tests": ["tests"], "package": "myproject"},
                "code_style": {"max_arguments": 5},
            },
        )
        lib = tmp_path / "lib"
        lib.mkdir()
        _write(lib / "m.py", "def too_many(a, b, c, d, e, g):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = MaxArgumentsScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["lib"]
        assert report["violation_count"] == 1

    def test_main_unreadable_file_warns_and_continues(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file that cannot be parsed warns on stderr and is skipped."""

        def _fail(*_args: object, **_kwargs: object) -> ModuleInfo:
            raise OSError("unreadable")

        monkeypatch.setattr(PythonEngine, "parse_module", _fail)
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write(root / "a.py", "def one(a):\n    pass\n")
        _write(root / "b.py", "def two(a):\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = MaxArgumentsScanner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err.count("Warning: could not parse") == 2
        assert "all clear" in captured.out
