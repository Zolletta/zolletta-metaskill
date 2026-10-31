"""Tests for the PHP ``acronym_casing_scanner``.

Covers ``_split_pascal_case``, ``_get_class_names``, ``_load_default_acronyms``,
``_load_acronyms_from_settings``, and ``main`` — including ``--skip``,
``--json``, ``--strict``, and the no-acronyms case.

Tests that require ``tree-sitter-php`` are skipped when the optional
dependency is not installed.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.php.acronym_casing_scanner import (
    AcronymCasingScanner,
)
from zolletta_metaskill.core.engine.php_engine import PHPEngine

TS_PHP_AVAILABLE = PHPEngine._have_tree_sitter_php()


_skip_no_ts = pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")


def _write_php(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestAcronymCasingScanner:
    # --- AcronymCasingScanner._load_default_acronyms ---

    def test_returns_non_empty_list(self) -> None:
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert isinstance(acronyms, list)
        assert len(acronyms) > 0
        assert all(isinstance(a, str) for a in acronyms)
        assert all(a == a.upper() for a in acronyms)

    def test_contains_common_acronyms(self) -> None:
        acronyms = AcronymCasingScanner._load_default_acronyms()
        for expected in ("API", "HTTP", "JSON", "URL", "SQL"):
            assert expected in acronyms

    def test_fallback_minimal_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no assets file is found, the fallback list is returned."""
        monkeypatch.setattr(Path, "exists", lambda self: False)
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms
        assert "CI" in acronyms
        assert "HTTP" in acronyms

    def test_load_default_acronyms_installed_layout_returns_exact_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The installed-package candidate is ``<scanner_dir>/assets/acronyms.json``."""
        module_file = sys.modules[AcronymCasingScanner.__module__].__file__
        assert module_file is not None
        installed = Path(module_file).resolve().parent / "assets" / "acronyms.json"
        monkeypatch.setattr(Path, "exists", lambda self: self == installed)
        monkeypatch.setattr(
            Path, "read_text", lambda self, encoding="utf-8": '{"acronyms": ["zzq", "API", 5]}'
        )
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert acronyms == ["ZZQ", "API"]

    def test_load_default_acronyms_repo_layout_uses_exact_shipped_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The checkout-layout candidate is probed at its exact path.

        Comparing the probed path — not just the result — also pins down the
        ``parents[3]`` index and each path segment's casing, which a
        filesystem-level comparison cannot see on a case-insensitive volume.
        """
        module_file = sys.modules[AcronymCasingScanner.__module__].__file__
        assert module_file is not None
        shipped = (
            Path(module_file).resolve().parent.parents[3]
            / "skills"
            / "zolletta-metaskill-python-code-style"
            / "assets"
            / "acronyms.json"
        )
        monkeypatch.setattr(Path, "exists", lambda self: self == shipped)
        monkeypatch.setattr(
            Path, "read_text", lambda self, encoding="utf-8": '{"acronyms": ["zzq"]}'
        )
        assert AcronymCasingScanner._load_default_acronyms() == ["ZZQ"]

    # --- AcronymCasingScanner._split_pascal_case ---

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("APIGateway", ["API", "Gateway"]),
            ("HTTPClientFactory", ["HTTP", "Client", "Factory"]),
            ("HttpClientFactory", ["Http", "Client", "Factory"]),
            ("MyDIProvider", ["My", "DI", "Provider"]),
            ("MRBranchResolver", ["MR", "Branch", "Resolver"]),
            ("SimpleClass", ["Simple", "Class"]),
            ("Class", ["Class"]),
            ("HTML", ["HTML"]),
            ("HTTP2", ["HTTP", "2"]),
            ("V2Client", ["V", "2", "Client"]),
            ("MyClass2", ["My", "Class", "2"]),
        ],
        ids=[
            "acronym_prefix_returns_acronym_then_words",
            "two_acronyms_returns_both",
            "mixed_case_returns_mixed",
            "mid_acronym_returns_parts",
            "mr_acronym_returns_parts",
            "two_words_returns_both",
            "single_word_returns_single",
            "acronym_only_returns_single",
            "acronym_digit_returns_split",
            "leading_digit_splits_digit",
            "trailing_digit_splits_digit",
        ],
    )
    def test_split_pascal_case_known_splits_returns_expected(
        self, name: str, expected: list[str]
    ) -> None:
        assert AcronymCasingScanner._split_pascal_case(name) == expected

    def test_split_pascal_case_with_empty_string_returns_empty_list(self) -> None:
        assert AcronymCasingScanner._split_pascal_case("") == []

    def test_single_word_lowercase(self) -> None:
        assert AcronymCasingScanner._split_pascal_case("word") == ["word"]

    def test_single_word_uppercase(self) -> None:
        assert AcronymCasingScanner._split_pascal_case("API") == ["API"]

    def test_all_uppercase_acronym(self) -> None:
        assert AcronymCasingScanner._split_pascal_case("HTTP") == ["HTTP"]

    def test_mixed_with_digits(self) -> None:
        assert AcronymCasingScanner._split_pascal_case("S3Bucket") == ["S", "3", "Bucket"]

    def test_consecutive_uppercase_then_lower(self) -> None:
        # HTTPSClient -> HTTPS | Client
        assert AcronymCasingScanner._split_pascal_case("HTTPSClient") == ["HTTPS", "Client"]

    # --- GetClassNames ---

    @_skip_no_ts
    def test_returns_class_names_with_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "Mod.php"
        _write_php(
            f,
            "<?php\nclass Foo {\n}\n\nclass Bar {\n}\n",
        )
        result = AcronymCasingScanner._get_class_names(f)
        assert ("Foo", 2) in result
        assert ("Bar", 5) in result

    @_skip_no_ts
    def test_includes_interfaces_and_traits(self, tmp_path: Path) -> None:
        f = tmp_path / "Mod.php"
        _write_php(
            f,
            "<?php\ninterface Foo {\n}\n\ntrait Bar {\n}\n",
        )
        result = AcronymCasingScanner._get_class_names(f)
        names = [name for name, _ in result]
        assert "Foo" in names
        assert "Bar" in names

    @_skip_no_ts
    def test_get_class_names_with_no_classes_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "Mod.php"
        _write_php(f, "<?php\n$x = 1;\n")
        assert AcronymCasingScanner._get_class_names(f) == []

    @_skip_no_ts
    def test_get_class_names_with_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.php"
        _write_php(f, "")
        assert AcronymCasingScanner._get_class_names(f) == []

    @_skip_no_ts
    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.php"
        _write_php(f, "<?php\nclass {\n")
        assert AcronymCasingScanner._get_class_names(f) == []

    # --- AcronymCasingScanner._check_skipped_tree_sitter ---

    @staticmethod
    def _patch_no_tree_sitter(monkeypatch: pytest.MonkeyPatch) -> None:
        """Pretend tree-sitter-php is not installed."""
        monkeypatch.setattr(
            "zolletta_metaskill.core.engine.php_engine.PHPEngine._have_tree_sitter_php",
            lambda: False,
        )

    def test_check_skipped_tree_sitter_json_mode_returns_exact_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._patch_no_tree_sitter(monkeypatch)
        assert AcronymCasingScanner._check_skipped_tree_sitter(json_mode=True) is True
        expected = (
            json.dumps(
                {
                    "total_classes": 0,
                    "violation_count": 0,
                    "acronyms_checked": [],
                    "violations": [],
                    "skipped": "tree-sitter-php not installed",
                },
                indent=2,
            )
            + "\n"
        )
        assert capsys.readouterr().out == expected

    def test_check_skipped_tree_sitter_text_mode_returns_exact_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._patch_no_tree_sitter(monkeypatch)
        assert AcronymCasingScanner._check_skipped_tree_sitter(json_mode=False) is True
        expected = (
            "=" * 70
            + "\nPHP ACRONYM CASING — VALIDATION REPORT\n"
            + "=" * 70
            + "\n\nResult: SKIPPED (tree-sitter-php not installed. "
            "Install with: uv add tree-sitter tree-sitter-php)\n\n"
        )
        assert capsys.readouterr().out == expected

    # --- AcronymCasingScanner._scan_classes ---

    @_skip_no_ts
    def test_scan_classes_two_files_returns_total_two(self, tmp_path: Path) -> None:
        _write_php(tmp_path / "a" / "One.php", "<?php\nclass Foo {}\n")
        _write_php(tmp_path / "b" / "Two.php", "<?php\nclass Bar {}\n")
        total, violations = AcronymCasingScanner._scan_classes([tmp_path / "a", tmp_path / "b"], {})
        assert total == 2
        assert violations == []

    @_skip_no_ts
    def test_scan_classes_violation_reports_relative_path(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        _write_php(root / "Mod.php", "<?php\nclass ApiGateway {}\n")
        total, violations = AcronymCasingScanner._scan_classes([root], {"api": "API"})
        assert total == 1
        assert violations == [
            {
                "file": "Mod.php",
                "line": 2,
                "class": "ApiGateway",
                "word": "Api",
                "expected": "API",
            }
        ]

    # --- AcronymCasingScanner._emit_json ---

    def test_emit_json_output_matches_exact_document(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        violations = [
            {
                "file": "Mod.php",
                "line": 2,
                "class": "ApiGateway",
                "word": "Api",
                "expected": "API",
            }
        ]
        AcronymCasingScanner._emit_json(1, violations, ["API"], [Path("src")])
        expected = (
            json.dumps(
                {
                    "total_classes": 1,
                    "violation_count": 1,
                    "acronyms_checked": ["API"],
                    "directories": ["src"],
                    "violations": violations,
                },
                indent=2,
            )
            + "\n"
        )
        assert capsys.readouterr().out == expected

    # --- AcronymCasingScanner._emit_text ---

    def test_emit_text_two_roots_joined_by_comma_space(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        AcronymCasingScanner._emit_text(0, [], ["API"], [Path("src"), Path("lib")])
        lines = capsys.readouterr().out.splitlines()
        assert "Source directories: src, lib" in lines

    def test_emit_text_no_violations_returns_exact_clean_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        AcronymCasingScanner._emit_text(1, [], ["API"], [Path("src")])
        expected = (
            "=" * 70
            + "\nPHP ACRONYM CASING — VALIDATION REPORT\n"
            + "=" * 70
            + "\n\nSource directories: src\n"
            "Acronyms checked: API\n"
            "Total classes scanned: 1\n"
            "Violations: 0\n"
            "\n"
            "All class names use acronyms in the correct uppercase form.\n\n"
        )
        assert capsys.readouterr().out == expected

    # --- AcronymCasingScanner._load_acronyms_from_settings ---

    def test_empty_settings_returns_empty(self) -> None:
        assert AcronymCasingScanner._project_acronyms({}) == []

    def test_no_acronyms_key_returns_empty(self) -> None:
        assert AcronymCasingScanner._project_acronyms({"other": 1}) == []

    def test_empty_list_returns_empty(self) -> None:
        assert AcronymCasingScanner._project_acronyms({"acronyms": []}) == []

    def test_returns_uppercased_acronyms(self) -> None:
        result = AcronymCasingScanner._project_acronyms({"acronyms": ["abc", "XYZ"]})
        assert "ABC" in result
        assert "XYZ" in result

    def test_not_a_list_returns_empty(self) -> None:
        assert AcronymCasingScanner._project_acronyms({"acronyms": "not a list"}) == []

    def test_filters_non_string_entries(self) -> None:
        result = AcronymCasingScanner._project_acronyms({"acronyms": ["API", 123]})
        assert result == ["API"]

    # --- AcronymCasingScanner.main ---

    def _write_settings(self, tmp_path: Path, **overrides: object) -> Path:
        """Write a minimal PHP settings.json under ``tmp_path/.zolletta-metaskill``."""
        settings: dict[str, object] = {
            "language": "php",
            "python": None,
            "php": {"autoload": {"psr-4": {"App\\": "src/"}}, "code_style": {}},
        }
        settings.update(overrides)
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "settings.json"
        path.write_text(json.dumps(settings))
        return path

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return AcronymCasingScanner.main()

    @_skip_no_ts
    def test_check_disabled_reports_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path,
            php={
                "autoload": {"psr-4": {"App\\": "src/"}},
                "code_style": {"check_acronym_casing": False},
            },
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert (
            "Result: SKIPPED (check_acronym_casing disabled in settings.json)" in out.splitlines()
        )

    @_skip_no_ts
    def test_check_disabled_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path,
            php={
                "autoload": {"psr-4": {"App\\": "src/"}},
                "code_style": {"check_acronym_casing": False},
            },
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report == {
            "skipped": True,
            "reason": "check_acronym_casing disabled in settings.json",
        }

    @_skip_no_ts
    def test_no_php_language_reports_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Python-only project: the PHP scanner has nothing to scan."""
        self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {}, "paths": {"source": ["src"], "tests": ["tests"]}},
            php=None,
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    @_skip_no_ts
    def test_missing_source_dir_returns_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path,
            php={"autoload": {"psr-4": {"App\\": ["src/", "lib/"]}}, "code_style": {}},
        )
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        err = capsys.readouterr().err
        assert rc == 1
        assert err == "Error: no configured source directories exist on disk (src, lib)\n"

    @_skip_no_ts
    def test_non_default_source_root_scanned_returns_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A configured psr-4 root other than ``src/`` must be used verbatim."""
        self._write_settings(
            tmp_path,
            php={"autoload": {"psr-4": {"App\\": "lib/"}}, "code_style": {}},
        )
        _write_php(tmp_path / "lib" / "Mod.php", "<?php\nclass ApiGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["total_classes"] == 1
        assert data["violation_count"] == 1

    @_skip_no_ts
    def test_scan_clean_class_reports_zero_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass Foo {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Total classes scanned: 1" in out.splitlines()
        assert "Violations: 0" in out.splitlines()

    @_skip_no_ts
    def test_violation_report_only(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass ApiGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0  # report-only
        assert "ApiGateway" in out
        assert "API" in out

    @_skip_no_ts
    def test_scan_json_flag_outputs_violation_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass ApiGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["total_classes"] == 1
        assert data["directories"] == ["src"]
        assert data["violation_count"] == 1
        assert data["violations"] == [
            {
                "file": "Mod.php",
                "line": 2,
                "class": "ApiGateway",
                "word": "Api",
                "expected": "API",
            }
        ]

    @_skip_no_ts
    def test_correct_casing_not_flagged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass APIGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 0

    @_skip_no_ts
    def test_gitignored_dirs_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("vendor/\n")
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "vendor" / "Mod.php", "<?php\nclass ApiGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 0

    @_skip_no_ts
    def test_settings_acronyms_merged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path, acronyms=["XYZ"])
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass XyzHelper {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1
        assert "XYZ" in data["acronyms_checked"]

    @_skip_no_ts
    def test_no_settings_uses_default_src(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Without settings.json, falls back to src/ for all registered languages."""
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass ApiGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1

    @_skip_no_ts
    def test_multiple_violations_in_one_class(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass ApiHttpGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 2

    @_skip_no_ts
    def test_main_with_interface_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Interfaces are also checked for acronym casing."""
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\ninterface ApiRepository {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1
        assert data["violations"][0]["class"] == "ApiRepository"

    # --- Coverage: _load_default_acronyms error handling (lines 112-118) ---

    @staticmethod
    def _patch_acronyms_file(
        monkeypatch: pytest.MonkeyPatch,
        content: str | Exception,
    ) -> None:
        """Monkeypatch Path so paths with 'acronyms.json' exist and return *content*.

        If *content* is an Exception, read_text raises it instead.
        """

        def fake_exists(self: Path) -> bool:
            return "acronyms.json" in str(self)

        if isinstance(content, Exception):

            def fake_read_text(self: Path, encoding: str = "utf-8") -> str:
                raise content
        else:

            def fake_read_text(self: Path, encoding: str = "utf-8") -> str:
                return content

        monkeypatch.setattr(Path, "exists", fake_exists)
        monkeypatch.setattr(Path, "read_text", fake_read_text)

    def test_corrupt_json_file_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When the assets file exists but contains invalid JSON, the fallback list is used."""
        self._patch_acronyms_file(monkeypatch, "{ invalid json")
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms
        assert "CI" in acronyms

    def test_empty_acronyms_list_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When the assets file has an empty acronyms list, the fallback is used."""
        self._patch_acronyms_file(monkeypatch, '{"acronyms": []}')
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms

    def test_non_list_acronyms_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When the acronyms value is not a list, the fallback is used."""
        self._patch_acronyms_file(monkeypatch, '{"acronyms": "not-a-list"}')
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms

    def test_oserror_reading_file_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When reading the file raises OSError, the fallback is used."""
        self._patch_acronyms_file(monkeypatch, OSError("permission denied"))
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms

    def test_valid_json_with_non_string_entries_filters_them(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the acronyms list contains non-string entries, they are filtered out."""
        self._patch_acronyms_file(monkeypatch, '{"acronyms": ["API", 42, "HTTP", null]}')
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms
        assert "HTTP" in acronyms
        assert all(isinstance(a, str) for a in acronyms)

    # --- Coverage: _get_class_names when tree-sitter-php not installed (line 188) ---

    def test_returns_empty_when_tree_sitter_not_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When tree-sitter-php is not installed, _get_class_names returns []."""
        f = tmp_path / "Mod.php"
        _write_php(f, "<?php\nclass Foo {}\n")
        monkeypatch.setattr(
            "zolletta_metaskill.core.engine.php_engine.PHPEngine._have_tree_sitter_php",
            lambda: False,
        )
        assert AcronymCasingScanner._get_class_names(f) == []

    # --- Coverage: main() when tree-sitter-php not installed (lines 249-270) ---

    def test_no_tree_sitter_text_output(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When tree-sitter-php is not installed, main() prints a skip message."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass Foo {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.engine.php_engine.PHPEngine._have_tree_sitter_php",
            lambda: False,
        )
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        assert "SKIPPED" in out
        assert "tree-sitter-php not installed" in out

    def test_no_tree_sitter_json_output(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When tree-sitter-php is not installed and --json, main() prints JSON skip."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass Foo {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", "--json"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.engine.php_engine.PHPEngine._have_tree_sitter_php",
            lambda: False,
        )
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 0
        assert data["skipped"] == "tree-sitter-php not installed"

    # --- text-output contract (tests.4) ---

    def test_emit_text_matches_committed_contract(
        self, capsys: pytest.CaptureFixture[str], text_contract: Callable[[str, str], None]
    ) -> None:
        """The text report is a byte-for-byte contract that must not be loosened.

        The committed fixture is the full captured stdout; a legitimate change is
        ``pytest --update-fixtures`` plus a reviewed diff.
        """
        violations = [
            {
                "file": "src/ApiGateway.php",
                "line": 12,
                "class": "ApiGateway",
                "word": "Api",
                "expected": "API",
            },
            {
                "file": "src/HttpClientFactory.php",
                "line": 3,
                "class": "HttpClientFactory",
                "word": "Http",
                "expected": "HTTP",
            },
        ]
        AcronymCasingScanner._emit_text(4, violations, ["API", "HTTP", "JSON"], [Path("src")])
        text_contract("code_style/php/acronym_casing_scanner.txt", capsys.readouterr().out)
