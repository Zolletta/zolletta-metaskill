"""Tests for core/ProjectConfig.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig


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


class TestProjectConfig:
    # --- EnsureEngines ---

    def test_registers_bundled_engines(self) -> None:
        EngineRegistry.clear()
        try:
            ProjectConfig.ensure_engines()
            assert set(EngineRegistry.available_languages()) == {"python", "php"}
        finally:
            ProjectConfig.ensure_engines()

    def test_idempotent(self) -> None:
        ProjectConfig.ensure_engines()
        ProjectConfig.ensure_engines()
        assert "python" in EngineRegistry.available_languages()

    # --- LoadSettings ---

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert ProjectConfig.load_settings(tmp_path / "nope.json") == {}

    def test_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        bad = tmp_path / "settings.json"
        bad.write_text("{ not json")
        assert ProjectConfig.load_settings(bad) == {}

    def test_non_object_json_returns_empty(self, tmp_path: Path) -> None:
        arr = tmp_path / "settings.json"
        arr.write_text('["a", "b"]')
        assert ProjectConfig.load_settings(arr) == {}

    def test_valid_settings(self, tmp_path: Path) -> None:
        path = _write_settings(tmp_path)
        data = ProjectConfig.load_settings(path)
        assert data["language"] == "python"

    # --- Setting ---

    def test_returns_value(self) -> None:
        settings = {"python": {"code_style": {"max_file_length": 500}}}
        assert ProjectConfig.setting(settings, "python.code_style.max_file_length", 800) == 500

    def test_missing_key_returns_default(self) -> None:
        assert ProjectConfig.setting({}, "python.code_style.x", 3) == 3

    def test_missing_leaf_returns_default(self) -> None:
        settings: dict[str, Any] = {"python": {"code_style": {}}}
        assert ProjectConfig.setting(settings, "python.code_style.x", 3) == 3

    def test_non_dict_intermediate_returns_default(self) -> None:
        settings = {"python": "oops"}
        assert ProjectConfig.setting(settings, "python.code_style.x", 3) == 3

    def test_bool_default_accepts_bool(self) -> None:
        settings = {"a": {"b": True}}
        assert ProjectConfig.setting(settings, "a.b", False) is True

    def test_bool_default_rejects_non_bool(self) -> None:
        settings = {"a": {"b": "yes"}}
        assert ProjectConfig.setting(settings, "a.b", False) is False

    def test_int_default_accepts_int(self) -> None:
        settings = {"a": {"b": 42}}
        assert ProjectConfig.setting(settings, "a.b", 0) == 42

    def test_int_default_rejects_bool(self) -> None:
        settings = {"a": {"b": True}}
        assert ProjectConfig.setting(settings, "a.b", 0) == 0

    def test_int_default_rejects_str(self) -> None:
        settings = {"a": {"b": "42"}}
        assert ProjectConfig.setting(settings, "a.b", 0) == 0

    def test_str_default(self) -> None:
        settings = {"a": {"b": "docs"}}
        assert ProjectConfig.setting(settings, "a.b", "x") == "docs"
        assert ProjectConfig.setting({"a": {"b": 5}}, "a.b", "x") == "x"

    def test_list_default(self) -> None:
        settings = {"a": {"b": ["src"]}}
        assert ProjectConfig.setting(settings, "a.b", ["x"]) == ["src"]
        assert ProjectConfig.setting({"a": {"b": "src"}}, "a.b", ["x"]) == ["x"]

    def test_dict_default(self) -> None:
        settings = {"a": {"b": {"k": 1}}}
        assert ProjectConfig.setting(settings, "a.b", {}) == {"k": 1}
        assert ProjectConfig.setting({"a": {"b": 5}}, "a.b", {"d": 1}) == {"d": 1}

    def test_none_default_returns_node_as_is(self) -> None:
        settings = {"a": {"b": {"anything": [1, 2]}}}
        assert ProjectConfig.setting(settings, "a.b", None) == {"anything": [1, 2]}

    def test_none_default_missing_returns_none(self) -> None:
        assert ProjectConfig.setting({}, "a.b", None) is None

    def test_other_default_type_returns_node(self) -> None:
        settings = {"a": {"b": 2.5}}
        assert ProjectConfig.setting(settings, "a.b", 1.0) == 2.5

    # --- ConfiguredLanguages ---

    def test_language_field(self) -> None:
        assert ProjectConfig.configured_languages({"language": "python"}) == {"python"}

    def test_populated_sections(self) -> None:
        settings = {"language": "", "python": {"tools": {}}, "php": {"tools": {}}}
        assert ProjectConfig.configured_languages(settings) == {"python", "php"}

    def test_null_sections_ignored(self) -> None:
        settings: dict[str, Any] = {"language": "python", "python": {"tools": {}}, "php": None}
        assert ProjectConfig.configured_languages(settings) == {"python"}

    def test_non_string_language_ignored(self) -> None:
        assert ProjectConfig.configured_languages({"language": 5}) == set()

    def test_empty_settings(self) -> None:
        assert ProjectConfig.configured_languages({}) == set()

    def test_unregistered_language_via_language_field(self) -> None:
        assert ProjectConfig.configured_languages({"language": "go"}) == {"go"}

    # --- EnabledLanguages ---

    def test_missing_toggle_is_enabled(self) -> None:
        settings = {"language": "python", "python": {"code_style": {}}}
        assert ProjectConfig.enabled_languages(settings, "code_style.check_x") == {"python"}

    def test_false_toggle_excludes_language(self) -> None:
        settings = {
            "language": "python",
            "python": {"code_style": {"check_x": False}},
            "php": {"code_style": {}},
        }
        assert ProjectConfig.enabled_languages(settings, "code_style.check_x") == {"php"}

    def test_enabled_languages_all_disabled_returns_empty(self) -> None:
        settings = {"language": "python", "python": {"code_style": {"check_x": False}}}
        assert ProjectConfig.enabled_languages(settings, "code_style.check_x") == set()

    def test_non_dict_section_is_enabled(self) -> None:
        settings = {"language": "python", "python": "unexpected"}
        assert ProjectConfig.enabled_languages(settings, "code_style.check_x") == {"python"}

    def test_nested_toggle_path(self) -> None:
        settings = {
            "language": "python",
            "python": {"patterns": {"check_ocp": False}},
            "php": {"patterns": {}},
        }
        assert ProjectConfig.enabled_languages(settings, "patterns.check_ocp") == {"php"}

    # --- AnyEnabled ---

    def test_toggle_true_for_one_language(self) -> None:
        settings = {"python": {"code_style": {"check_x": True}}}
        assert ProjectConfig.any_enabled(settings, {"python"}, "code_style.check_x") is True

    def test_toggle_false_for_all(self) -> None:
        settings = {"python": {"code_style": {"check_x": False}}}
        assert ProjectConfig.any_enabled(settings, {"python"}, "code_style.check_x") is False

    def test_missing_key_uses_default(self) -> None:
        assert ProjectConfig.any_enabled({"python": {}}, {"python"}, "code_style.check_x") is True

    def test_missing_key_default_false(self) -> None:
        assert (
            ProjectConfig.any_enabled(
                {"python": {}}, {"python"}, "code_style.check_x", default=False
            )
            is False
        )

    def test_sectionless_language_uses_default(self) -> None:
        assert ProjectConfig.any_enabled({}, {"go"}, "code_style.check_x") is True

    def test_empty_languages(self) -> None:
        assert ProjectConfig.any_enabled({}, set(), "code_style.check_x") is False

    # --- ScanLanguages ---

    def test_enabled_languages_returned(self) -> None:
        settings = {"language": "python", "python": {"code_style": {}}}
        assert ProjectConfig.scan_languages(settings, "code_style.check_x") == {"python"}

    def test_scan_languages_all_disabled_returns_empty(self) -> None:
        settings = {"language": "python", "python": {"code_style": {"check_x": False}}}
        assert ProjectConfig.scan_languages(settings, "code_style.check_x") == set()

    def test_no_settings_returns_registered(self) -> None:
        assert ProjectConfig.scan_languages({}, "code_style.check_x") == {"python", "php"}

    # --- ExtensionsFor ---

    def test_maps_languages(self) -> None:
        assert ProjectConfig.extensions_for({"python", "php"}) == {".py", ".php"}

    def test_unregistered_language_warns(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = ProjectConfig.extensions_for({"go", "python"})
        assert result == {".py"}
        assert "no engine for language 'go'" in capsys.readouterr().err

    # --- LanguagesForExtensions ---

    def test_filters_to_matching_engines(self) -> None:
        assert ProjectConfig.languages_for_extensions({"python", "php"}, {".py"}) == {"python"}

    def test_unregistered_language_excluded(self) -> None:
        assert ProjectConfig.languages_for_extensions({"go"}, {".go"}) == set()

    # --- SourceDirs ---

    def test_python_paths_source(self) -> None:
        settings = {"python": {"paths": {"source": ["lib", "app"]}}}
        assert ProjectConfig.source_dirs(settings, "python") == ["lib", "app"]

    def test_source_dirs_python_fallback(self) -> None:
        assert ProjectConfig.source_dirs({"python": {}}, "python") == ["src"]

    def test_php_autoload(self) -> None:
        settings = {"php": {"autoload": {"psr-4": {"App\\": "app/", "Lib\\": "lib/"}}}}
        assert ProjectConfig.source_dirs(settings, "php") == ["app/", "lib/"]

    def test_php_autoload_list_values(self) -> None:
        settings = {"php": {"autoload": {"psr-4": {"App\\": ["app/", "lib/"]}}}}
        assert ProjectConfig.source_dirs(settings, "php") == ["app/", "lib/"]

    def test_source_dirs_php_fallback(self) -> None:
        assert ProjectConfig.source_dirs({"php": {}}, "php") == ["src"]

    def test_php_autoload_non_dict(self) -> None:
        settings = {"php": {"autoload": {"psr-4": "oops"}}}
        assert ProjectConfig.source_dirs(settings, "php") == ["src"]

    def test_php_autoload_non_string_items_skipped(self) -> None:
        settings = {"php": {"autoload": {"psr-4": {"App\\": ["app/", 5]}}}}
        assert ProjectConfig.source_dirs(settings, "php") == ["app/"]

    def test_source_dirs_unknown_language_fallback(self) -> None:
        assert ProjectConfig.source_dirs({}, "go") == ["src"]

    # --- TestDirs ---

    def test_python_paths_tests(self) -> None:
        settings = {"python": {"paths": {"tests": ["spec"]}}}
        assert ProjectConfig.test_dirs(settings, "python") == ["spec"]

    def test_test_dirs_python_fallback(self) -> None:
        assert ProjectConfig.test_dirs({"python": {}}, "python") == ["tests"]

    def test_php_autoload_dev(self) -> None:
        settings = {"php": {"autoload": {"psr-4-dev": {"Tests\\": "tests/"}}}}
        assert ProjectConfig.test_dirs(settings, "php") == ["tests/"]

    def test_test_dirs_php_fallback(self) -> None:
        assert ProjectConfig.test_dirs({"php": {}}, "php") == ["tests"]

    def test_test_dirs_unknown_language_fallback(self) -> None:
        assert ProjectConfig.test_dirs({}, "go") == ["tests"]

    # --- PackageName ---

    def test_python_package(self) -> None:
        settings = {"python": {"paths": {"package": "myproject"}}}
        assert ProjectConfig.package_name(settings, "python") == "myproject"

    def test_python_package_null(self) -> None:
        settings = {"python": {"paths": {"package": None}}}
        assert ProjectConfig.package_name(settings, "python") is None

    def test_python_package_missing(self) -> None:
        assert ProjectConfig.package_name({"python": {}}, "python") is None

    def test_python_package_empty_string(self) -> None:
        settings = {"python": {"paths": {"package": ""}}}
        assert ProjectConfig.package_name(settings, "python") is None

    def test_php_package_first_psr4_dir(self) -> None:
        settings = {"php": {"autoload": {"psr-4": {"App\\": "src/"}}}}
        assert ProjectConfig.package_name(settings, "php") == "src/"

    def test_php_package_missing(self) -> None:
        assert ProjectConfig.package_name({"php": {}}, "php") is None

    def test_unknown_language(self) -> None:
        assert ProjectConfig.package_name({}, "go") is None

    # --- Roots ---

    def test_source_roots_unions_and_dedupes(self) -> None:
        settings = {
            "python": {"paths": {"source": ["src"]}},
            "php": {"autoload": {"psr-4": {"App\\": "src", "Lib\\": "lib"}}},
        }
        roots = ProjectConfig.source_roots(settings, {"python", "php"})
        assert roots == [Path("src"), Path("lib")]

    def test_test_roots_unions(self) -> None:
        settings = {
            "python": {"paths": {"tests": ["tests"]}},
            "php": {"autoload": {"psr-4-dev": {"Tests\\": "spec"}}},
        }
        roots = ProjectConfig.test_roots(settings, {"python", "php"})
        assert roots == [Path("spec"), Path("tests")]

    def test_existing_roots_filters(self, tmp_path: Path) -> None:
        (tmp_path / "real").mkdir()
        roots = [tmp_path / "real", tmp_path / "missing"]
        assert ProjectConfig.existing_roots(roots) == [tmp_path / "real"]

    # --- DocHelpers ---

    def test_docs_dir_default(self) -> None:
        assert ProjectConfig.docs_dir({}) == Path("docs")

    def test_docs_dir_configured(self) -> None:
        settings = {"documentation": {"dir": "documentation"}}
        assert ProjectConfig.docs_dir(settings) == Path("documentation")

    def test_adrs_dir_null(self) -> None:
        assert ProjectConfig.adrs_dir({"documentation": {"adrs": None}}) is None

    def test_adrs_dir_empty_means_docs_root(self) -> None:
        settings = {"documentation": {"dir": "docs", "adrs": ""}}
        assert ProjectConfig.adrs_dir(settings) == Path("docs")

    def test_adrs_dir_relative(self) -> None:
        settings = {"documentation": {"dir": "docs", "adrs": "adr"}}
        assert ProjectConfig.adrs_dir(settings) == Path("docs/adr")

    def test_adrs_dir_non_string(self) -> None:
        assert ProjectConfig.adrs_dir({"documentation": {"adrs": 5}}) is None

    def test_runs_dir_default(self) -> None:
        assert ProjectConfig.runs_dir({}) == Path(".zolletta-metaskill")

    def test_runs_dir_configured(self) -> None:
        assert ProjectConfig.runs_dir({"runs_dir": "out"}) == Path("out")

    # --- IterFiles ---

    def test_extension_filter(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "a.py").write_text("x")
        (root / "b.txt").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "a.py"]

    def test_gitignored_files_skipped(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        root = tmp_path / "src"
        root.mkdir()
        (root / "ignored.py").write_text("x")
        (root / "real.py").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "real.py"]

    def test_git_missing_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_git(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("git not installed")

        monkeypatch.setattr(subprocess, "run", _no_git)
        root = tmp_path / "src"
        root.mkdir()
        (root / "a.py").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "a.py"]

    def test_git_timeout_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _slow_git(*_args: object, **_kwargs: object) -> None:
            raise subprocess.TimeoutExpired(cmd="git", timeout=30)

        monkeypatch.setattr(subprocess, "run", _slow_git)
        root = tmp_path / "src"
        root.mkdir()
        (root / "a.py").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "a.py"]

    def test_git_failure_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=[], returncode=128, stdout=b"")

        monkeypatch.setattr(subprocess, "run", _fail_git)
        root = tmp_path / "src"
        root.mkdir()
        (root / "a.py").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "a.py"]

    def test_paths_outside_root_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``../``-prefixed entries from git ls-files are dropped."""

        def _fake_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b"../outside.py\0inside.py\0"
            )

        monkeypatch.setattr(subprocess, "run", _fake_git)
        root = tmp_path / "src"
        root.mkdir()
        (root / "inside.py").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "inside.py"]

    def test_non_file_git_entries_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Git ls-files entries that are not files on disk are dropped."""

        def _fake_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=b"ghost.py\0real.py\0")

        monkeypatch.setattr(subprocess, "run", _fake_git)
        root = tmp_path / "src"
        root.mkdir()
        (root / "real.py").write_text("x")
        assert ProjectConfig.iter_files(root, {".py"}) == [root / "real.py"]

    # --- EmitSkipped ---

    def test_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        ProjectConfig.emit_skipped(True, "check_x disabled")
        report = json.loads(capsys.readouterr().out)
        assert report == {"skipped": True, "reason": "check_x disabled"}

    def test_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        ProjectConfig.emit_skipped(False, "check_x disabled")
        assert "SKIPPED (check_x disabled)" in capsys.readouterr().out
