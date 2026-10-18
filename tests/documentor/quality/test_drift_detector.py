"""Tests for drift_detector.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.quality.drift_detector import DriftDetector
from zolletta_metaskill.documentor.quality.structs import DocContext, GitRunContext
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class TestDriftDetector:
    # --- Context builders (DriftDetector takes resolved contexts, not loose args). ---

    @staticmethod
    def _settings(include_referential: bool = False) -> DocumentorSettings:
        return DocumentorSettings.from_settings(
            {
                "runs_dir": ".zolletta-metaskill",
                "documentation": {"include_referential": include_referential},
            }
        )

    @staticmethod
    def _git_ctx(
        repo_root: str,
        renames: tuple[tuple[str, str], ...] = (),
        current_version: str | None = None,
    ) -> GitRunContext:
        return GitRunContext(repo_root=repo_root, renames=renames, current_version=current_version)

    @staticmethod
    def _doc_ctx(
        file_rel_path: str,
        refs: dict[str, Any] | None = None,
        since_date: str = "2026-01-01",
        associated_code_dirs: tuple[str, ...] = (),
    ) -> DocContext:
        return DocContext(
            file_rel_path=file_rel_path,
            refs=refs or {},
            since_date=since_date,
            associated_code_dirs=associated_code_dirs,
        )

    @staticmethod
    def _patch_git(
        last_commit: datetime | None = None,
        changed: list[dict[str, str]] | None = None,
    ) -> tuple[Any, Any]:
        """Patch the two GitHelper reads ``detect_drift_for_doc`` makes.

        Twelve tests opened the same two-patch block, each spelling the patch
        target out again. The pair is the *fixture* the detector needs rather
        than the subject of any one test, so it is built once and each test
        states only the commit date and the changed files it cares about.
        """
        return (
            patch.object(GitHelper, "get_file_last_commit_date", return_value=last_commit),
            patch.object(GitHelper, "get_files_changed_since", return_value=changed or []),
        )

    # --- detect_drift_for_doc ---

    def test_no_git_history(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        p = self._patch_git(None)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        assert len(issues) == 1
        assert issues[0]["category"] == "temporal"
        assert issues[0]["severity"] == "info"

    def test_factual_drift_referenced_files(self, tmp_path: Path) -> None:
        (tmp_path / "auth.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `auth.py` for auth.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified, [{"status": "M", "file": "auth.py"}])
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "low"

    def test_factual_drift_high_severity(self, tmp_path: Path) -> None:
        for i in range(7):
            (tmp_path / f"mod{i}.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text(
            "See " + " ".join(f"`mod{i}.py`" for i in range(7)), encoding="utf-8"
        )
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified, [{"status": "M", "file": "mod0.py"}])
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "high"

    def test_now_temporal_staleness_returns_medium(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        old_date = datetime.now(UTC) - timedelta(days=200)
        p = self._patch_git(old_date)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        temporal = [
            i for i in issues if i["category"] == "temporal" and "not updated" in i["description"]
        ]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "medium"

    def test_now_version_drift_returns_1(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("Requires v1.0.0", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), "2.0.0"),
                self._settings(),
                "README.md",
                [],
            )
        version_issues = [i for i in issues if "version" in i["description"].lower()]
        assert len(version_issues) == 1

    def test_referential_rename_round_trip_is_not_flagged(self, tmp_path: Path) -> None:
        """A rename that was undone leaves the reference correct — not a finding.

        Git records ``old.py → new.py``, but ``old.py`` is back on disk and
        ``new.py`` is gone. That is a round trip, the way this repo renamed
        ``tests.yml → ci.yml`` and back. Reporting ``high`` here flagged a
        perfectly correct file.
        """
        (tmp_path / "old.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `old.py`", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (("old.py", "new.py"),), None),
                self._settings(include_referential=True),
                "README.md",
                [],
            )
        assert [i for i in issues if i["category"] == "referential"] == []

    def test_referential_rename_edge_case_is_still_high(self, tmp_path: Path) -> None:
        """The genuine stale case: the rename stuck *and* the old name is occupied.

        ``new.py`` exists, so the rename held, and ``old.py`` exists as a
        different file — a document pointing at ``old.py`` now points at the
        wrong thing. That must stay ``high``.
        """
        (tmp_path / "old.py").write_text("# a different file\n", encoding="utf-8")
        (tmp_path / "new.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `old.py`", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (("old.py", "new.py"),), None),
                self._settings(include_referential=True),
                "README.md",
                [],
            )
        ref_issues = [i for i in issues if i["category"] == "referential"]
        assert len(ref_issues) == 1
        assert ref_issues[0]["severity"] == "high"
        assert ref_issues[0]["fix_type"] == "manual"

    def test_readme_structure_check(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n\nSome content.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        structural = [i for i in issues if i["category"] == "structural"]
        assert len(structural) > 0

    def test_naive_datetime_handled(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        old_date = datetime(2020, 1, 1)  # naive
        p = self._patch_git(old_date)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        temporal = [
            i for i in issues if i["category"] == "temporal" and "not updated" in i["description"]
        ]
        assert len(temporal) == 1

    # --- _resolve_referenced_files ---

    def test_resolve_referenced_files_skips_non_code_extensions(self, tmp_path: Path) -> None:
        """Markdown references are ignored because they are not code extensions."""
        (tmp_path / "mod.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "guide.md").write_text("notes", encoding="utf-8")
        refs = {"files": ["guide.md", "mod.py"]}
        resolved = DriftDetector._resolve_referenced_files(
            self._git_ctx(str(tmp_path)), self._doc_ctx("README.md", refs)
        )
        assert resolved == ["mod.py"]

    def test_resolve_referenced_files_falls_back_to_repo_root(self, tmp_path: Path) -> None:
        """A ref missing next to the doc but present at the repo root still resolves."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (tmp_path / "mod.py").write_text("x = 1", encoding="utf-8")
        refs = {"files": ["mod.py"]}
        resolved = DriftDetector._resolve_referenced_files(
            self._git_ctx(str(tmp_path)), self._doc_ctx("docs/doc.md", refs)
        )
        assert resolved == ["mod.py"]

    # --- _check_factual_drift severity tiers ---

    def test_factual_drift_medium_severity_for_three_files(self, tmp_path: Path) -> None:
        """Three changed referenced files land in the medium severity tier."""
        for i in range(3):
            (tmp_path / f"mod{i}.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text(
            "See " + " ".join(f"`mod{i}.py`" for i in range(3)), encoding="utf-8"
        )
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified, [{"status": "M", "file": "mod0.py"}])
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                [],
            )
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "medium"
        assert factual[0]["details"]["change_count"] == 3

    # --- _check_factual_fallback ---

    def test_factual_fallback_flags_heavy_associated_code_changes(self, tmp_path: Path) -> None:
        """With no source refs, heavy changes in associated dirs produce a review issue."""
        (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        changes = [{"status": "M", "file": f"src/mod{i}.py"} for i in range(25)]
        p = self._patch_git(doc_modified, changes)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(),
                "README.md",
                ["src"],
            )
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "low"
        assert factual[0]["details"]["change_count"] == 25
        assert factual[0]["details"]["changed_dirs"] == ["src"]

    # --- referential mode ---

    def test_rename_drift_referential_mode_flags_removed_file(self, tmp_path: Path) -> None:
        """In referential mode a renamed-and-deleted file yields a medium issue."""
        (tmp_path / "README.md").write_text("See [old](old.py)", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (("old.py", "new.py"),), None),
                self._settings(include_referential=True),
                "README.md",
                [],
            )
        ref_issues = [i for i in issues if i["category"] == "referential"]
        assert len(ref_issues) == 2
        renames = [i for i in ref_issues if "was renamed to" in i["description"]]
        assert len(renames) == 1
        assert renames[0]["severity"] == "medium"
        assert renames[0]["fix_type"] == "auto"

    def test_referential_mode_flags_broken_refs(self, tmp_path: Path) -> None:
        """Referential mode also reports links to files that no longer exist."""
        (tmp_path / "README.md").write_text("See [gone](gone.md)", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        p = self._patch_git(doc_modified)
        with p[0], p[1]:
            issues = DriftDetector.detect_drift_for_doc(
                self._git_ctx(str(tmp_path), (), None),
                self._settings(include_referential=True),
                "README.md",
                [],
            )
        broken = [i for i in issues if "non-existent" in i["description"]]
        assert len(broken) == 1
        assert broken[0]["severity"] == "medium"
        assert broken[0]["description"] == "References non-existent file: gone.md"

    def test_broken_refs_existing_file_returns_empty_list(self, tmp_path: Path) -> None:
        """An existing reference produces no broken-ref issue."""
        (tmp_path / "here.md").write_text("notes", encoding="utf-8")
        issues = DriftDetector._check_broken_refs(
            self._git_ctx(str(tmp_path)),
            self._doc_ctx("README.md", {"files": ["here.md"]}),
        )
        assert issues == []

    def test_broken_refs_existing_at_repo_root_returns_empty_list(self, tmp_path: Path) -> None:
        """A reference that exists only at the repo root is not reported as broken."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (tmp_path / "top.md").write_text("notes", encoding="utf-8")
        issues = DriftDetector._check_broken_refs(
            self._git_ctx(str(tmp_path)),
            self._doc_ctx("docs/doc.md", {"files": ["top.md"]}),
        )
        assert issues == []

    # --- check_readme_structure ---

    def test_check_readme_structure_missing_sections_contains_license(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n\nSome text.", encoding="utf-8")
        issues = DriftDetector.check_readme_structure(
            self._git_ctx(str(tmp_path)), self._doc_ctx("README.md")
        )
        sections = {i["description"].split(": ")[-1] for i in issues}
        assert "Installation" in sections
        assert "Usage" in sections
        assert "License" in sections

    def test_all_sections_present(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation\n## Usage\n## License\n", encoding="utf-8"
        )
        issues = DriftDetector.check_readme_structure(
            self._git_ctx(str(tmp_path)), self._doc_ctx("README.md")
        )
        assert len(issues) == 0

    def test_check_readme_structure_partial_match_returns_0(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation Guide\n## Usage Guide\n## License Info\n",
            encoding="utf-8",
        )
        issues = DriftDetector.check_readme_structure(
            self._git_ctx(str(tmp_path)), self._doc_ctx("README.md")
        )
        assert len(issues) == 0

    def test_check_readme_structure_unreadable_file_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            issues = DriftDetector.check_readme_structure(
                self._git_ctx(str(tmp_path)), self._doc_ctx("README.md")
            )
        assert issues == []

    # --- _check_temporal_drift severity tiers ---

    @pytest.mark.parametrize(
        ("days_ago", "naive", "expected_severity"),
        [
            pytest.param(10, False, None, id="recent_doc_has_no_issue"),
            pytest.param(180, False, None, id="exactly_180_days_has_no_issue"),
            pytest.param(181, False, "medium", id="just_past_180_days_is_medium"),
            pytest.param(365, False, "medium", id="exactly_365_days_stays_medium"),
            pytest.param(366, False, "high", id="past_365_days_is_high"),
            pytest.param(200, True, "medium", id="naive_datetime_is_utc"),
        ],
    )
    def test_temporal_drift_age_returns_expected_severity(
        self, days_ago: int, naive: bool, expected_severity: str | None
    ) -> None:
        """The 180- and 365-day boundaries are exclusive; a naive datetime is UTC."""
        when = datetime.now(UTC) - timedelta(days=days_ago)
        if naive:
            when = when.replace(tzinfo=None)
        issues = DriftDetector._check_temporal_drift(
            self._doc_ctx("README.md", since_date="2026-01-01"), when
        )
        if expected_severity is None:
            assert issues == []
            return
        assert len(issues) == 1
        assert issues[0]["severity"] == expected_severity

    # --- _parse_version_part / _version_is_older ---

    def test_parse_version_part_parse_numeric_returns_10(self) -> None:
        assert DriftDetector._parse_version_part("10") == 10

    def test_parse_with_suffix(self) -> None:
        assert DriftDetector._parse_version_part("2alpha") == 2

    def test_parse_version_part_parse_empty_returns_0(self) -> None:
        assert DriftDetector._parse_version_part("") == 0

    def test_parse_non_numeric(self) -> None:
        assert DriftDetector._parse_version_part("abc") == 0

    @pytest.mark.parametrize(
        ("v1", "v2", "expected"),
        [
            pytest.param("1.0.0", "2.0.0", True, id="older_version_is_true"),
            pytest.param("2.0.0", "1.0.0", False, id="newer_version_is_false"),
            pytest.param("1.0.0", "1.0.0", False, id="equal_version_is_false"),
            pytest.param("1.0", "1.0.1", True, id="shorter_first_is_true"),
            pytest.param("1.0.1", "1.0", False, id="shorter_second_is_false"),
            pytest.param("1.0.0-alpha", "1.0.0", False, id="prerelease_is_false"),
            pytest.param("", "1.0.0", True, id="empty_string_is_true"),
        ],
    )
    def test_version_is_older_pair_returns_expected(self, v1: str, v2: str, expected: bool) -> None:
        """An empty version parses to ``[0]``, so it is older than every release."""
        assert DriftDetector._version_is_older(v1, v2) is expected
