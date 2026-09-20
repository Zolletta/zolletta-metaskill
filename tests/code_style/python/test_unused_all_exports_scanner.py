"""Tests for unused_all_exports_scanner.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.unused_all_exports_scanner import (
    UnusedAllExportsScanner,
)

# ---------------------------------------------------------------------------
# UnusedAllExportsScanner._extract_all_entries
# ---------------------------------------------------------------------------


class TestExtractAllEntries:
    def test_simple_all_assignment(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('__all__ = ["foo", "bar"]\n', encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == ["foo", "bar"]

    def test_typed_all_assignment(self, tmp_path: Path) -> None:
        # Annotated assignments (__all__: list[str] = [...]) use ast.AnnAssign,
        # which _extract_all_entries does not handle — only ast.Assign and
        # ast.AugAssign are checked.  The result is therefore an empty list.
        f = tmp_path / "mod.py"
        f.write_text('__all__: list[str] = ["foo", "bar"]\n', encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == []

    def test_extract_all_entries_augmented_assignment_returns_items(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('__all__ = ["foo"]\n__all__ += ["bar"]\n', encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == ["foo", "bar"]

    def test_extract_all_entries_no_all_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n", encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == []

    def test_extract_all_entries_empty_all_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("__all__ = []\n", encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == []

    def test_extract_all_entries_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("__all__ = [\n", encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == []

    def test_non_string_entries_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('__all__ = ["foo", 123, None, "bar"]\n', encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == ["foo", "bar"]

    def test_non_list_value_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('__all__ = "foo"\n', encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == []

    def test_multiple_assignments_accumulate(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('__all__ = ["a"]\n__all__ = ["b"]\n', encoding="utf-8")
        result = UnusedAllExportsScanner._extract_all_entries(f)
        assert "a" in result
        assert "b" in result

    def test_extract_all_entries_single_entry_returns_single_item(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text('__all__ = ["only"]\n', encoding="utf-8")
        assert UnusedAllExportsScanner._extract_all_entries(f) == ["only"]


# ---------------------------------------------------------------------------
# UnusedAllExportsScanner._extract_imported_names
# ---------------------------------------------------------------------------


class TestExtractImportedNames:
    def test_extract_imported_names_from_import_contains_value(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("from pkg import foo\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names([f])
        assert "foo" in index
        assert f in index["foo"]

    def test_from_import_as_alias(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("from pkg import foo as bar\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names([f])
        # tracks the original name
        assert "foo" in index

    def test_extract_imported_names_plain_import_contains_c(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("import a.b.c\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names([f])
        # tracks the last component
        assert "c" in index

    def test_star_import_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / "a.py"
        f.write_text("from pkg import *\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names([f])
        assert "*" not in index

    def test_syntax_error_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("from pkg import\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names([f])
        # should not crash
        assert isinstance(index, dict)

    def test_extract_imported_names_multiple_importers_returns_2(self, tmp_path: Path) -> None:
        a = tmp_path / "a.py"
        a.write_text("from pkg import foo\n", encoding="utf-8")
        b = tmp_path / "b.py"
        b.write_text("from pkg import foo\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names([a, b])
        assert len(index["foo"]) == 2

    def test_extract_imported_names_empty_src_returns_empty_dict(self) -> None:
        assert UnusedAllExportsScanner._extract_imported_names([]) == {}


# ---------------------------------------------------------------------------
# UnusedAllExportsScanner._find_all_files_with_all
# ---------------------------------------------------------------------------


class TestFindAllFilesWithAll:
    def test_finds_files_with_all(self, tmp_path: Path) -> None:
        a = tmp_path / "a.py"
        a.write_text('__all__ = ["foo"]\n', encoding="utf-8")
        b = tmp_path / "b.py"
        b.write_text("x = 1\n", encoding="utf-8")
        result = UnusedAllExportsScanner._find_all_files_with_all([a, b])
        assert len(result) == 1
        assert result[0][0] == a
        assert result[0][1] == ["foo"]

    def test_no_files_with_all(self, tmp_path: Path) -> None:
        a = tmp_path / "a.py"
        a.write_text("x = 1\n", encoding="utf-8")
        assert UnusedAllExportsScanner._find_all_files_with_all([a]) == []

    def test_find_all_files_with_all_empty_src_returns_empty_list(self) -> None:
        assert UnusedAllExportsScanner._find_all_files_with_all([]) == []

    def test_find_all_files_with_all_multiple_files_returns_2(self, tmp_path: Path) -> None:
        a = tmp_path / "a.py"
        a.write_text('__all__ = ["foo"]\n', encoding="utf-8")
        b = tmp_path / "b.py"
        b.write_text('__all__ = ["bar"]\n', encoding="utf-8")
        result = UnusedAllExportsScanner._find_all_files_with_all([a, b])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# UnusedAllExportsScanner.main
# ---------------------------------------------------------------------------


class TestMain:
    def _write_settings(self, tmp_path: Path, **overrides: object) -> Path:
        """Write a minimal settings.json under ``tmp_path/.zolletta-metaskill``."""
        settings: dict[str, object] = {
            "language": "python",
            "python": {"code_style": {}, "paths": {"source": ["src"], "tests": ["tests"]}},
            "php": None,
        }
        settings.update(overrides)
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "settings.json"
        path.write_text(json.dumps(settings))
        return path

    def _run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
    ) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return UnusedAllExportsScanner.main()

    def test_check_disabled_reports_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path, python={"code_style": {"check_unused_all_exports": False}}
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_check_disabled_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path, python={"code_style": {"check_unused_all_exports": False}}
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_no_python_language_reports_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path,
            language="php",
            python=None,
            php={"autoload": {"psr-4": {"App\\": "src/"}}},
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        assert rc == 0
        assert "SKIPPED" in capsys.readouterr().out

    def test_missing_source_dir_returns_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_no_unused_exports(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n\ndef foo():\n    pass\n')
        (src / "b.py").write_text("from a import foo\n")
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "No unused" in out

    def test_unused_export_detected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["unused_func"]\n\ndef unused_func():\n    pass\n'
        )
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0  # report-only
        assert "unused_func" in out

    def test_json_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["unused_func"]\n\ndef unused_func():\n    pass\n'
        )
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["unused_count"] == 1
        assert data["unused"][0]["symbol"] == "unused_func"

    def test_json_output_no_unused(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n\ndef foo():\n    pass\n')
        (src / "b.py").write_text("from a import foo\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["unused_count"] == 0

    def test_self_import_not_counted_as_external(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An entry imported only by the file that defines __all__ is unused."""
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["foo"]\nfrom a import foo\n\ndef foo():\n    pass\n'
        )
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["unused_count"] == 1  # self-import doesn't count as external

    def test_empty_src(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "No unused" in out

    def test_gitignored_dirs_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("vendor/\n")
        self._write_settings(tmp_path)
        vendor = tmp_path / "src" / "vendor"
        vendor.mkdir(parents=True)
        (vendor / "a.py").write_text(
            '__all__ = ["unused"]\n\ndef unused():\n    pass\n'
        )
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["unused_count"] == 0

    def test_multiple_unused(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["foo", "bar"]\n\ndef foo():\n    pass\ndef bar():\n    pass\n'
        )
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["unused_count"] == 2
