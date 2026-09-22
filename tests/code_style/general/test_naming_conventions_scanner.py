"""Tests for naming_conventions_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.naming_conventions_scanner import (
    NamingConventionsScanner,
)


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {
            "code_style": {},
            "paths": {"source": ["src"], "tests": ["tests"], "package": "mypkg"},
        },
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


class TestSnakeToPascal:
    """Tests for NamingConventionsScanner._snake_to_pascal()."""

    def test_snake_to_pascal_simple_input_returns_myclass(self) -> None:
        assert NamingConventionsScanner._snake_to_pascal("my_class") == "MyClass"

    def test_snake_to_pascal_single_word_returns_cache(self) -> None:
        assert NamingConventionsScanner._snake_to_pascal("cache") == "Cache"

    def test_snake_to_pascal_empty_input_returns_empty(self) -> None:
        assert NamingConventionsScanner._snake_to_pascal("") == ""

    def test_snake_to_pascal_multiple_words_returns_myawesomeclass(self) -> None:
        assert NamingConventionsScanner._snake_to_pascal("my_awesome_class") == "MyAwesomeClass"


class TestPascalToSnake:
    """Tests for NamingConventionsScanner._pascal_to_snake()."""

    def test_pascal_to_snake_simple_input_returns_my_class(self) -> None:
        assert NamingConventionsScanner._pascal_to_snake("MyClass") == "my_class"

    def test_pascal_to_snake_single_word_returns_cache(self) -> None:
        assert NamingConventionsScanner._pascal_to_snake("Cache") == "cache"

    def test_pascal_to_snake_empty_input_returns_empty(self) -> None:
        assert NamingConventionsScanner._pascal_to_snake("") == ""

    def test_pascal_to_snake_multiple_words_returns_my_awesome_class(self) -> None:
        assert NamingConventionsScanner._pascal_to_snake("MyAwesomeClass") == "my_awesome_class"

    def test_pascal_to_snake_all_lower_returns_myclass(self) -> None:
        assert NamingConventionsScanner._pascal_to_snake("myclass") == "myclass"

    def test_pascal_to_snake_all_upper_returns_a_b_c(self) -> None:
        assert NamingConventionsScanner._pascal_to_snake("ABC") == "a_b_c"


class TestGetClassNames:
    """Tests for NamingConventionsScanner._get_class_names()."""

    def test_get_class_names_single_class_returns_single_item(self, tmp_path: Path) -> None:
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        assert NamingConventionsScanner._get_class_names(f) == ["User"]

    def test_get_class_names_multiple_classes_returns_multiple_items(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        assert NamingConventionsScanner._get_class_names(f) == ["Foo", "Bar"]

    def test_get_class_names_no_classes_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 1\n")
        assert NamingConventionsScanner._get_class_names(f) == []

    def test_get_class_names_syntax_error_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        assert NamingConventionsScanner._get_class_names(f) == []

    def test_get_class_names_nested_class_excludes_value(self, tmp_path: Path) -> None:
        """Only top-level classes are returned (engine does not walk into nested)."""
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        names = NamingConventionsScanner._get_class_names(f)
        assert "Outer" in names
        # Inner is nested inside Outer — the engine only extracts top-level classes
        assert "Inner" not in names


class TestAutoDetectPackage:
    """Tests for NamingConventionsScanner._auto_detect_package()."""

    def test_auto_detect_package_with_init_returns_mypkg(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        assert NamingConventionsScanner._auto_detect_package(src) == "mypkg"

    def test_without_init_fallback(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        assert NamingConventionsScanner._auto_detect_package(src) == "mypkg"

    def test_picks_first_with_init(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        (src / "aaa").mkdir(parents=True)
        (src / "bbb").mkdir(parents=True)
        (src / "bbb" / "__init__.py").write_text("")
        assert NamingConventionsScanner._auto_detect_package(src) == "bbb"

    def test_auto_detect_package_no_dirs_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        assert NamingConventionsScanner._auto_detect_package(src) is None

    def test_auto_detect_package_files_only_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.py").write_text("")
        assert NamingConventionsScanner._auto_detect_package(src) is None


class TestBuildSourceIndex:
    """Tests for NamingConventionsScanner._build_source_index()."""

    def test_build_source_index_basic_input_contains_test_cache(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = NamingConventionsScanner._build_source_index(pkg)
        assert Path(".") in index
        prefixes = index[Path(".")]
        assert "test_cache" in prefixes
        assert "test_cache" in prefixes  # class-name based too (same)

    def test_class_name_prefix(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        index = NamingConventionsScanner._build_source_index(pkg)
        prefixes = index[Path(".")]
        assert "test_user_service" in prefixes
        assert "test_user_service" in prefixes  # stem-based

    def test_build_source_index_gitignored_dir_contains_value(self, tmp_path: Path) -> None:
        """Git-ignored directories are excluded from the index."""
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("assets/\n")
        pkg = tmp_path / "mypkg"
        sub = pkg / "assets"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (sub / "image.py").write_text("class Image:\n    pass\n")
        index = NamingConventionsScanner._build_source_index(pkg)
        assert Path("assets") not in index
        assert Path(".") in index

    def test_build_source_index_empty_package_returns_empty_dict(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        index = NamingConventionsScanner._build_source_index(pkg)
        assert index == {}

    def test_build_source_index_nested_dirs_contains_test_item(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        sub = pkg / "models"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "item.py").write_text("class Item:\n    pass\n")
        index = NamingConventionsScanner._build_source_index(pkg)
        assert Path("models") in index
        assert "test_item" in index[Path("models")]


class TestMatchesPrefix:
    """Tests for NamingConventionsScanner._matches_prefix()."""

    def test_matches_prefix_exact_match_returns_test_cache(self) -> None:
        result = NamingConventionsScanner._matches_prefix("cache", {"test_cache"})
        assert result == "test_cache"

    def test_matches_prefix_suffix_match_returns_test_cache(self) -> None:
        result = NamingConventionsScanner._matches_prefix("cache_operations", {"test_cache"})
        assert result == "test_cache"

    def test_matches_prefix_no_match_returns_none(self) -> None:
        result = NamingConventionsScanner._matches_prefix("unknown", {"test_cache"})
        assert result is None

    def test_matches_prefix_longest_match_returns_test_scenario_writer(self) -> None:
        result = NamingConventionsScanner._matches_prefix(
            "scenario_writer", {"test_scenario", "test_scenario_writer"}
        )
        assert result == "test_scenario_writer"

    def test_matches_prefix_empty_prefixes_returns_none(self) -> None:
        result = NamingConventionsScanner._matches_prefix("cache", set())
        assert result is None

    def test_multiple_matches_returns_longest(self) -> None:
        result = NamingConventionsScanner._matches_prefix(
            "cache_init", {"test_cache", "test_cache_init"}
        )
        assert result == "test_cache_init"


class TestMain:
    """Tests for NamingConventionsScanner.main()."""

    def _make_project(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a realistic src/ and tests/ structure."""
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src_pkg = src / "mypkg"
        test_pkg = tests / "mypkg"
        src_pkg.mkdir(parents=True)
        test_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").write_text("")
        (test_pkg / "__init__.py").write_text("")
        return src_pkg, test_pkg

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return NamingConventionsScanner.main()

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_filename_matches_class=false for every configured language → SKIPPED."""
        _write_settings(tmp_path, python={"code_style": {"check_filename_matches_class": False}})
        self._make_project(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"check_filename_matches_class": False}})
        self._make_project(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        (tmp_path / "tests").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_missing_tests(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured test directories" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_name_mismatch_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class WrongName:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "WrongName" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class WrongName:\n    pass\n")
        (test_pkg / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["package"] == "mypkg"
        assert report["directories"]["source"] == ["src"]
        assert report["violation_count"] == 2
        assert report["name_mismatch"][0]["class"] == "WrongName"
        assert report["orphan_tests"][0]["file"] == "test_orphan.py"

    def test_main_orphan_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_orphan.py" in out
        assert "naming convention" in out

    def test_main_test_with_suffix(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache_operations.py").write_text("def test_x():\n    pass\n")
        (test_pkg / "test_cache_init.py").write_text("def test_y():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_class_name_based_prefix(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        (test_pkg / "test_user_service.py").write_text("def test_x():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_gitignored_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Git-ignored dirs are excluded from source scanning and test checks."""
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("assets/\n")
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        assets = src_pkg / "assets"
        assets.mkdir()
        (assets / "image.py").write_text("class Image:\n    pass\n")
        test_assets = test_pkg / "assets"
        test_assets.mkdir()
        (test_assets / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Image" not in out
        assert "test_orphan.py" not in out

    def test_main_no_package_auto_detect(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(
            tmp_path,
            python={
                "code_style": {},
                "paths": {"source": ["src"], "tests": ["tests"], "package": None},
            },
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "auto-detect" in err

    def test_main_src_package_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(
            tmp_path,
            python={
                "code_style": {},
                "paths": {"source": ["src"], "tests": ["tests"], "package": "nonexistent"},
            },
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_test_package_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        (src / "mypkg").mkdir(parents=True)
        tests.mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_empty_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        self._make_project(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_package_from_settings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """python.paths.package drives the mirror base for src and tests."""
        _write_settings(
            tmp_path,
            python={
                "code_style": {},
                "paths": {"source": ["src"], "tests": ["tests"], "package": "otherpkg"},
            },
        )
        src_pkg = tmp_path / "src" / "otherpkg"
        test_pkg = tmp_path / "tests" / "otherpkg"
        src_pkg.mkdir(parents=True)
        test_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").write_text("")
        (test_pkg / "__init__.py").write_text("")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_test_no_source_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file in a subdirectory with no corresponding source dir."""
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        test_sub = test_pkg / "subdir"
        test_sub.mkdir()
        (test_sub / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "no source directory" in out

    def test_main_syntax_error_in_source(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "bad.py").write_text("def broken(:\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        # Syntax error files yield no classes, so they're skipped in name check
        assert rc == 0

    def test_main_multi_class_source_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Files with 2+ classes are skipped in name check."""
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        (test_pkg / "test_multi.py").write_text("def test_multi():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_conftest_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """conftest.py in tests should not be flagged as orphan."""
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "conftest.py").write_text("def fixture():\n    return 1\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_test_conftest_file_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """test_conftest.py is not flagged as orphan (common non-SUT test file)."""
        _write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "test_conftest.py").write_text("def test_conftest():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_conftest.py" not in out
