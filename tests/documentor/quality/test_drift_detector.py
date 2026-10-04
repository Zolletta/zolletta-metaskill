"""Tests for drift_detector.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from zolletta_metaskill.documentor.quality.drift_detector import DriftDetector


class TestDriftDetector:
    # --- detect_drift_for_doc ---

    def test_no_git_history(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        with patch(
            "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
            return_value=None,
        ):
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        assert len(issues) == 1
        assert issues[0]["category"] == "temporal"
        assert issues[0]["severity"] == "info"

    def test_factual_drift_referenced_files(self, tmp_path: Path) -> None:
        (tmp_path / "auth.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `auth.py` for auth.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since"
            ) as mock_changed,
        ):
            mock_changed.return_value = [{"status": "M", "file": "auth.py"}]
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
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
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since"
            ) as mock_changed,
        ):
            mock_changed.return_value = [{"status": "M", "file": "mod0.py"}]
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "high"

    def test_now_temporal_staleness_returns_medium(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        old_date = datetime.now(UTC) - timedelta(days=200)
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=old_date,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        temporal = [
            i for i in issues if i["category"] == "temporal" and "not updated" in i["description"]
        ]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "medium"

    def test_now_version_drift_returns_1(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("Requires v1.0.0", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], "2.0.0")
        version_issues = [i for i in issues if "version" in i["description"].lower()]
        assert len(version_issues) == 1

    def test_referential_rename_edge_case(self, tmp_path: Path) -> None:
        (tmp_path / "old.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `old.py`", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = DriftDetector.detect_drift_for_doc(
                str(tmp_path), "README.md", [], [("old.py", "new.py")], None
            )
        ref_issues = [i for i in issues if i["category"] == "referential"]
        assert len(ref_issues) == 1
        assert ref_issues[0]["severity"] == "high"

    def test_readme_structure_check(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n\nSome content.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        structural = [i for i in issues if i["category"] == "structural"]
        assert len(structural) > 0

    def test_naive_datetime_handled(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        old_date = datetime(2020, 1, 1)  # naive
        with (
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_file_last_commit_date",
                return_value=old_date,
            ),
            patch(
                "zolletta_metaskill.documentor.quality.drift_detector.GitHelper.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = DriftDetector.detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        temporal = [
            i for i in issues if i["category"] == "temporal" and "not updated" in i["description"]
        ]
        assert len(temporal) == 1

    # --- check_readme_structure ---

    def test_check_readme_structure_missing_sections_contains_license(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n\nSome text.", encoding="utf-8")
        issues = DriftDetector.check_readme_structure(str(tmp_path), "README.md")
        sections = {i["description"].split(": ")[-1] for i in issues}
        assert "Installation" in sections
        assert "Usage" in sections
        assert "License" in sections

    def test_all_sections_present(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation\n## Usage\n## License\n", encoding="utf-8"
        )
        issues = DriftDetector.check_readme_structure(str(tmp_path), "README.md")
        assert len(issues) == 0

    def test_check_readme_structure_partial_match_returns_0(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation Guide\n## Usage Guide\n## License Info\n",
            encoding="utf-8",
        )
        issues = DriftDetector.check_readme_structure(str(tmp_path), "README.md")
        assert len(issues) == 0

    def test_check_readme_structure_unreadable_file_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            issues = DriftDetector.check_readme_structure(str(tmp_path), "README.md")
        assert issues == []

    # --- _parse_version_part / _version_is_older ---

    def test_parse_version_part_parse_numeric_returns_10(self) -> None:
        assert DriftDetector._parse_version_part("10") == 10

    def test_parse_with_suffix(self) -> None:
        assert DriftDetector._parse_version_part("2alpha") == 2

    def test_parse_version_part_parse_empty_returns_0(self) -> None:
        assert DriftDetector._parse_version_part("") == 0

    def test_parse_non_numeric(self) -> None:
        assert DriftDetector._parse_version_part("abc") == 0

    def test_version_is_older_older_version_returns_true(self) -> None:
        assert DriftDetector._version_is_older("1.0.0", "2.0.0") is True

    def test_version_is_older_newer_version_returns_false(self) -> None:
        assert DriftDetector._version_is_older("2.0.0", "1.0.0") is False

    def test_version_is_older_equal_version_returns_false(self) -> None:
        assert DriftDetector._version_is_older("1.0.0", "1.0.0") is False

    def test_version_is_older_different_lengths_returns_true(self) -> None:
        assert DriftDetector._version_is_older("1.0", "1.0.1") is True

    def test_v2_shorter_than_v1(self) -> None:
        assert DriftDetector._version_is_older("1.0.1", "1.0") is False

    def test_version_is_older_with_prerelease_returns_false(self) -> None:
        assert DriftDetector._version_is_older("1.0.0-alpha", "1.0.0") is False

    def test_empty_string_is_older(self) -> None:
        # Empty string parses to [0] which is older than [1, 0, 0]
        assert DriftDetector._version_is_older("", "1.0.0") is True
