"""Tests for quality_review.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.quality.quality_review import QualityReview
from zolletta_metaskill.documentor.quality.quality_scorer import QualityScorer
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
        from zolletta_metaskill.documentor.quality.drift_detector import DriftDetector

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
        assert mock_detect.call_args.kwargs["include_referential"] is True

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
