#!/usr/bin/env python3
"""Check the '1 class 1 file, 1 file 1 class' convention.

Reports three categories of violations:
  - Files with 2+ classes (should be split into separate files)
  - Files with 0 classes that are not __init__.py (utility/constant files —
    reported as low severity, not errors)
  - Class names that don't match the filename (snake_case -> PascalCase)

Usage:
    python3 scan_one_class_per_file.py [directory] [--strict] [--ignore-zero]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --strict        Treat name mismatches and zero-class files as errors
                    (exit code 1). Default: report only, exit 0.
    --ignore-zero   Don't report files with 0 classes (useful for projects
                    that allow utility modules with only functions).
    --skip          Skip this check entirely (exit 0 with 'skipped' message).
                    Use for projects that intentionally don't follow this
                    convention.

Exit code: 0 if no violations (or --strict not set or --skip), 1 if
           violations found with --strict.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from zolletta_metaskill.common.models import Finding, ModuleInfo
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


def scan_module(module: ModuleInfo) -> list[Finding]:
    """Scan a parsed module and return findings for class-structure violations.

    Args:
        module: The :class:`ModuleInfo` produced by an engine.

    Returns:
        A list of :class:`Finding` objects.  Categories:
        ``"multi_class"`` (2+ classes), ``"zero_class"`` (no classes),
        ``"name_mismatch"`` (class name != filename).

    """
    if module.has_syntax_error:
        return []

    classes = module.classes
    file_path = str(module.path)

    if len(classes) > 1:
        names = ", ".join(c.name for c in classes)
        return [
            Finding(
                file=file_path,
                line=classes[0].lineno,
                category="multi_class",
                severity="high",
                description=f"{len(classes)} classes: {names}",
                fix_type="manual",
            )
        ]

    if len(classes) == 0:
        return [
            Finding(
                file=file_path,
                line=0,
                category="zero_class",
                severity="low",
                description="No classes (utility/helper module)",
                fix_type="skip",
            )
        ]

    # Exactly 1 class — check name match
    cls = classes[0]
    expected_pascal = _snake_to_pascal(module.path.stem)
    if cls.name != expected_pascal and cls.name != module.path.stem:
        return [
            Finding(
                file=file_path,
                line=cls.lineno,
                category="name_mismatch",
                severity="medium",
                description=(
                    f"Class '{cls.name}' doesn't match filename. "
                    f"Expected '{expected_pascal}' (or rename file to match class)"
                ),
                fix_type="manual",
            )
        ]

    return []


def scan_file(path: Path) -> list[Finding]:
    """Backward-compatible wrapper that uses the registry to get an engine.

    Args:
        path: Path to a source file.

    Returns:
        A list of :class:`Finding` objects (empty if no engine matches or
        the file has a syntax error).

    """
    _ensure_python_engine()
    engine = get_engine_for_file(path)
    if engine is None:  # pragma: no cover
        return []
    module = engine.parse_module(path)
    return scan_module(module)


def main() -> int:
    """Entry point for the one-class-per-file checker CLI."""
    parser = argparse.ArgumentParser(
        description="Check '1 class 1 file, 1 file 1 class' convention."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="src",
        help="Root directory to scan (default: src)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if violations are found",
    )
    parser.add_argument(
        "--ignore-zero",
        action="store_true",
        help="Don't report files with 0 classes",
    )
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message). "
             "Use for projects that intentionally don't follow this convention.",
    )
    args = parser.parse_args()

    _ensure_python_engine()
    if args.skip:
        print("=" * 70)
        print("1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_findings: list[Finding] = []
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        if py.name == "__init__.py":
            continue
        all_findings.extend(scan_file(py))

    if args.ignore_zero:
        all_findings = [f for f in all_findings if f.category != "zero_class"]

    multi_class = [f for f in all_findings if f.category == "multi_class"]
    zero_class = [f for f in all_findings if f.category == "zero_class"]
    name_mismatch = [f for f in all_findings if f.category == "name_mismatch"]

    has_violations = bool(multi_class or name_mismatch or zero_class)

    print("=" * 70)
    print("1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT")
    print("=" * 70)

    if multi_class:
        print(f"\n## Files with 2+ classes ({len(multi_class)} files)\n")
        for f in multi_class:
            rel = str(Path(f.file).relative_to(root))
            print(f"  {f.description}")
            print(f"    -> {rel}")
            print("    Fix: split into one file per class")
    else:
        print("\n## Files with 2+ classes: none")

    if name_mismatch:
        print(f"\n## Class name != filename ({len(name_mismatch)} files)\n")
        for f in name_mismatch:
            rel = str(Path(f.file).relative_to(root))
            print(f"  {f.description} (line {f.line})")
            print(f"    -> {rel}")
    else:
        print("\n## Class name != filename: none")

    if not args.ignore_zero:
        if zero_class:
            print(f"\n## Files with 0 classes ({len(zero_class)} files)\n")
            for f in zero_class:
                rel = str(Path(f.file).relative_to(root))
                print(f"  {rel}")
            if not args.strict:
                print("  (Low severity — utility/helper modules. Use --ignore-zero to hide.)")
        else:
            print("\n## Files with 0 classes: none")

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
