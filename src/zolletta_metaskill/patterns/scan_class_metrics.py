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
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.common.models import Finding, ModuleInfo
from zolletta_metaskill.common.registry import (
    ensure_engine,
    get_engine_for_file,
)
from zolletta_metaskill.engines.python_engine import PythonEngine


def _ensure_python_engine() -> None:
    """Ensure the PythonEngine is registered."""
    ensure_engine(PythonEngine())


def _class_metrics(module: ModuleInfo) -> list[dict[str, Any]]:
    """Compute raw class metric dicts from a :class:`ModuleInfo`.

    Args:
        module: The parsed module to inspect.

    Returns:
        A list of dicts with keys ``file``, ``class``, ``lines``, ``methods``,
        ``public``, ``attrs``, ``start``, and ``end``.

    """
    results: list[dict[str, Any]] = []
    for cls in module.classes:
        start = cls.lineno
        end = cls.end_lineno
        lines = end - start + 1
        methods = len(cls.methods)
        public = sum(1 for m in cls.methods if m.is_public)
        attrs = len(cls.attributes)
        results.append({
            "file": str(module.path),
            "class": cls.name,
            "lines": lines,
            "methods": methods,
            "public": public,
            "attrs": attrs,
            "start": start,
            "end": end,
        })
    return results


def scan_module(module: ModuleInfo) -> list[Finding]:
    """Scan a :class:`ModuleInfo` and return class metric findings.

    Args:
        module: The parsed module to inspect.

    Returns:
        A list of :class:`Finding` objects, one per class.

    """
    findings: list[Finding] = []
    for r in _class_metrics(module):
        findings.append(Finding(
            file=r["file"],
            line=r["start"],
            category="class_metrics",
            severity="low",
            description=(
                f"class={r['class']} lines={r['lines']} "
                f"methods={r['methods']} public={r['public']} "
                f"attrs={r['attrs']} start={r['start']} end={r['end']}"
            ),
            fix_type="skip",
        ))
    return findings


def scan_file(path: Path) -> list[Finding]:
    """Backward-compatible wrapper that uses the registry to get an engine.

    Args:
        path: Path to a Python source file.

    Returns:
        A list of :class:`Finding` objects for each class in the file.

    """
    _ensure_python_engine()
    engine = get_engine_for_file(path)
    if engine is None:
        return []
    module = engine.parse_module(path)
    return scan_module(module)


def main() -> int:
    """Entry point for the class metrics scanner CLI."""
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

    _ensure_python_engine()
    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_results: list[dict[str, Any]] = []
    for py in root.rglob("*.py"):
        engine = get_engine_for_file(py)
        if engine is None:
            continue
        module = engine.parse_module(py)
        all_results.extend(_class_metrics(module))

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
