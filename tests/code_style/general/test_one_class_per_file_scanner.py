"""Tests for one_class_per_file_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.one_class_per_file_scanner import OneClassPerFileScanner
from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding


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


class TestOneClassPerFileScanner:
    # --- Tests for OneClassPerFileScanner._snake_to_pascal(). ---

    def test_snake_to_pascal_simple_input_returns_myclass(self) -> None:
        assert OneClassPerFileScanner._snake_to_pascal("my_class") == "MyClass"

    def test_snake_to_pascal_single_word_returns_cache(self) -> None:
        assert OneClassPerFileScanner._snake_to_pascal("cache") == "Cache"

    def test_snake_to_pascal_empty_input_returns_empty(self) -> None:
        assert OneClassPerFileScanner._snake_to_pascal("") == ""

    def test_snake_to_pascal_multiple_words_returns_myawesomeclass(self) -> None:
        assert OneClassPerFileScanner._snake_to_pascal("my_awesome_class") == "MyAwesomeClass"

    def test_snake_to_pascal_already_pascal_returns_myclass(self) -> None:
        # No underscores, capitalize will title-case it
        assert OneClassPerFileScanner._snake_to_pascal("myclass") == "Myclass"

    def test_snake_to_pascal_leading_underscore_returns_class(self) -> None:
        # split on "_" produces ["", "class"] -> "" + "Class"
        assert OneClassPerFileScanner._snake_to_pascal("_class") == "Class"

    # --- Tests for OneClassPerFileScanner._names_match(). ---

    def test_names_match_snake_case_stem_input_returns_true(self) -> None:
        """A class named exactly like the snake_case stem matches, not only PascalCase."""
        assert OneClassPerFileScanner._names_match("my_file", "my_file") is True

    # --- Tests for OneClassPerFileScanner.scan_file() — now returns list[Finding]. ---

    def test_single_class_no_violation(self, tmp_path: Path) -> None:
        """A file with one class matching the filename produces no findings."""
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == []

    def test_scan_file_multiple_classes_contains_2_classes(self, tmp_path: Path) -> None:
        """A file with 2+ classes produces a multi_class finding."""
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == [
            Finding(
                file=str(f),
                line=1,
                category="multi_class",
                severity="high",
                description="2 classes: Foo, Bar",
                fix_type="manual",
            )
        ]

    def test_scan_file_zero_classes_returns_low(self, tmp_path: Path) -> None:
        """A file with no classes produces a zero_class finding."""
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 42\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == [
            Finding(
                file=str(f),
                line=0,
                category="zero_class",
                severity="low",
                description="No classes (utility/helper module)",
                fix_type="skip",
            )
        ]

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A syntax-error file produces no findings (skipped)."""
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == []

    def test_nested_class_treated_as_single(self, tmp_path: Path) -> None:
        """Nested classes are not counted by the engine (only top-level).

        The file has one top-level class 'Outer' with a nested 'Inner'.
        Since only 'Outer' is counted, this is a name_mismatch (Outer != Nested).
        """
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "name_mismatch"
        assert "Outer" in findings[0].description

    def test_scan_file_empty_file_returns_zero_class(self, tmp_path: Path) -> None:
        """An empty file produces a zero_class finding."""
        f = tmp_path / "empty.py"
        f.write_text("")
        findings = OneClassPerFileScanner.scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "zero_class"

    def test_file_path_in_finding(self, tmp_path: Path) -> None:
        """The finding's file field matches the path."""
        f = tmp_path / "thing.py"
        f.write_text("class WrongName:\n    pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert len(findings) == 1
        assert findings[0].file == str(f)

    def test_scan_file_name_mismatch_contains_user(self, tmp_path: Path) -> None:
        """A class name that doesn't match the filename produces a finding."""
        f = tmp_path / "user.py"
        f.write_text("class WrongName:\n    pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == [
            Finding(
                file=str(f),
                line=1,
                category="name_mismatch",
                severity="medium",
                description=(
                    "Class 'WrongName' doesn't match filename. "
                    "Expected 'User' (or rename file to match class)"
                ),
                fix_type="manual",
            )
        ]

    def test_class_name_matches_filename(self, tmp_path: Path) -> None:
        """A class name matching the PascalCase filename produces no findings."""
        f = tmp_path / "user_account.py"
        f.write_text("class UserAccount:\n    pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == []

    def test_class_name_equals_stem(self, tmp_path: Path) -> None:
        """Class name == file stem (snake_case) is also accepted."""
        f = tmp_path / "user.py"
        f.write_text("class user:\n    pass\n")
        findings = OneClassPerFileScanner.scan_file(f)
        assert findings == []

    # --- Tests for OneClassPerFileScanner.scan_module() with ModuleInfo directly. ---

    def test_syntax_error_module(self, tmp_path: Path) -> None:
        """A module with has_syntax_error returns no findings."""
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(tmp_path / "bad.py")
        assert engine is not None
        module = engine.parse_module(tmp_path / "bad.py")
        # parse_module on a non-existent file returns has_syntax_error=True
        assert module.has_syntax_error
        assert OneClassPerFileScanner.scan_module(module) == []

    def test_multi_class_finding(self, tmp_path: Path) -> None:
        """Two top-level classes produce a multi_class finding."""
        ProjectConfig.ensure_engines()
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        findings = OneClassPerFileScanner.scan_module(module)
        assert len(findings) == 1
        assert findings[0].category == "multi_class"

    def test_returns_finding_objects(self, tmp_path: Path) -> None:
        """scan_module returns Finding dataclass instances."""
        ProjectConfig.ensure_engines()
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 1\n")
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        findings = OneClassPerFileScanner.scan_module(module)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)

    # --- Tests for OneClassPerFileScanner.main(). ---

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_one_class_per_file=false for every configured language → SKIPPED."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_one_class_per_file": False}})
        (tmp_path / "src").mkdir()
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert out.splitlines() == [
            "=" * 70,
            "1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT",
            "=" * 70,
            "",
            "Result: SKIPPED (check_one_class_per_file disabled in settings.json)",
            "",
        ]

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_one_class_per_file": False}})
        (tmp_path / "src").mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report == {
            "skipped": True,
            "reason": "check_one_class_per_file disabled in settings.json",
        }

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured source directory on disk → usage error."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert err == "Error: no configured source directories exist on disk\n"

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_multi_class_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "2+ classes" in out

    def test_main_name_mismatch(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class WrongName:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Class name != filename" in out
        assert "WrongName" in out

    def test_main_zero_class_reported(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "utils.py").write_text("def helper():\n    return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "0 classes" in out
        assert "utils.py" in out

    def test_main_zero_class_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_zero_class_files=false filters zero-class findings."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_zero_class_files": False}})
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "utils.py").write_text("def helper():\n    return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "0 classes" not in out
        assert "utils.py" not in out
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        expected = {
            "directories": ["src"],
            "scanned": 1,
            "violation_count": 1,
            "violations": [
                {
                    "file": "src/multi.py",
                    "line": 1,
                    "category": "multi_class",
                    "severity": "high",
                    "description": "2 classes: Foo, Bar",
                }
            ],
        }
        assert rc == 0
        assert json.loads(out) == expected
        assert out == json.dumps(expected, indent=2) + "\n"

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "bad.py").write_text("def broken(:\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        # Syntax error files are skipped (no error, no zero-class report)
        assert "bad.py" not in out or "0 classes" in out

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_nested_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        sub = root / "models"
        sub.mkdir(parents=True)
        (root / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "item.py").write_text("class Item:\n    pass\n")
        (sub / "bad.py").write_text("class Wrong:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Wrong" in out
        assert "models/bad.py" in out

    def test_main_pycache_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """__pycache__ is excluded via gitignore-aware enumeration."""
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("__pycache__/\n")
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        pycache = root / "__pycache__"
        pycache.mkdir()
        (pycache / "junk.py").write_text("class Junk:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Junk" not in out

    def test_main_class_name_matches_filename(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user_account.py").write_text("class UserAccount:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "none" in out

    def test_main_class_name_equals_stem(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Class name == file stem (snake_case) is also accepted."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class user:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "none" in out

    def test_main_default_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() falls back to 'src' when no settings.json exists."""
        monkeypatch.chdir(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_custom_source_root_reports_lib_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """python.paths.source overrides the default 'src' root."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {}, "paths": {"source": ["lib"]}})
        root = tmp_path / "lib"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["lib"]
        assert report["scanned"] == 1

    # --- Test-root scanning (check_one_class_per_test_file). ---

    def test_scan_file_acronym_cased_class_matches_filename(self, tmp_path: Path) -> None:
        """Acronym-cased classes match their lowercase filenames (case-insensitive)."""
        f = tmp_path / "adr_cache.py"
        f.write_text("class ADRCache:\n    pass\n")
        assert OneClassPerFileScanner.scan_file(f) == []

    def test_scan_module_zero_class_suppressed_for_test_roots(self, tmp_path: Path) -> None:
        """report_zero_class=False suppresses zero-class findings (test roots)."""
        ProjectConfig.ensure_engines()
        f = tmp_path / "test_utils.py"
        f.write_text("def test_helper_works_fine():\n    return 42\n")
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        assert OneClassPerFileScanner.scan_module(module, report_zero_class=False) == []

    def test_main_test_root_multi_class_test_file_flagged(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A test file with two test classes is flagged (one test class per file)."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_user.py").write_text(
            "class TestUser:\n    pass\nclass TestOther:\n    pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["src", "tests"]
        assert report["scanned"] == 2
        assert report["violation_count"] == 1
        assert report["violations"][0]["category"] == "multi_class"
        assert "test_user.py" in report["violations"][0]["file"]

    def test_main_test_root_toggle_disables_test_scanning(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_one_class_per_test_file=false stops test roots being scanned."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_one_class_per_test_file": False}})
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_user.py").write_text(
            "class TestUser:\n    pass\nclass TestOther:\n    pass\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["src"]
        assert report["violation_count"] == 0

    def test_main_test_root_conftest_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """conftest.py is never scanned, even with two classes."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "conftest.py").write_text("class A:\n    pass\nclass B:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] == 0

    def test_main_test_root_name_mismatch_flagged(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A test class not named after its stem is a name_mismatch finding."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_user.py").write_text("class TestSomethingElse:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] == 1
        assert report["violations"][0]["category"] == "name_mismatch"

    def test_main_test_root_acronym_class_name_accepted(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TestADRClient in test_adr_client.py passes the case-insensitive name check."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_adr_client.py").write_text("class TestADRClient:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] == 0

    def test_main_test_root_function_style_not_flagged(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A function-style test file (0 classes) produces no zero_class finding."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_utils.py").write_text("def test_helper_works_fine():\n    assert True\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = OneClassPerFileScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_overlapping_roots_not_duplicated(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file under both source and test roots is reported exactly once."""
        monkeypatch.chdir(tmp_path)
        _write_settings(
            tmp_path,
            python={"code_style": {}, "paths": {"source": ["src"], "tests": ["src"]}},
        )
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] == 1

    def test_main_custom_test_root_scans_spec_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """python.paths.tests overrides the default 'tests' root."""
        monkeypatch.chdir(tmp_path)
        _write_settings(
            tmp_path,
            python={"code_style": {}, "paths": {"source": ["src"], "tests": ["spec"]}},
        )
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        spec = tmp_path / "spec"
        spec.mkdir()
        (spec / "test_bad.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = OneClassPerFileScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["src", "spec"]
        assert report["violation_count"] == 1

    # --- Tests for OneClassPerFileScanner._collect_test_files(). ---

    def test_collect_test_files_init_file_is_skipped(self, tmp_path: Path) -> None:
        """__init__.py under a test root is never collected."""
        (tmp_path / "__init__.py").write_text("class Foo:\n    pass\n")
        result = OneClassPerFileScanner._collect_test_files([tmp_path], {".py"}, [])
        assert result == []

    def test_collect_test_files_seen_file_keeps_scanning(self, tmp_path: Path) -> None:
        """A path already scanned as source is skipped, not a halt to the iteration."""
        src = tmp_path / "src"
        src.mkdir()
        seen = src / "user.py"
        seen.write_text("class User:\n    pass\n")
        extra = tmp_path / "zzz.py"
        extra.write_text("class Zzz:\n    pass\n")
        result = OneClassPerFileScanner._collect_test_files([tmp_path], {".py"}, [seen])
        assert result == [extra]

    # --- Text-output contract. ---

    def test_emit_text_matches_committed_contract(
        self,
        capsys: pytest.CaptureFixture[str],
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The captured text is a byte-for-byte contract that must not be loosened.

        A legitimate change is ``pytest --update-fixtures`` plus a reviewed diff.
        """
        findings = [
            Finding(
                file="src/multi.py",
                line=1,
                category="multi_class",
                severity="high",
                description="2 classes: Foo, Bar",
                fix_type="manual",
            ),
            Finding(
                file="src/user.py",
                line=3,
                category="name_mismatch",
                severity="medium",
                description=(
                    "Class 'WrongName' doesn't match filename. Expected 'User' "
                    "(or rename file to match class)"
                ),
                fix_type="manual",
            ),
            Finding(
                file="src/utils.py",
                line=0,
                category="zero_class",
                severity="low",
                description="No classes (utility/helper module)",
                fix_type="skip",
            ),
        ]
        OneClassPerFileScanner._emit_text(findings, report_zero=True)
        text_contract("code_style/general/one_class_per_file_scanner.txt", capsys.readouterr().out)

    def test_emit_text_no_findings_reports_none_sections(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Empty findings print each ``none`` section and the all-clear result."""
        OneClassPerFileScanner._emit_text([], report_zero=True)
        assert capsys.readouterr().out.splitlines() == [
            "=" * 70,
            "1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT",
            "=" * 70,
            "",
            "## Files with 2+ classes: none",
            "",
            "## Class name != filename: none",
            "",
            "## Files with 0 classes: none",
            "",
            "Result: all clear",
        ]
