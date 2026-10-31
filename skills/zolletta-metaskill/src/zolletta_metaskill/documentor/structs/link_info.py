"""LinkInfo dataclass for markdown link checking.

Represents a link found in a markdown file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LinkInfo:
    """Represents a link found in a markdown file.

    Deliberately unfrozen (structs.1 deviation): ``is_valid``/``error`` are a
    verdict the checker fills in after construction — the same accumulator
    pattern as ``Finding``/``FileReport``.
    """

    source_file: str
    line_number: int
    link_text: str
    link_target: str
    link_type: str  # "local_file", "anchor", "cross_doc_anchor", "external", "image"
    is_valid: bool | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the link result to a dictionary."""
        return {
            "source_file": self.source_file,
            "line": self.line_number,
            "text": self.link_text,
            "target": self.link_target,
            "type": self.link_type,
            "valid": self.is_valid,
            "error": self.error,
        }
