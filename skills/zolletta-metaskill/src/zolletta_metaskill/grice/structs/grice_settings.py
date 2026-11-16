"""GriceSettings — the report thresholds read from ``subcommands.grice``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


@dataclass(frozen=True)
class GriceSettings:
    """The two knobs that shape the triage tables, never the indices.

    Both only select which already-scored documents the report lists, so
    changing them never moves a single index.

    Attributes:
        outlier_threshold: A document whose rounded ``grice_index`` is below
            this value is an outlier. Clamped to 0-100.
        benchmark_count: How many top-ranked documents become positive
            benchmarks. Never negative.

    """

    outlier_threshold: float = 40.0
    benchmark_count: int = 5

    @staticmethod
    def from_settings(settings: dict[str, Any]) -> GriceSettings:
        """Read the thresholds from ``subcommands.grice``, defaulting what is unusable.

        Args:
            settings: The project's ``settings.json`` contents.

        Returns:
            The thresholds, each falling back to its default when absent or of
            the wrong type.

        """
        defaults = GriceSettings()
        threshold = ProjectConfig.setting(settings, "subcommands.grice.outlier_threshold", None)
        count = ProjectConfig.setting(settings, "subcommands.grice.benchmark_count", None)
        return GriceSettings(
            outlier_threshold=(
                min(100.0, max(0.0, float(threshold)))
                if GriceSettings._is_number(threshold)
                else defaults.outlier_threshold
            ),
            benchmark_count=(
                max(0, count)
                if isinstance(count, int) and not isinstance(count, bool)
                else defaults.benchmark_count
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the thresholds for the JSON report.

        Returns:
            A mapping with the outlier threshold and the benchmark count.

        """
        return {
            "outlier_threshold": self.outlier_threshold,
            "benchmark_count": self.benchmark_count,
        }

    @staticmethod
    def _is_number(value: Any) -> bool:
        """Return whether *value* is an int or a float, excluding ``bool``.

        Args:
            value: The raw settings value.

        Returns:
            ``True`` for a real number.

        """
        return isinstance(value, (int, float)) and not isinstance(value, bool)
