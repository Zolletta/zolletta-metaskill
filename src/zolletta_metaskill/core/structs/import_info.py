"""Information about a single import statement."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImportInfo:
    r"""Information about a single import statement.

    Attributes:
        module: The imported module or namespace (e.g. ``"os.path"``
            or ``"Namespace\Sub\Class"``).
        names: Imported names for ``from X import a, b`` style imports.
        lineno: The 1-based line number of the import statement.
        is_relative: Whether the import is relative.

    """

    module: str
    names: list[str] = field(default_factory=list)
    lineno: int = 0
    is_relative: bool = False
