"""Tests for diagnosis_engine.py."""

from __future__ import annotations

import pytest

from zolletta_metaskill.grice.diagnosis_engine import DiagnosisEngine
from zolletta_metaskill.grice.structs import MaximScores


def _row(
    quantity: float | None, quality: float | None, relation: float | None, manner: float | None
) -> MaximScores:
    return MaximScores("docs/a/x.md", quantity, quality, relation, manner, group="a")


class TestDiagnosisEngine:
    # --- diagnose ---

    @pytest.mark.parametrize(
        ("scores", "code", "maxim"),
        [
            ((39.6, 35.0, 32.9, 34.7), "uniform_deficit", "relation"),
            ((71.9, 33.6, 4.5, 39.2), "dense_isolated", "relation"),
            ((38.7, 61.8, 12.2, 33.2), "isolated", "relation"),
            ((67.6, 31.7, 28.8, 34.1), "verbose_unreferenced", "quality"),
            ((58.0, 33.6, 24.4, 41.1), "weak_relation", "relation"),
            ((39.7, 45.8, 38.8, 31.6), "weak_manner", "manner"),
            ((30.0, 55.0, 45.0, 45.0), "weak_quantity", "quantity"),
            ((55.0, 30.0, 45.0, 45.0), "weak_quality", "quality"),
        ],
        ids=[
            "all_low_is_uniform_deficit",
            "dense_and_unlinked_is_dense_isolated",
            "unlinked_is_isolated",
            "long_and_unreferenced_is_verbose_unreferenced",
            "lowest_relation_is_weak_relation",
            "lowest_manner_is_weak_manner",
            "lowest_quantity_is_weak_quantity",
            "lowest_quality_is_weak_quality",
        ],
    )
    def test_diagnose_profile_returns_first_matching_rule(
        self, scores: tuple[float, float, float, float], code: str, maxim: str
    ) -> None:
        diagnosis = DiagnosisEngine.diagnose(_row(*scores))
        assert (diagnosis.code, diagnosis.maxim) == (code, maxim)
        assert (diagnosis.summary, diagnosis.action) == DiagnosisEngine.OUTLIER_RULES[code]

    def test_diagnose_nothing_measured_returns_unmeasured(self) -> None:
        diagnosis = DiagnosisEngine.diagnose(_row(None, None, None, None))
        assert (diagnosis.code, diagnosis.maxim) == ("unmeasured", None)

    def test_diagnose_single_low_maxim_is_not_a_uniform_deficit(self) -> None:
        assert DiagnosisEngine.diagnose(_row(None, 30.0, None, None)).code == "weak_quality"

    def test_diagnose_tied_weakest_maxims_picks_the_first_in_maxim_order(self) -> None:
        assert DiagnosisEngine.diagnose(_row(45.0, 30.0, 50.0, 30.0)).maxim == "quality"

    def test_diagnose_unmeasured_relation_skips_the_isolation_rules(self) -> None:
        assert DiagnosisEngine.diagnose(_row(70.0, 50.0, None, 30.0)).code == "weak_manner"

    # --- strength ---

    def test_strength_every_maxim_high_returns_balanced(self) -> None:
        diagnosis = DiagnosisEngine.strength(_row(61.0, 70.0, 65.0, 62.0))
        assert (diagnosis.code, diagnosis.maxim) == ("balanced", "quality")
        assert diagnosis.summary == DiagnosisEngine.STRENGTHS["balanced"]
        assert diagnosis.action == DiagnosisEngine.BENCHMARK_ACTION

    def test_strength_one_dominant_maxim_returns_strong_maxim(self) -> None:
        diagnosis = DiagnosisEngine.strength(_row(50.0, 55.0, 48.0, 80.0))
        assert (diagnosis.code, diagnosis.maxim) == ("strong_manner", "manner")

    def test_strength_tied_strongest_maxims_picks_the_first_in_maxim_order(self) -> None:
        assert DiagnosisEngine.strength(_row(70.0, 50.0, 70.0, 40.0)).maxim == "quantity"

    def test_strength_dominant_maxim_matches_strong_reading(self) -> None:
        assert DiagnosisEngine.strength(_row(50.0, 90.0, 48.0, 50.0)) == DiagnosisEngine.strong(
            "quality"
        )

    def test_strength_nothing_measured_returns_unmeasured(self) -> None:
        diagnosis = DiagnosisEngine.strength(_row(None, None, None, None))
        assert (diagnosis.code, diagnosis.maxim, diagnosis.action) == ("unmeasured", None, "")

    # --- strong ---

    def test_strong_maxim_returns_its_benchmark_reading(self) -> None:
        diagnosis = DiagnosisEngine.strong("relation")
        assert (diagnosis.code, diagnosis.maxim) == ("strong_relation", "relation")
        assert diagnosis.summary == DiagnosisEngine.STRENGTHS["strong_relation"]
        assert diagnosis.action == DiagnosisEngine.BENCHMARK_ACTION

    # --- measured ---

    def test_measured_partial_scores_returns_only_measured_maxims(self) -> None:
        assert DiagnosisEngine.measured(_row(10.0, None, 30.0, None)) == {
            "quantity": 10.0,
            "relation": 30.0,
        }
