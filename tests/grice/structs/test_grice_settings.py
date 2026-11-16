"""Tests for grice_settings.py."""

from __future__ import annotations

from typing import Any

import pytest

from zolletta_metaskill.grice.structs import GriceSettings


def _settings(**grice: Any) -> dict[str, Any]:
    return {"subcommands": {"grice": grice}}


class TestGriceSettings:
    # --- from_settings ---

    def test_from_settings_no_grice_entry_returns_defaults(self) -> None:
        assert GriceSettings.from_settings({}) == GriceSettings(40.0, 5)

    def test_from_settings_configured_values_returns_them(self) -> None:
        settings = _settings(outlier_threshold=35, benchmark_count=3)
        assert GriceSettings.from_settings(settings) == GriceSettings(35.0, 3)

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [(-5, 0.0), (150.5, 100.0), (42.5, 42.5)],
        ids=[
            "threshold_negative_clamps_to_zero",
            "threshold_above_scale_clamps_to_100",
            "threshold_fractional_is_kept",
        ],
    )
    def test_from_settings_threshold_out_of_scale_is_clamped(
        self, raw: float, expected: float
    ) -> None:
        assert GriceSettings.from_settings(_settings(outlier_threshold=raw)).outlier_threshold == (
            expected
        )

    @pytest.mark.parametrize(
        "raw",
        ["40", True, None, [40]],
        ids=[
            "threshold_string_uses_default",
            "threshold_bool_uses_default",
            "threshold_null_uses_default",
            "threshold_list_uses_default",
        ],
    )
    def test_from_settings_threshold_wrong_type_returns_default(self, raw: Any) -> None:
        assert GriceSettings.from_settings(_settings(outlier_threshold=raw)).outlier_threshold == (
            40.0
        )

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [(-1, 0), (True, 5), (2.5, 5), ("3", 5), (0, 0)],
        ids=[
            "count_negative_clamps_to_zero",
            "count_bool_uses_default",
            "count_float_uses_default",
            "count_string_uses_default",
            "count_zero_is_kept",
        ],
    )
    def test_from_settings_benchmark_count_is_validated(self, raw: Any, expected: int) -> None:
        assert GriceSettings.from_settings(_settings(benchmark_count=raw)).benchmark_count == (
            expected
        )

    # --- to_dict ---

    def test_to_dict_settings_serializes_both_thresholds(self) -> None:
        assert GriceSettings(35.0, 3).to_dict() == {"outlier_threshold": 35.0, "benchmark_count": 3}
