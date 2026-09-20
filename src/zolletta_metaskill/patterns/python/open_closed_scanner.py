#!/usr/bin/env python3
"""Open/Closed Principle (OCP) validator.

Detects patterns where adding a new type requires modifying existing code
instead of extending it. The canonical OCP solution is polymorphism (strategy
pattern, plugin registry) — the validator flags code that uses type-based
branching instead.

Checks:
  - if/elif chains that compare type names (string comparison or isinstance
    ladders with 3+ branches)
  - getattr(obj, "method_name_" + type_name) dynamic dispatch by string
  - match/case statements on type (Python 3.10+)

These are signals that the code is "open for modification" instead of "open
for extension."

Scan roots come from ``python.paths.source`` in ``settings.json``; the
branch threshold comes from ``python.patterns.ocp_min_branches`` (default
3). The check runs when ``python.patterns.check_ocp`` is not ``false``.
File enumeration is git-ignore aware.

Usage:
    python3 open_closed_scanner.py [--json]

Options:
    --json            Output as JSON instead of markdown.

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class OpenClosedScanner:
    """Open/Closed Principle (OCP) validator."""

    @staticmethod
    def _is_type_check(node: ast.AST) -> bool:
        """Check if a condition is an isinstance() or type() comparison."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "isinstance":
                return True
            if node.func.id == "type":
                return True
        # type(obj) == SomeClass
        if isinstance(node, ast.Compare):
            if (
                isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "type"
            ):
                return True
            # obj.__class__.__name__ == "SomeClass"
            if isinstance(node.left, ast.Attribute) and node.left.attr == "__name__":
                return True
        # String comparison: obj.type == "something" or obj.__class__.__name__
        if isinstance(node, ast.Compare):
            left = node.left
            if isinstance(left, ast.Attribute) and left.attr in ("type", "kind", "__class__"):
                return True
        return False

    @staticmethod
    def _count_type_branches(node: ast.If) -> int:
        """Count how many branches in an if/elif chain do type checks."""
        count = 0
        current = node
        while isinstance(current, ast.If):
            if OpenClosedScanner._is_type_check(
                current.test
            ) or OpenClosedScanner._contains_type_check(current.test):
                count += 1
            # Check elif chain
            if (
                current.orelse
                and len(current.orelse) == 1
                and isinstance(current.orelse[0], ast.If)
            ):
                current = current.orelse[0]
            else:
                # Final else doesn't count as a type branch
                break
        return count

    @staticmethod
    def _contains_type_check(node: ast.AST) -> bool:
        """Check if a boolean expression contains a type check."""
        if isinstance(node, ast.BoolOp):
            return any(
                OpenClosedScanner._is_type_check(v) or OpenClosedScanner._contains_type_check(v)
                for v in node.values
            )
        return OpenClosedScanner._is_type_check(node)

    @staticmethod
    def _is_string_type_dispatch(node: ast.Call) -> bool:
        """Detect getattr(obj, 'method_' + type_name) dynamic dispatch."""
        if not isinstance(node, ast.Call):
            return False
        if not isinstance(node.func, ast.Attribute):
            return False
        if node.func.attr != "getattr":
            # Direct attribute access with string concat: obj.__getattr__("method_" + x)
            return False
        if len(node.args) >= 2:
            second = node.args[1]
            # Check for string concatenation: "prefix_" + variable
            if isinstance(second, ast.BinOp) and isinstance(second.op, ast.Add):
                return True
            if isinstance(second, ast.JoinedStr):
                return True
        return False

    @staticmethod
    def _find_match_on_type(node: ast.Match) -> bool:
        """Check if a match statement matches on type/class."""
        for case in node.cases:
            pattern = case.pattern
            if isinstance(pattern, ast.MatchClass):
                return True
        return False

    @staticmethod
    def scan_file(path: Path) -> list[dict[str, Any]]:
        """Scan a file for OCP violations."""
        violations: list[dict[str, Any]] = []
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            # if/elif type ladders
            if isinstance(node, ast.If):
                branch_count = OpenClosedScanner._count_type_branches(node)
                if branch_count >= 3:
                    violations.append(
                        {
                            "type": "type_ladder",
                            "file": str(path),
                            "line": node.lineno,
                            "branches": branch_count,
                            "detail": f"if/elif chain with {branch_count} type-check branches",
                        }
                    )

            # getattr dynamic dispatch
            if isinstance(node, ast.Call) and OpenClosedScanner._is_string_type_dispatch(node):
                violations.append(
                    {
                        "type": "string_dispatch",
                        "file": str(path),
                        "line": node.lineno,
                        "branches": 0,
                        "detail": "getattr() with dynamic string — consider polymorphism",
                    }
                )

            # match/case on type (Python 3.10+)
            if isinstance(node, ast.Match) and OpenClosedScanner._find_match_on_type(node):
                case_count = sum(1 for c in node.cases if isinstance(c.pattern, ast.MatchClass))
                if case_count >= 3:
                    violations.append(
                        {
                            "type": "match_on_type",
                            "file": str(path),
                            "line": node.lineno,
                            "branches": case_count,
                            "detail": f"match/case on type with {case_count} class patterns",
                        }
                    )

        return violations

    @staticmethod
    def main() -> int:
        """Entry point for the Open/Closed Principle validator CLI."""
        parser = argparse.ArgumentParser(
            description="Open/Closed Principle (OCP) validator. "
            "Roots come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_ocp")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(args.json, "check_ocp disabled in settings.json")
            return 0

        roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, py_langs)
        )
        if not roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1

        limits: list[int] = []
        for lang in sorted(py_langs):
            value = ProjectConfig.setting(settings, f"{lang}.patterns.ocp_min_branches", None)
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        min_branches = min(limits) if limits else 3

        all_violations: list[dict[str, Any]] = []
        for root in roots:
            for py in ProjectConfig.iter_files(root, {".py"}):
                violations = OpenClosedScanner.scan_file(py)
                for v in violations:
                    v["file"] = str(py.relative_to(root))
                    all_violations.append(v)

        # Filter by min-branches for type ladders
        filtered = [
            v
            for v in all_violations
            if v["type"] != "type_ladder" or v["branches"] >= min_branches
        ]

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "min_branches": min_branches,
                        "violation_count": len(filtered),
                        "violations": filtered,
                    },
                    indent=2,
                )
            )
            return 0

        print("=" * 70)
        print("OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT")
        print("=" * 70)

        if filtered:
            print(f"\n## OCP violations ({len(filtered)} found)\n")
            for v in filtered:
                print(f"  [{v['type']}] {v['detail']}")
                print(f"    -> {v['file']}:{v['line']}")
                print("    Fix: replace type branching with polymorphism (strategy pattern,")
                print("         plugin registry, or protocol-based dispatch)")
        else:
            print("\n## OCP violations: none")

        print()
        if filtered:
            print("Result: OCP violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(OpenClosedScanner.main())
