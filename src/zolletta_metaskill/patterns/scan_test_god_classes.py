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


def _test_class_metrics(module: ModuleInfo) -> list[dict[str, Any]]:
    """Compute raw test class metric dicts from a :class:`ModuleInfo`.

    Args:
        module: The parsed module to inspect.

    Returns:
        A list of dicts with keys ``file``, ``class``, ``lines``, ``methods``,
        ``method_names``, ``start``, and ``end``.

    """
    results: list[dict[str, Any]] = []
    for cls in module.classes:
        start = cls.lineno
        end = cls.end_lineno
        lines = end - start + 1
        method_names = [m.name for m in cls.methods]
        results.append({
            "file": str(module.path),
            "class": cls.name,
            "lines": lines,
            "methods": len(cls.methods),
            "method_names": method_names,
            "start": start,
            "end": end,
        })
    return results


def scan_module(module: ModuleInfo) -> list[Finding]:
    """Scan a :class:`ModuleInfo` and return test class metric findings.

    Args:
        module: The parsed module to inspect.

    Returns:
        A list of :class:`Finding` objects, one per class.

    """
    findings: list[Finding] = []
    for r in _test_class_metrics(module):
        findings.append(Finding(
            file=r["file"],
            line=r["start"],
            category="test_god_class",
            severity="low",
            description=(
                f"class={r['class']} lines={r['lines']} "
                f"methods={r['methods']} "
                f"method_names={','.join(r['method_names'])} "
                f"start={r['start']} end={r['end']}"
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
    """Entry point for the test God class scanner CLI."""
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

    _ensure_python_engine()
    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_results: list[dict[str, Any]] = []
    for py in root.rglob("*.py"):
        engine = get_engine_for_file(py)
        if engine is None:  # pragma: no cover
            continue
        module = engine.parse_module(py)
        all_results.extend(_test_class_metrics(module))

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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
