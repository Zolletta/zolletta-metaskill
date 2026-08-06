"""Collected findings and edits for a single file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zolletta_metaskill.code_style.python.structs.finding import Finding


@dataclass
class FileReport:
    """Collected findings and edits for a single file."""

    path: Path
    findings: list[Finding] = field(default_factory=list)
