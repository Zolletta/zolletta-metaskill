#!/usr/bin/env python3
"""Check test function naming against the ``test_<unit>_<scenario>_<expected>``
convention.

Reports test functions whose name (after stripping the ``test_`` prefix) has
fewer than ``--min-segments`` underscore-separated segments. The convention
expects at least 3 segments: the unit under test, the scenario, and the
expected outcome.

Example::

    # Good — 3 segments: init, with_valid_dependencies, stores_attributes
    test_init_with_valid_dependencies_stores_attributes

    # Bad — 1 segment: init (no scenario, no expected outcome)
    test_init

    # Bad — 2 segments: to_dict, returns_expected (missing unit context)
    test_to_dict_returns_expected

The scanner is deterministic: the same input always produces the same output.
This replaces manual AI review of test function names, which was
non-deterministic and produced different violation counts on each run.

Usage:
    python3 scan_test_naming.py <directory> [--min-segments N] [--strict] [--json] [--skip]

Arguments:
    directory       Root test directory to scan (default: tests)

Options:
    --min-segments N   Minimum segments after test_ (default: 3)
    --strict           Exit with code 1 if violations are found
    --json             Output as JSON instead of markdown
    --skip             Skip this check entirely (exit 0 with 'skipped' message)

Exit code: 0 if no violations (or --strict not set or --skip),
           1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path


def _count_segments(func_name: str) -> int:
    """Count underscore-separated segments after the ``test_`` prefix.

    Returns 0 if the name doesn't start with ``test_``.
    """
    if not func_name.startswith("test_"):
        return 0
    rest = func_name[len("test_"):]
    # Filter out empty segments (e.g. test__foo) and count non-empty parts
    segments = [s for s in rest.split("_") if s]
    return len(segments)


def _find_test_functions(file_path: Path) -> list[tuple[str, int]]:
    """Return (function_name, line_number) for every test_ function in a file."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    results: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_") or isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
            results.append((node.name, node.lineno))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check test function naming: test_<unit>_<scenario>_<expected>. "
        "Flags functions with fewer than --min-segments segments after test_."
    )
    parser.add_argument(
        "directory", nargs="?", default="tests",
        help="Root test directory to scan (default: tests)",
    )
    parser.add_argument(
        "--min-segments", type=int, default=3,
        help="Minimum segments after test_ prefix (default: 3)",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 if violations found")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--skip", action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message)",
    )
    args = parser.parse_args()

    if args.skip:
        if not args.json:
            print("=" * 70)
            print("TEST FUNCTION NAMING — VALIDATION REPORT")
            print("=" * 70)
            print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    test_root = Path(args.directory)
    if not test_root.exists():
        print(f"Error: directory '{test_root}' does not exist", file=sys.stderr)
        return 1

    ignore_dirs = {"__pycache__", ".venv", "venv", ".tox", "dist", "build"}

    violations: list[dict] = []
    total_test_functions = 0

    for py in sorted(test_root.rglob("*.py")):
        if any(part in ignore_dirs for part in py.parts):
            continue
        # Only scan test files (test_*.py or *_test.py)
        if not (py.name.startswith("test_") or py.name.endswith("_test.py")):
            continue

        test_funcs = _find_test_functions(py)
        for func_name, line_no in test_funcs:
            total_test_functions += 1
            segments = _count_segments(func_name)
            if segments < args.min_segments:
                violations.append({
                    "file": str(py.relative_to(test_root)),
                    "line": line_no,
                    "function": func_name,
                    "segments": segments,
                    "min_required": args.min_segments,
                })

    if args.json:
        print(json.dumps({
            "total_test_functions": total_test_functions,
            "violation_count": len(violations),
            "min_segments": args.min_segments,
            "violations": violations,
        }, indent=2))
    else:
        print("=" * 70)
        print("TEST FUNCTION NAMING — VALIDATION REPORT")
        print("=" * 70)
        print(f"\nTest directory: {test_root}")
        print(f"Minimum segments after test_: {args.min_segments}")
        print(f"Total test functions scanned: {total_test_functions}")
        print(f"Violations: {len(violations)}")
        if total_test_functions > 0:
            pct = (len(violations) / total_test_functions) * 100
            print(f"Violation rate: {pct:.1f}%")
        print()

        if violations:
            print(f"{'File':<55} {'Line':>5} {'Function':<45} {'Segs':>5}")
            print("-" * 115)
            for v in violations:
                print(f"{v['file']:<55} {v['line']:>5} {v['function']:<45} {v['segments']:>5}")
            print()
            print(f"These test functions have fewer than {args.min_segments} segments")
            print("after the test_ prefix. The convention expects:")
            print("  test_<unit>_<scenario>_<expected_outcome>")
            print("Rename to include the scenario and expected outcome.")
        else:
            print("All test functions meet the naming convention.\n")

    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
