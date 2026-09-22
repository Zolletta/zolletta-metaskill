#!/usr/bin/env python3
"""PHP Open/Closed Principle (OCP) validator.

Detects ``if/elseif`` chains that use ``instanceof`` to branch on subtypes —
an OCP violation.  When code uses ``instanceof`` ladders to handle different
subtypes, it should use polymorphism instead (strategy pattern, interface
dispatch, etc.).  Adding a new subtype requires modifying the ladder instead
of simply adding a new implementation.

Since :class:`~zolletta_metaskill.core.structs.ModuleInfo` does not capture
``instanceof`` expressions, this scanner uses
:meth:`PHPEngine.parse_raw` to access the tree-sitter AST directly.

Scan roots come from ``php.autoload.psr-4`` in ``settings.json``; the
branch threshold comes from ``php.patterns.ocp_min_branches`` (default: 3).
The check runs when ``php.patterns.check_ocp`` is not ``false``. File
enumeration is git-ignore aware.

Usage:
    python3 open_closed_scanner.py [--json]

Options:
    --json             Output as JSON instead of markdown.

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tree_sitter import Node

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding, ModuleInfo


class OpenClosedScanner:
    """PHP Open/Closed Principle (OCP) validator.

    Detects ``if/elseif`` chains that use ``instanceof`` to branch on
    subtypes — an OCP violation.  All functions are exposed as
    ``@staticmethod`` methods on this class.
    """

    # Default threshold: 3+ instanceof branches in an if/elseif chain.
    _DEFAULT_MIN_BRANCHES = 3

    @staticmethod
    def _ensure_php_engine() -> None:
        """Ensure the PHPEngine is registered (idempotent)."""
        EngineRegistry.ensure(PHPEngine())

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
    def _contains_instanceof(node: Node) -> bool:
        """Return ``True`` if *node* or any descendant contains ``instanceof``.

        In the tree-sitter-php grammar, ``$a instanceof Foo`` is a
        ``binary_expression`` with an ``instanceof`` child node.
        """
        return any(desc.type == "instanceof" for desc in OpenClosedScanner._iter_descendants(node))

    @staticmethod
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
                if OpenClosedScanner._contains_instanceof(child):
                    count += 1
                break  # only the first parenthesized_expression is the if condition

        # Check each ``else_if_clause`` condition.
        for child in if_node.children:
            if child.type == "else_if_clause":
                for sub in child.children:
                    if sub.type == "parenthesized_expression":
                        if OpenClosedScanner._contains_instanceof(sub):
                            count += 1
                        break

        return count

    @staticmethod
    def _scan_tree(path: Path, min_branches: int) -> list[Finding]:
        """Parse *path* with PHPEngine and walk the raw AST for OCP violations."""
        OpenClosedScanner._ensure_php_engine()
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

        for desc in OpenClosedScanner._iter_descendants(root):
            if desc.type != "if_statement":
                continue
            branch_count = OpenClosedScanner._count_instanceof_branches(desc)
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

    @staticmethod
    def scan_module(module: ModuleInfo, min_branches: int | None = None) -> list[Finding]:
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
        if min_branches is None:
            min_branches = OpenClosedScanner._DEFAULT_MIN_BRANCHES
        if module.has_syntax_error:
            return []
        if module.language != "php":
            return []
        return OpenClosedScanner._scan_tree(module.path, min_branches)

    @staticmethod
    def scan_file(path: Path, min_branches: int | None = None) -> list[Finding]:
        """Scan a single PHP file for OCP violations.

        Args:
            path: Path to a ``.php`` source file.
            min_branches: The minimum instanceof branch count to flag.

        Returns:
            A list of :class:`Finding` objects (empty if no engine matches,
            the file has a syntax error, or tree-sitter-php is not installed).

        """
        if min_branches is None:
            min_branches = OpenClosedScanner._DEFAULT_MIN_BRANCHES
        OpenClosedScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        return OpenClosedScanner.scan_module(module, min_branches=min_branches)

    @staticmethod
    def main() -> int:
        """Entry point for the PHP Open/Closed Principle validator CLI."""
        parser = argparse.ArgumentParser(
            description=(
                "PHP Open/Closed Principle (OCP) validator — detect if/elseif instanceof chains."
            )
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        OpenClosedScanner._ensure_php_engine()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_ocp")
        php_langs = ProjectConfig.languages_for_extensions(languages, {".php"})
        if not php_langs:
            ProjectConfig.emit_skipped(args.json, "check_ocp disabled in settings.json")
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, php_langs))
        if not roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1

        raw_min = ProjectConfig.setting(settings, "php.patterns.ocp_min_branches", None)
        min_branches = (
            raw_min if isinstance(raw_min, int) else OpenClosedScanner._DEFAULT_MIN_BRANCHES
        )

        all_findings: list[Finding] = []
        scanned_files = 0
        for root in roots:
            for php_file in ProjectConfig.iter_files(root, {".php"}):
                scanned_files += 1
                all_findings.extend(
                    OpenClosedScanner.scan_file(php_file, min_branches=min_branches)
                )

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(r) for r in roots],
                        "scanned_files": scanned_files,
                        "min_branches": min_branches,
                        "violation_count": len(all_findings),
                        "violations": [
                            {
                                "file": f.file,
                                "line": f.line,
                                "severity": f.severity,
                                "description": f.description,
                            }
                            for f in all_findings
                        ],
                    },
                    indent=2,
                )
            )
            return 0

        print("=" * 70)
        print("PHP OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT")
        print("=" * 70)

        if all_findings:
            print(f"\n## OCP violations ({len(all_findings)} found)\n")
            for f in all_findings:
                print(f"  {f.description}")
                print(f"    -> {f.file}:{f.line}")
                print("    Fix: replace instanceof branching with polymorphism")
        else:
            print(f"\n## OCP violations: none (threshold: {min_branches} branches)")

        print()
        if all_findings:
            print("Result: OCP violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(OpenClosedScanner.main())  # pragma: no cover
