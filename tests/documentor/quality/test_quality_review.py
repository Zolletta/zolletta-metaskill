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
from zolletta_metaskill.documentor.structs import DocumentationInventory
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
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
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
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
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

    # --- _required_sections ---

    def test_required_sections_applies_to_the_readme_document(self) -> None:
        """The README is the one document scored against README sections."""
        inventory = DocumentationInventory(root_documents={"readme": "README.md"})
        settings = DocumentorSettings.from_settings(self._settings(readme_sections=["usage"]))
        assert QualityReview._required_sections(inventory, settings, "README.md") == ["usage"]

    def test_required_sections_skip_a_root_document_that_is_not_a_readme(self) -> None:
        """AGENTS.md is a document, but not a README, so no sections apply."""
        inventory = DocumentationInventory(root_documents={"agents": "AGENTS.md"})
        settings = DocumentorSettings.from_settings(self._settings(readme_sections=["usage"]))
        assert QualityReview._required_sections(inventory, settings, "AGENTS.md") == []

    def test_required_sections_skip_a_file_inside_the_docs_dir(self) -> None:
        """A file under documentation.dir is documentation, not a kind of one."""
        inventory = DocumentationInventory(documentation=("docs/index.md",))
        settings = DocumentorSettings.from_settings(self._settings(readme_sections=["usage"]))
        assert QualityReview._required_sections(inventory, settings, "docs/index.md") == []

    # --- run(): code file discovery and doc mapping ---

    def test_run_counts_docs_dir_and_root_documents_together(self, tmp_path: Path) -> None:
        """Discovery is documentation.dir plus the root documents, and nothing else."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with p[0], p[1], p[2], p[3], p[4]:
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        data = self._read_cache(cache_dir)
        assert data["summary"]["total_docs"] == 2
        assert sorted(d["file"] for d in data["documents"]) == ["README.md", "docs/guide.md"]

    def test_run_ignores_markdown_outside_docs_and_root_documents(self, tmp_path: Path) -> None:
        """Markdown that is not documentation is not scored as if it were."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        (tmp_path / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        (tmp_path / "skills" / "one").mkdir(parents=True)
        (tmp_path / "skills" / "one" / "SKILL.md").write_text("# Skill\n")
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with p[0], p[1], p[2], p[3], p[4]:
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        data = self._read_cache(cache_dir)
        assert data["summary"]["total_docs"] == 1
        assert data["documents"][0]["file"] == "README.md"

    def test_run_reports_a_configured_docs_dir_that_is_missing(self, tmp_path: Path) -> None:
        """A misconfigured documentation.dir is reported, not silently a zero."""
        cache_dir = tmp_path / "cache"
        settings: dict[str, object] = {"language": "python", "documentation": {"dir": "manual"}}
        QualityReview.run(str(tmp_path), settings, cache_dir)
        data = self._read_cache(cache_dir)
        assert data["summary"]["total_docs"] == 0
        assert data["skipped_reason"] == "documentation.dir 'manual' is not a directory"

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
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={"README.md": []}),
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]) as mock_detect,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert mock_detect.call_args.args[2] == "README.md"
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

        def fake_cache_dir(s: dict[str, Any]) -> Path:
            assert s is settings
            return cache_dir

        monkeypatch.setattr(DocumentorSettings, "resolve_cache_dir", fake_cache_dir)
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
        assert captured.out == json.dumps(payload, indent=2) + "\n"

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

    # --- Mutation-driven gaps in ``run`` orchestration. ---

    def test_no_docs_empty_record_exact_payload(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        data = self._read_cache(cache_dir)
        assert sorted(data) == [
            "documents",
            "issues",
            "repository",
            "scan_date",
            "skipped_reason",
            "summary",
        ]
        assert data["repository"] == str(tmp_path.resolve())
        assert data["scan_date"] is None
        assert data["summary"] == {
            "total_docs": 0,
            "aggregate_score": 0.0,
            "aggregate_label": "unknown",
            "drifted_docs": 0,
            "total_issues": 0,
            "by_severity": {},
            "by_category": {},
            "by_fix_type": {},
        }
        assert data["skipped_reason"] == "No documentation files found"

    def test_no_docs_cache_file_is_indented_with_trailing_newline(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        text = (cache_dir / "quality.json").read_text()
        assert text.endswith("\n")
        assert '\n  "repository"' in text

    def test_run_creates_nested_cache_dir(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "deep" / "nested" / "cache"
        cache_path = QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert cache_path.exists()

    def test_readme_focus_absent_does_not_filter_docs(self, tmp_path: Path) -> None:
        """Without the setting, non-README docs are scored too."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with p[0], p[1], p[2], p[3], p[4]:
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert self._read_cache(cache_dir)["summary"]["total_docs"] == 1

    def test_run_passes_repo_path_and_window_to_git_helpers(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        with (
            patch.object(GitHelper, "get_file_last_commit_date", return_value=None),
            patch.object(GitHelper, "get_latest_tag", return_value=None) as tag,
            patch.object(GitHelper, "get_files_changed_since", return_value=[]),
            patch.object(GitHelper, "get_renamed_files", return_value=[]) as renamed,
            patch.object(GitHelper, "get_code_changes_since", return_value=0),
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        renamed.assert_called_once_with(str(tmp_path), "90 days ago")
        tag.assert_called_with(str(tmp_path))

    def test_run_empty_source_dirs_scans_repo_root(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(ProjectConfig, "existing_roots", return_value=[]),
            patch.object(DocCodeMapper, "find_code_files", return_value=[]) as mock_files,
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={}),
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        mock_files.assert_called_once_with(str(tmp_path), "")

    def test_run_find_code_files_gets_repo_path_and_scope(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(ProjectConfig, "existing_roots", return_value=[Path("src")]),
            patch.object(DocCodeMapper, "find_code_files", return_value=["a.py"]) as mock_files,
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={}),
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        mock_files.assert_called_once_with(str(tmp_path), "src")

    def test_run_source_roots_called_with_settings(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(ProjectConfig, "source_roots", return_value=[Path("src")]) as roots,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert roots.call_args.args == (self._settings(), {"python"})

    def test_run_git_run_context_carries_repo_renames_and_version(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        with (
            patch.object(GitHelper, "get_file_last_commit_date", return_value=None),
            patch.object(GitHelper, "get_latest_tag", return_value="v2.0") as tag,
            patch.object(GitHelper, "get_files_changed_since", return_value=[]),
            patch.object(GitHelper, "get_renamed_files", return_value=[("old.md", "new.md")]),
            patch.object(GitHelper, "get_code_changes_since", return_value=0),
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]) as detect,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        ctx = detect.call_args.args[0]
        assert ctx.repo_root == str(tmp_path)
        assert ctx.renames == (("old.md", "new.md"),)
        assert ctx.current_version == "v2.0"
        assert tag.call_args_list
        assert all(c.args == (str(tmp_path),) for c in tag.call_args_list)

    def test_run_associated_dirs_come_from_doc_code_map(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={"README.md": ["pkg"]}),
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]) as detect,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert detect.call_args.args[3] == ["pkg"]

    def test_run_missing_doc_key_falls_back_to_root_scope(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DocCodeMapper, "map_docs_to_code", return_value={}),
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=[]) as detect,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert detect.call_args.args[3] == [""]

    def test_run_score_document_receives_configured_quadrants(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(
                QualityScorer,
                "score_document",
                return_value={
                    "file": "README.md",
                    "total_score": 50.0,
                    "label": "fair",
                    "dimensions": {},
                },
            ) as score,
        ):
            QualityReview.run(str(tmp_path), self._settings(), cache_dir)
        assert (
            score.call_args.args[4] == DocumentorSettings.from_settings(self._settings()).quadrants
        )

    def test_min_severity_boundary_keeps_equal_and_drops_lower(self, tmp_path: Path) -> None:
        """``<=`` matters: an issue at exactly min_severity is kept, one below dropped."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        issues = [
            {"file": "README.md", "severity": "low", "description": "below"},
            {"file": "README.md", "severity": "medium", "description": "at"},
            {"file": "README.md", "severity": "high", "description": "above"},
        ]
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=issues),
            patch.object(
                QualityScorer,
                "score_document",
                return_value={
                    "file": "README.md",
                    "total_score": 50.0,
                    "label": "fair",
                    "dimensions": {},
                },
            ),
        ):
            QualityReview.run(str(tmp_path), self._settings(min_severity="medium"), cache_dir)
        kept = [i["description"] for i in self._read_cache(cache_dir)["issues"]]
        assert kept == ["at", "above"]

    def test_issue_missing_severity_defaults_to_info_and_is_filtered(self, tmp_path: Path) -> None:
        """A dict without ``severity`` counts as ``info`` — the .get() default is observable."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        issues = [
            {"file": "README.md", "description": "no severity key"},
            {"file": "README.md", "severity": "high", "description": "kept"},
        ]
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=issues),
            patch.object(
                QualityScorer,
                "score_document",
                return_value={
                    "file": "README.md",
                    "total_score": 50.0,
                    "label": "fair",
                    "dimensions": {},
                },
            ),
        ):
            QualityReview.run(str(tmp_path), self._settings(min_severity="medium"), cache_dir)
        kept = [i["description"] for i in self._read_cache(cache_dir)["issues"]]
        assert kept == ["kept"]

    def test_unknown_severity_string_falls_past_every_threshold(self, tmp_path: Path) -> None:
        """An unmapped severity resolves through the 99 sentinel — always filtered out."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        issues = [
            {"file": "README.md", "severity": "bogus", "description": "unmapped"},
            {"file": "README.md", "severity": "info", "description": "kept"},
        ]
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=issues),
            patch.object(
                QualityScorer,
                "score_document",
                return_value={
                    "file": "README.md",
                    "total_score": 50.0,
                    "label": "fair",
                    "dimensions": {},
                },
            ),
        ):
            QualityReview.run(str(tmp_path), self._settings(min_severity="info"), cache_dir)
        kept = [i["description"] for i in self._read_cache(cache_dir)["issues"]]
        assert kept == ["kept"]

    def test_main_json_payload_passes_settings_and_repo_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        payload = {"summary": {"total_issues": 0, "total_docs": 0}}
        with (
            patch.object(
                QualityReview, "run", return_value=tmp_path / "cache" / "quality.json"
            ) as run,
            patch.object(ProjectConfig, "load_settings", return_value={"language": "python"}),
            patch.object(
                __import__(
                    "zolletta_metaskill.documentor.utils.documentor_settings",
                    fromlist=["DocumentorSettings"],
                ).DocumentorSettings,
                "resolve_cache_dir",
                return_value=tmp_path / "cache",
            ),
        ):
            monkeypatch.chdir(tmp_path)
            monkeypatch.setattr(sys, "argv", ["quality_review.py", "--json"])
            (tmp_path / "cache").mkdir()
            (tmp_path / "cache" / "quality.json").write_text(json.dumps(payload))
            assert QualityReview.main() == 0
        run.assert_called_once_with(str(tmp_path), {"language": "python"}, tmp_path / "cache")

    def test_min_severity_info_keeps_unkeyed_issue(self, tmp_path: Path) -> None:
        """Severity-less issue is kept at ``min_severity='info'`` (kills ``get`` defaults)."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        issues = [{"file": "README.md", "description": "no sev key"}]
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=issues),
            patch.object(
                QualityScorer,
                "score_document",
                return_value={
                    "file": "README.md",
                    "total_score": 50.0,
                    "label": "fair",
                    "dimensions": {},
                },
            ),
        ):
            QualityReview.run(str(tmp_path), self._settings(min_severity="info"), cache_dir)
        kept = [i["description"] for i in self._read_cache(cache_dir)["issues"]]
        assert kept == ["no sev key"]

    def test_unknown_min_severity_defaults_to_low_and_drops_info(self, tmp_path: Path) -> None:
        """Unmapped ``min_severity`` falls back to low and drops an info issue."""
        (tmp_path / "README.md").write_text("# Installation\n\n" + "content\n" * 15)
        cache_dir = tmp_path / "cache"
        issues = [
            {"file": "README.md", "severity": "info", "description": "dropped"},
            {"file": "README.md", "severity": "low", "description": "kept"},
        ]
        p = self._patch_git()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch.object(DriftDetector, "detect_drift_for_doc", return_value=issues),
            patch.object(
                QualityScorer,
                "score_document",
                return_value={
                    "file": "README.md",
                    "total_score": 50.0,
                    "label": "fair",
                    "dimensions": {},
                },
            ),
        ):
            QualityReview.run(str(tmp_path), self._settings(min_severity="bogus"), cache_dir)
        kept = [i["description"] for i in self._read_cache(cache_dir)["issues"]]
        assert kept == ["kept"]

    def test_main_prints_defaults_when_summary_keys_absent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Missing ``summary``/keys print the 0-defaults — kills the .get() mutants."""
        payload: dict[str, Any] = {"documents": [], "issues": []}
        self._patch_main(monkeypatch, tmp_path, payload, {"language": "python"}, ["x.py"])
        assert QualityReview.main() == 0
        out = capsys.readouterr().out
        assert "0 drift issue(s) across 0 doc(s)" in out
