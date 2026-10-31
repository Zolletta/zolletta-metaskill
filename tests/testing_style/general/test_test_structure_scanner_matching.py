"""Tests for test_structure_scanner.py. — split from TestTestStructureScanner."""

from __future__ import annotations

import json
import subprocess
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
        python_overrides = overrides.pop("python", {})
        assert isinstance(python_overrides, dict)
        base_python = settings["python"]
        assert isinstance(base_python, dict)
        for key, value in python_overrides.items():
            if isinstance(value, dict) and isinstance(base_python.get(key), dict):
                base_python[key].update(value)
            else:  # pragma: no cover — every caller here passes dict overrides
                base_python[key] = value
        settings.update(overrides)
        meta = dirpath / ".zolletta-metaskill"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "settings.json"
        path.write_text(json.dumps(settings))
        return path

    # --- Tests for TestStructureScanner._resolve_packages(). ---

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

    # --- Tests for TestStructureScanner._find_indirect_refs(). ---

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

    # --- Tests for TestStructureScanner._match_test_to_source(). ---

    def test_match_test_to_source_exact_match_returns_cache_py(self) -> None:
        index = {"cache.py": {"prefixes": {"test_cache"}, "dir": "."}}
        assert (
            TestStructureScanner._match_test_to_source("test_cache.py", index, test_dir=".")
            == "cache.py"
        )

    def test_match_test_to_source_suffix_match_returns_cache_py(self) -> None:
        index = {"cache.py": {"prefixes": {"test_cache"}, "dir": "."}}
        assert (
            TestStructureScanner._match_test_to_source(
                "test_cache_operations.py", index, test_dir="."
            )
            == "cache.py"
        )

    def test_match_test_to_source_no_match_returns_none(self) -> None:
        index = {"cache.py": {"prefixes": {"test_cache"}, "dir": "."}}
        assert (
            TestStructureScanner._match_test_to_source("test_unknown.py", index, test_dir=".")
            is None
        )

    def test_longest_prefix_wins(self) -> None:
        index = {
            "scenario.py": {"prefixes": {"test_scenario"}, "dir": "."},
            "scenario_writer.py": {"prefixes": {"test_scenario_writer"}, "dir": "."},
        }
        assert (
            TestStructureScanner._match_test_to_source(
                "test_scenario_writer.py", index, test_dir="."
            )
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
        assert TestStructureScanner._match_test_to_source("test_cache.py", {}, test_dir=".") is None

    def test_match_test_to_source_shorter_later_prefix_keeps_longer_match(self) -> None:
        """A shorter prefix appearing later in the index must not displace the winner."""
        index = {
            "ab/thing_one.py": {"prefixes": {"test_thing_one"}, "dir": "ab"},
            "cd/thing.py": {"prefixes": {"test_thing"}, "dir": "cd"},
        }
        result = TestStructureScanner._match_test_to_source(
            "test_thing_one.py", index, test_dir="."
        )
        assert result == "ab/thing_one.py"

    def test_match_test_to_source_second_same_dir_prefix_keeps_first(self) -> None:
        """Once a same-dir match wins, a later equal-length same-dir match must not."""
        index = {
            "b/cache.py": {"prefixes": {"test_cache"}, "dir": "b"},
            "a1/cache.py": {"prefixes": {"test_cache"}, "dir": "a"},
            "a2/cache.py": {"prefixes": {"test_cache"}, "dir": "a"},
        }
        result = TestStructureScanner._match_test_to_source("test_cache.py", index, test_dir="a")
        assert result == "a1/cache.py"

    # --- Tests for TestStructureScanner._build_source_index() edge cases. ---

    def test_build_source_index_init_with_class_returns_empty(self, tmp_path: Path) -> None:
        """``__init__.py`` is never indexed, even when it defines a class."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("class Exported:\n    pass\n")
        assert TestStructureScanner._build_source_index(pkg) == {}

    def test_build_source_index_class_prefix_differs_from_stem(self, tmp_path: Path) -> None:
        """Both the stem prefix and the class-derived prefix must be recorded."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.py").write_text("class UserService:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        assert index["mod.py"]["prefixes"] == {"test_mod", "test_user_service"}

    # --- Tests for TestStructureScanner._resolve_packages() custom roots. ---

    def test_resolve_packages_custom_source_root_resolves_pkg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path, python={"paths": {"source": ["lib"]}})
        (tmp_path / "lib" / "mypkg").mkdir(parents=True)
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        src_pkgs, _test_pkgs = TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        )
        assert src_pkgs == [Path("lib") / "mypkg"]

    def test_resolve_packages_custom_test_root_falls_back_to_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_settings(tmp_path, python={"paths": {"tests": ["specs"]}})
        self._make_src_pkg(tmp_path)
        (tmp_path / "specs").mkdir()
        monkeypatch.chdir(tmp_path)
        _src_pkgs, test_pkgs = TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        )
        assert test_pkgs == [Path("specs")]

    def test_resolve_packages_missing_source_reports_exact_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "tests").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        assert TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        ) == (None, None)
        assert capsys.readouterr().err == (
            "Error: no configured source directories exist on disk\n"
        )

    def test_resolve_packages_missing_tests_reports_exact_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self._write_settings(tmp_path)
        self._make_src_pkg(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        ) == (None, None)
        assert capsys.readouterr().err == ("Error: no configured test directories exist on disk\n")

    def test_resolve_packages_no_package_detectable_reports_exact_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self._write_settings(tmp_path, python={"paths": {"package": None}})
        (tmp_path / "src").mkdir(parents=True)
        (tmp_path / "tests").mkdir()
        monkeypatch.chdir(tmp_path)
        assert TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        ) == (None, None)
        assert capsys.readouterr().err == ("Error: could not auto-detect package under src/\n")

    def test_resolve_packages_absent_pkg_reports_exact_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "src" / "other").mkdir(parents=True)
        (tmp_path / "tests").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        assert TestStructureScanner._resolve_packages(
            ProjectConfig.load_settings(), {"python"}
        ) == (None, None)
        assert capsys.readouterr().err == (
            "Error: source package 'mypkg' does not exist under any configured source root\n"
        )

    # --- Tests for TestStructureScanner._classify_one_test(). ---

    def test_classify_one_test_prefers_same_dir_source(self, tmp_path: Path) -> None:
        """The caller-supplied test_dir decides the same-dir tiebreak."""
        index = {
            "a/cache.py": {
                "stem": "cache",
                "classes": ["Cache"],
                "prefixes": {"test_cache"},
                "dir": "a",
            },
            "b/cache.py": {
                "stem": "cache",
                "classes": ["Cache"],
                "prefixes": {"test_cache"},
                "dir": "b",
            },
        }
        result = TestStructureScanner._classify_one_test(
            "b/test_cache.py", tmp_path, "", index, {"Cache": "a/cache.py"}
        )
        assert result["covered"] == {"b/cache.py"}
        assert result["misplaced"] is None
        assert result["test_ref"]["primary_source"] == "b/cache.py"

    def test_classify_one_test_name_match_wrong_dir_reports_misplaced(self, tmp_path: Path) -> None:
        index = {
            "models/item.py": {
                "stem": "item",
                "classes": ["Item"],
                "prefixes": {"test_item"},
                "dir": "models",
            }
        }
        result = TestStructureScanner._classify_one_test(
            "test_item.py", tmp_path, "", index, {"Item": "models/item.py"}
        )
        assert result["covered"] == {"models/item.py"}
        assert result["misnamed"] is None
        assert result["orphaned"] is None
        assert result["misplaced"] == {
            "test_file": "test_item.py",
            "source_file": "models/item.py",
            "test_dir": ".",
            "expected_dir": "models",
        }
        assert result["test_ref"] == {
            "test_file": "test_item.py",
            "primary_source": "models/item.py",
            "primary_classes": {"Item"},
            "referenced_classes": [],
        }

    def test_classify_one_test_misnamed_picks_most_referenced_source(self, tmp_path: Path) -> None:
        """The primary source is the one with the most referenced classes."""
        index = {
            "z.py": {"stem": "z", "classes": ["Zeta"], "prefixes": {"test_z"}, "dir": "."},
            "a.py": {
                "stem": "a",
                "classes": ["AlphaOne", "AlphaTwo"],
                "prefixes": {"test_a"},
                "dir": ".",
            },
        }
        class_to_source = {"Zeta": "z.py", "AlphaOne": "a.py", "AlphaTwo": "a.py"}
        content = "Zeta AlphaOne AlphaTwo"
        result = TestStructureScanner._classify_one_test(
            "test_wrong.py", tmp_path, content, index, class_to_source
        )
        assert result["covered"] == {"z.py", "a.py"}
        assert result["misplaced"] is None
        assert result["orphaned"] is None
        assert result["misnamed"] == {
            "test_file": "test_wrong.py",
            "referenced_classes": "AlphaOne, AlphaTwo, Zeta",
            "expected_prefix": "test_a*.py",
            "expected_dir": ".",
        }
        assert result["test_ref"] == {
            "test_file": "test_wrong.py",
            "primary_source": "a.py",
            "primary_classes": {"AlphaOne", "AlphaTwo"},
            "referenced_classes": ["Zeta", "AlphaOne", "AlphaTwo"],
        }

    def test_classify_one_test_misnamed_wrong_dir_reports_misplaced(self, tmp_path: Path) -> None:
        index = {
            "models/item.py": {
                "stem": "item",
                "classes": ["Item"],
                "prefixes": {"test_item"},
                "dir": "models",
            }
        }
        result = TestStructureScanner._classify_one_test(
            "other/test_wrong.py", tmp_path, "Item", index, {"Item": "models/item.py"}
        )
        assert result["covered"] == {"models/item.py"}
        assert result["misnamed"] == {
            "test_file": "other/test_wrong.py",
            "referenced_classes": "Item",
            "expected_prefix": "test_item*.py",
            "expected_dir": "models",
        }
        assert result["misplaced"] == {
            "test_file": "other/test_wrong.py",
            "source_file": "models/item.py",
            "test_dir": "other",
            "expected_dir": "models",
        }
        assert result["test_ref"] == {
            "test_file": "other/test_wrong.py",
            "primary_source": "models/item.py",
            "primary_classes": {"Item"},
            "referenced_classes": ["Item"],
        }

    # --- Tests for TestStructureScanner._find_indirect_refs() exact output. ---

    def test_find_indirect_refs_multiple_sources_reports_sorted_join(self) -> None:
        test_refs = [
            {
                "test_file": "test_a.py",
                "primary_source": "a.py",
                "primary_classes": {"A"},
                "referenced_classes": ["A", "B", "C"],
            }
        ]
        refs, covered = TestStructureScanner._find_indirect_refs(
            test_refs, {"A": "a.py", "B": "b.py", "C": "c.py"}, set()
        )
        assert refs == [
            {
                "test_file": "test_a.py",
                "primary_source": "a.py",
                "indirectly_tested_sources": "b.py, c.py",
                "indirectly_tested_classes": "B, C",
            }
        ]
        assert covered == {"b.py", "c.py"}

    # --- Tests for TestStructureScanner._find_missing_tests() exact output. ---

    def test_find_missing_tests_multi_class_source_joins_classes(self) -> None:
        index = {
            "multi.py": {
                "stem": "multi",
                "classes": ["Foo", "Bar"],
                "prefixes": {"test_multi"},
                "dir": ".",
            }
        }
        assert TestStructureScanner._find_missing_tests(index, set(), set()) == [
            {
                "source_file": "multi.py",
                "classes": "Foo, Bar",
                "expected_prefix": "test_multi*.py",
                "expected_dir": ".",
            }
        ]
