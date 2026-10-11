"""The :class:`RawAstEngine` protocol — engines that expose their own parser tree.

:class:`~zolletta_metaskill.core.engine.language_engine.LanguageEngine` is
language-neutral: it returns :class:`~zolletta_metaskill.core.structs.module_info.ModuleInfo`
and says nothing about how a file was parsed. A few scanners genuinely need
the parser's own tree — PHP's ``new``/``instanceof`` chains, tree-sitter node
types — and used to reach for :class:`~zolletta_metaskill.core.engine.php_engine.PHPEngine`
to get it.

That coupled a *language-general* scanner to one engine. This protocol states
the capability instead, so a scanner that needs raw AST depends on the
capability and not on which language happens to provide it.

The tree type is :data:`typing.Any` on purpose. A tree-sitter tree is not a
Python :class:`ast.AST`, so naming either concrete type here would put the
language of one engine into a protocol meant to stay neutral.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RawAstEngine(Protocol):
    """An engine that can return its parser's own tree for a source file."""

    def parse_raw(self, path: Path) -> tuple[Any, bytes]:
        """Parse *path* and return the parser tree plus the source bytes.

        Args:
            path: Path to the source file.

        Returns:
            A ``(tree, source)`` pair, where ``tree`` is whatever the engine's
            parser produces and ``source`` is the file's bytes.

        """
        ...
