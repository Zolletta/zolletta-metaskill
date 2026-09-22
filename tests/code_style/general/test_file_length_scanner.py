"""Tests for file_length_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.file_length_scanner import FileLengthScanner
from zolletta_metaskill.core.structs import Finding


def _write_lines(path: Path, n: int) -> None:
    """Write a file with exactly *n* lines."""
    path.write_text("\n".join(f"line {i}" for i in range(n)) + "\n")


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {"code_style": {}},
        "php": None,
    }
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def _git_init(root: Path) -> None:
    """Initialise a git repo at *root* so gitignore rules apply."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


class TestFileLengthScanner:
    # --- Tests for FileLengthScanner.count_lines(). ---

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

    # --- Tests for FileLengthScanner.resolve_extensions(). ---

    def test_python_language_returns_py(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="python")
        assert FileLengthScanner.resolve_extensions(settings) == {".py"}

    def test_php_language_returns_php(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="php", python=None, php={"code_style": {}})
        assert FileLengthScanner.resolve_extensions(settings) == {".php"}

    def test_polyglot_settings_scans_all_configured_languages(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="python", php={"code_style": {}})
        assert FileLengthScanner.resolve_extensions(settings) == {".py", ".php"}

    def test_missing_settings_falls_back_to_all_engines(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert FileLengthScanner.resolve_extensions(missing) == {".py", ".php"}

    def test_unknown_language_falls_back_to_all_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = _write_settings(tmp_path, language="go", python=None)
        result = FileLengthScanner.resolve_extensions(settings)
        err = capsys.readouterr().err
        assert "no engine for language 'go'" in err
        assert result == {".py", ".php"}

    def test_invalid_json_falls_back(self, tmp_path: Path) -> None:
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        bad = meta / "settings.json"
        bad.write_text("{ not json")
        assert FileLengthScanner.resolve_extensions(bad) == {".py", ".php"}

    def test_disabled_language_not_scanned(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_file_length": False}},
            php={"code_style": {}},
        )
        assert FileLengthScanner.resolve_extensions(settings) == {".php"}

    def test_all_languages_disabled_returns_empty(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_file_length": False}},
        )
        assert FileLengthScanner.resolve_extensions(settings) == set()

    # --- Tests for FileLengthScanner.resolve_max_lines(). ---

    def test_reads_max_file_length_from_settings(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python={"code_style": {"max_file_length": 500}})
        assert FileLengthScanner.resolve_max_lines(settings) == 500

    def test_smallest_limit_wins_across_languages(self, tmp_path: Path) -> None:
        settings = _write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_file_length": 800}},
            php={"code_style": {"max_file_length": 500}},
        )
        assert FileLengthScanner.resolve_max_lines(settings) == 500

    def test_no_configured_limit_falls_back_to_default(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path)  # code_style is empty
        assert FileLengthScanner.resolve_max_lines(settings) == 800

    def test_missing_settings_falls_back_to_default(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert FileLengthScanner.resolve_max_lines(missing) == 800

    def test_language_field_without_section_falls_back(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python=None)
        assert FileLengthScanner.resolve_max_lines(settings) == 800

    def test_section_without_code_style_falls_back(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python={"tools": {}})
        assert FileLengthScanner.resolve_max_lines(settings) == 800

    # --- Tests for FileLengthScanner.scan_file(). ---

    def test_file_under_limit_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "short.py"
        _write_lines(f, 10)
        assert FileLengthScanner.scan_file(f, max_lines=800) == []

    def test_file_at_limit_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "exact.py"
        _write_lines(f, 800)
        assert FileLengthScanner.scan_file(f, max_lines=800) == []

    def test_file_over_limit_returns_finding(self, tmp_path: Path) -> None:
        f = tmp_path / "long.py"
        _write_lines(f, 801)
        findings = FileLengthScanner.scan_file(f, max_lines=800)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "file_length"
        assert findings[0].severity == "medium"
        assert findings[0].fix_type == "manual"
        assert findings[0].file == str(f)

    def test_finding_line_points_past_limit(self, tmp_path: Path) -> None:
        f = tmp_path / "long.py"
        _write_lines(f, 850)
        findings = FileLengthScanner.scan_file(f, max_lines=800)
        assert findings[0].line == 801

    def test_finding_description_includes_counts(self, tmp_path: Path) -> None:
        f = tmp_path / "long.py"
        _write_lines(f, 850)
        findings = FileLengthScanner.scan_file(f, max_lines=800)
        assert "850" in findings[0].description
        assert "800" in findings[0].description

    def test_custom_max_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "mid.py"
        _write_lines(f, 50)
        assert FileLengthScanner.scan_file(f, max_lines=100) == []
        assert len(FileLengthScanner.scan_file(f, max_lines=49)) == 1

    # --- Tests for FileLengthScanner.scan_directory(). ---

    def test_scans_only_matching_extension(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "a.py", 10)
        _write_lines(root / "b.php", 10)
        _write_lines(root / "c.txt", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "a.py")

    def test_php_project_scans_php_only(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, language="php", python=None, php={"code_style": {}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "a.py", 10)
        _write_lines(root / "b.php", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, settings_path=settings)
        assert len(findings) == 1
        assert findings[0].file == str(root / "b.php")

    def test_nested_directories_scanned(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        sub = root / "pkg" / "sub"
        sub.mkdir(parents=True)
        _write_lines(sub / "deep.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1
        assert findings[0].file == str(sub / "deep.py")

    def test_gitignored_file_skipped(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "ignored.py", 10)
        _write_lines(root / "real.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "real.py")

    def test_gitignored_directory_skipped(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("vendor/\nbuild/\n")
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        _write_lines(vendor / "dep.py", 10)
        _write_lines(root / "real.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "real.py")

    def test_gitignore_wildcard_skipped(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("*_pb2.py\n")
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "big_pb2.py", 10)
        _write_lines(root / "real.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "real.py")

    def test_tracked_file_despite_gitignore_still_scanned(self, tmp_path: Path) -> None:
        """A tracked file matching .gitignore is not ignored (git semantics)."""
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("committed.py\n")
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "committed.py", 10)
        subprocess.run(["git", "add", "-f", "src/committed.py"], cwd=tmp_path, check=True)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1
        assert findings[0].file == str(root / "committed.py")

    def test_outside_git_repo_scans_everything(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        _write_lines(vendor / "dep.py", 10)
        _write_lines(root / "real.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 2

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        assert FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"}) == []

    def test_max_lines_resolved_from_settings(self, tmp_path: Path) -> None:
        settings = _write_settings(tmp_path, python={"code_style": {"max_file_length": 5}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 10)
        findings = FileLengthScanner.scan_directory(
            root, extensions={".py"}, settings_path=settings
        )
        assert len(findings) == 1

    def test_git_missing_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_git(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("git not installed")

        monkeypatch.setattr(subprocess, "run", _no_git)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 10)
        findings = FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"})
        assert len(findings) == 1

    def test_unreadable_file_warns_and_continues(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> list[Finding]:
            raise OSError("unreadable")

        monkeypatch.setattr(FileLengthScanner, "scan_file", _fail)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "a.py", 10)
        _write_lines(root / "b.py", 10)
        assert FileLengthScanner.scan_directory(root, max_lines=5, extensions={".py"}) == []
        assert "Warning: could not read" in capsys.readouterr().err

    # --- Tests for FileLengthScanner.main(). ---

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_file_length=false for every configured language → SKIPPED."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_file_length": False}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"check_file_length": False}})
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = FileLengthScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured source directory on disk → usage error."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "short.py", 10)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_violation_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"max_file_length": 10}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "long.py" in out
        assert "20" in out

    def test_main_only_scans_configured_language(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, language="python", python={"code_style": {"max_file_length": 10}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.php", 20)
        _write_lines(root / "short.py", 5)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "long.php" not in out

    def test_main_php_project(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(
            tmp_path,
            language="php",
            python=None,
            php={"code_style": {"max_file_length": 10}},
        )
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.php", 20)
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "long.php" in out
        assert "long.py" not in out

    def test_main_max_lines_from_settings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The limit comes from settings.json max_file_length."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"max_file_length": 10}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "long.py" in out
        assert "max 10" in out

    def test_main_gitignored_files_not_scanned(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _git_init(tmp_path)
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"max_file_length": 10}})
        (tmp_path / ".gitignore").write_text("vendor/\n")
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        _write_lines(vendor / "dep.py", 20)
        _write_lines(root / "real.py", 5)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "dep.py" not in out

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"max_file_length": 10}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "long.py", 20)
        _write_lines(root / "short.py", 5)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--json"],
        )
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        report = json.loads(out)
        assert report["scanned"] == 2
        assert report["max_lines"] == 10
        assert report["violation_count"] == 1
        assert report["directories"] == ["src"]
        assert report["violations"] == [{"file": "src/long.py", "lines": 20, "over": 10}]

    def test_main_json_violations_sorted_by_lines_desc(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path, python={"code_style": {"max_file_length": 10}})
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "medium.py", 20)
        _write_lines(root / "biggest.py", 50)
        _write_lines(root / "small_over.py", 12)
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "--json"],
        )
        rc = FileLengthScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert [v["file"] for v in report["violations"]] == [
            "src/biggest.py",
            "src/medium.py",
            "src/small_over.py",
        ]

    def test_main_default_max_lines_is_800(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "ok.py", 800)
        _write_lines(root / "long.py", 801)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "long.py" in out
        assert "ok.py" not in out

    def test_main_default_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() with default 'src' directory."""
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "short.py", 10)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_source_roots_from_settings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scan roots come from python.paths.source in settings.json."""
        monkeypatch.chdir(tmp_path)
        _write_settings(
            tmp_path,
            python={
                "paths": {"source": ["lib"], "tests": ["tests"], "package": "myproject"},
                "code_style": {"max_file_length": 10},
            },
        )
        lib = tmp_path / "lib"
        lib.mkdir()
        _write_lines(lib / "long.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = FileLengthScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["directories"] == ["lib"]
        assert report["violation_count"] == 1

    def test_main_unreadable_file_warns_and_continues(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file that cannot be read warns on stderr and is skipped."""

        def _fail(*_args: object, **_kwargs: object) -> int:
            raise OSError("unreadable")

        monkeypatch.setattr(FileLengthScanner, "count_lines", _fail)
        monkeypatch.chdir(tmp_path)
        _write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        _write_lines(root / "a.py", 20)
        _write_lines(root / "b.py", 20)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = FileLengthScanner.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err.count("Warning: could not read") == 2
        assert "all clear" in captured.out
