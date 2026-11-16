"""Tests for group_summarizer.py."""

from __future__ import annotations

from zolletta_metaskill.grice.group_summarizer import GroupSummarizer
from zolletta_metaskill.grice.structs import (
    DefectLocation,
    Diagnosis,
    GroupSummary,
    MaximScores,
    StructuralDefect,
    TriageEntry,
)


def _row(path: str, group: str, index: float | None) -> MaximScores:
    return MaximScores(path, index, index, index, index, group=group)


def _defect(*groups: str) -> StructuralDefect:
    return StructuralDefect(
        id="G1",
        kind="broken_link",
        severity="medium",
        description="d",
        target="t",
        locations=tuple(DefectLocation(f"{group}.md", 1, group) for group in groups),
    )


class TestGroupSummarizer:
    # --- summarise ---

    def test_summarise_corpus_returns_one_row_per_group_root_last(self) -> None:
        documents = (
            _row("README.md", "(root)", 60.0),
            _row("docs/old/a.md", "old", 30.0),
            _row("docs/old/b.md", "old", 50.0),
            _row("docs/current/c.md", "current", 70.0),
            _row("docs/current/d.md", "current", None),
        )
        outlier = TriageEntry(documents[1], Diagnosis("uniform_deficit", "quantity", "", ""))
        defects = (_defect("old", "current", "old"), _defect("old"))
        assert GroupSummarizer.summarise(documents, (outlier,), defects) == (
            GroupSummary("current", 2, 70.0, 0, 1),
            GroupSummary("old", 2, 40.0, 1, 2),
            GroupSummary("(root)", 1, 60.0, 0, 0),
        )

    def test_summarise_empty_corpus_returns_no_rows(self) -> None:
        assert GroupSummarizer.summarise((), (), ()) == ()

    # --- median ---

    def test_median_unmeasured_values_are_ignored(self) -> None:
        assert GroupSummarizer.median([10.0, None, 30.0]) == 20.0

    def test_median_nothing_measured_returns_none(self) -> None:
        assert GroupSummarizer.median([None]) is None
