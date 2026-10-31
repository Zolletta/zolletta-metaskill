"""A single issue found by a scanner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """A single issue found by a scanner.

    Attributes:
        file: The file path where the issue was found.
        line: The 1-based line number of the issue.
        category: The issue category (e.g. ``"naming"``, ``"structure"``, ``"god_class"``).
        severity: The severity level (``"high"``, ``"medium"``, ``"low"``).
        description: A human-readable description of the issue.
        fix_type: The fix type (``"auto"``, ``"manual"``, ``"skip"``).

    """

    file: str
    line: int
    category: str
    severity: str
    description: str
    fix_type: str = "manual"
