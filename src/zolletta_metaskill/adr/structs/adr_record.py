"""ADR record data model.

Extracted metadata from a single ADR file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ADRRecord:
    """A single ADR file's extracted metadata."""

    number: str  # "001", "002", etc. (zero-padded or not, as in the heading)
    title: str
    status: str
    decision_text: str
    file_path: Path
    mtime: float
