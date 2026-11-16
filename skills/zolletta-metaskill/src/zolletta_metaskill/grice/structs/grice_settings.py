"""GriceSettings — the report threshold read from ``subcommands.grice``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


@dataclass(frozen=True)
class GriceSettings:
    """The knob that shapes the triage tables, never the indices.

    It only selects which already-scored documents the report lists, so
    changing it never moves a single index. The positive benchmarks need no
    knob: every group has the same five slots.

    Attributes:
        outlier_threshold: A document whose rounded ``grice_index`` is below
            this value is an outlier. Clamped to 0-100.

    """

    outlier_threshold: float = 40.0

    @staticmethod
    def from_settings(settings: dict[str, Any]) -> GriceSettings:
        """Read the threshold from ``subcommands.grice``, defaulting what is unusable.

        Args:
            settings: The project's ``settings.json`` contents.

        Returns:
            The threshold, falling back to its default when absent or of the
            wrong type.

        """
        threshold = ProjectConfig.setting(settings, "subcommands.grice.outlier_threshold", None)
        if not GriceSettings._is_number(threshold):
            return GriceSettings()
        return GriceSettings(outlier_threshold=min(100.0, max(0.0, float(threshold))))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the threshold for the JSON report.

        Returns:
            A mapping with the outlier threshold.

        """
        return {"outlier_threshold": self.outlier_threshold}

    @staticmethod
    def _is_number(value: Any) -> bool:
        """Return whether *value* is an int or a float, excluding ``bool``.

        Args:
            value: The raw settings value.

        Returns:
            ``True`` for a real number.

        """
        return isinstance(value, (int, float)) and not isinstance(value, bool)
