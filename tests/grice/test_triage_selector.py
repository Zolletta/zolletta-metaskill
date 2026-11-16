"""Tests for triage_selector.py."""

from __future__ import annotations

from zolletta_metaskill.grice.diagnosis_engine import DiagnosisEngine
from zolletta_metaskill.grice.structs import BenchmarkEntry, MaximScores
from zolletta_metaskill.grice.triage_selector import TriageSelector


def _row(path: str, index: float | None) -> MaximScores:
    return MaximScores(path, index, index, index, index, group="g")


def _profile(
    path: str,
    scores: tuple[float | None, float | None, float | None, float | None],
    group: str = "g",
) -> MaximScores:
    return MaximScores(path, *scores, group=group)


CORPUS = (
    _row("e.md", 80.0),
    _row("a.md", 30.0),
    _row("b.md", 39.96),
    _row("c.md", 30.0),
    _row("d.md", 60.0),
    _row("f.md", 80.0),
    _row("n.md", None),
)

GROUP = (
    _profile("bal-low.md", (62.0, 62.0, 62.0, 62.0)),
    _profile("bal-high.md", (65.0, 65.0, 65.0, 65.0)),
    _profile("qty.md", (95.0, 40.0, 40.0, 40.0)),
    _profile("rel.md", (40.0, 40.0, 90.0, 90.0)),
    _profile("weak.md", (90.0, 10.0, 10.0, 10.0)),
)


def _slots(entries: tuple[BenchmarkEntry, ...]) -> list[tuple[str, list[str]]]:
    return [(e.scores.path, [s.code for s in e.strengths]) for e in entries]


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

    def test_benchmarks_group_returns_balanced_then_top_per_maxim(self) -> None:
        assert _slots(TriageSelector.benchmarks(GROUP, 40.0)) == [
            ("bal-high.md", ["balanced", "strong_quality"]),
            ("qty.md", ["strong_quantity"]),
            ("rel.md", ["strong_relation", "strong_manner"]),
        ]

    def test_benchmarks_balanced_slot_carries_the_strength_reading(self) -> None:
        (first, *_) = TriageSelector.benchmarks(GROUP, 40.0)
        assert first.strengths[0] == DiagnosisEngine.strength(first.scores)
        assert first.strengths[1] == DiagnosisEngine.strong("quality")

    def test_benchmarks_outlier_never_wins_a_slot(self) -> None:
        paths = [e.scores.path for e in TriageSelector.benchmarks(GROUP, 40.0)]
        assert "weak.md" not in paths

    def test_benchmarks_no_balanced_document_leaves_that_slot_empty(self) -> None:
        group = (
            _profile("x.md", (70.0, 50.0, 50.0, 50.0)),
            _profile("y.md", (50.0, 70.0, 50.0, 50.0)),
        )
        assert _slots(TriageSelector.benchmarks(group, 40.0)) == [
            ("x.md", ["strong_quantity", "strong_relation", "strong_manner"]),
            ("y.md", ["strong_quality"]),
        ]

    def test_benchmarks_tied_maxim_breaks_on_index_then_path(self) -> None:
        group = (
            _profile("b.md", (80.0, 50.0, 50.0, 50.0)),
            _profile("a.md", (80.04, 50.0, 50.0, 50.0)),
            _profile("c.md", (80.0, 60.0, 60.0, 60.0)),
        )
        (top_quantity, *_) = TriageSelector.benchmarks(group, 40.0)
        assert top_quantity.scores.path == "c.md"
        assert TriageSelector.benchmarks(group[:2], 40.0)[0].scores.path == "a.md"

    def test_benchmarks_unmeasured_maxim_has_no_winner(self) -> None:
        group = (_profile("x.md", (70.0, None, None, None)),)
        assert _slots(TriageSelector.benchmarks(group, 40.0)) == [("x.md", ["strong_quantity"])]

    def test_benchmarks_only_outliers_returns_empty_tuple(self) -> None:
        assert TriageSelector.benchmarks(CORPUS, 100.0) == ()

    def test_benchmarks_rounded_index_at_threshold_is_a_candidate(self) -> None:
        assert TriageSelector.benchmarks((_row("b.md", 39.96),), 40.0)[0].scores.path == "b.md"

    # --- by_group ---

    def test_by_group_splits_outliers_and_benchmarks_in_group_order(self) -> None:
        documents = (
            _profile("r.md", (70.0, 70.0, 70.0, 70.0), group="(root)"),
            _profile("z/a.md", (10.0, 10.0, 10.0, 10.0), group="z"),
            _profile("a/b.md", (70.0, 50.0, 50.0, 50.0), group="a"),
            _profile("a/c.md", (20.0, 20.0, 20.0, 20.0), group="a"),
        )
        outliers = TriageSelector.outliers(documents, 40.0)
        triage = TriageSelector.by_group(documents, outliers, 40.0)
        assert [group.name for group in triage] == ["a", "z", "(root)"]
        assert [[e.scores.path for e in group.outliers] for group in triage] == [
            ["a/c.md"],
            ["z/a.md"],
            [],
        ]
        assert [_slots(group.benchmarks) for group in triage] == [
            [("a/b.md", ["strong_quantity", "strong_quality", "strong_relation", "strong_manner"])],
            [],
            [
                (
                    "r.md",
                    [
                        "balanced",
                        "strong_quantity",
                        "strong_quality",
                        "strong_relation",
                        "strong_manner",
                    ],
                )
            ],
        ]
