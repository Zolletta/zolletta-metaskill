"""Tests for scan_naming_conventions.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.shared.scan_naming_conventions import (
    _auto_detect_package,
    _build_source_index,
    _get_class_names,
    _matches_prefix,
    _pascal_to_snake,
    _snake_to_pascal,
    main,
)


class TestSnakeToPascal:
    """Tests for _snake_to_pascal()."""

    def test_simple(self) -> None:
        assert _snake_to_pascal("my_class") == "MyClass"

    def test_single_word(self) -> None:
        assert _snake_to_pascal("cache") == "Cache"

    def test_empty(self) -> None:
        assert _snake_to_pascal("") == ""

    def test_multiple_words(self) -> None:
        assert _snake_to_pascal("my_awesome_class") == "MyAwesomeClass"


class TestPascalToSnake:
    """Tests for _pascal_to_snake()."""

    def test_simple(self) -> None:
        assert _pascal_to_snake("MyClass") == "my_class"

    def test_single_word(self) -> None:
        assert _pascal_to_snake("Cache") == "cache"

    def test_empty(self) -> None:
        assert _pascal_to_snake("") == ""

    def test_multiple_words(self) -> None:
        assert _pascal_to_snake("MyAwesomeClass") == "my_awesome_class"

    def test_all_lower(self) -> None:
        assert _pascal_to_snake("myclass") == "myclass"

    def test_all_upper(self) -> None:
        assert _pascal_to_snake("ABC") == "a_b_c"


class TestGetClassNames:
    """Tests for _get_class_names()."""

    def test_single_class(self, tmp_path: Path) -> None:
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        assert _get_class_names(f) == ["User"]

    def test_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        assert _get_class_names(f) == ["Foo", "Bar"]

    def test_no_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 1\n")
        assert _get_class_names(f) == []

    def test_syntax_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        assert _get_class_names(f) == []

    def test_nested_class(self, tmp_path: Path) -> None:
        """Only top-level classes are returned (engine does not walk into nested)."""
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        names = _get_class_names(f)
        assert "Outer" in names
        # Inner is nested inside Outer — the engine only extracts top-level classes
        assert "Inner" not in names


class TestAutoDetectPackage:
    """Tests for _auto_detect_package()."""

    def test_with_init(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        assert _auto_detect_package(src) == "mypkg"

    def test_without_init_fallback(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        assert _auto_detect_package(src) == "mypkg"

    def test_picks_first_with_init(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        (src / "aaa").mkdir(parents=True)
        (src / "bbb").mkdir(parents=True)
        (src / "bbb" / "__init__.py").write_text("")
        assert _auto_detect_package(src) == "bbb"

    def test_no_dirs(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        assert _auto_detect_package(src) is None

    def test_files_only(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.py").write_text("")
        assert _auto_detect_package(src) is None


class TestBuildSourceIndex:
    """Tests for _build_source_index()."""

    def test_basic(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = _build_source_index(pkg, set())
        assert Path(".") in index
        prefixes = index[Path(".")]
        assert "test_cache" in prefixes
        assert "test_cache" in prefixes  # class-name based too (same)

    def test_class_name_prefix(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        index = _build_source_index(pkg, set())
        prefixes = index[Path(".")]
        assert "test_user_service" in prefixes
        assert "test_user_service" in prefixes  # stem-based

    def test_ignore_dirs(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        sub = pkg / "assets"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (sub / "image.py").write_text("class Image:\n    pass\n")
        index = _build_source_index(pkg, {"assets"})
        assert Path("assets") not in index
        assert Path(".") in index

    def test_empty_package(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        index = _build_source_index(pkg, set())
        assert index == {}

    def test_nested_dirs(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        sub = pkg / "models"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "item.py").write_text("class Item:\n    pass\n")
        index = _build_source_index(pkg, set())
        assert Path("models") in index
        assert "test_item" in index[Path("models")]


class TestMatchesPrefix:
    """Tests for _matches_prefix()."""

    def test_exact_match(self) -> None:
        result = _matches_prefix("cache", {"test_cache"})
        assert result == "test_cache"

    def test_suffix_match(self) -> None:
        result = _matches_prefix("cache_operations", {"test_cache"})
        assert result == "test_cache"

    def test_no_match(self) -> None:
        result = _matches_prefix("unknown", {"test_cache"})
        assert result is None

    def test_longest_match(self) -> None:
        result = _matches_prefix("scenario_writer", {"test_scenario", "test_scenario_writer"})
        assert result == "test_scenario_writer"

    def test_empty_prefixes(self) -> None:
        result = _matches_prefix("cache", set())
        assert result is None

    def test_multiple_matches_returns_longest(self) -> None:
        result = _matches_prefix("cache_init", {"test_cache", "test_cache_init"})
        assert result == "test_cache_init"


class TestMain:
    """Tests for main()."""

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

    def test_main_skip(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                       monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--skip"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_missing_src(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "nosrc"),
                                          "--tests", str(tests)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_missing_tests(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src"
        src.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src),
                                          "--tests", str(tmp_path / "notests")])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_all_clear(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                            monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_name_mismatch_report_only(self, tmp_path: Path,
                                            capsys: pytest.CaptureFixture[str],
                                            monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class WrongName:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "WrongName" in out

    def test_main_name_mismatch_strict(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                       monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class WrongName:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests"), "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "VIOLATIONS FOUND" in out

    def test_main_orphan_test(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_orphan.py" in out
        assert "naming convention" in out

    def test_main_orphan_test_strict(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests"), "--strict"])
        rc = main()
        assert rc == 1

    def test_main_test_with_suffix(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                   monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache_operations.py").write_text("def test_x():\n    pass\n")
        (test_pkg / "test_cache_init.py").write_text("def test_y():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_class_name_based_prefix(self, tmp_path: Path,
                                          capsys: pytest.CaptureFixture[str],
                                          monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        (test_pkg / "test_user_service.py").write_text("def test_x():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_ignore_dirs(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        assets = src_pkg / "assets"
        assets.mkdir()
        (assets / "image.py").write_text("class Image:\n    pass\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests"),
                                          "--ignore-dirs", "assets"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Image" not in out

    def test_main_no_package_auto_detect(self, tmp_path: Path,
                                         capsys: pytest.CaptureFixture[str],
                                         monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (tests / "test_x.py").write_text("def test_x():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src), "--tests", str(tests)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "auto-detect" in err

    def test_main_src_package_not_exist(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                        monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "other").mkdir()
        (tests / "other").mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src), "--tests", str(tests),
                                          "--src-package", "nonexistent"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_test_package_not_exist(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                         monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "mypkg").mkdir()
        (src / "mypkg" / "__init__.py").write_text("")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src), "--tests", str(tests),
                                          "--tests-package", "nonexistent"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_empty_dirs(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                             monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_explicit_packages(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                    monkeypatch: pytest.MonkeyPatch) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src_pkg = src / "mypkg"
        test_pkg = tests / "otherpkg"
        src_pkg.mkdir(parents=True)
        test_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").write_text("")
        (test_pkg / "__init__.py").write_text("")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src), "--tests", str(tests),
                                          "--src-package", "mypkg", "--tests-package", "otherpkg"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_test_no_source_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        """Test file in a subdirectory with no corresponding source dir."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        test_sub = test_pkg / "subdir"
        test_sub.mkdir()
        (test_sub / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "no source directory" in out

    def test_main_syntax_error_in_source(self, tmp_path: Path,
                                         capsys: pytest.CaptureFixture[str],
                                         monkeypatch: pytest.MonkeyPatch) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "bad.py").write_text("def broken(:\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        # Syntax error files yield no classes, so they're skipped in name check
        assert rc == 0

    def test_main_multi_class_source_skipped(self, tmp_path: Path,
                                             capsys: pytest.CaptureFixture[str],
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        """Files with 2+ classes are skipped in name check."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        (test_pkg / "test_multi.py").write_text("def test_multi():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_conftest_skipped(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                   monkeypatch: pytest.MonkeyPatch) -> None:
        """conftest.py in tests should not be flagged as orphan."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "conftest.py").write_text("def fixture():\n    return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_test_conftest_file_skipped(self, tmp_path: Path,
                                             capsys: pytest.CaptureFixture[str],
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        """test_conftest.py is not flagged as orphan (common non-SUT test file)."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "test_conftest.py").write_text("def test_conftest():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_conftest.py" not in out

    def test_main_ignore_dirs_on_test_files(self, tmp_path: Path,
                                            capsys: pytest.CaptureFixture[str],
                                            monkeypatch: pytest.MonkeyPatch) -> None:
        """Test files in ignored dirs are not flagged."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        test_assets = test_pkg / "assets"
        test_assets.mkdir()
        (test_assets / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(tmp_path / "src"),
                                          "--tests", str(tmp_path / "tests"),
                                          "--ignore-dirs", "assets"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "test_orphan.py" not in out
