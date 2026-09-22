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


# ---------------------------------------------------------------------------
# AcronymCasingScanner._load_default_acronyms
# ---------------------------------------------------------------------------


class TestLoadDefaultAcronyms:
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


# ---------------------------------------------------------------------------
# AcronymCasingScanner._split_pascal_case
# ---------------------------------------------------------------------------


class TestSplitPascalCase:
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


# ---------------------------------------------------------------------------
# AcronymCasingScanner._get_class_names (requires tree-sitter-php)
# ---------------------------------------------------------------------------


@_skip_no_ts
class TestGetClassNames:
    def test_returns_class_names_with_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "Mod.php"
        _write_php(
            f,
            "<?php\nclass Foo {\n}\n\nclass Bar {\n}\n",
        )
        result = AcronymCasingScanner._get_class_names(f)
        assert ("Foo", 2) in result
        assert ("Bar", 5) in result

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

    def test_get_class_names_with_no_classes_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "Mod.php"
        _write_php(f, "<?php\n$x = 1;\n")
        assert AcronymCasingScanner._get_class_names(f) == []

    def test_get_class_names_with_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.php"
        _write_php(f, "")
        assert AcronymCasingScanner._get_class_names(f) == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.php"
        _write_php(f, "<?php\nclass {\n")
        assert AcronymCasingScanner._get_class_names(f) == []


# ---------------------------------------------------------------------------
# AcronymCasingScanner._load_acronyms_from_settings
# ---------------------------------------------------------------------------


class TestProjectAcronyms:
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


# ---------------------------------------------------------------------------
# AcronymCasingScanner.main
# ---------------------------------------------------------------------------


class TestMain:
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
        assert "SKIPPED" in out

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
        assert report["skipped"] is True

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
        self._write_settings(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    @_skip_no_ts
    def test_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass Foo {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Violations: 0" in out

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
    def test_json_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Mod.php", "<?php\nclass ApiGateway {}\n")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1
        assert data["violations"][0]["class"] == "ApiGateway"
        assert data["violations"][0]["expected"] == "API"

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


# ---------------------------------------------------------------------------
# Coverage: _load_default_acronyms error handling (lines 112-118)
# ---------------------------------------------------------------------------


class TestLoadDefaultAcronymsErrorHandling:
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


# ---------------------------------------------------------------------------
# Coverage: _get_class_names when tree-sitter-php not installed (line 188)
# ---------------------------------------------------------------------------


class TestGetClassNamesNoTreeSitter:
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


# ---------------------------------------------------------------------------
# Coverage: main() when tree-sitter-php not installed (lines 249-270)
# ---------------------------------------------------------------------------


class TestMainNoTreeSitter:
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
