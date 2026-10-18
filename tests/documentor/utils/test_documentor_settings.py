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
                "include_referential": True,
                "min_severity": "medium",
                "check_external": True,
            },
        }
        resolved = DocumentorSettings.from_settings(settings)
        assert resolved.documentation_rel_dir == Path("guide")
        assert resolved.adrs_dir == Path("guide/decisions")
        assert resolved.include_referential is True
        assert resolved.min_severity == "medium"
        assert resolved.check_external is True

    def test_from_settings_applies_documented_defaults(self, tmp_path: Path) -> None:
        settings = {"runs_dir": str(tmp_path / "runs"), "documentation": {}}
        resolved = DocumentorSettings.from_settings(settings)
        assert resolved.documentation_rel_dir == Path("docs")
        assert resolved.adrs_dir is None
        assert resolved.include_referential is False
        assert resolved.min_severity == "low"
        assert resolved.check_external is False

    def test_from_settings_carries_default_quadrants(self, tmp_path: Path) -> None:
        settings = {"runs_dir": str(tmp_path / "runs"), "documentation": {}}
        resolved = DocumentorSettings.from_settings(settings)
        assert set(resolved.quadrants) >= {"tutorials", "how-to", "reference", "explanation"}

    # --- staleness weights ---

    def test_resolve_staleness_weights_defaults_when_unset(self) -> None:
        weights = DocumentorSettings._resolve_staleness_weights({})
        assert weights["code_doc_alignment"] == 0.30
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_resolve_staleness_weights_custom_setting(self) -> None:
        settings = {
            "documentation": {
                "staleness_weights": {
                    "last_updated": 0.5,
                    "code_doc_alignment": 0.5,
                    "link_health": 0.2,
                    "completeness": 0.2,
                    "accuracy": 0.2,
                }
            }
        }
        weights = DocumentorSettings._resolve_staleness_weights(settings)
        # Weights are normalized to sum to 1 (total here is 1.6)
        assert weights["last_updated"] == pytest.approx(0.5 / 1.6)
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_resolve_staleness_weights_non_numeric_ignored(self) -> None:
        settings = {"documentation": {"staleness_weights": {"last_updated": "high"}}}
        weights = DocumentorSettings._resolve_staleness_weights(settings)
        assert weights["last_updated"] == DocumentorSettings.DEFAULT_WEIGHTS["last_updated"]

    def test_resolve_staleness_weights_zero_total_returns_unnormalized(self) -> None:
        """All-zero weights come back un-normalized: there is nothing to divide by."""
        settings = {
            "documentation": {
                "staleness_weights": {
                    "last_updated": 0,
                    "code_doc_alignment": 0,
                    "link_health": 0,
                    "completeness": 0,
                    "accuracy": 0,
                }
            }
        }
        weights = DocumentorSettings._resolve_staleness_weights(settings)
        assert sum(weights.values()) == 0.0

    def test_resolve_staleness_weights_returns_a_fresh_mapping(self) -> None:
        """The class attribute must never be handed out, or a caller could mutate it."""
        weights = DocumentorSettings._resolve_staleness_weights({})
        weights["last_updated"] = 99.0
        assert DocumentorSettings.DEFAULT_WEIGHTS["last_updated"] == 0.20

    # --- required sections ---

    def test_resolve_required_sections_defaults(self) -> None:
        assert (
            DocumentorSettings._resolve_required_sections({})
            == DocumentorSettings.DEFAULT_README_SECTIONS
        )

    def test_resolve_required_sections_setting(self) -> None:
        settings = {"documentation": {"readme_sections": ["Foo", "Bar"]}}
        assert DocumentorSettings._resolve_required_sections(settings) == ("Foo", "Bar")

    def test_resolve_required_sections_from_translations_file(self, tmp_path: Path) -> None:
        """Translated readme sections are loaded from the configured translations file."""
        trans_file = tmp_path / "translations.json"
        trans_file.write_text(
            '{"readme_sections": [" installazione ", "uso"], "quadrants": {}}', encoding="utf-8"
        )
        settings = {"documentation": {"diataxis_translations": str(trans_file)}}
        assert DocumentorSettings._resolve_required_sections(settings) == (
            "installazione",
            "uso",
        )

    def test_resolve_required_sections_translations_without_readme_sections(
        self, tmp_path: Path
    ) -> None:
        """A translations file without readme_sections falls back to the defaults."""
        trans_file = tmp_path / "translations.json"
        trans_file.write_text('{"quadrants": {}}', encoding="utf-8")
        settings = {"documentation": {"diataxis_translations": str(trans_file)}}
        assert (
            DocumentorSettings._resolve_required_sections(settings)
            == DocumentorSettings.DEFAULT_README_SECTIONS
        )

    def test_required_sections_is_a_tuple(self) -> None:
        """Frozen blocks rebinding; a list attribute would stay mutable through it."""
        assert isinstance(DocumentorSettings._resolve_required_sections({}), tuple)

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

    # --- rename window ---

    def test_rename_window_days_defaults_to_90(self) -> None:
        assert DocumentorSettings._resolve_rename_window_days({}) == 90

    def test_rename_window_days_from_settings(self) -> None:
        settings = {"documentation": {"rename_window_days": 30}}
        assert DocumentorSettings._resolve_rename_window_days(settings) == 30

    def test_rename_window_days_rejects_non_positive(self) -> None:
        assert (
            DocumentorSettings._resolve_rename_window_days(
                {"documentation": {"rename_window_days": 0}}
            )
            == 90
        )

    def test_rename_window_days_rejects_bool(self) -> None:
        settings = {"documentation": {"rename_window_days": True}}
        assert DocumentorSettings._resolve_rename_window_days(settings) == 90

    def test_rename_window_days_rejects_wrong_type(self) -> None:
        settings = {"documentation": {"rename_window_days": "30"}}
        assert DocumentorSettings._resolve_rename_window_days(settings) == 90

    def test_rename_window_reaches_the_struct(self) -> None:
        settings = DocumentorSettings.from_settings({"documentation": {"rename_window_days": 7}})
        assert settings.rename_window_days == 7
