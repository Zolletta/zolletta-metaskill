"""Tests for test_structure_scanner.py. — split from TestTestStructureScanner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.testing_style.general.test_structure_scanner import TestStructureScanner


class TestTestStructureScannerMain:
    """Tests for TestStructureScanner (main), split from TestTestStructureScanner."""

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
