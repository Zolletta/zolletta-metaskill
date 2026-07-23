"""Python language engine — parses Python source files via :mod:`ast`.

Implements the :class:`~zolletta_metaskill.common.language_engine.LanguageEngine`
protocol by wrapping the standard library :mod:`ast` module and translating
the resulting tree into language-neutral :class:`~zolletta_metaskill.common.models.ModuleInfo`.
"""

from __future__ import annotations

import ast
from pathlib import Path

from zolletta_metaskill.common.models import (
    ClassInfo,
    ImportInfo,
    MethodInfo,
    ModuleInfo,
)

__all__ = ["PythonEngine"]


class PythonEngine:
    """Parse Python source files into :class:`ModuleInfo`.

    Uses :func:`ast.parse` to build the syntax tree and walks it to extract
    classes, functions, imports, ``__all__`` exports, and module docstrings.
    Syntax errors are caught and reported via ``has_syntax_error`` rather
    than being raised.
    """

    @property
    def language(self) -> str:
        """The language identifier — always ``"python"``."""
        return "python"

    def parse_module(self, path: Path) -> ModuleInfo:
        """Parse the Python file at *path* and return its :class:`ModuleInfo`.

        If the file cannot be read or contains a syntax error, a
        :class:`ModuleInfo` with ``has_syntax_error=True`` and empty
        collections is returned.

        Args:
            path: Path to a ``.py`` source file.

        Returns:
            A :class:`ModuleInfo` describing the file's contents.

        """
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            return ModuleInfo(path=path, language=self.language, has_syntax_error=True)

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return ModuleInfo(path=path, language=self.language, has_syntax_error=True)

        classes: list[ClassInfo] = []
        imports: list[ImportInfo] = []
        functions: list[MethodInfo] = []
        all_exports: list[str] | None = None
        docstring: str | None = None

        # Module docstring: first statement is an Expr with a string constant.
        if tree.body and isinstance(tree.body[0], ast.Expr):
            first = tree.body[0].value
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                docstring = first.value

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(self._build_class(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._build_method(node))
            elif isinstance(node, ast.Import):
                imports.append(
                    ImportInfo(
                        module=node.names[0].name,
                        names=[alias.name for alias in node.names],
                        lineno=node.lineno,
                        is_relative=False,
                    )
                )
            elif isinstance(node, ast.ImportFrom):
                imports.append(
                    ImportInfo(
                        module=node.module or "",
                        names=[alias.name for alias in node.names],
                        lineno=node.lineno,
                        is_relative=node.level > 0,
                    )
                )
            elif isinstance(node, ast.Assign):
                exports = self._extract_all(node)
                if exports is not None:
                    all_exports = exports

        return ModuleInfo(
            path=path,
            language=self.language,
            classes=classes,
            imports=imports,
            functions=functions,
            all_exports=all_exports,
            docstring=docstring,
            has_syntax_error=False,
        )

    def is_test_file(self, path: Path) -> bool:
        """Return ``True`` if *path* is a Python test file.

        A file is considered a test file if its name starts with ``test_``
        or if it lives inside a ``tests/`` directory.

        Args:
            path: The file path to check.

        Returns:
            ``True`` if the path looks like a test file, ``False`` otherwise.

        """
        if path.name.startswith("test_"):
            return True
        return any(part == "tests" for part in path.parts)

    def is_source_file(self, path: Path) -> bool:
        """Return ``True`` if *path* has a ``.py`` suffix.

        Args:
            path: The file path to check.

        Returns:
            ``True`` if the suffix is ``.py``, ``False`` otherwise.

        """
        return path.suffix == ".py"

    def file_extensions(self) -> list[str]:
        """Return the list of file extensions handled by this engine.

        Returns:
            ``[".py"]``.

        """
        return [".py"]

    def test_file_pattern(self) -> str:
        """Return the glob pattern for Python test files.

        Returns:
            ``"test_*.py"``.

        """
        return "test_*.py"

    # --- Internal helpers -------------------------------------------------

    def _build_class(self, node: ast.ClassDef) -> ClassInfo:
        """Build a :class:`ClassInfo` from an :class:`ast.ClassDef` node."""
        bases = [ast.unparse(base) for base in node.bases]
        is_abstract = any(base in {"ABC", "Protocol"} for base in bases)
        methods = [
            self._build_method(child)
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        attributes = self._extract_attributes(node)
        return ClassInfo(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno if node.end_lineno is not None else node.lineno,
            methods=methods,
            bases=bases,
            attributes=attributes,
            is_abstract=is_abstract,
            is_test_class=node.name.startswith("Test"),
        )

    def _build_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> MethodInfo:
        """Build a :class:`MethodInfo` from a function definition node."""
        params = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
        is_static = any(
            isinstance(dec, ast.Name) and dec.id == "staticmethod"
            for dec in node.decorator_list
        )
        return_type: str | None = None
        if node.returns is not None:
            return_type = ast.unparse(node.returns)
        raises = self._extract_raises(node)
        return MethodInfo(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno if node.end_lineno is not None else node.lineno,
            params=params,
            is_public=not node.name.startswith("_"),
            is_static=is_static,
            return_type=return_type,
            raises=raises,
        )

    def _extract_attributes(self, class_node: ast.ClassDef) -> list[str]:
        """Extract instance attribute names (``self.x``) from a class body.

        Only attributes assigned via ``self.x = ...`` within method bodies
        are collected. Duplicates are removed while preserving order.

        Args:
            class_node: The :class:`ast.ClassDef` to inspect.

        Returns:
            A list of attribute names assigned to ``self``.

        """
        attributes: list[str] = []
        seen: set[str] = set()
        for child in class_node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for sub in ast.walk(child):
                if isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        name = self._self_attr_name(target)
                        if name is not None and name not in seen:
                            seen.add(name)
                            attributes.append(name)
        return attributes

    @staticmethod
    def _self_attr_name(target: ast.expr) -> str | None:
        """Return the attribute name if *target* is a ``self.x`` assignment.

        Args:
            target: An assignment target expression.

        Returns:
            The attribute name, or ``None`` if *target* is not ``self.x``.

        """
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            return target.attr
        return None

    @staticmethod
    def _extract_raises(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Extract exception type names raised within a function body.

        Walks the function body for :class:`ast.Raise` nodes and extracts
        the exception type name via :func:`ast.unparse` when available.

        Args:
            node: The function definition node.

        Returns:
            A list of exception type names.

        """
        raises: list[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Raise) and sub.exc is not None:
                exc = sub.exc
                # Handle `raise SomeError(...)` — extract the call's func.
                if isinstance(exc, ast.Call):
                    exc = exc.func
                try:
                    name = ast.unparse(exc)
                except Exception:  # pragma: no cover
                    # Defensive: ast.unparse should not fail on valid nodes,
                    # but guard against unexpected forms anyway.
                    continue
                if name not in raises:
                    raises.append(name)
        return raises

    @staticmethod
    def _extract_all(node: ast.Assign) -> list[str] | None:
        """Extract string constants from an ``__all__`` assignment.

        Args:
            node: An :class:`ast.Assign` node to inspect.

        Returns:
            A list of exported names if *node* assigns to ``__all__``,
            otherwise ``None``.

        """
        is_all = any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        )
        if not is_all:
            return None
        value = node.value
        if isinstance(value, ast.List):
            exports: list[str] = []
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    exports.append(elt.value)
            return exports
        return None
