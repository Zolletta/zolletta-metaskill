"""Tests for triage_selector.py."""

from __future__ import annotations

from zolletta_metaskill.grice.diagnosis_engine import DiagnosisEngine
from zolletta_metaskill.grice.structs import MaximScores
from zolletta_metaskill.grice.triage_selector import TriageSelector


def _row(path: str, index: float | None) -> MaximScores:
    return MaximScores(path, index, index, index, index, group="g")


CORPUS = (
    _row("e.md", 80.0),
    _row("a.md", 30.0),
    _row("b.md", 39.96),
    _row("c.md", 30.0),
    _row("d.md", 60.0),
    _row("f.md", 80.0),
    _row("n.md", None),
)


class TestTriageSelector:
    # --- outliers ---

    def test_outliers_threshold_returns_rows_below_it_worst_first(self) -> None:
        outliers = TriageSelector.outliers(CORPUS, 40.0)
        assert [entry.scores.path for entry in outliers] == ["a.md", "c.md"]

    def test_outliers_each_entry_carries_its_diagnosis(self) -> None:
        (entry, _) = TriageSelector.outliers(CORPUS, 40.0)
        assert entry.diagnosis == DiagnosisEngine.diagnose(entry.scores)

    def test_outliers_raised_threshold_includes_rounded_boundary(self) -> None:
        outliers = TriageSelector.outliers(CORPUS, 40.1)
        assert [entry.scores.path for entry in outliers] == ["a.md", "c.md", "b.md"]

    # --- benchmarks ---

    def test_benchmarks_count_returns_best_first_ties_by_path(self) -> None:
        benchmarks = TriageSelector.benchmarks(CORPUS, 3, 40.0)
        assert [entry.scores.path for entry in benchmarks] == ["e.md", "f.md", "d.md"]
        assert benchmarks[0].diagnosis == DiagnosisEngine.strength(benchmarks[0].scores)

    def test_benchmarks_large_count_never_includes_outliers(self) -> None:
        benchmarks = TriageSelector.benchmarks(CORPUS, 10, 40.0)
        assert [entry.scores.path for entry in benchmarks] == ["e.md", "f.md", "d.md", "b.md"]

    def test_benchmarks_zero_count_returns_empty_tuple(self) -> None:
        assert TriageSelector.benchmarks(CORPUS, 0, 40.0) == ()
