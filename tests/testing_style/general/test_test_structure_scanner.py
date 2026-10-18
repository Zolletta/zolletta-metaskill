"""Tests for test_structure_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.core.project_config import ProjectConfig

# Aliased: the struct's name starts with ``Test``, so importing it directly makes
# pytest try to collect it as a test class (PytestCollectionWarning). The mirror
# test uses the same alias.
from zolletta_metaskill.testing_style.general.structs import (
    TestStructureResults as Results,
)
from zolletta_metaskill.testing_style.general.test_structure_scanner import (
    TestStructureScanner,
)


class TestTestStructureScanner:
    # --- Tests for TestStructureScanner._resolve_packages(). ---

    @staticmethod
    def _make_src_pkg(root: Path) -> None:
        (root / "src" / "mypkg").mkdir(parents=True, exist_ok=True)
        (root / "src" / "mypkg" / "__init__.py").write_text("")

    def test_resolve_packages_accepts_flat_test_mirror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A flat ``tests/<path>/`` mirror resolves — no package level required.

        This is the layout AGENTS.md mandates (``src/<pkg>/<path>/<name>.py``
        → ``tests/<path>/test_<name>.py``) and the one
        ``structural-conventions.md`` documents. Requiring a package-named test
        directory aborted the scanner with exit 1 and zero output for two
        consecutive review runs.
        """
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        (tmp_path / "tests" / "core").mkdir(parents=True)
        (tmp_path / "tests" / "core" / "test_config.py").write_text("")
        monkeypatch.chdir(tmp_path)
        src_pkgs, test_pkgs = TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        )
        # Paths are built from the configured roots, so they stay relative.
        assert src_pkgs == [Path("src") / "mypkg"]
        assert test_pkgs == [Path("tests")]

    def test_resolve_packages_still_accepts_packaged_test_mirror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The packaged layout ``tests/<pkg>/`` keeps working unchanged."""
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        (tmp_path / "tests" / "mypkg" / "core").mkdir(parents=True)
        (tmp_path / "tests" / "mypkg" / "core" / "test_config.py").write_text("")
        monkeypatch.chdir(tmp_path)
        _, test_pkgs = TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        )
        assert test_pkgs == [Path("tests") / "mypkg"]

    def test_resolve_packages_prefers_packaged_when_both_exist(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        (tmp_path / "tests" / "mypkg").mkdir(parents=True)
        (tmp_path / "tests" / "mypkg" / "__init__.py").write_text("")
        (tmp_path / "tests" / "core").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        _, test_pkgs = TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        )
        assert test_pkgs == [Path("tests") / "mypkg"]

    def test_resolve_packages_errors_when_source_package_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "src").mkdir(parents=True)
        (tmp_path / "tests").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        assert TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        ) == (None, None)

    def test_resolve_packages_errors_when_no_test_dir_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        ) == (None, None)

    # --- Tests for TestStructureScanner._pascal_to_snake(). ---

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

    # --- Tests for TestStructureScanner._get_class_names(). ---

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

    # --- Tests for TestStructureScanner._auto_detect_package(). ---

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

    # --- Tests for TestStructureScanner._build_source_index(). ---

    def test_build_source_index_basic_input_contains_test_cache(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
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
        index = TestStructureScanner._build_source_index(pkg)
        assert "utils.py" not in index

    def test_build_source_index_gitignored_dirs_skipped(self, tmp_path: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("mypkg/assets/\n")
        pkg = tmp_path / "mypkg"
        sub = pkg / "assets"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (sub / "image.py").write_text("class Image:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        assert "assets/image.py" not in index
        assert "cache.py" in index

    def test_class_name_prefix(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        info = index["user_service.py"]
        assert "test_user_service" in info["prefixes"]
        assert "test_user_service" in info["prefixes"]  # class-based, same

    def test_build_source_index_empty_package_returns_empty_dict(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        index = TestStructureScanner._build_source_index(pkg)
        assert index == {}

    def test_build_source_index_nested_dirs_returns_models(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        sub = pkg / "models"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "item.py").write_text("class Item:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        assert "models/item.py" in index
        info = index["models/item.py"]
        assert info["dir"] == "models"

    def test_abs_path_stored(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        assert index["cache.py"]["abs_path"] == pkg / "cache.py"

    # --- Tests for TestStructureScanner._match_test_to_source(). ---

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

    # --- Tests for TestStructureScanner.main(). ---

    def _make_tree(self, root: Path) -> tuple[Path, Path]:
        """Create a ``src/mypkg`` and ``tests/`` pair and return both roots."""
        (root / "src" / "mypkg").mkdir(parents=True)
        (root / "src" / "mypkg" / "widget.py").write_text(
            "class Widget:\n    def spin(self) -> None:\n        pass\n"
        )
        (root / "tests").mkdir()
        return root / "src" / "mypkg", root / "tests"

    # --- fixture directories are not tests ---

    def test_collect_inputs_excludes_fixture_directories(self, tmp_path: Path) -> None:
        """``tests/fixtures/`` holds golden files, so it is never an orphaned test dir."""
        src_pkg, test_pkg = self._make_tree(tmp_path)
        (test_pkg / "fixtures" / "mypkg").mkdir(parents=True)
        (test_pkg / "fixtures" / "mypkg" / "sample.py").write_text("x = 1\n")

        test_only_dirs, _index, _files = TestStructureScanner._collect_inputs([src_pkg], [test_pkg])

        assert all(TestStructureScanner.FIXTURE_DIR not in d.parts for d in test_only_dirs), (
            f"fixture directory reported as orphaned: {test_only_dirs}"
        )

    def test_collect_inputs_keeps_non_fixture_test_only_dirs(self, tmp_path: Path) -> None:
        """The exclusion is scoped to ``fixtures/``; other stray dirs still report."""
        src_pkg, test_pkg = self._make_tree(tmp_path)
        (test_pkg / "helpers").mkdir()
        (test_pkg / "helpers" / "util.py").write_text("x = 1\n")

        test_only_dirs, _index, _files = TestStructureScanner._collect_inputs([src_pkg], [test_pkg])

        assert "helpers" in [str(d) for d in test_only_dirs]

    def test_collect_inputs_skips_golden_file_named_like_a_test(self, tmp_path: Path) -> None:
        """A committed golden file called ``test_*.py`` is not read as a test."""
        src_pkg, test_pkg = self._make_tree(tmp_path)
        fixture = test_pkg / "fixtures" / "mypkg" / "test_expected_output.py"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("def test_expected_output() -> None:\n    pass\n")

        _dirs, _index, test_files = TestStructureScanner._collect_inputs([src_pkg], [test_pkg])

        assert "fixtures/mypkg/test_expected_output.py" not in test_files

    def test_collect_inputs_keeps_real_tests_outside_fixtures(self, tmp_path: Path) -> None:
        """The exclusion does not swallow a real test in a normal directory."""
        src_pkg, test_pkg = self._make_tree(tmp_path)
        (test_pkg / "test_widget.py").write_text("def test_spin() -> None:\n    pass\n")

        _dirs, _index, test_files = TestStructureScanner._collect_inputs([src_pkg], [test_pkg])

        assert "test_widget.py" in test_files

    def _write_settings(self, dirpath: Path, **overrides: object) -> Path:
        """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
        settings: dict[str, object] = {
            "language": "python",
            "python": {
                "patterns": {},
                "paths": {
                    "source": ["src"],
                    "tests": ["tests"],
                    "package": "mypkg",
                },
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

    def test_write_settings_replaces_non_dict_python_value(self, tmp_path: Path) -> None:
        """A non-dict ``python`` override value replaces the base value."""
        path = self._write_settings(tmp_path, python={"tools": "none"})
        written = json.loads(path.read_text())
        python = written["python"]
        assert isinstance(python, dict)
        assert python["tools"] == "none"

    def _make_project(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a realistic src/ and tests/ structure."""
        src_pkg = tmp_path / "src" / "mypkg"
        test_pkg = tmp_path / "tests" / "mypkg"
        src_pkg.mkdir(parents=True)
        test_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").write_text("")
        (test_pkg / "__init__.py").write_text("")
        return src_pkg, test_pkg

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return TestStructureScanner.main()

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path, python={"patterns": {"check_test_structure": False}})
        self._make_project(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path, python={"patterns": {"check_test_structure": False}})
        self._make_project(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "tests" / "mypkg").mkdir(parents=True)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_missing_tests(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "src" / "mypkg").mkdir(parents=True)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured test directories" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_missing_tests_reported(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (src_pkg / "user.py").write_text("class User:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Missing tests" in out
        assert "user.py" in out

    def test_main_orphaned_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "test_orphan.py").write_text("def test_orphan():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Orphaned tests" in out
        assert "test_orphan.py" in out

    def test_main_misnamed_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file references a class but has wrong name."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_wrong_name.py").write_text(
            "from mypkg.cache import Cache\n\ndef test_cache():\n    assert Cache\n"
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Misnamed tests" in out
        assert "test_wrong_name.py" in out

    def test_main_misplaced_test(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file in wrong directory."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        src_sub = src_pkg / "models"
        src_sub.mkdir()
        (src_sub / "__init__.py").write_text("")
        (src_sub / "item.py").write_text("class Item:\n    pass\n")
        (test_pkg / "test_item.py").write_text("def test_item():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Misplaced tests" in out

    def test_main_indirect_reference(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file provides indirect coverage for a source file."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (src_pkg / "user.py").write_text("class User:\n    pass\n")
        (test_pkg / "test_cache.py").write_text(
            "from mypkg.cache import Cache\nfrom mypkg.user import User\n"
            "def test_both():\n    assert Cache and User\n"
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Indirect references" in out

    def test_main_gitignored_dirs_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("src/mypkg/assets/\n")
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        assets = src_pkg / "assets"
        assets.mkdir()
        (assets / "image.py").write_text("class Image:\n    pass\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "image.py" not in out

    def test_main_no_package_auto_detect(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No package under any source root and none configured -> error."""
        self._write_settings(tmp_path, python={"paths": {"package": None}})
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "auto-detect" in err

    def test_main_src_package_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configured package missing under every source root -> error."""
        self._write_settings(tmp_path)
        (tmp_path / "src" / "other").mkdir(parents=True)
        (tmp_path / "tests" / "mypkg").mkdir(parents=True)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_flat_test_mirror_is_accepted_not_an_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A test root with no ``mypkg/`` subdir is a valid flat mirror, not an error.

        This test previously asserted ``rc == 1`` — it encoded the bug. The
        scanner required a package-named test directory, contradicting both
        AGENTS.md and ``structural-conventions.md``, and so aborted with zero
        output for two consecutive review runs.
        """
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        (tmp_path / "tests" / "core").mkdir(parents=True)
        (tmp_path / "tests" / "core" / "test_config.py").write_text("")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Test Structure" in out

    def test_main_test_dir_absent_is_an_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured test directory on disk -> exit 1 with a clear message.

        Previously this case reported "test package 'mypkg' does not exist under
        any configured test root", which blamed the package name rather than the
        missing directory. The ``test_roots`` guard names the real cause.
        """
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured test directories exist on disk" in err

    def test_main_empty_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        self._make_project(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--json emits machine-readable results."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (src_pkg / "user.py").write_text("class User:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["has_issues"] is True
        assert len(report["missing"]) == 1
        assert report["missing"][0]["source_file"] == "user.py"
        assert report["source_packages"] == ["src/mypkg"]
        assert report["test_packages"] == ["tests/mypkg"]

    def test_main_json_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["has_issues"] is False

    def test_main_orphaned_test_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty test directory with no corresponding source dir."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "orphan_dir").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "orphan_dir" in out

    def test_main_split_tests(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple test files for one source file (split tests)."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache_operations.py").write_text("def test_x():\n    pass\n")
        (test_pkg / "test_cache_init.py").write_text("def test_y():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_class_based_test_name(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file named after class (snake_case) instead of source stem."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        (test_pkg / "test_user_service.py").write_text("def test_x():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_conftest_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """conftest.py should not be treated as a test file."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        (test_pkg / "conftest.py").write_text("def fixture():\n    return 1\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_in_source(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Source file with syntax error is skipped (no classes)."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "bad.py").write_text("def broken(:\n")
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_nested_structure_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nested src/tests structure that mirrors correctly."""
        self._write_settings(tmp_path)
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
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_misnamed_and_misplaced(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file that is both misnamed (references class) and misplaced."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        src_sub = src_pkg / "models"
        src_sub.mkdir()
        (src_sub / "__init__.py").write_text("")
        (src_sub / "item.py").write_text("class Item:\n    pass\n")
        (test_pkg / "test_wrong.py").write_text(
            "from mypkg.models.item import Item\ndef test_item():\n    assert Item\n"
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Misnamed tests" in out
        assert "Misplaced tests" in out

    def test_main_test_file_read_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file that can't be read is handled gracefully."""
        self._write_settings(tmp_path)
        src_pkg, test_pkg = self._make_project(tmp_path)
        (src_pkg / "cache.py").write_text("class Cache:\n    pass\n")
        (test_pkg / "test_cache.py").write_text("def test_cache():\n    pass\n")
        bad_test = test_pkg / "test_bad.py"
        bad_test.write_text("def test_bad():\n    pass\n")

        original_read_text = Path.read_text

        def mock_read_text(
            self: Path, encoding: str | None = None, errors: str | None = None
        ) -> str:
            if self.resolve() == bad_test.resolve():
                raise OSError("permission denied")
            return original_read_text(self, encoding=encoding, errors=errors)

        monkeypatch.setattr(Path, "read_text", mock_read_text)
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "STRUCTURAL MISMATCHES" in out or "all clear" in out

    # --- text-output contract (tests.4) ---

    def test_emit_text_matches_committed_contract(
        self, capsys: pytest.CaptureFixture[str], text_contract: Callable[[str, str], None]
    ) -> None:
        """The markdown report is a byte-for-byte contract that must not be loosened.

        The committed fixture is the full captured stdout; a legitimate change is
        ``pytest --update-fixtures`` plus a reviewed diff.
        """
        results = Results(
            misnamed=[
                {
                    "test_file": "test_wrong_name.py",
                    "referenced_classes": "Cache",
                    "expected_prefix": "test_cache*.py",
                    "expected_dir": ".",
                }
            ],
            misplaced=[
                {
                    "test_file": "test_item.py",
                    "source_file": "models/item.py",
                    "test_dir": ".",
                    "expected_dir": "models",
                }
            ],
            orphaned=[{"test_file": "test_orphan.py"}],
            orphaned_dirs=[{"test_dir": "helpers/"}],
            missing=[
                {
                    "source_file": "user.py",
                    "classes": "User",
                    "expected_prefix": "test_user*.py",
                    "expected_dir": ".",
                }
            ],
            indirect_refs=[
                {
                    "test_file": "test_cache.py",
                    "primary_source": "cache.py",
                    "indirectly_tested_sources": "user.py",
                    "indirectly_tested_classes": "User",
                }
            ],
        )
        TestStructureScanner._emit_text([Path("src/mypkg")], [Path("tests/mypkg")], results)
        text_contract("testing_style/general/test_structure_scanner.txt", capsys.readouterr().out)
