"""Tests for quality_review.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.quality.drift_detector import DriftDetector
from zolletta_metaskill.documentor.quality.quality_review import QualityReview
from zolletta_metaskill.documentor.quality.quality_scorer import QualityScorer
from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class TestQualityReview:
    def _settings(self, **doc_overrides: object) -> dict[str, object]:
        """Return a minimal settings dict with ``documentation`` overrides."""
        settings: dict[str, object] = {"language": "python", "documentation": {}}
        doc = settings["documentation"]
        assert isinstance(doc, dict)
        doc.update(doc_overrides)
        return settings

    def _patch_git(self) -> tuple[Any, ...]:
        """Patch GitHelper so no real git history is needed."""
        return (
            patch.object(GitHelper, "get_file_last_commit_date", return_value=None),
            patch.object(GitHelper, "get_latest_tag", return_value=None),
            patch.object(GitHelper, "get_files_changed_since", return_value=[]),
            patch.object(GitHelper, "get_renamed_files", return_value=[]),
            patch.object(GitHelper, "get_code_changes_since", return_value=0),
        )

    def _read_cache(self, cache_dir: Path) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads((cache_dir / "quality.json").read_text()))

    def test_no_docs_writes_empty_record(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        data = self._read_cache(cache_dir)
        assert data["summary"]["total_docs"] == 0
        assert data["summary"]["aggregate_score"] == 0.0
        assert data["documents"] == []
        assert data["skipped_reason"] == "No documentation files found"

    def test_doc_present_writes_scored_document(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n# Usage\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with p[0], p[1], p[2], p[3], p[4]:
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        data = self._read_cache(cache_dir)
        assert data["summary"]["total_docs"] == 1
        assert "aggregate_score" in data["summary"]
        assert data["documents"][0]["file"] == "README.md"

    def test_readme_focus_setting(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        (tmp_path / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        score = {
            "file": "README.md",
            "total_score": 50.0,
            "label": "fair",
            "dimensions": {},
        }
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(QualityScorer, "score_document", return_value=score) as mock_score,
        ):
            QualityReview.run(
                str(tmp_path),
                self._settings(readme_focus=True),
                cache_dir,
            )
        assert mock_score.call_count == 1

    def test_readme_sections_override_translations(self, tmp_path: Path) -> None:
        """Explicit readme_sections win over the translations file's."""
        trans = tmp_path / "trans.json"
        trans.write_text(json.dumps({"readme_sections": ["installazione", "utilizzo"]}))
        (tmp_path / "README.md").write_text("# Foo\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        score = {
            "file": "README.md",
            "total_score": 50.0,
            "label": "fair",
            "dimensions": {},
        }
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(QualityScorer, "score_document", return_value=score) as mock_score,
        ):
            QualityReview.run(
                str(tmp_path),
                self._settings(
                    diataxis_translations=str(trans),
                    readme_sections=["Foo"],
                ),
                cache_dir,
            )
        assert mock_score.call_args.args[3] == ["Foo"]

    def test_custom_weights_setting(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        score = {
            "file": "README.md",
            "total_score": 50.0,
            "label": "fair",
            "dimensions": {},
        }
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(QualityScorer, "score_document", return_value=score) as mock_score,
        ):
            QualityReview.run(
                str(tmp_path),
                self._settings(
                    staleness_weights={
                        "last_updated": 0.5,
                        "code_doc_alignment": 0.5,
                        "link_health": 0.2,
                        "completeness": 0.2,
                        "accuracy": 0.2,
                    }
                ),
                cache_dir,
            )
        weights = mock_score.call_args.args[2]
        # Weights are normalized to sum to 1 (total here is 1.6)
        assert weights["last_updated"] == pytest.approx(0.5 / 1.6)

    def test_include_referential_setting(self, tmp_path: Path) -> None:
        """include_referential is forwarded to DriftDetector."""
        (tmp_path / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]) as mock_detect,
        ):
            QualityReview.run(
                str(tmp_path),
                self._settings(include_referential=True),
                cache_dir,
            )
        doc_settings: DocumentorSettings = mock_detect.call_args.args[1]
        assert doc_settings.include_referential is True

    def test_min_severity_filters_issues(self, tmp_path: Path) -> None:
        """Issues below min_severity are excluded from the cache report."""
        (tmp_path / "README.md").write_text("# Installation\n\n# Usage\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        # Structural README issues have low severity; min_severity=critical filters them out
        with p[0], p[1], p[2], p[3], p[4]:
            QualityReview.run(
                str(tmp_path),
                self._settings(min_severity="critical"),
                cache_dir,
            )
        data = self._read_cache(cache_dir)
        assert data["summary"]["total_issues"] == 0

    # --- _configured_doc_patterns ---

    def test_configured_doc_patterns_drops_non_string_entries(self) -> None:
        """Mixed lists keep only the string glob patterns."""
        settings = {
            "language": "python",
            "documentation": {"doc_patterns": ["*.md", 42, None, "*.rst"]},
        }
        assert QualityReview._configured_doc_patterns(settings) == ["*.md", "*.rst"]

    def test_configured_doc_patterns_returns_none_for_non_list(self) -> None:
        """A non-list ``doc_patterns`` value falls back to the default discovery."""
        settings = {"language": "python", "documentation": {"doc_patterns": "*.md"}}
        assert QualityReview._configured_doc_patterns(settings) is None

    def test_configured_doc_patterns_returns_none_when_unset(self) -> None:
        """Missing ``doc_patterns`` resolves to ``None``."""
        assert QualityReview._configured_doc_patterns({"language": "python"}) is None

    # --- run(): code file discovery and doc mapping ---

    def test_duplicate_code_files_across_scopes_are_deduplicated(self, tmp_path: Path) -> None:
        """Two scopes yielding the same code files contribute each file once."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"

        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(ProjectConfig, "existing_roots", return_value=[Path("src"), Path("lib")]),
            patch.object(DocCodeMapper, "find_code_files", return_value=["a.py", "b.py"]),
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={"README.md": [""]}) as m,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert m.call_args.args[2] == ["a.py", "b.py"]

    def test_empty_doc_mapping_falls_back_to_repository_root(self, tmp_path: Path) -> None:
        """An empty mapping for a doc falls back to the whole repository."""
        (tmp_path / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={"guide.md": []}),
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]) as mock_detect,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert mock_detect.call_args.args[2] == "guide.md"
        assert mock_detect.call_args.args[3] == [""]

    def test_unknown_min_severity_falls_back_to_info(self, tmp_path: Path) -> None:
        """An unknown ``min_severity`` string is mapped to the default rank."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]),
        ):
            QualityReview.run(str(tmp_path), self._settings(min_severity="nonsense"), cache_dir)
        assert self._read_cache(cache_dir)["summary"]["total_issues"] == 0

    # --- main() ---

    def _patch_main(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        payload: dict[str, Any],
        settings: dict[str, Any],
        argv: list[str],
    ) -> Path:
        """Patch main() collaborators and return the cache directory used."""
        cache_dir = tmp_path / "cache"

        def fake_run(repo_path: str, s: dict[str, Any], cd: Path) -> Path:
            cd.mkdir(parents=True, exist_ok=True)
            path = cd / "quality.json"
            path.write_text(json.dumps(payload))
            return path

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        monkeypatch.setattr(ProjectConfig, "load_settings", lambda: settings)
        monkeypatch.setattr(DocumentorSettings, "resolve_cache_dir", lambda s: cache_dir)
        monkeypatch.setattr(QualityReview, "run", fake_run)
        return cache_dir

    def test_main_prints_human_readable_summary(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The default output is a one-line aggregate summary plus the cache path."""
        payload = {
            "summary": {
                "aggregate_score": 72.5,
                "aggregate_label": "acceptable",
                "total_issues": 4,
                "total_docs": 3,
            },
            "documents": [],
            "issues": [],
        }
        cache_dir = self._patch_main(
            monkeypatch, tmp_path, payload, {"language": "python"}, ["quality_review.py"]
        )
        rc = QualityReview.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Aggregate score: 72.5/100 (acceptable)" in out
        assert "4 drift issue(s) across 3 doc(s)" in out
        assert f"Cache written to {cache_dir / 'quality.json'}" in out

    def test_main_json_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--json`` prints the cache payload verbatim."""
        payload = {"summary": {"aggregate_score": 10.0, "total_docs": 1}, "issues": []}
        self._patch_main(
            monkeypatch, tmp_path, payload, {"language": "python"}, ["quality_review.py", "--json"]
        )
        rc = QualityReview.main()
        assert rc == 0
        assert json.loads(capsys.readouterr().out) == payload

    def test_main_prints_skipped_reason(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A skipped run prints the reason instead of the aggregate line."""
        payload = {"summary": {}, "documents": [], "issues": [], "skipped_reason": "nothing here"}
        cache_dir = self._patch_main(
            monkeypatch, tmp_path, payload, {"language": "python"}, ["quality_review.py"]
        )
        rc = QualityReview.main()
        out = capsys.readouterr().out
        assert rc == 0
        cache_path = cache_dir / "quality.json"
        assert out.splitlines() == ["nothing here", f"Cache written to {cache_path}"]

    def test_main_threshold_failure_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A score below ``staleness_threshold`` exits 1 and explains on stderr."""
        payload = {"summary": {"aggregate_score": 42.0, "aggregate_label": "poor"}}
        settings = {
            "language": "python",
            "documentation": {"staleness_threshold": 90},
        }
        self._patch_main(monkeypatch, tmp_path, payload, settings, ["quality_review.py"])
        rc = QualityReview.main()
        captured = capsys.readouterr()
        assert rc == 1
        assert "FAILED: Aggregate score 42.0 is below threshold 90.0" in captured.err
        assert "FAILED" not in captured.out

    def test_main_threshold_failure_json_is_quiet(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--json`` suppresses the stderr failure message but still exits 1."""
        payload = {"summary": {"aggregate_score": 42.0}}
        settings = {
            "language": "python",
            "documentation": {"staleness_threshold": 90},
        }
        self._patch_main(monkeypatch, tmp_path, payload, settings, ["quality_review.py", "--json"])
        rc = QualityReview.main()
        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err == ""
        assert json.loads(captured.out) == payload

    def test_main_score_above_threshold_returns_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A score at or above the threshold exits 0."""
        payload = {"summary": {"aggregate_score": 90.0, "aggregate_label": "good"}}
        settings = {
            "language": "python",
            "documentation": {"staleness_threshold": 90},
        }
        self._patch_main(monkeypatch, tmp_path, payload, settings, ["quality_review.py"])
        rc = QualityReview.main()
        assert rc == 0
        assert capsys.readouterr().err == ""

    def test_main_without_threshold_returns_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An unconfigured threshold never fails the run."""
        payload = {"summary": {"aggregate_score": 1.0}}
        self._patch_main(
            monkeypatch, tmp_path, payload, {"language": "python"}, ["quality_review.py"]
        )
        assert QualityReview.main() == 0

    def test_main_threshold_ignored_when_score_absent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A missing aggregate score skips the threshold comparison."""
        payload = {"skipped_reason": "nothing here"}
        settings = {
            "language": "python",
            "documentation": {"staleness_threshold": 90},
        }
        self._patch_main(monkeypatch, tmp_path, payload, settings, ["quality_review.py"])
        assert QualityReview.main() == 0

    def test_main_threshold_must_be_numeric(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A non-numeric threshold string is ignored rather than crashing."""
        payload = {"summary": {"aggregate_score": 1.0}}
        settings = {
            "language": "python",
            "documentation": {"staleness_threshold": "90"},
        }
        self._patch_main(monkeypatch, tmp_path, payload, settings, ["quality_review.py"])
        assert QualityReview.main() == 0
