"""LinkInfo dataclass for markdown link checking.

Represents a link found in a markdown file.
"""

from __future__ import annotations

from typing import Any


class LinkInfo:
    """Represents a link found in a markdown file."""

    def __init__(
        self,
        source_file: str,
        line_number: int,
        link_text: str,
        link_target: str,
        link_type: str,  # "local_file", "anchor", "cross_doc_anchor", "external", "image"
    ):
        self.source_file = source_file
        self.line_number = line_number
        self.link_text = link_text
        self.link_target = link_target
        self.link_type = link_type
        self.is_valid: bool | None = None
        self.error: str | None = None

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
