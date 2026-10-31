"""Collected findings and edits for a single file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zolletta_metaskill.code_style.python.structs.finding import Finding


@dataclass
class FileReport:
    """Collected findings and edits for a single file.

    Deliberately unfrozen (structs.1 deviation): the streamliner appends to
    ``findings`` as it walks the file's functions — a report accumulator,
    not a value object.
    """

    path: Path
    findings: list[Finding] = field(default_factory=list)
