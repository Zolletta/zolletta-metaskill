"""Tests for grice_report.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.structs import GriceReport, MaximScores


class TestGriceReport:
    # --- corpus_size ---

    def test_corpus_size_empty_report_returns_zero(self) -> None:
        report = GriceReport(documents=(), findings=(), disabled_metrics=(), notes=())
        assert report.corpus_size == 0

    def test_corpus_size_two_documents_returns_two(self) -> None:
        report = GriceReport(
            documents=(
                MaximScores(path="a.md", quantity=1.0, quality=None, relation=None, manner=None),
                MaximScores(path="b.md", quantity=2.0, quality=None, relation=None, manner=None),
            ),
            findings=(),
            disabled_metrics=(),
            notes=(),
        )
        assert report.corpus_size == 2

    # --- corpus_index ---

    def test_corpus_index_measured_documents_returns_mean_of_document_indices(self) -> None:
        report = GriceReport(
            documents=(
                MaximScores(path="a.md", quantity=10.0, quality=10.0, relation=None, manner=None),
                MaximScores(path="b.md", quantity=30.0, quality=30.0, relation=None, manner=None),
            ),
            findings=(),
            disabled_metrics=(),
            notes=(),
        )
        assert report.corpus_index == 20.0

    def test_corpus_index_no_measured_document_returns_none(self) -> None:
        report = GriceReport(
            documents=(
                MaximScores(path="a.md", quantity=None, quality=None, relation=None, manner=None),
            ),
            findings=(),
            disabled_metrics=(),
            notes=(),
        )
        assert report.corpus_index is None

    def test_corpus_index_empty_report_returns_none(self) -> None:
        report = GriceReport(documents=(), findings=(), disabled_metrics=(), notes=())
        assert report.corpus_index is None

    # --- to_dict ---

    def test_to_dict_full_report_serializes_every_section(self) -> None:
        report = GriceReport(
            documents=(
                MaximScores(path="a.md", quantity=50.0, quality=50.0, relation=50.0, manner=50.0),
            ),
            findings=(
                Finding(
                    file="a.md",
                    line=7,
                    category="grice",
                    severity="low",
                    description="heading skips a level",
                ),
            ),
            disabled_metrics=("readability",),
            notes=("Indices are relative to this corpus.",),
        )
        payload = report.to_dict()
        assert payload["corpus_size"] == 1
        assert payload["corpus_index"] == 50.0
        assert payload["documents"] == [
            {
                "path": "a.md",
                "quantity": 50.0,
                "quality": 50.0,
                "relation": 50.0,
                "manner": 50.0,
                "grice_index": 50.0,
            }
        ]
        assert payload["findings"] == [
            {
                "file": "a.md",
                "line": 7,
                "category": "grice",
                "severity": "low",
                "description": "heading skips a level",
            }
        ]
        assert payload["disabled_metrics"] == ["readability"]
        assert payload["notes"] == ["Indices are relative to this corpus."]

    def test_to_dict_document_without_measured_maxim_keeps_null_index(self) -> None:
        report = GriceReport(
            documents=(
                MaximScores(path="a.md", quantity=None, quality=None, relation=None, manner=None),
            ),
            findings=(),
            disabled_metrics=(),
            notes=(),
        )
        assert report.to_dict()["documents"][0]["grice_index"] is None

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (49.94, 49.9),
            (49.95, 50.0),
            (0.0, 0.0),
            (100.0, 100.0),
        ],
        ids=[
            "raw_below_half_rounds_down",
            "raw_at_half_rounds_up",
            "raw_zero_stays_zero",
            "raw_hundred_stays_hundred",
        ],
    )
    def test_to_dict_corpus_index_rounds_to_one_decimal(self, raw: float, expected: float) -> None:
        report = GriceReport(
            documents=(
                MaximScores(path="a.md", quantity=raw, quality=None, relation=None, manner=None),
            ),
            findings=(),
            disabled_metrics=(),
            notes=(),
        )
        assert report.to_dict()["corpus_index"] == expected
