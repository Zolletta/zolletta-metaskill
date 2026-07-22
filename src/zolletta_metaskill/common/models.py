"""Language-neutral data models for scanner consumption.

These dataclasses are produced by :class:`~zolletta_metaskill.common.language_engine.LanguageEngine`
implementations and consumed by language-agnostic scanners in ``shared/`` and ``patterns/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MethodInfo:
    """Information about a single method or module-level function.

    Attributes:
        name: The method or function name.
        lineno: The 1-based line number where the definition starts.
        end_lineno: The 1-based line number where the definition ends.
        params: Parameter names excluding the receiver (``self`` / ``this``).
        is_public: Whether the member is publicly visible.
        is_static: Whether the member is static.
        return_type: Return type annotation as a string, if any.
        raises: Exception or throw type names that the method may raise.

    """

    name: str
    lineno: int
    end_lineno: int
    params: list[str] = field(default_factory=list)
    is_public: bool = True
    is_static: bool = False
    return_type: str | None = None
    raises: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClassInfo:
    """Information about a single class, interface, trait, or struct.

    Attributes:
        name: The class name.
        lineno: The 1-based line number where the definition starts.
        end_lineno: The 1-based line number where the definition ends.
        methods: Methods defined directly in the class body.
        bases: Base class or interface names.
        attributes: Instance attribute names (e.g. ``self.x`` → ``"x"``).
        is_abstract: Whether the class is abstract or an interface.
        is_test_class: Whether the class is a test class (name-based heuristic).

    """

    name: str
    lineno: int
    end_lineno: int
    methods: list[MethodInfo] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    is_abstract: bool = False
    is_test_class: bool = False


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


@dataclass(frozen=True)
class ModuleInfo:
    """Language-neutral representation of a parsed source file.

    Produced by :meth:`~zolletta_metaskill.common.language_engine.LanguageEngine.parse_module`
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


@dataclass(frozen=True)
class Finding:
    """A single issue found by a scanner.

    Attributes:
        file: The file path where the issue was found.
        line: The 1-based line number of the issue.
        category: The issue category (e.g. ``"naming"``, ``"structure"``, ``"god_class"``).
        severity: The severity level (``"high"``, ``"medium"``, ``"low"``).
        description: A human-readable description of the issue.
        fix_type: The fix type (``"auto"``, ``"manual"``, ``"skip"``).

    """

    file: str
    line: int
    category: str
    severity: str
    description: str
    fix_type: str = "manual"
