"""Language-neutral representation of a parsed source file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zolletta_metaskill.core.structs.class_info import ClassInfo
from zolletta_metaskill.core.structs.import_info import ImportInfo
from zolletta_metaskill.core.structs.method_info import MethodInfo


@dataclass(frozen=True)
class ModuleInfo:
    """Language-neutral representation of a parsed source file.

    Produced by :meth:`~zolletta_metaskill.core.engine.language_engine.LanguageEngine.parse_module`
    and consumed by language-agnostic scanners.

    Attributes:
        path: The filesystem path to the source file.
        language: The language identifier (e.g. ``"python"``, ``"php"``).
        classes: Top-level and nested classes found in the module.
        imports: Import statements found in the module.
        functions: Module-level functions (not methods).
        all_exports: ``__all__`` for Python, ``None`` for other languages.
        docstring: The module docstring, if any.
        has_syntax_error: Whether the file could not be parsed.

    """

    path: Path
    language: str
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    functions: list[MethodInfo] = field(default_factory=list)
    all_exports: list[str] | None = None
    docstring: str | None = None
    has_syntax_error: bool = False
