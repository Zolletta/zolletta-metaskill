#!/usr/bin/env python3
"""PHP Dependency Inversion Principle (DIP) validator.

Detects ``new ClassName()`` inside class methods — a DIP violation.  When a
class instantiates a dependency directly in its constructor (or any method)
using ``new``, it is tightly coupled to that concrete class instead of
receiving it via dependency injection.

Since :class:`~zolletta_metaskill.core.structs.ModuleInfo` does not capture
``new`` expressions, this scanner uses
:meth:`PHPEngine.parse_raw` to access the tree-sitter AST directly.

Usage:
    python3 dependency_inversion_scanner.py <directory> [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --skip          Skip this check entirely (exit 0 with 'skipped' message)
    --strict        Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.structs import Finding, ModuleInfo

if TYPE_CHECKING:
    from tree_sitter import Node


class DependencyInversionScanner:
    """PHP Dependency Inversion Principle (DIP) validator.

    Detects ``new ClassName()`` inside class methods — a DIP violation.
    All functions are exposed as ``@staticmethod`` methods on this class.
    """

    # PHP built-in / scalar types that are not "real" dependencies.
    _PHP_BUILTIN_TYPES = frozenset(
        {
            "array",
            "string",
            "int",
            "float",
            "bool",
            "null",
            "void",
            "mixed",
            "object",
            "callable",
            "iterable",
            "self",
            "static",
            "parent",
            "stdClass",
            "ArrayObject",
            "SplStack",
            "SplQueue",
            "SplDoublyLinkedList",
            "DateTime",
            "DateTimeImmutable",
            "DateInterval",
            "DatePeriod",
            "Exception",
            "RuntimeException",
            "InvalidArgumentException",
            "TypeError",
            "ValueError",
            "Error",
            "LogicException",
            "RangeException",
            "OverflowException",
            "UnderflowException",
            "OutOfBoundsException",
            "DomainException",
            "LengthException",
            "UnexpectedValueException",
            "BadFunctionCallException",
            "BadMethodCallException",
            "UninitializedPropertyError",
        }
    )

    # Minimum number of methods a class needs before we skip "factory" detection.
    # A class whose name contains "Factory" or "Builder" is considered a composition
    # root where object creation is expected.

    @staticmethod
    def _ensure_php_engine() -> None:
        """Ensure the PHPEngine is registered (idempotent)."""
        EngineRegistry.ensure(PHPEngine())

    @staticmethod
    def _is_factory(class_name: str) -> bool:
        """Return ``True`` if *class_name* suggests a factory or builder."""
        return "Factory" in class_name or "Builder" in class_name

    @staticmethod
    def _is_real_dependency(class_name: str) -> bool:
        """Return ``True`` if *class_name* is a real dependency (not a built-in)."""
        return class_name not in DependencyInversionScanner._PHP_BUILTIN_TYPES

    @staticmethod
    def _iter_descendants(node: Node) -> list[Node]:
        """Yield all descendants of *node* in document order (pre-order)."""
        result: list[Node] = []
        stack: list[Node] = list(reversed(node.children))
        while stack:
            current = stack.pop()
            result.append(current)
            for child in reversed(current.children):
                stack.append(child)
        return result

    @staticmethod
    def _extract_class_name_from_new(node: Node, source: bytes) -> str | None:
        """Extract the class name from an ``object_creation_expression`` node.

        The node looks like::

            object_creation_expression
              new
              name              <- simple class name
              arguments

        Or with a qualified name::

            object_creation_expression
              new
              qualified_name
                name
                name
              arguments

        """
        for child in node.children:
            if child.type == "name":
                return source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
            if child.type == "qualified_name":
                # Collect all ``name`` descendants in order and join with ``\``.
                parts: list[str] = []
                for desc in DependencyInversionScanner._iter_descendants(child):
                    if desc.type == "name":
                        parts.append(
                            source[desc.start_byte : desc.end_byte].decode(
                                "utf-8", errors="replace"
                            )
                        )
                if parts:
                    return "\\".join(parts)
        return None  # pragma: no cover

    @staticmethod
    def _find_new_in_method(method_node: Node, source: bytes) -> list[tuple[str, int]]:
        """Find all ``new ClassName()`` calls within a method body.

        Args:
            method_node: A ``method_declaration`` tree-sitter node.
            source: The raw source bytes.

        Returns:
            A list of ``(class_name, line_number)`` tuples.

        """
        violations: list[tuple[str, int]] = []
        for desc in DependencyInversionScanner._iter_descendants(method_node):
            if desc.type == "object_creation_expression":
                class_name = DependencyInversionScanner._extract_class_name_from_new(desc, source)
                if class_name and DependencyInversionScanner._is_real_dependency(class_name):
                    line = desc.start_point[0] + 1
                    violations.append((class_name, line))
        return violations

    @staticmethod
    def _find_class_name(class_node: Node, source: bytes) -> str:
        """Extract the class name from a ``class_declaration`` node."""
        for child in class_node.children:
            if child.type == "name":
                return source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
        return ""  # pragma: no cover

    @staticmethod
    def _find_method_name(method_node: Node, source: bytes) -> str:
        """Extract the method name from a ``method_declaration`` node."""
        for child in method_node.children:
            if child.type == "name":
                return source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
        return ""  # pragma: no cover

    @staticmethod
    def _scan_tree(path: Path) -> list[Finding]:
        """Parse *path* with PHPEngine and walk the raw AST for DIP violations.

        This is the core detection logic that uses tree-sitter directly.
        """
        DependencyInversionScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None or not isinstance(engine, PHPEngine):  # pragma: no cover
            return []  # pragma: no cover

        try:
            tree, source = engine.parse_raw(path)
        except (OSError, ImportError):  # pragma: no cover
            return []  # pragma: no cover

        root = tree.root_node
        if root.has_error:  # pragma: no cover
            return []  # pragma: no cover

        findings: list[Finding] = []
        file_path = str(path)

        for child in root.children:
            if child.type != "class_declaration":
                continue
            class_name = DependencyInversionScanner._find_class_name(child, source)
            if not class_name or DependencyInversionScanner._is_factory(class_name):
                continue

            # Find the declaration_list (class body)
            body = None
            for c in child.children:
                if c.type == "declaration_list":
                    body = c
                    break
            if body is None:  # pragma: no cover
                continue  # pragma: no cover

            for member in body.children:
                if member.type != "method_declaration":
                    continue
                method_name = DependencyInversionScanner._find_method_name(member, source)
                new_calls = DependencyInversionScanner._find_new_in_method(member, source)
                for created_class, line in new_calls:
                    findings.append(
                        Finding(
                            file=file_path,
                            line=line,
                            category="dip",
                            severity="medium",
                            description=(
                                f"{class_name}::{method_name}() instantiates "
                                f"'{created_class}' directly — depend on an "
                                f"abstraction instead (inject via constructor)"
                            ),
                            fix_type="manual",
                        )
                    )

        return findings

    @staticmethod
    def scan_module(module: ModuleInfo) -> list[Finding]:
        """Scan a parsed PHP module and return DIP findings.

        Since :class:`ModuleInfo` does not capture ``new`` expressions, this
        method re-parses the file using :meth:`PHPEngine.parse_raw` to access
        the tree-sitter AST.

        Args:
            module: The :class:`ModuleInfo` produced by :meth:`PHPEngine.parse_module`.

        Returns:
            A list of :class:`Finding` objects with category ``"dip"``.

        """
        if module.has_syntax_error:
            return []
        if module.language != "php":
            return []
        return DependencyInversionScanner._scan_tree(module.path)

    @staticmethod
    def scan_file(path: Path) -> list[Finding]:
        """Scan a single PHP file for DIP violations.

        Args:
            path: Path to a ``.php`` source file.

        Returns:
            A list of :class:`Finding` objects (empty if no engine matches,
            the file has a syntax error, or tree-sitter-php is not installed).

        """
        DependencyInversionScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        return DependencyInversionScanner.scan_module(module)

    @staticmethod
    def main() -> int:
        """Entry point for the PHP Dependency Inversion validator CLI."""
        parser = argparse.ArgumentParser(
            description=(
                "PHP Dependency Inversion validator — detect 'new Dep()' "
                "in constructors and methods."
            )
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default="src",
            help="Root directory to scan (default: src)",
        )
        parser.add_argument(
            "--skip",
            action="store_true",
            help="Skip this check entirely (exit 0 with 'skipped' message)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with code 1 if violations are found",
        )
        args = parser.parse_args()

        DependencyInversionScanner._ensure_php_engine()
        if args.skip:
            print("=" * 70)
            print("PHP DEPENDENCY INVERSION (DIP) — VALIDATION REPORT")
            print("=" * 70)
            print("\nResult: SKIPPED (--skip flag)\n")
            return 0

        root = Path(args.directory)
        if not root.exists():
            print(f"Error: directory '{root}' does not exist", file=sys.stderr)
            return 1

        all_findings: list[Finding] = []
        for php_file in root.rglob("*.php"):
            all_findings.extend(DependencyInversionScanner.scan_file(php_file))

        print("=" * 70)
        print("PHP DEPENDENCY INVERSION (DIP) — VALIDATION REPORT")
        print("=" * 70)

        if all_findings:
            print(f"\n## DIP violations ({len(all_findings)} found)\n")
            for f in all_findings:
                try:
                    rel = str(Path(f.file).relative_to(root))
                except ValueError:  # pragma: no cover
                    rel = f.file  # pragma: no cover
                print(f"  {f.description}")
                print(f"    -> {rel}:{f.line}")
                print("    Fix: inject the dependency via constructor instead of 'new'")
        else:
            print("\n## DIP violations: none")

        print()
        if all_findings and args.strict:
            print("Result: DIP VIOLATIONS FOUND (strict mode)")
            return 1
        elif all_findings:
            print("Result: DIP violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(DependencyInversionScanner.main())  # pragma: no cover
