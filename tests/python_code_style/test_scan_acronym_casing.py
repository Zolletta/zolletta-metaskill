"""Tests for scan_acronym_casing.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.python_code_style.scan_acronym_casing import (
    _get_class_names,
    _load_acronyms_from_settings,
    _load_default_acronyms,
    _split_pascal_case,
    main,
)

# ---------------------------------------------------------------------------
# _load_default_acronyms
# ---------------------------------------------------------------------------


class TestLoadDefaultAcronyms:
    def test_returns_non_empty_list(self) -> None:
        acronyms = _load_default_acronyms()
        assert isinstance(acronyms, list)
        assert len(acronyms) > 0
        assert all(isinstance(a, str) for a in acronyms)
        assert all(a == a.upper() for a in acronyms)

    def test_contains_common_acronyms(self) -> None:
        acronyms = _load_default_acronyms()
        for expected in ("API", "HTTP", "JSON", "URL", "SQL"):
            assert expected in acronyms

    def test_fallback_minimal_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When the JSON file is missing, the fallback list is returned."""
        import zolletta_metaskill.python_code_style.scan_acronym_casing as mod

        nonexistent = Path("/nonexistent/acronyms.json")
        monkeypatch.setattr(mod, "_ACRONYMS_JSON", nonexistent)
        acronyms = _load_default_acronyms()
        assert "API" in acronyms
        assert "CI" in acronyms
        assert "HTTP" in acronyms

    def test_fallback_on_invalid_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import zolletta_metaskill.python_code_style.scan_acronym_casing as mod

        bad_json = tmp_path / "acronyms.json"
        bad_json.write_text("{invalid json", encoding="utf-8")
        monkeypatch.setattr(mod, "_ACRONYMS_JSON", bad_json)
        acronyms = _load_default_acronyms()
        assert "API" in acronyms  # fallback

    def test_fallback_on_empty_acronyms_list(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An empty acronyms array triggers the fallback."""
        import zolletta_metaskill.python_code_style.scan_acronym_casing as mod

        empty_json = tmp_path / "acronyms.json"
        empty_json.write_text(json.dumps({"acronyms": []}), encoding="utf-8")
        monkeypatch.setattr(mod, "_ACRONYMS_JSON", empty_json)
        acronyms = _load_default_acronyms()
        assert "API" in acronyms  # fallback

    def test_loads_from_valid_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        import zolletta_metaskill.python_code_style.scan_acronym_casing as mod

        custom_json = tmp_path / "acronyms.json"
        custom_json.write_text(
            json.dumps({"acronyms": ["XYZ", "ABC", "abc"]}), encoding="utf-8"
        )
        monkeypatch.setattr(mod, "_ACRONYMS_JSON", custom_json)
        acronyms = _load_default_acronyms()
        assert "XYZ" in acronyms
        assert "ABC" in acronyms
        # lowercase entries are uppercased
        assert "ABC" in acronyms

    def test_filters_non_string_entries(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import zolletta_metaskill.python_code_style.scan_acronym_casing as mod

        custom_json = tmp_path / "acronyms.json"
        custom_json.write_text(
            json.dumps({"acronyms": ["API", 123, None, "HTTP"]}), encoding="utf-8"
        )
        monkeypatch.setattr(mod, "_ACRONYMS_JSON", custom_json)
        acronyms = _load_default_acronyms()
        assert "API" in acronyms
        assert "HTTP" in acronyms
        assert 123 not in acronyms
        assert None not in acronyms


# ---------------------------------------------------------------------------
# _split_pascal_case
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
    def test_known_splits(self, name: str, expected: list[str]) -> None:
        assert _split_pascal_case(name) == expected

    def test_empty_string(self) -> None:
        assert _split_pascal_case("") == []

    def test_single_word_lowercase(self) -> None:
        assert _split_pascal_case("word") == ["word"]

    def test_single_word_uppercase(self) -> None:
        assert _split_pascal_case("API") == ["API"]

    def test_all_uppercase_acronym(self) -> None:
        assert _split_pascal_case("HTTP") == ["HTTP"]

    def test_mixed_with_digits(self) -> None:
        assert _split_pascal_case("S3Bucket") == ["S", "3", "Bucket"]

    def test_consecutive_uppercase_then_lower(self) -> None:
        # HTTPSClient -> HTTPS | Client
        assert _split_pascal_case("HTTPSClient") == ["HTTPS", "Client"]


# ---------------------------------------------------------------------------
# _get_class_names
# ---------------------------------------------------------------------------


class TestGetClassNames:
    def test_returns_class_names_with_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Foo:\n    pass\n\nclass Bar:\n    pass\n",
            encoding="utf-8",
        )
        result = _get_class_names(f)
        assert result == [("Foo", 1), ("Bar", 4)]

    def test_nested_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Outer:\n    class Inner:\n        pass\n",
            encoding="utf-8",
        )
        result = _get_class_names(f)
        assert ("Outer", 1) in result
        assert ("Inner", 2) in result

    def test_no_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("x = 1\n", encoding="utf-8")
        assert _get_class_names(f) == []

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        assert _get_class_names(f) == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def (:\n", encoding="utf-8")
        assert _get_class_names(f) == []

    def test_classes_with_decorators(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "@staticmethod\nclass Foo:\n    pass\n",
            encoding="utf-8",
        )
        result = _get_class_names(f)
        assert result == [("Foo", 2)]


# ---------------------------------------------------------------------------
# _load_acronyms_from_settings
# ---------------------------------------------------------------------------


class TestLoadAcronymsFromSettings:
    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        assert _load_acronyms_from_settings(tmp_path / "missing.json") is None

    def test_returns_none_when_no_acronyms_key(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"other": 1}), encoding="utf-8")
        assert _load_acronyms_from_settings(f) is None

    def test_returns_none_when_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"acronyms": []}), encoding="utf-8")
        assert _load_acronyms_from_settings(f) is None

    def test_returns_uppercased_acronyms(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"acronyms": ["abc", "XYZ"]}), encoding="utf-8")
        result = _load_acronyms_from_settings(f)
        assert result is not None
        assert "ABC" in result
        assert "XYZ" in result

    def test_returns_none_on_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text("{invalid", encoding="utf-8")
        assert _load_acronyms_from_settings(f) is None

    def test_returns_none_when_acronyms_not_list(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.json"
        f.write_text(json.dumps({"acronyms": "not a list"}), encoding="utf-8")
        assert _load_acronyms_from_settings(f) is None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_skip_flag_returns_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "--skip"])
        assert main() == 0
        out = capsys.readouterr().out
        assert "SKIPPED" in out

    def test_skip_flag_with_json_no_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "--skip", "--json"])
        assert main() == 0
        out = capsys.readouterr().out
        assert out == ""

    def test_nonexistent_directory(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["scan", "/nonexistent/path/xyz"])
        assert main() == 1
        err = capsys.readouterr().err
        assert "does not exist" in err

    def test_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API"])
        assert main() == 0
        out = capsys.readouterr().out
        assert "Violations: 0" in out

    def test_detects_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API"])
        assert main() == 0  # no --strict
        out = capsys.readouterr().out
        assert "ApiGateway" in out
        assert "API" in out

    def test_strict_returns_one_on_violation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert main() == 1

    def test_strict_returns_zero_when_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class APIGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert main() == 0

    def test_json_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 1
        assert data["violations"][0]["class"] == "ApiGateway"
        assert data["violations"][0]["expected"] == "API"

    def test_json_output_no_violations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class APIGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 0

    def test_skips_init_files(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert main() == 0  # __init__.py is skipped

    def test_skips_ignored_dirs(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        src = tmp_path / "src"
        venv = src / ".venv"
        venv.mkdir(parents=True)
        (venv / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--strict"])
        assert main() == 0  # .venv is ignored

    def test_settings_merge(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class XyzHelper:\n    pass\n", encoding="utf-8")
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"acronyms": ["XYZ"]}), encoding="utf-8")
        monkeypatch.setattr(
            sys, "argv", ["scan", str(src), "--settings", str(settings), "--strict"]
        )
        assert main() == 1  # XYZ is merged, Xyz is a violation

    def test_acronyms_flag_overrides_settings(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        # ApiGateway violates API, but we only check XYZ
        (src / "mod.py").write_text("class ApiGateway:\n    pass\n", encoding="utf-8")
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"acronyms": ["XYZ"]}), encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            ["scan", str(src), "--acronyms", "XYZ", "--settings", str(settings), "--strict"],
        )
        assert main() == 0  # --acronyms overrides, API not checked

    def test_default_directory_src(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", "--acronyms", "API"])
        assert main() == 0

    def test_multiple_violations_in_one_class(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        # ApiHttpGateway has both Api and Http in wrong case
        (src / "mod.py").write_text("class ApiHttpGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API,HTTP", "--json"])
        assert main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 2

    def test_correct_casing_not_flagged(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class APIGateway:\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["scan", str(src), "--acronyms", "API", "--json"])
        assert main() == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["violation_count"] == 0
