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
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("from pkg import foo\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        assert "foo" in index
        assert src / "a.py" in index["foo"]

    def test_from_import_as_alias(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("from pkg import foo as bar\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        # tracks the original name
        assert "foo" in index

    def test_extract_imported_names_plain_import_contains_c(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("import a.b.c\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        # tracks the last component
        assert "c" in index

    def test_star_import_ignored(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("from pkg import *\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        assert "*" not in index

    def test_ignored_dirs_skipped(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        venv = src / ".venv"
        venv.mkdir(parents=True)
        (venv / "a.py").write_text("from pkg import foo\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, {".venv"})
        assert "foo" not in index

    def test_syntax_error_skipped(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("from pkg import\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        # should not crash
        assert isinstance(index, dict)

    def test_extract_imported_names_multiple_importers_returns_2(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("from pkg import foo\n", encoding="utf-8")
        (src / "b.py").write_text("from pkg import foo\n", encoding="utf-8")
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        assert len(index["foo"]) == 2

    def test_extract_imported_names_empty_src_returns_empty_dict(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        index = UnusedAllExportsScanner._extract_imported_names(src, set())
        assert index == {}


# ---------------------------------------------------------------------------
# UnusedAllExportsScanner._find_all_files_with_all
# ---------------------------------------------------------------------------


class TestFindAllFilesWithAll:
    def test_finds_files_with_all(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n', encoding="utf-8")
        (src / "b.py").write_text("x = 1\n", encoding="utf-8")
        result = UnusedAllExportsScanner._find_all_files_with_all(src, set())
        assert len(result) == 1
        assert result[0][0] == src / "a.py"
        assert result[0][1] == ["foo"]

    def test_no_files_with_all(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("x = 1\n", encoding="utf-8")
        assert UnusedAllExportsScanner._find_all_files_with_all(src, set()) == []

    def test_find_all_files_with_all_ignored_dirs_returns_empty_list(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        venv = src / ".venv"
        venv.mkdir(parents=True)
        (venv / "a.py").write_text('__all__ = ["foo"]\n', encoding="utf-8")
        result = UnusedAllExportsScanner._find_all_files_with_all(src, {".venv"})
        assert result == []

    def test_find_all_files_with_all_empty_src_returns_empty_list(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        assert UnusedAllExportsScanner._find_all_files_with_all(src, set()) == []

    def test_find_all_files_with_all_multiple_files_returns_2(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n', encoding="utf-8")
        (src / "b.py").write_text('__all__ = ["bar"]\n', encoding="utf-8")
        result = UnusedAllExportsScanner._find_all_files_with_all(src, set())
        assert len(result) == 2


# ---------------------------------------------------------------------------
# UnusedAllExportsScanner.main
# ---------------------------------------------------------------------------


class TestMain:
    def test_readouterr_skip_flag_contains_skipped(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "--skip"])
        assert UnusedAllExportsScanner.main() == 0
        out = capsys.readouterr().out
        assert "SKIPPED" in out

    def test_skip_flag_json(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "--skip", "--json"])
        assert UnusedAllExportsScanner.main() == 0
        assert capsys.readouterr().out == ""

    def test_readouterr_nonexistent_directory_contains_does_not_exist(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "/nonexistent/xyz"])
        assert UnusedAllExportsScanner.main() == 1
        err = capsys.readouterr().err
        assert "does not exist" in err

    def test_no_unused_exports(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n\ndef foo():\n    pass\n', encoding="utf-8")
        (src / "b.py").write_text("from a import foo\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src)])
        assert UnusedAllExportsScanner.main() == 0
        out = capsys.readouterr().out
        assert "No unused" in out

    def test_unused_export_detected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["unused_func"]\n\ndef unused_func():\n    pass\n', encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["scan", str(src)])
        assert UnusedAllExportsScanner.main() == 0  # no --strict
        out = capsys.readouterr().out
        assert "unused_func" in out

    def test_strict_returns_one_on_unused(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["unused_func"]\n\ndef unused_func():\n    pass\n', encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--strict"])
        assert UnusedAllExportsScanner.main() == 1

    def test_strict_returns_zero_when_all_used(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n\ndef foo():\n    pass\n', encoding="utf-8")
        (src / "b.py").write_text("from a import foo\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--strict"])
        assert UnusedAllExportsScanner.main() == 0

    def test_loads_json_output_returns_unused_func(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["unused_func"]\n\ndef unused_func():\n    pass\n', encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--json"])
        assert UnusedAllExportsScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["unused_count"] == 1
        assert data["unused"][0]["symbol"] == "unused_func"

    def test_json_output_no_unused(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text('__all__ = ["foo"]\n\ndef foo():\n    pass\n', encoding="utf-8")
        (src / "b.py").write_text("from a import foo\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--json"])
        assert UnusedAllExportsScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["unused_count"] == 0

    def test_self_import_not_counted_as_external(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An entry imported only by the file that defines __all__ is unused."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["foo"]\nfrom a import foo\n\ndef foo():\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--strict"])
        assert UnusedAllExportsScanner.main() == 1  # self-import doesn't count as external

    def test_readouterr_empty_src_contains_no_unused(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        monkeypatch.setattr(sys, "argv", ["scan", str(src)])
        assert UnusedAllExportsScanner.main() == 0
        out = capsys.readouterr().out
        assert "No unused" in out

    def test_module_ignored_dirs_returns_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        venv = src / ".venv"
        venv.mkdir(parents=True)
        (venv / "a.py").write_text(
            '__all__ = ["unused"]\n\ndef unused():\n    pass\n', encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--strict"])
        assert UnusedAllExportsScanner.main() == 0  # .venv is ignored

    def test_loads_multiple_unused_returns_2(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            '__all__ = ["foo", "bar"]\n\ndef foo():\n    pass\ndef bar():\n    pass\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--json"])
        assert UnusedAllExportsScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["unused_count"] == 2
