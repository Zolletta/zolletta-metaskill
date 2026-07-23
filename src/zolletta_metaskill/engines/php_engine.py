"""PHP language engine — parses PHP source files via tree-sitter-php.

Implements the :class:`~zolletta_metaskill.common.language_engine.LanguageEngine`
protocol by wrapping tree-sitter and the tree-sitter-php grammar, translating
the resulting syntax tree into language-neutral
:class:`~zolletta_metaskill.common.models.ModuleInfo`.

If the optional ``tree-sitter-php`` dependency is not installed, the engine
still exists and satisfies the protocol, but :meth:`PHPEngine.parse_module`
raises a clear :class:`ImportError` with installation instructions.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from zolletta_metaskill.common.models import (
    ClassInfo,
    ImportInfo,
    MethodInfo,
    ModuleInfo,
)

if TYPE_CHECKING:
    from tree_sitter import Node, Parser, Tree  # type: ignore[import-not-found]

__all__ = ["PHPEngine"]


def _have_tree_sitter_php() -> bool:
    """Return ``True`` if ``tree-sitter-php`` is importable."""
    import importlib.util

    return importlib.util.find_spec("tree_sitter_php") is not None


class PHPEngine:
    """Parse PHP source files into :class:`ModuleInfo`.

    Uses tree-sitter with the tree-sitter-php grammar to build the syntax
    tree and walks it to extract classes, interfaces, traits, methods,
    functions, and namespace imports. Syntax errors are reported via
    ``has_syntax_error`` rather than being raised.

    The ``tree-sitter-php`` package is an optional dependency. If it is not
    installed, the engine still instantiates and satisfies the
    :class:`~zolletta_metaskill.common.language_engine.LanguageEngine`
    protocol, but :meth:`parse_module` raises an :class:`ImportError`.
    """

    def __init__(self) -> None:
        """Initialise the engine, lazily preparing a parser if possible."""
        self._parser: Parser | None = None
        self._ready: bool | None = None

    # -- Protocol properties ------------------------------------------------

    @property
    def language(self) -> str:
        """The language identifier — always ``"php"``."""
        return "php"

    def file_extensions(self) -> list[str]:
        """Return the list of file extensions handled by this engine.

        Returns:
            ``[".php"]``.

        """
        return [".php"]

    def test_file_pattern(self) -> str:
        """Return the glob pattern for PHP test files.

        Returns:
            ``"*Test.php"``.

        """
        return "*Test.php"

    def is_source_file(self, path: Path) -> bool:
        """Return ``True`` if *path* has a ``.php`` suffix.

        Args:
            path: The file path to check.

        Returns:
            ``True`` if the suffix is ``.php``, ``False`` otherwise.

        """
        return path.suffix == ".php"

    def is_test_file(self, path: Path) -> bool:
        """Return ``True`` if *path* is a PHP test file.

        A file is considered a test file if its name ends with ``Test.php``
        or if it lives inside a ``tests/`` directory.

        Args:
            path: The file path to check.

        Returns:
            ``True`` if the path looks like a test file, ``False`` otherwise.

        """
        if path.name.endswith("Test.php"):
            return True
        return any(part == "tests" for part in path.parts)

    # -- Parsing ------------------------------------------------------------

    def parse_module(self, path: Path) -> ModuleInfo:
        """Parse the PHP file at *path* and return its :class:`ModuleInfo`.

        If ``tree-sitter-php`` is not installed, an :class:`ImportError` is
        raised with installation instructions. If the file cannot be read or
        contains a syntax error, a :class:`ModuleInfo` with
        ``has_syntax_error=True`` and empty collections is returned.

        Args:
            path: Path to a ``.php`` source file.

        Returns:
            A :class:`ModuleInfo` describing the file's contents.

        Raises:
            ImportError: If ``tree-sitter-php`` is not installed.

        """
        parser = self._get_parser()

        try:
            source = path.read_bytes()
        except OSError:
            return ModuleInfo(path=path, language=self.language, has_syntax_error=True)

        tree = parser.parse(source)
        root = tree.root_node

        has_syntax_error = bool(root.has_error)

        classes: list[ClassInfo] = []
        imports: list[ImportInfo] = []
        functions: list[MethodInfo] = []

        for child in root.children:
            kind = child.type
            if kind == "class_declaration":
                cls = self._build_class(child, source)
                if cls is not None:
                    classes.append(cls)
            elif kind == "interface_declaration":
                cls = self._build_interface(child, source)
                if cls is not None:
                    classes.append(cls)
            elif kind == "trait_declaration":
                cls = self._build_trait(child, source)
                if cls is not None:
                    classes.append(cls)
            elif kind == "method_declaration":  # pragma: no cover
                # Top-level function declarations use function_definition,
                # but handle method_declaration defensively.
                func = self._build_method(child, source)
                if func is not None:
                    functions.append(func)
            elif kind == "function_definition":
                func = self._build_function(child, source)
                if func is not None:
                    functions.append(func)
            elif kind == "namespace_use_declaration":
                imports.extend(self._build_imports(child, source))

        return ModuleInfo(
            path=path,
            language=self.language,
            classes=classes,
            imports=imports,
            functions=functions,
            all_exports=None,
            docstring=None,
            has_syntax_error=has_syntax_error,
        )

    def parse_raw(self, path: Path) -> tuple[Tree, bytes]:
        """Parse the PHP file at *path* and return the raw tree-sitter tree.

        This is used by PHP-specific scanners that need direct access to the
        tree-sitter AST (e.g. to detect ``new`` expressions or ``instanceof``
        chains that are not captured in :class:`ModuleInfo`).

        Args:
            path: Path to a ``.php`` source file.

        Returns:
            A tuple of ``(Tree, source_bytes)``.  The source bytes are needed
            to extract text from individual nodes via
            ``source[node.start_byte:node.end_byte]``.

        Raises:
            ImportError: If ``tree-sitter-php`` is not installed.

        """
        parser = self._get_parser()
        source = path.read_bytes()
        tree = parser.parse(source)
        return tree, source

    # -- Internal: parser setup --------------------------------------------

    def _get_parser(self) -> Parser:
        """Return a configured parser, raising if tree-sitter-php is missing."""
        if self._parser is not None:
            return self._parser
        if self._ready is None:
            self._ready = _have_tree_sitter_php()
        if not self._ready:
            raise ImportError(
                "tree-sitter-php is required to parse PHP files. "
                "Install it with: uv add tree-sitter tree-sitter-php"
            )
        import tree_sitter
        import tree_sitter_php  # type: ignore[import-not-found]

        language = tree_sitter.Language(tree_sitter_php.language_php())
        self._parser = tree_sitter.Parser(language)
        return self._parser

    # -- Internal: node helpers --------------------------------------------

    @staticmethod
    def _node_text(node: Node, source: bytes) -> str:
        """Return the source text covered by *node* as a string."""
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _child_by_type(node: Node, name: str) -> Node | None:
        """Return the first direct child of *node* with the given type."""
        for child in node.children:
            if child.type == name:
                return child
        return None

    @staticmethod
    def _children_by_type(node: Node, name: str) -> list[Node]:
        """Return all direct children of *node* with the given type."""
        return [child for child in node.children if child.type == name]

    def _name_text(self, node: Node, source: bytes) -> str:
        """Return the text of the ``name`` child of *node*, or empty string."""
        name_node = self._child_by_type(node, "name")
        if name_node is None:  # pragma: no cover
            return ""
        return self._node_text(name_node, source)

    def _qualified_name_text(self, node: Node, source: bytes) -> str:
        """Return a readable name for a name/qualified_name/namespace_name node."""
        # Collect all ``name`` descendants in document (pre-order) order.
        names: list[str] = []

        def walk(current: Node) -> None:
            if current.type == "name":
                names.append(self._node_text(current, source))
                return
            for child in current.children:
                walk(child)

        walk(node)
        return "\\".join(names)

    # -- Internal: class-like builders --------------------------------------

    def _build_class(self, node: Node, source: bytes) -> ClassInfo | None:
        """Build a :class:`ClassInfo` from a ``class_declaration`` node."""
        name = self._name_text(node, source)
        if not name:  # pragma: no cover
            return None
        bases = self._collect_bases(node, source)
        is_abstract = self._child_by_type(node, "abstract_modifier") is not None
        methods = self._collect_methods(node, source)
        return ClassInfo(
            name=name,
            lineno=node.start_point[0] + 1,
            end_lineno=node.end_point[0] + 1,
            methods=methods,
            bases=bases,
            attributes=[],
            is_abstract=is_abstract,
            is_test_class=name.endswith("Test"),
        )

    def _build_interface(self, node: Node, source: bytes) -> ClassInfo | None:
        """Build a :class:`ClassInfo` from an ``interface_declaration`` node."""
        name = self._name_text(node, source)
        if not name:  # pragma: no cover
            return None
        bases = self._collect_bases(node, source)
        methods = self._collect_methods(node, source)
        return ClassInfo(
            name=name,
            lineno=node.start_point[0] + 1,
            end_lineno=node.end_point[0] + 1,
            methods=methods,
            bases=bases,
            attributes=[],
            is_abstract=True,
            is_test_class=name.endswith("Test"),
        )

    def _build_trait(self, node: Node, source: bytes) -> ClassInfo | None:
        """Build a :class:`ClassInfo` from a ``trait_declaration`` node."""
        name = self._name_text(node, source)
        if not name:  # pragma: no cover
            return None
        methods = self._collect_methods(node, source)
        return ClassInfo(
            name=name,
            lineno=node.start_point[0] + 1,
            end_lineno=node.end_point[0] + 1,
            methods=methods,
            bases=[],
            attributes=[],
            is_abstract=False,
            is_test_class=name.endswith("Test"),
        )

    def _collect_bases(self, node: Node, source: bytes) -> list[str]:
        """Collect base class and interface names from a class-like node."""
        bases: list[str] = []
        base_clause = self._child_by_type(node, "base_clause")
        if base_clause is not None:
            bases.extend(self._names_from_clause(base_clause, source))
        interface_clause = self._child_by_type(node, "class_interface_clause")
        if interface_clause is not None:
            bases.extend(self._names_from_clause(interface_clause, source))
        return bases

    def _names_from_clause(self, clause: Node, source: bytes) -> list[str]:
        """Extract names from a base/interface clause node."""
        names: list[str] = []
        for child in clause.children:
            if child.type in ("name", "qualified_name", "namespace_name"):
                text = self._qualified_name_text(child, source)
                if text:
                    names.append(text)
        return names

    def _collect_methods(self, class_node: Node, source: bytes) -> list[MethodInfo]:
        """Collect method declarations from a class-like node's body."""
        body = self._child_by_type(class_node, "declaration_list")
        if body is None:  # pragma: no cover
            return []
        methods: list[MethodInfo] = []
        for child in body.children:
            if child.type == "method_declaration":
                info = self._build_method(child, source)
                if info is not None:
                    methods.append(info)
        return methods

    # -- Internal: method/function builders ---------------------------------

    def _build_method(self, node: Node, source: bytes) -> MethodInfo | None:
        """Build a :class:`MethodInfo` from a ``method_declaration`` node."""
        name = self._name_text(node, source)
        if not name:  # pragma: no cover
            return None
        params = self._collect_params(node, source)
        is_public = self._is_public(node)
        is_static = self._child_by_type(node, "static_modifier") is not None
        return_type = self._collect_return_type(node, source)
        raises = self._collect_raises(node, source)
        return MethodInfo(
            name=name,
            lineno=node.start_point[0] + 1,
            end_lineno=node.end_point[0] + 1,
            params=params,
            is_public=is_public,
            is_static=is_static,
            return_type=return_type,
            raises=raises,
        )

    def _build_function(self, node: Node, source: bytes) -> MethodInfo | None:
        """Build a :class:`MethodInfo` from a ``function_definition`` node."""
        name = self._name_text(node, source)
        if not name:  # pragma: no cover
            return None
        params = self._collect_params(node, source)
        return_type = self._collect_return_type(node, source)
        raises = self._collect_raises(node, source)
        return MethodInfo(
            name=name,
            lineno=node.start_point[0] + 1,
            end_lineno=node.end_point[0] + 1,
            params=params,
            is_public=True,
            is_static=False,
            return_type=return_type,
            raises=raises,
        )

    def _is_public(self, node: Node) -> bool:
        """Determine visibility from a ``visibility_modifier`` child.

        PHP defaults to public when no visibility modifier is present.
        ``private`` and ``protected`` are treated as non-public.
        """
        vis = self._child_by_type(node, "visibility_modifier")
        if vis is None:
            return True
        for child in vis.children:
            if child.type in ("public", "protected", "private"):
                return bool(child.type == "public")
        return True  # pragma: no cover

    def _collect_params(self, node: Node, source: bytes) -> list[str]:
        """Extract parameter names from a ``formal_parameters`` child."""
        params_node = self._child_by_type(node, "formal_parameters")
        if params_node is None:  # pragma: no cover
            return []
        names: list[str] = []
        for descendant in self._iter_descendants(params_node):
            if descendant.type == "variable_name":
                name_child = self._child_by_type(descendant, "name")
                if name_child is not None:
                    names.append(self._node_text(name_child, source))
        return names

    def _collect_return_type(self, node: Node, source: bytes) -> str | None:
        """Extract the return type text following the ``:`` in a signature."""
        # The return type appears as a typed child after formal_parameters.
        # Common node types: primitive_type, optional_type, named_type,
        # qualified_name, nullable_type, union_type, intersection_type.
        found_colon = False
        for child in node.children:
            if not found_colon:
                if child.type == ":":
                    found_colon = True
                continue
            if child.type in {
                "primitive_type",
                "optional_type",
                "named_type",
                "qualified_name",
                "nullable_type",
                "union_type",
                "intersection_type",
                "named_type_list",
            }:
                return self._node_text(child, source).strip()
        return None

    def _collect_raises(self, node: Node, source: bytes) -> list[str]:
        """Collect exception type names from ``throw`` expressions in a body."""
        raises: list[str] = []
        seen: set[str] = set()
        for descendant in self._iter_descendants(node):
            if descendant.type == "throw_expression":
                type_name = self._thrown_type(descendant, source)
                if type_name and type_name not in seen:
                    seen.add(type_name)
                    raises.append(type_name)
        return raises

    def _thrown_type(self, throw_node: Node, source: bytes) -> str | None:
        """Return the exception class name from a ``throw_expression``."""
        creation = self._child_by_type(throw_node, "object_creation_expression")
        if creation is None:
            return None
        for child in creation.children:
            if child.type in ("qualified_name", "name", "named_type"):
                return self._qualified_name_text(child, source)
        return None  # pragma: no cover

    # -- Internal: imports --------------------------------------------------

    def _build_imports(self, node: Node, source: bytes) -> list[ImportInfo]:
        """Build :class:`ImportInfo` entries from a ``namespace_use_declaration``."""
        imports: list[ImportInfo] = []
        lineno = node.start_point[0] + 1
        # For grouped imports (``use Ns\{A, B}``) the namespace prefix is a
        # direct ``namespace_name`` / ``qualified_name`` child of the
        # declaration, and each group clause only carries the final name.
        prefix = ""
        group_node: Node | None = None
        standalone_clauses: list[Node] = []
        for child in node.children:
            if child.type in ("namespace_name", "qualified_name", "name"):
                prefix = self._qualified_name_text(child, source)
            elif child.type == "namespace_use_group":
                group_node = child
            elif child.type == "namespace_use_clause":
                standalone_clauses.append(child)

        if group_node is not None:
            for group_clause in self._children_by_type(group_node, "namespace_use_clause"):
                info = self._import_from_clause(
                    group_clause, source, lineno, prefix=prefix
                )
                if info is not None:
                    imports.append(info)
        for clause in standalone_clauses:
            info = self._import_from_clause(clause, source, lineno, prefix="")
            if info is not None:
                imports.append(info)
        return imports

    def _import_from_clause(
        self, clause: Node, source: bytes, lineno: int, prefix: str = ""
    ) -> ImportInfo | None:
        """Build an :class:`ImportInfo` from a single ``namespace_use_clause``."""
        module = ""
        alias = ""
        seen_as = False
        for child in clause.children:
            if child.type == "as":
                seen_as = True
                continue
            if seen_as and child.type == "name":
                alias = self._node_text(child, source)
                seen_as = False
                continue
            if child.type in ("qualified_name", "name", "namespace_name"):
                if not module:
                    module = self._qualified_name_text(child, source)
            elif child.type == "namespace_use_group":  # pragma: no cover
                # Handled by caller; skip here.
                pass
        if prefix and module:
            module = f"{prefix}\\{module}"
        names = [alias] if alias else []
        if not module:  # pragma: no cover
            return None
        return ImportInfo(
            module=module,
            names=names,
            lineno=lineno,
            is_relative=False,
        )

    # -- Internal: tree walking --------------------------------------------

    @staticmethod
    def _iter_descendants(node: Node) -> Iterator[Node]:
        """Yield all descendants of *node* in document order (pre-order)."""
        stack: list[Node] = list(reversed(node.children))
        while stack:
            current = stack.pop()
            yield current
            for child in reversed(current.children):
                stack.append(child)
