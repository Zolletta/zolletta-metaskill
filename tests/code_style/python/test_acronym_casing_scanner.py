"""Tests for acronym_casing_scanner.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from zolletta_metaskill.code_style.python.acronym_casing_scanner import (
    AcronymCasingScanner,
)

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
        """When the JSON file is missing, the fallback list is returned."""
        import zolletta_metaskill.code_style.python.acronym_casing_scanner as mod

        nonexistent = Path("/nonexistent/acronyms.json")
        monkeypatch.setattr(mod.AcronymCasingScanner, "_ACRONYMS_JSON", nonexistent)
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms
        assert "CI" in acronyms
        assert "HTTP" in acronyms

    def test_fallback_on_invalid_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import zolletta_metaskill.code_style.python.acronym_casing_scanner as mod

        bad_json = tmp_path / "acronyms.json"
        bad_json.write_text("{invalid json", encoding="utf-8")
        monkeypatch.setattr(mod.AcronymCasingScanner, "_ACRONYMS_JSON", bad_json)
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms  # fallback

    def test_fallback_on_empty_acronyms_list(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An empty acronyms array triggers the fallback."""
        import zolletta_metaskill.code_style.python.acronym_casing_scanner as mod

        empty_json = tmp_path / "acronyms.json"
        empty_json.write_text(json.dumps({"acronyms": []}), encoding="utf-8")
        monkeypatch.setattr(mod.AcronymCasingScanner, "_ACRONYMS_JSON", empty_json)
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms  # fallback

    def test_loads_from_valid_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        import zolletta_metaskill.code_style.python.acronym_casing_scanner as mod

        custom_json = tmp_path / "acronyms.json"
        custom_json.write_text(json.dumps({"acronyms": ["XYZ", "ABC", "abc"]}), encoding="utf-8")
        monkeypatch.setattr(mod.AcronymCasingScanner, "_ACRONYMS_JSON", custom_json)
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "XYZ" in acronyms
        assert "ABC" in acronyms
        # lowercase entries are uppercased
        assert "ABC" in acronyms

    def test_filters_non_string_entries(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import zolletta_metaskill.code_style.python.acronym_casing_scanner as mod

        custom_json = tmp_path / "acronyms.json"
        custom_json.write_text(
            json.dumps({"acronyms": ["API", 123, None, "HTTP"]}), encoding="utf-8"
        )
        monkeypatch.setattr(mod.AcronymCasingScanner, "_ACRONYMS_JSON", custom_json)
        acronyms = AcronymCasingScanner._load_default_acronyms()
        assert "API" in acronyms
        assert "HTTP" in acronyms
        assert cast(Any, 123) not in acronyms
        assert None not in acronyms


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
    def test_split_pascal_case_known_splits(self, name: str, expected: list[str]) -> None:
        assert AcronymCasingScanner._split_pascal_case(name) == expected

    def test_split_pascal_case_empty_string_returns_empty_list(self) -> None:
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
# AcronymCasingScanner._get_class_names
# ---------------------------------------------------------------------------


class TestGetClassNames:
    def test_returns_class_names_with_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Foo:\n    pass\n\nclass Bar:\n    pass\n",
            encoding="utf-8",
        )
        result = AcronymCasingScanner._get_class_names(f)
        assert result == [("Foo", 1), ("Bar", 4)]

    def test_get_class_names_nested_classes_contains_value(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Outer:\n    class Inner:\n        pass\n",
            encoding="utf-8",
        )
        result = AcronymCasingScanner._get_class_names(f)
        assert ("Outer", 1) in result
        assert ("Inner", 2) in result

    def test_get_class_names_no_classes_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n", encoding="utf-8")
        assert AcronymCasingScanner._get_class_names(f) == []

    def test_get_class_names_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        assert AcronymCasingScanner._get_class_names(f) == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def (:\n", encoding="utf-8")
        assert AcronymCasingScanner._get_class_names(f) == []

    def test_classes_with_decorators(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "@staticmethod\nclass Foo:\n    pass\n",
            encoding="utf-8",
        )
        result = AcronymCasingScanner._get_class_names(f)
        assert result == [("Foo", 2)]


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
        return AcronymCasingScanner.main()

    def test_check_disabled_reports_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(
            tmp_path, python={"code_style": {"check_acronym_casing": False}}
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
            tmp_path, python={"code_style": {"check_acronym_casing": False}}
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_no_python_language_reports_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """PHP-only project: the Python scanner has nothing to scan."""
        self._write_settings(
            tmp_path,
            language="php",
            python=None,
            php={"autoload": {"psr-4": {"App\\": "src/"}}},
        )
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_missing_source_dir_returns_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Violations: 0" in out

    def test_detects_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan"])
        out = capsys.readouterr().out
        assert rc == 0  # report-only
        assert "ApiGateway" in out
        assert "API" in out

    def test_json_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1
        assert data["violations"][0]["class"] == "ApiGateway"
        assert data["violations"][0]["expected"] == "API"
        assert "API" in data["acronyms_checked"]

    def test_json_output_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class APIGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 0

    def test_skips_init_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 0

    def test_gitignored_dirs_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("assets/\n")
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        assets = src / "assets"
        assets.mkdir(parents=True)
        (assets / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 0

    def test_settings_acronyms_merged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path, acronyms=["XYZ"])
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class XyzHelper:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1
        assert "XYZ" in data["acronyms_checked"]

    def test_no_settings_uses_default_src(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Without settings.json, falls back to src/ for all registered languages."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 1

    def test_multiple_violations_in_one_class(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiHttpGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 2

    def test_correct_casing_not_flagged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class APIGateway:\n    pass\n", encoding="utf-8")
        rc = self._run(tmp_path, monkeypatch, ["scan", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data["violation_count"] == 0
