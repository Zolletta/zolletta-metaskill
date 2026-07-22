#!/usr/bin/env python3
"""Scan Python source files for class metrics (lines, methods, attributes).

Triage tool for God class detection. Reports every class sorted by line count,
with method count, public method count, and self.* attribute count.

Usage:
    python3 scan_class_metrics.py [directory] [--top N] [--min-lines N]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --top N         Show only the top N classes (default: 30)
    --min-lines N   Skip classes shorter than N lines (default: 50)

Exit code: 0 on success, 1 if no classes are found.

"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _get_class_end(node: ast.ClassDef) -> int:
    """Return the last line number of a class (including nested nodes)."""
    return max(getattr(n, "lineno", node.lineno) for n in ast.walk(node))


def _count_self_attrs(node: ast.ClassDef) -> int:
    """Count distinct self.* attribute accesses in a class."""
    attrs: set[str] = set()
    for n in ast.walk(node):
        if (
            isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id == "self"
        ):
            attrs.add(n.attr)
    return len(attrs)


def scan_file(path: Path) -> list[dict]:
    """Scan a single .py file and return class metric dicts."""
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
        public = [m for m in methods if not m.name.startswith("_")]
        results.append({
            "file": str(path),
            "class": node.name,
            "lines": end - start + 1,
            "methods": len(methods),
            "public": len(public),
            "attrs": _count_self_attrs(node),
            "start": start,
            "end": end,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Python source for class metrics (God class triage)."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="src",
        help="Root directory to scan (default: src)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Show only the top N classes (default: 30)",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=50,
        help="Skip classes shorter than N lines (default: 50)",
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
        print(f"No classes found in {root}", file=sys.stderr)
        return 1

    filtered = [r for r in all_results if r["lines"] >= args.min_lines]
    filtered.sort(key=lambda r: r["lines"], reverse=True)
    top = filtered[: args.top]

    print(
        f"{'LINES':>6} {'ALL':>4} {'PUB':>4} {'ATTRS':>5}  "
        f"CLASS  (file:start-end)"
    )
    print("-" * 110)
    for r in top:
        print(
            f"{r['lines']:>6} {r['methods']:>4} {r['public']:>4} {r['attrs']:>5}  "
            f"{r['class']}  ({r['file']}:{r['start']}-{r['end']})"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
