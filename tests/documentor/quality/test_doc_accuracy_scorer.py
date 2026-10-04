"""Tests for doc_accuracy_scorer.py."""

from __future__ import annotations

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
