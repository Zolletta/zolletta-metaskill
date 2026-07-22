#!/usr/bin/env python3
"""Scan Python test files for test class metrics and mixed-SUT detection.

Triage tool for test-side God classes. Reports test classes sorted by size,
with method count and optional method name listing. Use --show-methods to
spot test classes that test multiple unrelated SUTs.

Usage:
    python3 scan_test_god_classes.py [directory] [--top N] [--show-methods]

Arguments:
    directory       Root directory to scan (default: tests)

Options:
    --top N           Show only the top N classes (default: 30)
    --show-methods    List all method names per class (helps spot mixed SUTs)

Exit code: 0 on success, 1 if no test classes are found.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _get_class_end(node: ast.ClassDef) -> int:
    """Return the last line number of a class (including nested nodes)."""
    return max(getattr(n, "lineno", node.lineno) for n in ast.walk(node))


def scan_file(path: Path) -> list[dict]:
    """Scan a single test file and return test class metric dicts."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        start = node.lineno
        end = _get_class_end(node)
        methods = [
            n for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        results.append({
            "file": str(path),
            "class": node.name,
            "lines": end - start + 1,
            "methods": len(methods),
            "method_names": [m.name for m in methods],
            "start": start,
            "end": end,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Python test classes for size and mixed-SUT detection."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="tests",
        help="Root directory to scan (default: tests)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Show only the top N classes (default: 30)",
    )
    parser.add_argument(
        "--show-methods",
        action="store_true",
        help="List all method names per class (helps spot mixed SUTs)",
    )
    args = parser.parse_args()

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_results: list[dict] = []
    for py in root.rglob("*.py"):
        all_results.extend(scan_file(py))

    if not all_results:
        print(f"No test classes found in {root}", file=sys.stderr)
        return 1

    all_results.sort(key=lambda r: r["lines"], reverse=True)
    top = all_results[: args.top]

    if args.show_methods:
        for r in top:
            print(f"\n=== {r['class']} ({r['lines']} lines, {r['methods']} methods) ===")
            for name in r["method_names"]:
                print(f"  {name}")
    else:
        print(
            f"{'LINES':>6} {'METHODS':>7}  "
            f"CLASS  (file:start-end)"
        )
        print("-" * 100)
        for r in top:
            print(
                f"{r['lines']:>6} {r['methods']:>7}  "
                f"{r['class']}  ({r['file']}:{r['start']}-{r['end']})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
