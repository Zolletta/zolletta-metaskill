"""Tests for test_structure_scanner.py. — split from TestTestStructureScanner."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.testing_style.general.structs import TestStructureResults as Results
from zolletta_metaskill.testing_style.general.test_structure_scanner import TestStructureScanner


class TestTestStructureScannerCollection:
    """Tests for TestStructureScanner (collection), split from TestTestStructureScanner."""

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

    def test_without_init_fallback(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        assert TestStructureScanner._auto_detect_package(src) == "mypkg"

    def test_no_classes_skipped(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "utils.py").write_text("def helper():\n    return 1\n")
        index = TestStructureScanner._build_source_index(pkg)
        assert "utils.py" not in index

    def test_class_name_prefix(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "user_service.py").write_text("class UserService:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        info = index["user_service.py"]
        assert "test_user_service" in info["prefixes"]
        assert "test_user_service" in info["prefixes"]

    def test_abs_path_stored(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "cache.py").write_text("class Cache:\n    pass\n")
        index = TestStructureScanner._build_source_index(pkg)
        assert index["cache.py"]["abs_path"] == pkg / "cache.py"

    def test_class_based_prefix(self) -> None:
        index = {"user_service.py": {"prefixes": {"test_user_service"}, "dir": "."}}
        assert (
            TestStructureScanner._match_test_to_source("test_user_service.py", index)
            == "user_service.py"
        )

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

    def test_write_settings_replaces_non_dict_python_value(self, tmp_path: Path) -> None:
        """A non-dict ``python`` override value replaces the base value."""
        path = self._write_settings(tmp_path, python={"tools": "none"})
        written = json.loads(path.read_text())
        python = written["python"]
        assert isinstance(python, dict)
        assert python["tools"] == "none"

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
