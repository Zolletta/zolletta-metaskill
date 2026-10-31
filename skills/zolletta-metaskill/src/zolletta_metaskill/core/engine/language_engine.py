"""The :class:`LanguageEngine` protocol — the seam between scanners and parsers.

Language-agnostic scanners depend only on this protocol and
:class:`~zolletta_metaskill.core.structs.module_info.ModuleInfo`.
They never import ``ast`` or tree-sitter directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from zolletta_metaskill.core.structs.module_info import ModuleInfo


@runtime_checkable
class LanguageEngine(Protocol):
    """Protocol for language-specific AST parsing engines.

    Each registered engine knows how to parse source files of one language
    into :class:`~zolletta_metaskill.core.structs.module_info.ModuleInfo`.
    """

    @property
    def language(self) -> str:
        """The language identifier (e.g. ``"python"``, ``"php"``)."""
        ...

    def parse_module(self, path: Path) -> ModuleInfo:
        """Parse a source file and return its :class:`ModuleInfo`.

        Args:
            path: Path to the source file.

        Returns:
            A :class:`ModuleInfo` describing the file's contents.
            If the file has a syntax error, ``has_syntax_error`` is ``True``
            and the other fields may be empty.

        """
        ...

    def file_extensions(self) -> list[str]:
        """Return the list of file extensions this engine handles (e.g. ``[".py"]``)."""
        ...
