"""Diagnosis — the rule-based reading of one document's four maxim indices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Diagnosis:
    """What a document's sub-score profile says, and what to do about it.

    Computed by a fixed rule table over the four maxim indices, so the same
    profile always yields the same reading. The ``code`` is the stable part a
    report can translate; ``summary`` and ``action`` are its English wording.

    Attributes:
        code: Stable rule identifier, e.g. ``"isolated"`` or ``"strong_manner"``.
        maxim: The maxim the rule turned on — the weakest for an outlier, the
            strongest for a benchmark — or ``None`` when nothing was measured.
        summary: One-line English reading of the profile.
        action: One-line English recommendation, ``""`` when none applies.

    """

    code: str
    maxim: str | None
    summary: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the diagnosis for the JSON report.

        Returns:
            A mapping with the code, the maxim, the summary and the action.

        """
        return {
            "code": self.code,
            "maxim": self.maxim,
            "summary": self.summary,
            "action": self.action,
        }
