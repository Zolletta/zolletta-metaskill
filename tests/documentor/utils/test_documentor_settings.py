"""Tests for documentor_settings.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings


class TestDocumentorSettings:
    # --- from_settings ---

    def test_from_settings_resolves_every_documentation_key(self, tmp_path: Path) -> None:
        settings = {
            "runs_dir": str(tmp_path / "runs"),
            "documentation": {
                "dir": "guide",
                "adrs": "decisions",
                "doc_patterns": ["*.md", 7, "*.rst"],
                "include_referential": True,
                "min_severity": "medium",
                "check_external": True,
            },
        }
        resolved = DocumentorSettings.from_settings(settings)
        assert resolved.documentation_rel_dir == Path("guide")
        assert resolved.adrs_dir == Path("guide/decisions")
        assert resolved.doc_patterns == ("*.md", "*.rst")
        assert resolved.include_referential is True
        assert resolved.min_severity == "medium"
        assert resolved.check_external is True

    def test_from_settings_applies_documented_defaults(self, tmp_path: Path) -> None:
        settings = {"runs_dir": str(tmp_path / "runs"), "documentation": {}}
        resolved = DocumentorSettings.from_settings(settings)
        assert resolved.documentation_rel_dir == Path("docs")
        assert resolved.adrs_dir is None
        assert resolved.doc_patterns is None
        assert resolved.include_referential is False
        assert resolved.min_severity == "low"
        assert resolved.check_external is False

    def test_from_settings_carries_default_quadrants(self, tmp_path: Path) -> None:
        settings = {"runs_dir": str(tmp_path / "runs"), "documentation": {}}
        resolved = DocumentorSettings.from_settings(settings)
        assert set(resolved.quadrants) >= {"tutorials", "how-to", "reference", "explanation"}

    # --- resolve_cache_dir: explicit override ---

    def test_resolve_cache_dir_configured_path_returns_absolute(self, tmp_path: Path) -> None:
        settings = {"documentation": {"cache_dir": str(tmp_path / "mycache")}}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == Path(os.path.abspath(str(tmp_path / "mycache")))

    def test_resolve_cache_dir_relative_path_is_resolved(self) -> None:
        settings = {"documentation": {"cache_dir": "custom-cache"}}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == Path(os.path.abspath("custom-cache"))

    def test_resolve_cache_dir_empty_string_falls_back_to_runs_dir(self, tmp_path: Path) -> None:
        settings = {"runs_dir": str(tmp_path), "documentation": {"cache_dir": ""}}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == Path(os.path.abspath(tmp_path / "cache"))

    def test_resolve_cache_dir_non_string_falls_back_to_runs_dir(self, tmp_path: Path) -> None:
        settings = {"runs_dir": str(tmp_path), "documentation": {"cache_dir": 42}}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == Path(os.path.abspath(tmp_path / "cache"))

    # --- resolve_cache_dir: per-run resolution ---

    def test_resolve_cache_dir_uses_latest_run_folder_cache(self, tmp_path: Path) -> None:
        runs = tmp_path / ".zolletta-metaskill"
        for name in ("2026-09-27-17-21", "2026-10-04-19-30"):
            (runs / name / "cache").mkdir(parents=True)
        settings = {"runs_dir": str(runs)}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == runs / "2026-10-04-19-30" / "cache"

    def test_resolve_cache_dir_run_folders_sorted_by_name_not_mtime(self, tmp_path: Path) -> None:
        runs = tmp_path / ".zolletta-metaskill"
        older = runs / "2026-09-27-17-21"
        newer = runs / "2026-10-04-19-30"
        for folder in (older, newer):
            folder.mkdir(parents=True)
        settings = {"runs_dir": str(runs)}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == newer / "cache"

    def test_resolve_cache_dir_ignores_flat_cache_sibling(self, tmp_path: Path) -> None:
        runs = tmp_path / ".zolletta-metaskill"
        (runs / "2026-10-04-19-30").mkdir(parents=True)
        (runs / "cache").mkdir()
        settings = {"runs_dir": str(runs)}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == runs / "2026-10-04-19-30" / "cache"

    def test_resolve_cache_dir_no_run_folder_returns_runs_dir_cache(self, tmp_path: Path) -> None:
        runs = tmp_path / ".zolletta-metaskill"
        runs.mkdir()
        settings = {"runs_dir": str(runs)}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == runs / "cache"

    def test_resolve_cache_dir_missing_runs_dir_returns_absolute_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = DocumentorSettings.resolve_cache_dir({})
        assert result == Path(os.path.abspath(DocumentorSettings.DEFAULT_CACHE_DIR))
        assert result.is_absolute()

    # --- _latest_run_dir ---

    def test_latest_run_dir_returns_none_when_runs_dir_absent(self, tmp_path: Path) -> None:
        assert DocumentorSettings._latest_run_dir(tmp_path / "absent") is None

    def test_latest_run_dir_ignores_non_run_directories(self, tmp_path: Path) -> None:
        (tmp_path / "cache").mkdir()
        (tmp_path / "plans").mkdir()
        assert DocumentorSettings._latest_run_dir(tmp_path) is None

    def test_latest_run_dir_ignores_files(self, tmp_path: Path) -> None:
        (tmp_path / "2026-10-04-19-30").mkdir()
        (tmp_path / "adr-cache.json").write_text("{}", encoding="utf-8")
        result = DocumentorSettings._latest_run_dir(tmp_path)
        assert result == tmp_path / "2026-10-04-19-30"

    def test_latest_run_dir_flat_cache_does_not_outrank_timestamped_run(
        self, tmp_path: Path
    ) -> None:
        """``"cache"`` sorts after ``"YYYY-..."``, so a name filter is required."""
        (tmp_path / "2026-01-02-03-04").mkdir()
        (tmp_path / "cache").mkdir()
        result = DocumentorSettings._latest_run_dir(tmp_path)
        assert result == tmp_path / "2026-01-02-03-04"
