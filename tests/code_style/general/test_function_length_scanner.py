"""Tests for function_length_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.function_length_scanner import (
    FunctionLengthScanner,
)
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.engine.python_engine import PythonEngine
from zolletta_metaskill.core.structs import ClassInfo, Finding, MethodInfo, ModuleInfo

TS_PHP_AVAILABLE = PHPEngine._have_tree_sitter_php()


class TestFunctionLengthScanner:
    # --- Helpers. ---

    @staticmethod
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

    @staticmethod
    def _git_init(root: Path) -> None:
        """Initialise a git repo at *root* so gitignore rules apply."""
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    @staticmethod
    def _write(path: Path, source: str) -> Path:
        """Write *source* to *path* and return it."""
        path.write_text(source)
        return path

    @staticmethod
    def _method(name: str, lineno: int, end_lineno: int) -> MethodInfo:
        """Build a :class:`MethodInfo` spanning ``lineno``..``end_lineno``."""
        return MethodInfo(name=name, lineno=lineno, end_lineno=end_lineno)

    @staticmethod
    def _py_function(name: str, body_lines: int) -> str:
        """Return Python source for a function spanning ``body_lines + 1`` lines."""
        body = "\n".join(f"    x{i} = {i}" for i in range(body_lines))
        return f"def {name}():\n{body}\n"

    # --- Tests for FunctionLengthScanner.resolve_extensions(). ---

    def test_python_language_returns_py(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, language="python")
        assert FunctionLengthScanner.resolve_extensions(settings) == {".py"}

    def test_php_language_returns_php(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, language="php", python=None, php={"code_style": {}}
        )
        assert FunctionLengthScanner.resolve_extensions(settings) == {".php"}

    def test_polyglot_settings_scans_all_configured_languages(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, language="python", php={"code_style": {}})
        assert FunctionLengthScanner.resolve_extensions(settings) == {".py", ".php"}

    def test_missing_settings_falls_back_to_all_engines(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert FunctionLengthScanner.resolve_extensions(missing) == {".py", ".php"}

    def test_unknown_language_falls_back_to_all_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = self._write_settings(tmp_path, language="go", python=None)
        result = FunctionLengthScanner.resolve_extensions(settings)
        err = capsys.readouterr().err
        assert "no engine for language 'go'" in err
        assert result == {".py", ".php"}

    def test_invalid_json_falls_back(self, tmp_path: Path) -> None:
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        bad = meta / "settings.json"
        bad.write_text("{ not json")
        assert FunctionLengthScanner.resolve_extensions(bad) == {".py", ".php"}

    def test_disabled_language_not_scanned(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_function_length": False}},
            php={"code_style": {}},
        )
        assert FunctionLengthScanner.resolve_extensions(settings) == {".php"}

    def test_all_languages_disabled_returns_empty(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_function_length": False}},
        )
        assert FunctionLengthScanner.resolve_extensions(settings) == set()

    # --- Tests for FunctionLengthScanner.resolve_max_lines(). ---

    def test_reads_max_function_length_from_settings(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, python={"code_style": {"max_function_length": 50}}
        )
        assert FunctionLengthScanner.resolve_max_lines(settings) == 50

    def test_smallest_limit_wins_across_languages(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_function_length": 100}},
            php={"code_style": {"max_function_length": 60}},
        )
        assert FunctionLengthScanner.resolve_max_lines(settings) == 60

    def test_no_configured_limit_falls_back_to_default(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path)  # code_style is empty
        assert FunctionLengthScanner.resolve_max_lines(settings) == 100

    def test_missing_settings_falls_back_to_default(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert FunctionLengthScanner.resolve_max_lines(missing) == 100

    def test_language_field_without_section_falls_back(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, python=None)
        assert FunctionLengthScanner.resolve_max_lines(settings) == 100

    def test_section_without_code_style_falls_back(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, python={"tools": {}})
        assert FunctionLengthScanner.resolve_max_lines(settings) == 100

    # --- Tests for FunctionLengthScanner.scan_module(). ---

    def test_function_over_limit_flagged(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            functions=[self._method("big", 10, 140)],
        )
        findings = FunctionLengthScanner.scan_module(module, max_lines=100)
        assert len(findings) == 1
        f = findings[0]
        assert isinstance(f, Finding)
        assert f.category == "function_length"
        assert f.severity == "medium"
        assert f.fix_type == "manual"
        assert f.line == 10
        assert "'big'" in f.description
        assert "131" in f.description
        assert "100" in f.description

    def test_function_at_limit_not_flagged(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            functions=[self._method("ok", 1, 100)],
        )
        assert FunctionLengthScanner.scan_module(module, max_lines=100) == []

    def test_method_inside_class_flagged(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Big",
                    lineno=1,
                    end_lineno=200,
                    methods=[self._method("run", 20, 150)],
                )
            ],
        )
        findings = FunctionLengthScanner.scan_module(module, max_lines=100)
        assert len(findings) == 1
        assert "'Big.run'" in findings[0].description
        assert "Method" in findings[0].description

    def test_syntax_error_module_produces_no_findings(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "bad.py",
            language="python",
            functions=[self._method("big", 1, 200)],
            has_syntax_error=True,
        )
        assert FunctionLengthScanner.scan_module(module, max_lines=5) == []

    def test_short_functions_ignored(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            functions=[self._method("a", 1, 5), self._method("b", 10, 20)],
        )
        assert FunctionLengthScanner.scan_module(module, max_lines=100) == []

    # --- Tests for FunctionLengthScanner.scan_file(). ---

    def test_python_file_over_limit_returns_finding(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "mod.py", self._py_function("big", 150))
        findings = FunctionLengthScanner.scan_file(f, max_lines=100)
        assert len(findings) == 1
        assert findings[0].category == "function_length"
        assert findings[0].file == str(f)

    def test_python_file_under_limit_returns_empty(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "mod.py", self._py_function("small", 10))
        assert FunctionLengthScanner.scan_file(f, max_lines=100) == []

    def test_unknown_extension_returns_empty(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "script.rb", "def big\n" * 200)
        assert FunctionLengthScanner.scan_file(f, max_lines=5) == []

    def test_syntax_error_file_returns_empty(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "bad.py", "def broken(:\n" * 200)
        assert FunctionLengthScanner.scan_file(f, max_lines=5) == []

    def test_import_error_warns_and_returns_empty(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> ModuleInfo:
            raise ImportError("tree-sitter-php missing")

        monkeypatch.setattr(PythonEngine, "parse_module", _fail)
        f = self._write(tmp_path / "mod.py", self._py_function("big", 150))
        assert FunctionLengthScanner.scan_file(f, max_lines=5) == []
        assert "Warning: could not parse" in capsys.readouterr().err

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_file_over_limit_returns_finding(self, tmp_path: Path) -> None:
        body = "\n".join(f"    $x{i} = {i};" for i in range(120))
        f = self._write(tmp_path / "lib.php", f"<?php\nfunction big() {{\n{body}\n}}\n")
        findings = FunctionLengthScanner.scan_file(f, max_lines=100)
        assert len(findings) == 1
        assert "'big'" in findings[0].description

    # --- Tests for FunctionLengthScanner.scan_directory(). ---

    def test_scans_only_matching_extension(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "a.py", self._py_function("big", 150))
        self._write(root / "b.txt", "x\n" * 200)
        findings = FunctionLengthScanner.scan_directory(
            root, max_lines=100, extensions={".py"}
        )
        assert len(findings) == 1
        assert findings[0].file == str(root / "a.py")

    def test_nested_directories_scanned(self, tmp_path: Path) -> None:
        sub = tmp_path / "src" / "pkg" / "sub"
        sub.mkdir(parents=True)
        self._write(sub / "deep.py", self._py_function("big", 150))
        findings = FunctionLengthScanner.scan_directory(
            tmp_path / "src", max_lines=100, extensions={".py"}
        )
        assert len(findings) == 1
        assert findings[0].file == str(sub / "deep.py")

    def test_gitignored_file_skipped(self, tmp_path: Path) -> None:
        self._git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "ignored.py", self._py_function("big", 150))
        self._write(root / "real.py", self._py_function("small", 5))
        findings = FunctionLengthScanner.scan_directory(
            root, max_lines=100, extensions={".py"}
        )
        assert findings == []

    def test_outside_git_repo_scans_everything(self, tmp_path: Path) -> None:
        vendor = tmp_path / "src" / "vendor"
        vendor.mkdir(parents=True)
        self._write(vendor / "dep.py", self._py_function("big", 150))
        findings = FunctionLengthScanner.scan_directory(
            tmp_path / "src", max_lines=100, extensions={".py"}
        )
        assert len(findings) == 1

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        assert (
            FunctionLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
            == []
        )

    def test_max_lines_resolved_from_settings(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, python={"code_style": {"max_function_length": 10}}
        )
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "mid.py", self._py_function("mid", 20))
        findings = FunctionLengthScanner.scan_directory(
            root, extensions={".py"}, settings_path=settings
        )
        assert len(findings) == 1

    def test_extensions_resolved_from_settings(self, tmp_path: Path) -> None:
        """scan_directory() without ``extensions`` resolves them itself."""
        settings = self._write_settings(tmp_path, python={"code_style": {}})
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "mid.py", self._py_function("mid", 20))
        self._write(root / "mid.txt", "x\n" * 200)
        findings = FunctionLengthScanner.scan_directory(
            root, max_lines=10, settings_path=settings
        )
        assert len(findings) == 1
        assert findings[0].file == str(root / "mid.py")

    # --- Tests for FunctionLengthScanner.main(). ---

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_function_length=false for every configured language → SKIPPED."""
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path, python={"code_style": {"check_function_length": False}})
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "mod.py", self._py_function("big", 150))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path, python={"code_style": {"check_function_length": False}})
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = FunctionLengthScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured source directory on disk → usage error."""
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "short.py", self._py_function("small", 10))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_violation_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path, python={"code_style": {"max_function_length": 10}})
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "long.py", self._py_function("big", 20))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "long.py" in out
        assert "big" in out

    def test_main_only_scans_configured_language(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_function_length": 10}},
        )
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "long.php", "<?php\n" + "echo 1;\n" * 50)
        self._write(root / "short.py", self._py_function("small", 5))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "long.php" not in out

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_main_php_project(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(
            tmp_path,
            language="php",
            python=None,
            php={
                "code_style": {"max_function_length": 10},
                "autoload": {"psr-4": {"App\\\\": "src"}},
            },
        )
        root = tmp_path / "src"
        root.mkdir()
        body = "\n".join(f"    $x{i} = {i};" for i in range(20))
        self._write(root / "long.php", f"<?php\nfunction big() {{\n{body}\n}}\n")
        self._write(root / "long.py", self._py_function("alsolong", 30))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "long.php" in out
        assert "long.py" not in out

    def test_main_json_output_shape(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path, python={"code_style": {"max_function_length": 5}})
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "mod.py", self._py_function("big", 10))
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = FunctionLengthScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["src"]
        assert report["scanned"] == 1
        assert report["max_function_length"] == 5
        assert report["violation_count"] == 1
        v = report["violations"][0]
        assert v["file"].endswith("mod.py")
        assert v["function"] == "big"
        assert v["line"] == 1
        assert v["lines"] == 11
        assert v["over"] == 6

    def test_main_skips_unparsable_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file whose engine parse fails warns on stderr and is skipped."""
        def _fail(*_args: object, **_kwargs: object) -> ModuleInfo:
            raise ImportError("engine unavailable")

        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path, python={"code_style": {"max_function_length": 5}})
        monkeypatch.setattr(PythonEngine, "parse_module", _fail)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "mod.py", self._py_function("big", 10))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FunctionLengthScanner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "all clear" in captured.out
        assert "Warning: could not parse" in captured.err
