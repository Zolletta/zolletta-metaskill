#!/usr/bin/env python3
"""PHP Open/Closed Principle (OCP) validator.

Detects ``if/elseif`` chains that use ``instanceof`` to branch on subtypes —
an OCP violation.  When code uses ``instanceof`` ladders to handle different
subtypes, it should use polymorphism instead (strategy pattern, interface
dispatch, etc.).  Adding a new subtype requires modifying the ladder instead
of simply adding a new implementation.

Since :class:`~zolletta_metaskill.common.models.ModuleInfo` does not capture
``instanceof`` expressions, this scanner uses
:meth:`PHPEngine.parse_raw` to access the tree-sitter AST directly.

Usage:
    python3 scan_php_open_closed.py <directory>
        [--min-branches N] [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --min-branches N   Minimum instanceof branches to flag (default: 3)
    --skip             Skip this check entirely
    --strict           Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from zolletta_metaskill.common.models import Finding, ModuleInfo
from zolletta_metaskill.common.registry import (
    ensure_engine,
    get_engine_for_file,
)
from zolletta_metaskill.engines.php_engine import PHPEngine

if TYPE_CHECKING:
    from tree_sitter import Node

__all__ = ["main", "scan_file", "scan_module"]

# Default threshold: 3+ instanceof branches in an if/elseif chain.
_DEFAULT_MIN_BRANCHES = 3


def _ensure_php_engine() -> None:
    """Ensure the PHPEngine is registered (idempotent)."""
    ensure_engine(PHPEngine())


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


def _contains_instanceof(node: Node) -> bool:
    """Return ``True`` if *node* or any descendant contains ``instanceof``.

    In the tree-sitter-php grammar, ``$a instanceof Foo`` is a
    ``binary_expression`` with an ``instanceof`` child node.
    """
    return any(desc.type == "instanceof" for desc in _iter_descendants(node))


def _count_instanceof_branches(if_node: Node) -> int:
    """Count how many branches in an ``if_statement`` use ``instanceof``.

    The ``if_statement`` node has:
    - An initial ``if`` branch with a ``parenthesized_expression`` condition.
    - Zero or more ``else_if_clause`` children, each with its own condition.
    - An optional ``else_clause`` (not counted — no type check).

    Args:
        if_node: A ``if_statement`` tree-sitter node.

    Returns:
        The number of branches (if + elseif) whose condition contains
        ``instanceof``.

    """
    count = 0

    # Check the initial ``if`` condition.
    for child in if_node.children:
        if child.type == "parenthesized_expression":
            if _contains_instanceof(child):
                count += 1
            break  # only the first parenthesized_expression is the if condition

    # Check each ``else_if_clause`` condition.
    for child in if_node.children:
        if child.type == "else_if_clause":
            for sub in child.children:
                if sub.type == "parenthesized_expression":
                    if _contains_instanceof(sub):
                        count += 1
                    break

    return count


def _scan_tree(path: Path, min_branches: int) -> list[Finding]:
    """Parse *path* with PHPEngine and walk the raw AST for OCP violations."""
    _ensure_php_engine()
    engine = get_engine_for_file(path)
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

    for desc in _iter_descendants(root):
        if desc.type != "if_statement":
            continue
        branch_count = _count_instanceof_branches(desc)
        if branch_count >= min_branches:
            line = desc.start_point[0] + 1
            findings.append(
                Finding(
                    file=file_path,
                    line=line,
                    category="ocp",
                    severity="medium",
                    description=(
                        f"if/elseif chain with {branch_count} instanceof "
                        f"branches — use polymorphism instead of type "
                        f"branching (strategy pattern, interface dispatch)"
                    ),
                    fix_type="manual",
                )
            )

    return findings


def scan_module(
    module: ModuleInfo, min_branches: int = _DEFAULT_MIN_BRANCHES
) -> list[Finding]:
    """Scan a parsed PHP module and return OCP findings.

    Since :class:`ModuleInfo` does not capture ``instanceof`` expressions,
    this method re-parses the file using :meth:`PHPEngine.parse_raw` to
    access the tree-sitter AST.

    Args:
        module: The :class:`ModuleInfo` produced by :meth:`PHPEngine.parse_module`.
        min_branches: The minimum instanceof branch count to flag.

    Returns:
        A list of :class:`Finding` objects with category ``"ocp"``.

    """
    if module.has_syntax_error:
        return []
    if module.language != "php":
        return []
    return _scan_tree(module.path, min_branches)


def scan_file(
    path: Path, min_branches: int = _DEFAULT_MIN_BRANCHES
) -> list[Finding]:
    """Scan a single PHP file for OCP violations.

    Args:
        path: Path to a ``.php`` source file.
        min_branches: The minimum instanceof branch count to flag.

    Returns:
        A list of :class:`Finding` objects (empty if no engine matches,
        the file has a syntax error, or tree-sitter-php is not installed).

    """
    _ensure_php_engine()
    engine = get_engine_for_file(path)
    if engine is None:  # pragma: no cover
        return []
    module = engine.parse_module(path)
    return scan_module(module, min_branches=min_branches)


def main() -> int:
    """Entry point for the PHP Open/Closed Principle validator CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "PHP Open/Closed Principle (OCP) validator — detect "
            "if/elseif instanceof chains."
        )
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="src",
        help="Root directory to scan (default: src)",
    )
    parser.add_argument(
        "--min-branches",
        type=int,
        default=_DEFAULT_MIN_BRANCHES,
        help=f"Min instanceof branches to flag (default: {_DEFAULT_MIN_BRANCHES})",
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

    _ensure_php_engine()
    if args.skip:
        print("=" * 70)
        print("PHP OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_findings: list[Finding] = []
    for php_file in root.rglob("*.php"):
        all_findings.extend(
            scan_file(php_file, min_branches=args.min_branches)
        )

    print("=" * 70)
    print("PHP OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT")
    print("=" * 70)

    if all_findings:
        print(f"\n## OCP violations ({len(all_findings)} found)\n")
        for f in all_findings:
            try:
                rel = str(Path(f.file).relative_to(root))
            except ValueError:  # pragma: no cover
                rel = f.file  # pragma: no cover
            print(f"  {f.description}")
            print(f"    -> {rel}:{f.line}")
            print("    Fix: replace instanceof branching with polymorphism")
    else:
        print(f"\n## OCP violations: none (threshold: {args.min_branches} branches)")

    print()
    if all_findings and args.strict:
        print("Result: OCP VIOLATIONS FOUND (strict mode)")
        return 1
    elif all_findings:
        print("Result: OCP violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())  # pragma: no cover
