"""Tests for test_structure_scanner.py. — split from TestTestStructureScanner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.testing_style.general.test_structure_scanner import TestStructureScanner


class TestTestStructureScannerMatching:
    """Tests for TestStructureScanner (matching), split from TestTestStructureScanner."""

    @staticmethod
    def _make_src_pkg(root: Path) -> None:
        (root / "src" / "mypkg").mkdir(parents=True, exist_ok=True)
        (root / "src" / "mypkg" / "__init__.py").write_text("")

    def _make_tree(self, root: Path) -> tuple[Path, Path]:
        """Create a ``src/mypkg`` and ``tests/`` pair and return both roots."""
        (root / "src" / "mypkg").mkdir(parents=True)
        (root / "src" / "mypkg" / "widget.py").write_text(
            "class Widget:\n    def spin(self) -> None:\n        pass\n"
        )
        (root / "tests").mkdir()
        return (root / "src" / "mypkg", root / "tests")

    def _write_settings(self, dirpath: Path, **overrides: object) -> Path:
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

    def _make_project(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a realistic src/ and tests/ structure."""
        src_pkg = tmp_path / "src" / "mypkg"
        test_pkg = tmp_path / "tests" / "mypkg"
        src_pkg.mkdir(parents=True)
        test_pkg.mkdir(parents=True)
        (src_pkg / "__init__.py").write_text("")
        (test_pkg / "__init__.py").write_text("")
        return (src_pkg, test_pkg)

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return TestStructureScanner.main()

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
        assert "Inner" not in names

    def test_auto_detect_package_with_init_returns_mypkg(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
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

    def test_find_indirect_refs_skips_directly_covered_source(self) -> None:
        test_refs = [
            {
                "test_file": "test_a.py",
                "primary_source": "a.py",
                "primary_classes": {"A"},
                "referenced_classes": ["A", "B"],
            }
        ]
        refs, covered = TestStructureScanner._find_indirect_refs(
            test_refs, {"A": "a.py", "B": "b.py"}, {"b.py"}
        )
        assert refs == []
        assert covered == set()

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

    def test_same_dir_winner_not_replaced_by_other_dir(self) -> None:
        """An equal-length prefix in a different dir must not displace the same-dir match."""
        index = {
            "a/cache.py": {"prefixes": {"test_cache"}, "dir": "a"},
            "b/cache.py": {"prefixes": {"test_cache"}, "dir": "b"},
        }
        result = TestStructureScanner._match_test_to_source("test_cache.py", index, test_dir="a")
        assert result == "a/cache.py"

    def test_match_test_to_source_empty_index_returns_none(self) -> None:
        assert TestStructureScanner._match_test_to_source("test_cache.py", {}) is None
