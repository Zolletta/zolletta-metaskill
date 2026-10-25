"""Tests for doc_accuracy_scorer.py."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from zolletta_metaskill.documentor.quality.doc_accuracy_scorer import DocAccuracyScorer


class TestDocAccuracyScorer:
    # --- score_accuracy ---

    def test_score_accuracy_no_file_returns_50_0(self, tmp_path: Path) -> None:
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "nonexistent.md")
        assert score == 50.0

    def test_no_verifiable_facts(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nJust some text.\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 75.0

    def test_version_match_returns_100_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 1.2.3\n")
        score, details = DocAccuracyScorer.score_accuracy(
            str(tmp_path), "doc.md", latest_tag="1.2.3"
        )
        assert score == 100.0

    def test_version_mismatch_returns_0_0(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 0.9.0\n")
        score, details = DocAccuracyScorer.score_accuracy(
            str(tmp_path), "doc.md", latest_tag="1.2.3"
        )
        assert score == 0.0

    def test_manifest_version_match(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 1.0.0\n")
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 100.0

    def test_manifest_version_mismatch(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 0.9.0\n")
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 0.0
        assert any("FAIL" in c for c in details["checks"])

    def test_file_paths_valid(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("# code")
        (tmp_path / "doc.md").write_text("# Title\n\nSee `src/mod.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 100.0

    def test_file_paths_resolved_from_repo_root(self, tmp_path: Path) -> None:
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "doc.md").write_text("# Title\n\nSee `src/mod.py`.\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("# code")
        score, details = DocAccuracyScorer.score_accuracy(
            str(tmp_path), "docs/doc.md", latest_tag=None
        )
        assert score == 100.0

    def test_file_paths_broken(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nSee `src/missing.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 0.0

    def test_future_date_returns_0_0(self, tmp_path: Path) -> None:
        future = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%d")
        (tmp_path / "doc.md").write_text(f"# Title\n\nDate: {future}\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 0.0

    def test_valid_date_returns_100_0(self, tmp_path: Path) -> None:
        past = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
        (tmp_path / "doc.md").write_text(f"# Title\n\nDate: {past}\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 100.0

    def test_latest_tag_fallback_uses_git(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 1.2.3\n")
        with patch.object(DocAccuracyScorer, "get_latest_tag", return_value="1.2.3"):
            score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md")
            assert score == 100.0

    def test_score_accuracy_mixed_checks_returns_partial_score(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("# Title\n\nVersion 1.2.3\n\nSee `src/missing.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(
            str(tmp_path), "doc.md", latest_tag="1.2.3"
        )
        assert score == 50.0

    # --- get_latest_tag ---

    def test_get_latest_tag_success_returns_stripped_tag(self, tmp_path: Path) -> None:
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="v1.2.3\n", stderr=""
            )
            assert DocAccuracyScorer.get_latest_tag(str(tmp_path)) == "v1.2.3"
        mock_run.assert_called_once_with(
            ["git", "-C", str(tmp_path), "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_get_latest_tag_nonzero_returncode_ignores_stdout(self, tmp_path: Path) -> None:
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="v9.9.9\n", stderr=""
            )
            assert DocAccuracyScorer.get_latest_tag(str(tmp_path)) is None

    def test_get_latest_tag_returns_none_on_success_no_tag(self, tmp_path: Path) -> None:
        """A successful git call without tags yields None instead of an empty string."""
        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="   \n", stderr=""
            )
            assert DocAccuracyScorer.get_latest_tag(str(tmp_path)) is None

    def test_get_latest_tag_oserror_returns_none(self, tmp_path: Path) -> None:
        """A subprocess failure is swallowed and reported as no tag."""
        with patch.object(subprocess, "run", side_effect=OSError("no git")):
            assert DocAccuracyScorer.get_latest_tag(str(tmp_path)) is None

    # --- _version_refs ---

    def test_version_refs_mixed_forms_returns_all_versions(self) -> None:
        content = "v1.2 version: 3.4 V5.6.7\n"
        assert DocAccuracyScorer._version_refs(content) == ["1.2", "3.4", "5.6.7"]

    # --- _check_version_match ---

    def test_check_version_match_pass_details(self, tmp_path: Path) -> None:
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_version_match(
            str(tmp_path), "Version 1.2.3\n", details, "1.2.3"
        )
        assert result == (1.0, 1)
        assert details == {"checks": ["version_match: PASS"], "issues": []}

    def test_check_version_match_fail_details(self, tmp_path: Path) -> None:
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_version_match(
            str(tmp_path), "Version 0.9.0\n", details, "1.2.3"
        )
        assert result == (0.0, 1)
        assert details == {
            "checks": ["version_match: FAIL (doc has ['0.9.0'], git has 1.2.3)"],
            "issues": ["Version mismatch: doc=['0.9.0'], git=1.2.3"],
        }

    # --- _check_manifest_versions ---

    def test_check_manifest_versions_all_manifests_pass(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "t", "version": "1.0.0"}\n')
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        (tmp_path / "setup.py").write_text('setup(version="1.0.0")\n')
        (tmp_path / "Cargo.toml").write_text('version = "1.0.0"\n')
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_manifest_versions(
            str(tmp_path), "Version 1.0.0\n", details
        )
        assert result == (4.0, 4)
        assert details == {
            "checks": [
                "manifest_version (package.json): PASS",
                "manifest_version (pyproject.toml): PASS",
                "manifest_version (setup.py): PASS",
                "manifest_version (Cargo.toml): PASS",
            ],
            "issues": [],
        }

    def test_check_manifest_versions_no_doc_refs_skips_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_manifest_versions(
            str(tmp_path), "# Title\n\nNo versions here.\n", details
        )
        assert result == (0.0, 0)
        assert details == {"checks": [], "issues": []}

    def test_check_manifest_versions_mismatch_reports_exact_details(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('version = "1.0.0"\n')
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_manifest_versions(
            str(tmp_path), "Version 0.9.0\n", details
        )
        assert result == (0.0, 1)
        assert details == {
            "checks": ["manifest_version (pyproject.toml): FAIL (doc=['0.9.0'], manifest=1.0.0)"],
            "issues": ["Manifest version mismatch: pyproject.toml has 1.0.0"],
        }

    # --- _check_file_paths ---

    def test_file_paths_resolved_relative_to_doc_dir(self, tmp_path: Path) -> None:
        sub = tmp_path / "docs"
        (sub / "sub").mkdir(parents=True)
        (sub / "sub" / "mod.py").write_text("# code")
        (sub / "doc.md").write_text("# Title\n\nSee `sub/mod.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(
            str(tmp_path), "docs/doc.md", latest_tag=None
        )
        assert score == 100.0
        assert details["checks"] == ["file_paths: PASS (1/1)"]

    def test_file_paths_two_existing_refs_pass(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("# code")
        (tmp_path / "src" / "b.py").write_text("# code")
        (tmp_path / "doc.md").write_text("# Title\n\nSee `src/a.py` and `src/b.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 100.0
        assert details["checks"] == ["file_paths: PASS (2/2)"]

    def test_file_paths_two_root_refs_pass(self, tmp_path: Path) -> None:
        sub = tmp_path / "docs"
        sub.mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("# code")
        (tmp_path / "src" / "b.py").write_text("# code")
        (sub / "doc.md").write_text("# Title\n\nSee `src/a.py` and `src/b.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(
            str(tmp_path), "docs/doc.md", latest_tag=None
        )
        assert score == 100.0
        assert details["checks"] == ["file_paths: PASS (2/2)"]

    def test_file_paths_partial_reports_exact_details(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("# code")
        (tmp_path / "doc.md").write_text("# Title\n\nSee `src/a.py` and `src/missing.py`.\n")
        score, details = DocAccuracyScorer.score_accuracy(str(tmp_path), "doc.md", latest_tag=None)
        assert score == 50.0
        assert details == {
            "checks": ["file_paths: PARTIAL (1/2)"],
            "issues": ["1 referenced file paths not found"],
        }

    # --- _check_dates ---

    def test_check_dates_future_date_details(self) -> None:
        future = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%d")
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_dates(f"Date: {future}\n", details)
        assert result == (0.0, 1)
        assert details == {
            "checks": ["dates: FAIL"],
            "issues": [f"Future date found: {future}"],
        }

    def test_check_dates_past_date_details(self) -> None:
        past = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
        details: dict[str, list[str]] = {"checks": [], "issues": []}
        result = DocAccuracyScorer._check_dates(f"Date: {past}\n", details)
        assert result == (1.0, 1)
        assert details == {"checks": ["dates: PASS"], "issues": []}

    # --- _extract_version_from_manifest ---

    def test_extract_version_package_json(self, tmp_path: Path) -> None:
        p = tmp_path / "package.json"
        p.write_text('{"name": "test", "version": "1.2.3"}')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "package.json") == "1.2.3"

    def test_extract_version_pyproject_toml(self, tmp_path: Path) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text('[project]\nversion = "2.0.0"\n')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "pyproject.toml") == "2.0.0"

    def test_extract_version_setup_py(self, tmp_path: Path) -> None:
        p = tmp_path / "setup.py"
        p.write_text('setup(version="3.1.0")')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "setup.py") == "3.1.0"

    def test_extract_version_cargo_toml(self, tmp_path: Path) -> None:
        p = tmp_path / "Cargo.toml"
        p.write_text('[package]\nversion = "0.1.0"\n')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "Cargo.toml") == "0.1.0"

    def test_extract_version_no_version_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "package.json"
        p.write_text('{"name": "test"}')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "package.json") is None

    def test_extract_version_pyproject_no_version_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text('[project]\nname = "test"\n')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "pyproject.toml") is None

    def test_extract_version_setup_py_no_version_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "setup.py"
        p.write_text('setup(name="test")\n')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "setup.py") is None

    def test_extract_version_cargo_no_version_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "Cargo.toml"
        p.write_text('[package]\nname = "test"\n')
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "Cargo.toml") is None

    def test_extract_version_unknown_manifest_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "unknown.txt"
        p.write_text("nothing")
        assert DocAccuracyScorer._extract_version_from_manifest(str(p), "unknown.txt") is None

    def test_extract_version_oserror_returns_none(self, tmp_path: Path) -> None:
        assert (
            DocAccuracyScorer._extract_version_from_manifest(
                str(tmp_path / "nope.json"), "package.json"
            )
            is None
        )
