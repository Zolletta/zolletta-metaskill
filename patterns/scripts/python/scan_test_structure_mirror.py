#!/usr/bin/env python3
"""Check that the test directory structure mirrors the source directory structure.

Reports three categories of structural mismatches:
  - Source directories with no corresponding test directory
  - Test directories with no corresponding source directory (orphan tests)
  - Source files containing classes with no corresponding test file

The script checks directory-level mirroring and file-level coverage using
prefix matching. One source class can have many test files, so the convention
is:

    src/.../my_module.py  ->  tests/.../test_my_module*.py

This matches both single-file tests (test_my_module.py) and split tests
(test_my_module_operations.py, test_my_module_init.py, etc.).
It also checks class-name-based prefixes (snake_case):
    src/.../my_module.py (class MyClass)  ->  tests/.../test_my_class*.py

Usage:
    python3 scan_test_structure_mirror.py --src <src_root> --tests <test_root>
        [--src-package <package_path>] [--tests-package <package_path>]
        [--ignore-dirs <dir1,dir2,...>]

Arguments:
    --src            Source root directory (default: src)
    --tests          Test root directory (default: tests)
    --src-package    Package path within --src to use as mirror base
                     (default: auto-detect first child of --src)
    --tests-package  Package path within --tests to use as mirror base
                     (default: same as --src-package)
    --ignore-dirs    Comma-separated dir names to skip (e.g. assets,templates)
    --skip           Skip this check entirely (exit 0 with 'skipped' message).
                     Use for projects that intentionally don't mirror test
                     structure.

Exit code: 0 if no mismatches (or --skip), 1 if mismatches found.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")


def _get_class_names(path: Path) -> list[str]:
    """Return class names defined in a .py file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    return [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]


def _auto_detect_package(src_root: Path) -> str | None:
    """Auto-detect the package path under src/ (first child dir with __init__.py)."""
    for child in sorted(src_root.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            return child.name
    # Fallback: first child dir
    for child in sorted(src_root.iterdir()):
        if child.is_dir():
            return child.name
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that test directory structure mirrors source structure."
    )
    parser.add_argument("--src", default="src", help="Source root (default: src)")
    parser.add_argument("--tests", default="tests", help="Test root (default: tests)")
    parser.add_argument(
        "--src-package",
        default=None,
        help="Package path within --src (default: auto-detect)",
    )
    parser.add_argument(
        "--tests-package",
        default=None,
        help="Package path within --tests (default: same as --src-package)",
    )
    parser.add_argument(
        "--ignore-dirs",
        default="",
        help="Comma-separated dir names to skip (e.g. assets,templates)",
    )
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message). "
             "Use for projects that intentionally don't mirror test structure.",
    )
    args = parser.parse_args()

    if args.skip:
        print("=" * 70)
        print("TEST STRUCTURE MIRROR — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    src_root = Path(args.src)
    test_root = Path(args.tests)
    if not src_root.exists():
        print(f"Error: src directory '{src_root}' does not exist", file=sys.stderr)
        return 1
    if not test_root.exists():
        print(f"Error: tests directory '{test_root}' does not exist", file=sys.stderr)
        return 1

    ignore_dirs = set(args.ignore_dirs.split(",")) if args.ignore_dirs else set()
    ignore_dirs.update({"__pycache__"})

    # Resolve package roots
    src_pkg_name = args.src_package or _auto_detect_package(src_root)
    if not src_pkg_name:
        print("Error: could not auto-detect package under src/", file=sys.stderr)
        return 1
    tests_pkg_name = args.tests_package or src_pkg_name

    src_pkg = src_root / src_pkg_name
    test_pkg = test_root / tests_pkg_name

    if not src_pkg.exists():
        print(f"Error: src package '{src_pkg}' does not exist", file=sys.stderr)
        return 1
    if not test_pkg.exists():
        print(f"Error: test package '{test_pkg}' does not exist", file=sys.stderr)
        return 1

    # Collect relative directory paths
    def _collect_dirs(root: Path) -> set[Path]:
        result = set()
        for p in root.rglob("*"):
            if not p.is_dir():
                continue
            if any(part in ignore_dirs for part in p.parts):
                continue
            result.add(p.relative_to(root))
        return result

    src_dirs = _collect_dirs(src_pkg)
    test_dirs = _collect_dirs(test_pkg)

    src_only_dirs = sorted(src_dirs - test_dirs)
    test_only_dirs = sorted(test_dirs - src_dirs)

    # Collect src files with classes and check for matching test files
    missing_tests: list[dict] = []
    for py in sorted(src_pkg.rglob("*.py")):
        if any(part in ignore_dirs for part in py.parts):
            continue
        if py.name == "__init__.py":
            continue

        classes = _get_class_names(py)
        if not classes:
            continue

        rel = py.relative_to(src_pkg)
        test_dir = test_pkg / rel.parent
        stem = py.stem  # filename without .py

        # Build the set of candidate test-file prefixes for this source file.
        # Convention: src/.../my_module.py -> tests/.../test_my_module*.py
        # One source class can have many test files (test_my_module_ops.py,
        # test_my_module_init.py, etc.), so we match by prefix, not exact name.
        prefixes = {f"test_{stem}"}
        for cls_name in classes:
            prefixes.add(f"test_{_pascal_to_snake(cls_name)}")

        # Check if any test file in the mirrored dir starts with a candidate prefix.
        # Matches both exact (test_cache.py) and split (test_cache_operations.py).
        if not test_dir.exists():
            missing_tests.append({
                "src_file": str(rel),
                "classes": classes,
                "expected_test_dir": str(rel.parent),
                "expected_prefix": f"test_{stem}*.py",
            })
            continue

        found = False
        for test_py in test_dir.glob("test_*.py"):
            for prefix in prefixes:
                if test_py.name == f"{prefix}.py" or test_py.name.startswith(f"{prefix}_"):
                    found = True
                    break
            if found:
                break
        if found:
            continue

        missing_tests.append({
            "src_file": str(rel),
            "classes": classes,
            "expected_test_dir": str(rel.parent),
            "expected_prefix": f"test_{stem}*.py",
        })

    has_mismatches = bool(src_only_dirs or test_only_dirs or missing_tests)

    print("=" * 70)
    print("TEST STRUCTURE MIRROR — VALIDATION REPORT")
    print("=" * 70)
    print(f"\nSource package:  {src_pkg}")
    print(f"Test package:    {test_pkg}")

    if src_only_dirs:
        print(f"\n## Source dirs with no test dir ({len(src_only_dirs)})\n")
        for d in src_only_dirs:
            print(f"  {d}/")
    else:
        print("\n## Source dirs with no test dir: none")

    if test_only_dirs:
        print(f"\n## Test dirs with no source dir ({len(test_only_dirs)})\n")
        for d in test_only_dirs:
            print(f"  {d}/")
    else:
        print("\n## Test dirs with no source dir: none")

    if missing_tests:
        print(f"\n## Source files with classes but no test file ({len(missing_tests)})\n")
        for item in missing_tests:
            print(f"  {item['src_file']}  (classes: {', '.join(item['classes'])})")
            print(f"    Expected in: {item['expected_test_dir']}/  matching: {item['expected_prefix']}")
    else:
        print("\n## Source files with classes but no test file: none")

    print()
    if has_mismatches:
        print("Result: STRUCTURAL MISMATCHES FOUND")
        return 1
    print("Result: all clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
