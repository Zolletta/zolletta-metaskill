"""A single streamline finding for one docstring."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    """A single streamline finding for one docstring."""

    file: Path
    line: int
    kind: str  # "redundant_args", "redundant_returns", "obsolete",
    # "private", "test", "nested", "obvious_init"
    detail: str
    node: ast.AST
    # New docstring text after streamlining (None = remove entirely).
    new_text: str | None = None
    # Whether the docstring should be removed entirely.
    remove: bool = False
