"""Tests for ``suppression_reason_scanner`` — suppress-with-reason enforcement.

Covers both language paths (Python ``# type: ignore`` via ``tokenize``, PHP
``@phpstan-ignore*`` / ``@psalm-suppress`` annotations), the missing-code /
missing-reason combinations, docblock continuation reasons, the standard
``[--json]`` CLI contract, settings-driven root/language resolution, and the
git-ignore-aware file enumeration.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.suppression_reason_scanner import (
    SuppressionReasonScanner,
)


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {"paths": {"source": ["src"]}},
        "php": None,
    }
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def _write_source(tmp_path: Path, rel: str, content: str) -> Path:
    """Write *content* to ``tmp_path/<rel>``, creating parents."""
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _main_with_argv(argv: list[str]) -> int:
    """Run ``SuppressionReasonScanner.main()`` with a mocked ``sys.argv``."""
    saved = sys.argv
    sys.argv = argv
    try:
        return SuppressionReasonScanner.main()
    finally:
        sys.argv = saved


def _run_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Chdir into *tmp_path* and run ``main()`` with *argv*."""
    monkeypatch.chdir(tmp_path)
    return _main_with_argv(["scanner", *argv])


class TestSuppressionReasonScanner:
    # --- Python type-ignore comments: codes and reasons. ---

    def test_python_coded_with_same_line_reason_is_clean(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            'x = get()  # type: ignore[no-any-return]  # plugin payload is dynamic\n',
        )
        assert SuppressionReasonScanner._scan_python(f) == []

    def test_python_coded_with_reason_on_line_above_is_clean(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            "# plugin payload is genuinely dynamic\n"
            "x = get()  # type: ignore[no-any-return]\n",
        )
        assert SuppressionReasonScanner._scan_python(f) == []

    def test_python_coded_without_reason_is_flagged(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            "x = 1\ny = get()  # type: ignore[no-any-return]\n",
        )
        violations = SuppressionReasonScanner._scan_python(f)
        assert len(violations) == 1
        assert violations[0]["line"] == 2
        assert violations[0]["suppression"] == "# type: ignore"
        assert violations[0]["missing"] == ["reason"]

    def test_python_blanket_ignore_is_flagged_for_code(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            "x = get()  # type: ignore  # genuinely dynamic\n",
        )
        violations = SuppressionReasonScanner._scan_python(f)
        assert len(violations) == 1
        assert violations[0]["missing"] == ["error code"]

    def test_python_blanket_ignore_without_reason_is_flagged_for_both(
        self, tmp_path: Path
    ) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            "x = get()  # type: ignore\n",
        )
        violations = SuppressionReasonScanner._scan_python(f)
        assert len(violations) == 1
        assert violations[0]["missing"] == ["error code", "reason"]

    def test_python_empty_code_list_is_flagged_for_code(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            "x = get()  # type: ignore[]  # why\n",
        )
        violations = SuppressionReasonScanner._scan_python(f)
        assert violations[0]["missing"] == ["error code"]

    def test_python_ignore_on_first_line_has_no_line_above(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            "x = get()  # type: ignore[no-any-return]\n",
        )
        violations = SuppressionReasonScanner._scan_python(f)
        assert violations[0]["missing"] == ["reason"]

    def test_python_ignore_in_string_literal_not_flagged(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "mod.py",
            'help_text = "# type: ignore suppresses a diagnostic"\n',
        )
        assert SuppressionReasonScanner._scan_python(f) == []

    def test_python_unparseable_file_warns_and_skips(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = _write_source(tmp_path, "mod.py", "def broken(:\n    # type: ignore\n")
        assert SuppressionReasonScanner._scan_python(f) == []
        assert "Warning" in capsys.readouterr().err

    def test_python_unreadable_file_warns_and_skips(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "ghost.py"
        assert SuppressionReasonScanner._scan_python(missing) == []
        assert "Warning" in capsys.readouterr().err

    # --- PHP: identifier slots and reasons. ---

    def test_php_phpstan_ignore_with_identifier_and_reason_is_clean(
        self, tmp_path: Path
    ) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n// @phpstan-ignore argument.type decoded JSON is dynamic\n",
        )
        assert SuppressionReasonScanner._scan_php(f) == []

    def test_php_phpstan_ignore_without_identifier_is_flagged(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n// @phpstan-ignore\n",
        )
        violations = SuppressionReasonScanner._scan_php(f)
        assert len(violations) == 1
        assert violations[0]["suppression"] == "@phpstan-ignore"
        assert violations[0]["missing"] == ["identifier", "reason"]

    def test_php_phpstan_ignore_next_line_with_reason_is_clean(
        self, tmp_path: Path
    ) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n// @phpstan-ignore-next-line decoded JSON payload\n",
        )
        assert SuppressionReasonScanner._scan_php(f) == []

    def test_php_phpstan_ignore_next_line_without_reason_is_flagged(
        self, tmp_path: Path
    ) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n/** @phpstan-ignore-next-line */\n",
        )
        violations = SuppressionReasonScanner._scan_php(f)
        assert violations[0]["missing"] == ["reason"]

    def test_php_psalm_suppress_with_type_and_reason_is_clean(
        self, tmp_path: Path
    ) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n/** @psalm-suppress MixedReturnStatement decoded JSON */\n",
        )
        assert SuppressionReasonScanner._scan_php(f) == []

    def test_php_psalm_suppress_without_type_is_flagged(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n/** @psalm-suppress */\n",
        )
        violations = SuppressionReasonScanner._scan_php(f)
        assert violations[0]["suppression"] == "@psalm-suppress"
        assert violations[0]["missing"] == ["identifier", "reason"]

    def test_php_psalm_suppress_type_only_is_flagged_for_reason(
        self, tmp_path: Path
    ) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n/** @psalm-suppress MixedReturnStatement */\n",
        )
        violations = SuppressionReasonScanner._scan_php(f)
        assert violations[0]["missing"] == ["reason"]

    def test_php_docblock_continuation_counts_as_reason(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n/**\n * @psalm-suppress MixedReturnStatement\n"
            " * decoded JSON payload — typed at the consumer boundary\n */\n",
        )
        assert SuppressionReasonScanner._scan_php(f) == []

    def test_php_docblock_empty_continuation_not_a_reason(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n/**\n * @psalm-suppress MixedReturnStatement\n *\n */\n",
        )
        violations = SuppressionReasonScanner._scan_php(f)
        assert violations[0]["missing"] == ["reason"]

    def test_php_line_comment_next_line_is_not_a_reason(self, tmp_path: Path) -> None:
        f = _write_source(
            tmp_path,
            "src/User.php",
            "<?php\n// @phpstan-ignore-next-line\n// the reason lives in a separate comment\n",
        )
        violations = SuppressionReasonScanner._scan_php(f)
        assert violations[0]["missing"] == ["reason"]

    def test_php_unreadable_file_warns_and_skips(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "ghost.php"
        assert SuppressionReasonScanner._scan_php(missing) == []
        assert "Warning" in capsys.readouterr().err

    def test_scan_file_dispatches_by_extension(self, tmp_path: Path) -> None:
        py = _write_source(tmp_path, "a.py", "x = f()  # type: ignore\n")
        php = _write_source(tmp_path, "a.php", "<?php // @psalm-suppress\n")
        assert SuppressionReasonScanner.scan_file(py)[0]["suppression"] == (
            "# type: ignore"
        )
        assert SuppressionReasonScanner.scan_file(php)[0]["suppression"] == (
            "@psalm-suppress"
        )

    # --- ``main``: SKIPPED, error, text and JSON runs. ---

    def test_main_no_supported_language_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, language="go", python=None)
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 0
        assert "SKIPPED" in capsys.readouterr().out

    def test_main_no_supported_language_json_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, language="go", python=None)
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        assert json.loads(capsys.readouterr().out)["skipped"] is True

    def test_main_no_settings_falls_back_to_all_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without settings.json every registered language is scanned."""
        _write_source(tmp_path, "src/mod.py", "x = f()  # type: ignore\n")
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        assert json.loads(capsys.readouterr().out)["violation_count"] == 1

    def test_main_missing_source_dir_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 1
        assert "no configured source directories" in capsys.readouterr().err

    def test_main_clean_tree_text_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        _write_source(tmp_path, "src/mod.py", "x = f()  # type: ignore[a]  # why\n")
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 0
        out = capsys.readouterr().out
        assert "SUPPRESSION REASON" in out
        assert "missing code/reason: none" in out
        assert "Result: all clear" in out

    def test_main_violations_text_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        _write_source(tmp_path, "src/mod.py", "x = f()  # type: ignore\n")
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 0
        out = capsys.readouterr().out
        assert "missing error code and reason" in out
        assert "Result: violations found (report-only mode)" in out

    def test_main_json_report_shape(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        _write_source(tmp_path, "src/mod.py", "x = f()  # type: ignore\n")
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["directories"] == ["src"]
        assert data["scanned"] == 1
        assert data["violation_count"] == 1
        violation = data["violations"][0]
        assert violation["file"].endswith("mod.py")
        assert violation["line"] == 1
        assert violation["suppression"] == "# type: ignore"
        assert violation["missing"] == ["error code", "reason"]
        assert "type: ignore" in violation["line_text"]

    def test_main_polyglot_scans_both_languages(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(
            tmp_path,
            php={"autoload": {"psr-4": {"App\\": "lib/"}}},
        )
        _write_source(tmp_path, "src/mod.py", "x = f()  # type: ignore\n")
        _write_source(tmp_path, "lib/User.php", "<?php // @psalm-suppress\n")
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["violation_count"] == 2
        assert {v["suppression"] for v in data["violations"]} == {
            "# type: ignore",
            "@psalm-suppress",
        }

    def test_main_gitignored_files_not_scanned(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        _write_settings(tmp_path)
        (tmp_path / ".gitignore").write_text("src/ignored/\n")
        _write_source(tmp_path, "src/ignored/mod.py", "x = f()  # type: ignore\n")
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        assert json.loads(capsys.readouterr().out)["violation_count"] == 0
