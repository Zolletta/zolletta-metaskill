"""Tests for quality_metrics.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from zolletta_metaskill.grice.markdown_corpus import MarkdownCorpus
from zolletta_metaskill.grice.quality_metrics import QualityMetrics


class TestQualityMetrics:
    # --- link_resolution ---

    def test_links_existing_target_returns_full_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "other.md").write_text("# Other\n")
        text = "# Index\n\nSee [other](other.md).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == pytest.approx(100.0)
        assert findings == []

    def test_links_missing_target_returns_zero_and_a_finding(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee [gone](gone.md).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == pytest.approx(0.0)
        assert len(findings) == 1
        assert findings[0].file == "docs/index.md"
        assert findings[0].line == 3
        assert findings[0].category == "grice"
        assert findings[0].severity == "medium"
        assert findings[0].description.startswith("internal link 'gone.md' does not resolve")

    def test_links_missing_anchor_returns_zero_and_a_finding(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee [nowhere](#nowhere).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == pytest.approx(0.0)
        assert len(findings) == 1
        assert findings[0].line == 3

    def test_links_one_broken_of_two_returns_half_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "other.md").write_text("# Other\n")
        text = "# Index\n\nSee [other](other.md) and [gone](gone.md).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == pytest.approx(50.0)
        assert len(findings) == 1

    def test_links_missing_target_finding_carries_the_error_detail(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee [gone](gone.md).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        _, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert findings[0].description == (
            "internal link 'gone.md' does not resolve: File not found: 'gone.md'"
        )

    def test_links_no_link_returns_full_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nNo links here.\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == 100.0
        assert findings == []

    def test_links_external_target_only_returns_full_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee [Python](https://python.org).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == 100.0
        assert findings == []

    def test_links_external_link_is_not_counted_toward_resolution(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee [gone](gone.md) and [Python](https://python.org).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["link_resolution"] == pytest.approx(0.0)

    # --- reference_resolution ---

    def test_references_existing_file_returns_full_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "api.md").write_text("# API\n")
        text = "# Index\n\nSee [api](api.md).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["reference_resolution"] == pytest.approx(100.0)

    def test_references_missing_code_path_returns_zero_without_a_finding(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee `gone.py`.\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, findings = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["reference_resolution"] == pytest.approx(0.0)
        assert findings == []

    def test_references_no_file_returns_full_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nSee [Python](https://python.org).\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["reference_resolution"] == 100.0

    def test_references_one_missing_of_two_returns_half_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "api.py").write_text("")
        text = "# Index\n\nSee `api.py` and `gone.py`.\n"
        (tmp_path / "docs" / "index.md").write_text(text)
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["reference_resolution"] == pytest.approx(50.0)

    # --- lexical_alignment ---

    def test_lexical_alignment_identical_source_returns_full_marks(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nrender invoice template\n"
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text),
            str(tmp_path),
            "render invoice template",
        )
        assert metrics["lexical_alignment"] == pytest.approx(100.0)

    def test_lexical_alignment_unrelated_source_returns_zero(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nrender invoice template\n"
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text),
            str(tmp_path),
            "binary heap allocator",
        )
        assert metrics["lexical_alignment"] == pytest.approx(0.0)

    def test_lexical_alignment_empty_source_returns_zero(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        text = "# Index\n\nrender invoice template\n"
        metrics, _ = QualityMetrics.evaluate(
            MarkdownCorpus.parse("docs/index.md", text), str(tmp_path), ""
        )
        assert metrics["lexical_alignment"] == 0.0

    # --- _is_file_reference ---

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            ("docs/api.md", True),
            ("#anchor", False),
            ("/absolute/path.py", False),
            ("https://example.com", False),
            ("mailto:dev@example.com", False),
            ("   ", False),
        ],
        ids=[
            "relative_path_is_a_file_reference",
            "anchor_is_not_a_file_reference",
            "absolute_path_is_not_a_file_reference",
            "https_url_is_not_a_file_reference",
            "mailto_target_is_not_a_file_reference",
            "blank_target_is_not_a_file_reference",
        ],
    )
    def test_is_file_reference_target_returns_expected(self, target: str, expected: bool) -> None:
        assert QualityMetrics._is_file_reference(target) is expected

    # --- _resolves ---

    def test_resolves_target_beside_document_returns_true(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "api.md").write_text("# API\n")
        assert QualityMetrics._resolves(str(tmp_path), "docs/index.md", "api.md") is True

    def test_resolves_target_at_repository_root_returns_true(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        assert QualityMetrics._resolves(str(tmp_path), "docs/index.md", "pyproject.toml") is True

    def test_resolves_target_under_source_tree_returns_true(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("")
        assert QualityMetrics._resolves(str(tmp_path), "docs/index.md", "module.py") is True

    def test_resolves_absent_target_returns_false(self, tmp_path: Path) -> None:
        assert QualityMetrics._resolves(str(tmp_path), "docs/index.md", "gone.md") is False

    def test_resolves_probes_repo_doc_and_source_roots_in_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        probed: list[str] = []

        def _probe(path: str) -> bool:
            probed.append(path)
            return False

        monkeypatch.setattr(os.path, "exists", _probe)
        assert QualityMetrics._resolves(str(tmp_path), "docs/index.md", "module.py") is False
        assert probed == [
            os.path.join(str(tmp_path), "module.py"),
            os.path.join(str(tmp_path), "docs", "module.py"),
            os.path.join(str(tmp_path), "src", "module.py"),
        ]
