"""Tests for file_length_scanner.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.file_length_scanner import FileLengthScanner
from zolletta_metaskill.core.structs import Finding


def _write_lines(path: Path, n: int) -> None:
    """Write a file with exactly *n* lines."""
    path.write_text("\n".join(f"line {i}" for i in range(n)) + "\n")


class TestCountLines:
    """Tests for FileLengthScanner.count_lines()."""

    def test_empty_file_returns_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        assert FileLengthScanner.count_lines(f) == 0

    def test_single_line_with_newline_returns_one(self, tmp_path: Path) -> None:
        f = tmp_path / "one.py"
        f.write_text("x = 1\n")
        assert FileLengthScanner.count_lines(f) == 1

    def test_single_line_without_newline_returns_one(self, tmp_path: Path) -> None:
        f = tmp_path / "one.py"
        f.write_text("x = 1")
        assert FileLengthScanner.count_lines(f) == 1

    def test_multiple_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        _write_lines(f, 10)
        assert FileLengthScanner.count_lines(f) == 10

    def test_trailing_newline_does_not_add_phantom_line(self, tmp_path: Path) -> None:
        f = tmp_path / "trailing.py"
        f.write_text("a\nb\nc\n")
        assert FileLengthScanner.count_lines(f) == 3

    def test_no_trailing_newline_counts_last_line(self, tmp_path: Path) -> None:
        f = tmp_path / "notrail.py"
        f.write_text("a\nb\nc")
        assert FileLengthScanner.count_lines(f) == 3

    def test_only_newlines(self, tmp_path: Path) -> None:
        f = tmp_path / "blank.py"
        f.write_text("\n\n\n")
        assert FileLengthScanner.count_lines(f) == 3

    def test_non_utf8_bytes_do_not_fail(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.py"
        f.write_bytes(b"\xff\xfe\n\x00\x01\n")
        assert FileLengthScanner.count_lines(f) == 2


class TestParseExtensions:
    """Tests for FileLengthScanner._parse_extensions()."""

    def test_single_extension_with_dot(self) -> None:
        assert FileLengthScanner._parse_extensions(".py") == {".py"}

    def test_single_extension_without_dot(self) -> None:
        assert FileLengthScanner._parse_extensions("php") == {".php"}

    def test_multiple_extensions(self) -> None:
        assert FileLengthScanner._parse_extensions(".py,.php") == {".py", ".php"}

    def test_empty_input_defaults_to_py(self) -> None:
        assert FileLengthScanner._parse_extensions("") == {".py"}

    def test_whitespace_and_case_normalized(self) -> None:
        assert FileLengthScanner._parse_extensions(" PY , .PHP ") == {".py", ".php"}


class TestScanFile:
    """Tests for FileLengthScanner.scan_file()."""

    def test_file_under_limit_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "short.py"
        _write_lines(f, 10)
        assert FileLengthScanner.scan_file(f, max_lines=300) == []

    def test_file_at_limit_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "exact.py"
        _write_lines(f, 300)
        assert FileLengthScanner.scan_file(f, max_lines=300) == []

    def test_file_over_limit_returns_finding(self, tmp_path: Path) -> None:
        f = tmp_path / "long.py"
        _write_lines(f, 301)
        findings = FileLengthScanner.scan_file(f, max_lines=300)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "file_length"
        assert findings[0].severity == "medium"
        assert findings[0].fix_type == "manual"
        assert findings[0].file == str(f)

    def test_finding_line_points_past_limit(self, tmp_path: Path) -> None:
        f = tmp_path / "long.py"
        _write_lines(f, 350)
        findings = FileLengthScanner.scan_file(f, max_lines=300)
        assert findings[0].line == 301

    def test_finding_description_includes_counts(self, tmp_path: Path) -> None:
        f = tmp_path / "long.py"
        _write_lines(f, 350)
        findings = FileLengthScanner.scan_file(f, max_lines=300)
        assert "350" in findings[0].description
        assert "300" in findings[0].description

    def test_custom_max_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "mid.py"
        _write_lines(f, 50)
        assert FileLengthScanner.scan_file(f, max_lines=100) == []
        assert len(FileLengthScanner.scan_file(f, max_lines=49)) == 1


class TestScanDirectory:
    """Tests for FileLengthScanner.scan_directory()."""

    def test_scans_only_matching_extension_by_default(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 10)
        _write_lines(root / "long.php", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5)
        assert len(findings) == 1
        assert findings[0].file == str(root / "long.py")

    def test_scans_php_when_extension_given(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.php", 10)
        _write_lines(root / "long.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".php"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "long.php")

    def test_scans_multiple_extensions(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "a.py", 10)
        _write_lines(root / "b.php", 10)
        _write_lines(root / "c.txt", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py", ".php"})
        assert len(findings) == 2

    def test_nested_directories_scanned(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        sub = root / "pkg" / "sub"
        sub.mkdir(parents=True)
        _write_lines(sub / "deep.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5)
        assert len(findings) == 1
        assert findings[0].file == str(sub / "deep.py")

    def test_pycache_always_ignored(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        cache = root / "__pycache__"
        cache.mkdir(parents=True)
        _write_lines(cache / "junk.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5)
        assert findings == []

    def test_ignore_dirs_skips_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        gen = root / "generated"
        gen.mkdir(parents=True)
        _write_lines(gen / "gen.py", 10)
        _write_lines(root / "real.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, ignore_dirs={"generated"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "real.py")

    def test_vendor_always_ignored(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        _write_lines(vendor / "dep.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5)
        assert findings == []

    def test_exclude_pattern_skips_file(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "big_pb2.py", 10)
        _write_lines(root / "real.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, exclude=["*_pb2.py"])
        assert len(findings) == 1
        assert findings[0].file == str(root / "real.py")

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        assert FileLengthScanner.scan_directory(root, max_lines=5) == []


class TestMain:
    """Tests for FileLengthScanner.main()."""

    def test_main_skip_contains_skipped(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--skip"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(missing)])
        rc = FileLengthScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "short.py", 10)
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_violation_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--max-lines", "10"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "long.py" in out
        assert "20" in out

    def test_main_violation_strict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--max-lines", "10", "--strict"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "VIOLATIONS FOUND" in out

    def test_main_default_max_lines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "ok.py", 300)
        _write_lines(root / "long.py", 301)
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "long.py" in out
        assert "ok.py" not in out

    def test_main_extensions_php(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.php", 20)
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", str(root), "--max-lines", "10", "--extensions", ".php"],
        )
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "long.php" in out
        assert "long.py" not in out

    def test_main_exclude_pattern(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "big_pb2.py", 20)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", str(root), "--max-lines", "10", "--exclude", "*_pb2.py"],
        )
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "big_pb2.py" not in out

    def test_main_ignore_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        gen = root / "generated"
        gen.mkdir(parents=True)
        _write_lines(gen / "gen.py", 20)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", str(root), "--max-lines", "10", "--ignore-dirs", "generated"],
        )
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        _write_lines(root / "short.py", 5)
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--max-lines", "10", "--json"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        report = json.loads(out)
        assert report["scanned"] == 2
        assert report["max_lines"] == 10
        assert report["violation_count"] == 1
        assert report["violations"] == [{"file": "long.py", "lines": 20, "over": 10}]

    def test_main_json_violations_sorted_by_lines_desc(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "medium.py", 20)
        _write_lines(root / "biggest.py", 50)
        _write_lines(root / "small_over.py", 12)
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--max-lines", "10", "--json"])
        rc = FileLengthScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert [v["file"] for v in report["violations"]] == [
            "biggest.py",
            "medium.py",
            "small_over.py",
        ]

    def test_main_default_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() with default 'src' directory."""
        monkeypatch.chdir(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "short.py", 10)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
