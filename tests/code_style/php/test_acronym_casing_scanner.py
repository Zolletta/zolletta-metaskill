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
from zolletta_metaskill.core.engine.php_engine import _have_tree_sitter_php

TS_PHP_AVAILABLE = _have_tree_sitter_php()
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


class TestLoadAcronymsFromSettings:
    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        assert AcronymCasingScanner._load_acronyms_from_settings(tmp_path / "missing.json") is None

    def test_returns_none_when_no_acronyms_key(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"other": 1}), encoding="utf-8")
        assert AcronymCasingScanner._load_acronyms_from_settings(f) is None

    def test_returns_none_when_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"acronyms": []}), encoding="utf-8")
        assert AcronymCasingScanner._load_acronyms_from_settings(f) is None

    def test_returns_uppercased_acronyms(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"acronyms": ["abc", "XYZ"]}), encoding="utf-8")
        result = AcronymCasingScanner._load_acronyms_from_settings(f)
        assert result is not None
        assert "ABC" in result
        assert "XYZ" in result

    def test_returns_none_on_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text("{invalid", encoding="utf-8")
        assert AcronymCasingScanner._load_acronyms_from_settings(f) is None

    def test_returns_none_when_acronyms_not_list(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"acronyms": "not a list"}), encoding="utf-8")
        assert AcronymCasingScanner._load_acronyms_from_settings(f) is None


# ---------------------------------------------------------------------------
# AcronymCasingScanner.main
# ---------------------------------------------------------------------------


class TestMain:
    def test_skip_flag_returns_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "--skip"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        assert "SKIPPED" in out

    def test_skip_flag_with_json_no_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "--skip", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        assert out == ""

    def test_main_with_nonexistent_directory_returns_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "/nonexistent/path/xyz"])
        assert AcronymCasingScanner.main() == 1
        err = capsys.readouterr().err
        assert "does not exist" in err

    @_skip_no_ts
    def test_main_with_no_violations_returns_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass Foo {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        assert "Violations: 0" in out

    @_skip_no_ts
    def test_main_with_violation_reports_apigateway(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass ApiGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API"])
        assert AcronymCasingScanner.main() == 0  # no --strict
        out = capsys.readouterr().out
        assert "ApiGateway" in out
        assert "API" in out

    @_skip_no_ts
    def test_correct_casing_not_flagged(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass APIGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 0

    @_skip_no_ts
    def test_strict_returns_one_on_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass ApiGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert AcronymCasingScanner.main() == 1

    @_skip_no_ts
    def test_strict_returns_zero_when_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass APIGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert AcronymCasingScanner.main() == 0

    @_skip_no_ts
    def test_main_with_json_output_returns_violation_count(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass ApiGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 1
        assert data["violations"][0]["class"] == "ApiGateway"
        assert data["violations"][0]["expected"] == "API"

    @_skip_no_ts
    def test_json_output_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass APIGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 0

    @_skip_no_ts
    def test_skips_ignored_dirs(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        src = tmp_path / "src"
        vendor = src / "vendor"
        vendor.mkdir(parents=True)
        (vendor / "Mod.php").write_text("<?php\nclass ApiGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert AcronymCasingScanner.main() == 0  # vendor is ignored

    @_skip_no_ts
    def test_main_settings_merge_detects_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass XyzHelper {}\n", encoding="utf-8")
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"acronyms": ["XYZ"]}), encoding="utf-8")
        monkeypatch.setattr(
            sys, "argv", ["scan", str(src), "--settings", str(settings), "--strict"]
        )
        assert AcronymCasingScanner.main() == 1  # XYZ is merged, Xyz is a violation

    @_skip_no_ts
    def test_acronyms_flag_overrides_settings(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        # ApiGateway violates API, but we only check XYZ
        (src / "Mod.php").write_text("<?php\nclass ApiGateway {}\n", encoding="utf-8")
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"acronyms": ["XYZ"]}), encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            ["scan", str(src), "--acronyms", "XYZ", "--settings", str(settings), "--strict"],
        )
        assert AcronymCasingScanner.main() == 0  # --acronyms overrides, API not checked

    @_skip_no_ts
    def test_default_directory_src(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass Foo {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", "--acronyms", "API"])
        assert AcronymCasingScanner.main() == 0

    @_skip_no_ts
    def test_multiple_violations_in_one_class(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        # ApiHttpGateway has both Api and Http in wrong case
        (src / "Mod.php").write_text("<?php\nclass ApiHttpGateway {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API,HTTP", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 2

    @_skip_no_ts
    def test_no_acronyms_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When --acronyms specifies only non-matching acronyms, nothing is flagged."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\nclass ApiGateway {}\n", encoding="utf-8")
        # XYZ is checked but does not appear in ApiGateway, so no violations
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "XYZ", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 0

    @_skip_no_ts
    def test_main_with_interface_violation_reports_apirepository(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Interfaces are also checked for acronym casing."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "Mod.php").write_text("<?php\ninterface ApiRepository {}\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert AcronymCasingScanner.main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 1
        assert data["violations"][0]["class"] == "ApiRepository"
