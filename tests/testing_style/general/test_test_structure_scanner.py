"""Tests for test_structure_scanner.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.testing_style.general.test_structure_scanner import (
    TestStructureScanner,
)


class TestPascalToSnake:
    """Tests for TestStructureScanner._pascal_to_snake()."""

    def test_pascal_to_snake_simple_input_returns_my_class(self) -> None:
        assert TestStructureScanner._pascal_to_snake("MyClass") == "my_class"

    def test_pascal_to_snake_single_word_returns_cache(self) -> None:
        assert TestStructureScanner._pascal_to_snake("Cache") == "cache"

    def test_pascal_to_snake_empty_input_returns_empty(self) -> None:
        assert TestStructureScanner._pascal_to_snake("") == ""

    def test_pascal_to_snake_multiple_words_returns_my_awesome_class(self) -> None:
        assert TestStructureScanner._pascal_to_snake("MyAwesomeClass") == "my_awesome_class"

    def test_pascal_to_snake_all_lower_returns_myclass(self) -> None:
        assert TestStructureScanner._pascal_to_snake("myclass") == "myclass"

    def test_pascal_to_snake_all_upper_returns_a_b_c(self) -> None:
        assert TestStructureScanner._pascal_to_snake("ABC") == "a_b_c"


class TestGetClassNames:
    """Tests for TestStructureScanner._get_class_names()."""

    def test_get_class_names_single_class_returns_single_item(self, tmp_path: Path) -> None:
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        assert TestStructureScanner._get_class_names(f) == ["User"]

    def test_get_class_names_multiple_classes_returns_multiple_items(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        assert TestStructureScanner._get_class_names(f) == ["Foo", "Bar"]

    def test_get_class_names_no_classes_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 1\n")
        assert TestStructureScanner._get_class_names(f) == []

    def test_get_class_names_syntax_error_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        assert TestStructureScanner._get_class_names(f) == []

    def test_get_class_names_nested_class_excludes_value(self, tmp_path: Path) -> None:
        """Only top-level classes are returned (engine does not walk into nested)."""
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        names = TestStructureScanner._get_class_names(f)
        assert "Outer" in names
        # Inner is nested inside Outer — the engine only extracts top-level classes
        assert "Inner" not in names


class TestAutoDetectPackage:
    """Tests for TestStructureScanner._auto_detect_package()."""

    def test_auto_detect_package_with_init_returns_mypkg(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        assert TestStructureScanner._auto_detect_package(src) == "mypkg"

    def test_without_init_fallback(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        assert TestStructureScanner._auto_detect_package(src) == "mypkg"

    def test_auto_detect_package_no_dirs_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        assert TestStructureScanner._auto_detect_package(src) is None

    def test_auto_detect_package_files_only_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.py").write_text("")
        assert TestStructureScanner._auto_detect_package(src) is None


class TestBuildSourceIndex:
    """Tests for TestStructureScanner._build_source_index()."""

    def test_build_source_index_basic_input_contains_test_cache(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg, set())
        assert "cache.py" in index
        info = index["cache.py"]
        assert info["stem"] == "cache"
        assert info["classes"] == ["Cache"]
        assert "test_cache" in info["prefixes"]

    def test_no_classes_skipped(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "utils.py").write_text("def helper():\n    return 1\n")
        index = TestStructureScanner._build_source_index(pkg, set())
        assert "utils.py" not in index

    def test_build_source_index_ignore_dirs_contains_cache_py(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        sub = pkg / "assets"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (sub / "image.py").write_text("class Image:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg, {"assets"})
        assert "assets/image.py" not in index
        assert "cache.py" in index

    def test_class_name_prefix(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg, set())
        info = index["user_service.py"]
        assert "test_user_service" in info["prefixes"]
        assert "test_user_service" in info["prefixes"]  # class-based, same

    def test_build_source_index_empty_package_returns_empty_dict(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        index = TestStructureScanner._build_source_index(pkg, set())
        assert index == {}

    def test_build_source_index_nested_dirs_returns_models(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        sub = pkg / "models"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "item.py").write_text("class Item:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg, set())
        assert "models/item.py" in index
        info = index["models/item.py"]
        assert info["dir"] == "models"

    def test_abs_path_stored(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg, set())
        assert index["cache.py"]["abs_path"] == pkg / "cache.py"


class TestMatchTestToSource:
    """Tests for TestStructureScanner._match_test_to_source()."""

    def test_match_test_to_source_exact_match_returns_cache_py(self) -> None:
        index = {"cache.py": {"prefixes": {"test_cache"}, "dir": "."}}
        assert TestStructureScanner._match_test_to_source("test_cache.py", index) == "cache.py"

    def test_match_test_to_source_suffix_match_returns_cache_py(self) -> None:
        index = {"cache.py": {"prefixes": {"test_cache"}, "dir": "."}}
        assert (
            TestStructureScanner._match_test_to_source("test_cache_operations.py", index)
            == "cache.py"
        )

    def test_match_test_to_source_no_match_returns_none(self) -> None:
        index = {"cache.py": {"prefixes": {"test_cache"}, "dir": "."}}
        assert TestStructureScanner._match_test_to_source("test_unknown.py", index) is None

    def test_longest_prefix_wins(self) -> None:
        index = {
            "scenario.py": {"prefixes": {"test_scenario"}, "dir": "."},
            "scenario_writer.py": {"prefixes": {"test_scenario_writer"}, "dir": "."},
        }
        assert (
            TestStructureScanner._match_test_to_source("test_scenario_writer.py", index)
            == "scenario_writer.py"
        )

    def test_same_dir_preference(self) -> None:
        """Two source files with same-length prefix, prefer same dir."""
        index = {
            "a/cache.py": {"prefixes": {"test_cache"}, "dir": "a"},
            "b/cache.py": {"prefixes": {"test_cache"}, "dir": "b"},
        }
        result = TestStructureScanner._match_test_to_source("test_cache.py", index, test_dir="b")
        assert result == "b/cache.py"

    def test_match_test_to_source_empty_index_returns_none(self) -> None:
        assert TestStructureScanner._match_test_to_source("test_cache.py", {}) is None

    def test_class_based_prefix(self) -> None:
        index = {"user_service.py": {"prefixes": {"test_user_service"}, "dir": "."}}
        assert (
            TestStructureScanner._match_test_to_source("test_user_service.py", index)
            == "user_service.py"
        )


class TestMain:
    """Tests for TestStructureScanner.main()."""

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

    def test_readouterr_main_skip_contains_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--skip"])
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        monkeypatch.setattr(
            sys, "argv", ["prog", "--src", str(tmp_path / "nosrc"), "--tests", str(tests)]
        )
        rc = TestStructureScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_missing_tests(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        monkeypatch.setattr(
            sys, "argv", ["prog", "--src", str(src), "--tests", str(tmp_path / "notests")]
        )
        rc = TestStructureScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_missing_tests_reported(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (src_pkg / "user.py").write_text("class User:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "Missing tests" in out
        assert "user.py" in out

    def test_main_orphaned_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "Orphaned tests" in out
        assert "test_orphan.py" in out

    def test_main_misnamed_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file references a class but has wrong name."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_wrong_name.py").write_text(
            "from mypkg.cache import Cache\n\ndef test_cache():\n    assert Cache\n"
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "Misnamed tests" in out
        assert "test_wrong_name.py" in out

    def test_main_misplaced_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file in wrong directory."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        src_sub = src_pkg / "models"
        src_sub.mkdir()
        (src_sub / "__init__.py").write_text("")
        (src_sub / "item.py").write_text("class Item:\n    pass\n")
        # test_item.py is in root test_pkg, not in models/
        (test_pkg / "test_item.py").write_text("def test_item():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "Misplaced tests" in out

    def test_main_indirect_reference(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file provides indirect coverage for a source file."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (src_pkg / "user.py").write_text("class User:\n    pass\n")
        # test_cache.py references both Cache and User
        (test_pkg / "test_cache.py").write_text(
            "from mypkg.cache import Cache\nfrom mypkg.user import User\n"
            "def test_both():\n    assert Cache and User\n"
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        TestStructureScanner.main()
        out = capsys.readouterr().out
        # User is indirectly covered, so not in missing
        assert "Indirect references" in out

    def test_main_ignore_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        assets = src_pkg / "assets"
        assets.mkdir()
        (assets / "image.py").write_text("class Image:\n    pass\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--src",
                str(tmp_path / "src"),
                "--tests",
                str(tmp_path / "tests"),
                "--ignore-dirs",
                "assets",
            ],
        )
        TestStructureScanner.main()
        out = capsys.readouterr().out
        assert "image.py" not in out

    def test_main_no_package_auto_detect(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src), "--tests", str(tests)])
        rc = TestStructureScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "auto-detect" in err

    def test_main_src_package_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "other").mkdir()
        (tests / "other").mkdir()
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(src), "--tests", str(tests), "--src-package", "nonexistent"],
        )
        rc = TestStructureScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_test_package_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "mypkg").mkdir()
        (src / "mypkg" / "__init__.py").write_text("")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(src), "--tests", str(tests), "--tests-package", "nonexistent"],
        )
        rc = TestStructureScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_empty_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_explicit_packages(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--src",
                str(src),
                "--tests",
                str(tests),
                "--src-package",
                "mypkg",
                "--tests-package",
                "otherpkg",
            ],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_orphaned_test_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test directory with no corresponding source dir."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        orphan_dir = test_pkg / "orphan_dir"
        orphan_dir.mkdir()
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "orphan_dir" in out

    def test_main_split_tests(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple test files for one source file (split tests)."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache_operations.py").write_text("def test_x():\n    pass\n")
        (test_pkg / "test_cache_init.py").write_text("def test_y():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_class_based_test_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file named after class (snake_case) instead of source stem."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        (test_pkg / "test_user_service.py").write_text("def test_x():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_conftest_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """conftest.py should not be treated as a test file."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "conftest.py").write_text("def fixture():\n    return 1\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_in_source(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Source file with syntax error is skipped (no classes)."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "bad.py").write_text("def broken(:\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_nested_structure_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nested src/tests structure that mirrors correctly."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        src_sub = src_pkg / "models"
        test_sub = test_pkg / "models"
        src_sub.mkdir()
        test_sub.mkdir()
        (src_sub / "__init__.py").write_text("")
        (test_sub / "__init__.py").write_text("")
        (src_sub / "item.py").write_text("class Item:\n    pass\n")
        (test_sub / "test_item.py").write_text("def test_item():\n    pass\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_pycache_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        test_pycache = test_pkg / "__pycache__"
        test_pycache.mkdir()
        (test_pycache / "test_junk.py").write_text("def test_junk():\n    pass\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        TestStructureScanner.main()
        out = capsys.readouterr().out
        assert "__pycache__" not in out or "junk" not in out

    def test_main_misnamed_and_misplaced(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file that is both misnamed (references class) and misplaced."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        src_sub = src_pkg / "models"
        src_sub.mkdir()
        (src_sub / "__init__.py").write_text("")
        (src_sub / "item.py").write_text("class Item:\n    pass\n")
        # test_wrong.py in root references Item class but is in wrong dir
        (test_pkg / "test_wrong.py").write_text(
            "from mypkg.models.item import Item\ndef test_item():\n    assert Item\n"
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        rc = TestStructureScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "Misnamed tests" in out
        assert "Misplaced tests" in out

    def test_main_test_file_read_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file that can't be read is handled gracefully."""
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        # Create a test file then make it unreadable by mocking read_text
        bad_test = test_pkg / "test_bad.py"
        bad_test.write_text("def test_bad():\n    pass\n")

        original_read_text = Path.read_text

        def mock_read_text(
            self: Path, encoding: str | None = None, errors: str | None = None
        ) -> str:
            if self == bad_test:
                raise OSError("permission denied")
            return original_read_text(self, encoding=encoding, errors=errors)

        monkeypatch.setattr(Path, "read_text", mock_read_text)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--src", str(tmp_path / "src"), "--tests", str(tmp_path / "tests")],
        )
        TestStructureScanner.main()
        out = capsys.readouterr().out
        # Should not crash; test_bad.py content becomes ""
        assert "STRUCTURAL MISMATCHES" in out or "all clear" in out
