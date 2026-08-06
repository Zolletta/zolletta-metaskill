"""SourceSignature dataclass for API documentation validation.

Represents an extracted function or class signature from Python source files.
"""

from __future__ import annotations

from typing import Any


class SourceSignature:
    """Represents an extracted function or class signature."""

    def __init__(
        self,
        name: str,
        kind: str,  # "function", "method", "class"
        file_path: str,
        line_number: int,
        parameters: list[dict[str, Any]],
        return_annotation: str | None = None,
        decorators: list[str] | None = None,
        docstring: str | None = None,
        is_private: bool = False,
        parent_class: str | None = None,
    ):
        self.name = name
        self.kind = kind
        self.file_path = file_path
        self.line_number = line_number
        self.parameters = parameters
        self.return_annotation = return_annotation
        self.decorators = decorators or []
        self.docstring = docstring
        self.is_private = is_private
        self.parent_class = parent_class

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name including the parent class if present."""
        if self.parent_class:
            return f"{self.parent_class}.{self.name}"
        return self.name

    @property
    def is_deprecated(self) -> bool:
        """Return True if the signature is decorated as deprecated."""
        return any("deprecated" in d.lower() for d in self.decorators)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the signature to a dictionary."""
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "file": self.file_path,
            "line": self.line_number,
            "parameters": self.parameters,
            "return_annotation": self.return_annotation,
            "decorators": self.decorators,
            "is_private": self.is_private,
            "is_deprecated": self.is_deprecated,
        }
