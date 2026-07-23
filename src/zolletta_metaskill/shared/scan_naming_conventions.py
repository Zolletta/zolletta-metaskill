#!/usr/bin/env python3
"""Check naming conventions for source files and test files.

Reports two categories of violations:

1. **Source file name != class name** — each source file containing exactly one
   class should have a filename that matches the class name (snake_case file ->
   PascalCase class). Files with 0 or 2+ classes are skipped (handled by
   ``scan_one_class_per_file.py``).

2. **Test file naming** — every ``test_*.py`` file must follow the convention::

       test_<source_stem><eventual_suffix>.py

   where ``<source_stem>`` is the stem of a source file (or the snake_case form
   of a source class name) in the mirrored source directory, and ``<eventual_suffix>``
   is an optional ``_word`` suffix used when a single source file's tests are split
   across multiple files (e.g. ``test_cache_operations.py``, ``test_cache_init.py``).

   Test files whose name does not match any source file or class in the mirrored
   directory are reported as naming violations (orphan or misnamed tests).

Usage:
    python3 scan_naming_conventions.py --src <src_root> --tests <test_root>
        [--src-package <name>] [--tests-package <name>]
        [--ignore-dirs <dir1,dir2,...>] [--strict] [--skip]

Arguments:
    --src            Source root directory (default: src)
    --tests          Test root directory (default: tests)
    --src-package    Package path within --src to use as mirror base
                     (default: auto-detect first child of --src)
    --tests-package  Package path within --tests to use as mirror base
                     (default: same as --src-package)
    --ignore-dirs    Comma-separated dir names to skip (e.g. assets,templates)
    --strict         Exit with code 1 if violations are found
    --skip           Skip this check entirely (exit 0 with 'skipped' message).
                     Use for projects that intentionally don't follow these
                     conventions.

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.common.registry import (
    ensure_engine,
    get_engine_for_file,
)
from zolletta_metaskill.engines.python_engine import PythonEngine


def _ensure_python_engine() -> None:
    """Ensure the PythonEngine is registered."""
    ensure_engine(PythonEngine())


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase (e.g. my_class -> MyClass)."""
    return "".join(word.capitalize() for word in name.split("_"))


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case (e.g. MyClass -> my_class)."""
    return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")


def _get_class_names(path: Path) -> list[str]:
    """Return top-level class names defined in a source file.

    Uses the registered language engine to parse the file, so no ``ast``
    import is needed here.
    """
    _ensure_python_engine()
    engine = get_engine_for_file(path)
    if engine is None:  # pragma: no cover
        return []
    module = engine.parse_module(path)
    if module.has_syntax_error:
        return []
    return [cls.name for cls in module.classes]


def _auto_detect_package(src_root: Path) -> str | None:
    """Auto-detect the package path under src/ (first child dir with __init__.py)."""
    for child in sorted(src_root.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            return child.name
    for child in sorted(src_root.iterdir()):
        if child.is_dir():
            return child.name
    return None


def _build_source_index(
    src_pkg: Path, ignore_dirs: set[str]
) -> dict[Path, set[str]]:
    """Build an index: relative_dir -> set of valid test-name prefixes.

    For each source file in a directory, the valid prefixes are:
      - ``test_<source_stem>`` (file-name based)
      - ``test_<snake_case_class_name>`` for each class in the file (class-name based)
    """
    index: dict[Path, set[str]] = {}
    for py in sorted(src_pkg.rglob("*.py")):
        if any(part in ignore_dirs for part in py.parts):
            continue
        if py.name == "__init__.py":
            continue

        rel_dir = py.relative_to(src_pkg).parent
        prefixes = index.setdefault(rel_dir, set())
        prefixes.add(f"test_{py.stem}")

        for cls_name in _get_class_names(py):
            prefixes.add(f"test_{_pascal_to_snake(cls_name)}")

    return index


def _matches_prefix(test_stem_rest: str, prefixes: set[str]) -> str | None:
    """Return the matching prefix if test_stem_rest starts with a valid prefix.

    A prefix matches if:
      - ``test_stem_rest == prefix`` (exact, no suffix), or
      - ``test_stem_rest.startswith(prefix + "_")`` (suffix after underscore)

    Returns the longest matching prefix (most specific) or None.
    """
    matches = []
    for prefix in prefixes:
        # prefix is like "test_cache" — but test_stem_rest is like "cache_operations"
        # (the "test_" has already been stripped). So we compare against prefix[5:].
        bare = prefix[5:]  # strip "test_" from prefix
        if test_stem_rest == bare or test_stem_rest.startswith(bare + "_"):
            matches.append(prefix)
    if not matches:
        return None
    return max(matches, key=len)


def main() -> int:
    """Entry point for the naming conventions checker CLI."""
    parser = argparse.ArgumentParser(
        description="Check naming conventions: source file name == class name, "
        "test files named test_<source_stem><suffix>.py."
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
        "--strict",
        action="store_true",
        help="Exit with code 1 if violations are found",
    )
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message). "
        "Use for projects that intentionally don't follow these conventions.",
    )
    args = parser.parse_args()

    _ensure_python_engine()
    if args.skip:
        print("=" * 70)
        print("NAMING CONVENTIONS — VALIDATION REPORT")
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

    # --- Check 1: source file name == class name ---
    name_mismatch: list[dict[str, Any]] = []
    for py in sorted(src_pkg.rglob("*.py")):
        if any(part in ignore_dirs for part in py.parts):
            continue
        if py.name == "__init__.py":
            continue

        classes = _get_class_names(py)
        if len(classes) != 1:
            continue

        cls_name = classes[0]
        expected_pascal = _snake_to_pascal(py.stem)
        if cls_name != expected_pascal and cls_name != py.stem:
            name_mismatch.append({
                "file": str(py.relative_to(src_pkg)),
                "class": cls_name,
                "expected": expected_pascal,
            })

    # --- Check 2: test file naming convention ---
    source_index = _build_source_index(src_pkg, ignore_dirs)
    orphan_tests: list[dict[str, Any]] = []

    for test_py in sorted(test_pkg.rglob("test_*.py")):
        if any(part in ignore_dirs for part in test_py.parts):
            continue
        if test_py.name == "conftest.py":  # pragma: no cover
            continue

        rel_dir = test_py.relative_to(test_pkg).parent
        stem = test_py.stem  # e.g. "test_cache_operations"

        # Skip test files that don't start with "test_" (shouldn't happen due to glob)
        if not stem.startswith("test_"):  # pragma: no cover
            continue

        test_stem_rest = stem[5:]  # e.g. "cache_operations"

        # Skip common non-SUT test files
        if test_stem_rest in {"", "conftest"}:
            continue

        prefixes = source_index.get(rel_dir, set())
        if not prefixes:
            orphan_tests.append({
                "file": str(test_py.relative_to(test_pkg)),
                "reason": f"no source directory at {rel_dir}/",
            })
            continue

        match = _matches_prefix(test_stem_rest, prefixes)
        if match is None:
            orphan_tests.append({
                "file": str(test_py.relative_to(test_pkg)),
                "reason": f"no source file or class matching '{test_stem_rest}' "
                f"in {rel_dir}/",
            })

    has_violations = bool(name_mismatch or orphan_tests)

    print("=" * 70)
    print("NAMING CONVENTIONS — VALIDATION REPORT")
    print("=" * 70)
    print(f"\nSource package:  {src_pkg}")
    print(f"Test package:    {test_pkg}")

    if name_mismatch:
        print(f"\n## Source file name != class name ({len(name_mismatch)} files)\n")
        for item in name_mismatch:
            print(f"  {item['class']}")
            print(f"    -> {item['file']}")
            print(f"    Expected: {item['expected']} "
                  f"(or rename file to match class)")
    else:
        print("\n## Source file name != class name: none")

    if orphan_tests:
        print(f"\n## Test files not matching naming convention ({len(orphan_tests)} files)\n")
        for item in orphan_tests:
            print(f"  {item['file']}")
            print(f"    Reason: {item['reason']}")
            print("    Expected: test_<source_stem><eventual_suffix>.py")
    else:
        print("\n## Test files not matching naming convention: none")

    print()
    if has_violations and args.strict:
        print("Result: VIOLATIONS FOUND (strict mode)")
        return 1
    elif has_violations:
        print("Result: violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
