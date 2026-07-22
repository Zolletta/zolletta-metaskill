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
import ast
import sys
from pathlib import Path


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase (e.g. my_class -> MyClass)."""
    return "".join(word.capitalize() for word in name.split("_"))


def scan_file(path: Path) -> dict:
    """Scan a single .py file and return its class info."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {"file": str(path), "classes": [], "error": True}

    classes = [
        {"name": n.name, "line": n.lineno}
        for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef)
    ]
    return {"file": str(path), "classes": classes, "error": False}


def main() -> int:
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

    multi_class: list[dict] = []
    zero_class: list[str] = []
    name_mismatch: list[dict] = []

    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        if py.name == "__init__.py":
            continue

        info = scan_file(py)
        if info.get("error"):
            continue

        classes = info["classes"]
        rel_path = str(py.relative_to(root))

        if len(classes) > 1:
            multi_class.append({
                "file": rel_path,
                "count": len(classes),
                "names": [c["name"] for c in classes],
            })
        elif len(classes) == 0:
            if not args.ignore_zero:
                zero_class.append(rel_path)
        else:
            # Exactly 1 class — check name match
            cls = classes[0]
            expected_pascal = _snake_to_pascal(py.stem)
            if cls["name"] != expected_pascal and cls["name"] != py.stem:
                name_mismatch.append({
                    "file": rel_path,
                    "class": cls["name"],
                    "line": cls["line"],
                    "expected": expected_pascal,
                })

    has_violations = bool(multi_class or name_mismatch or zero_class)

    print("=" * 70)
    print("1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT")
    print("=" * 70)

    if multi_class:
        print(f"\n## Files with 2+ classes ({len(multi_class)} files)\n")
        for item in multi_class:
            print(f"  {item['count']} classes: {', '.join(item['names'])}")
            print(f"    -> {item['file']}")
            print("    Fix: split into one file per class")
    else:
        print("\n## Files with 2+ classes: none")

    if name_mismatch:
        print(f"\n## Class name != filename ({len(name_mismatch)} files)\n")
        for item in name_mismatch:
            print(f"  {item['class']} (line {item['line']})")
            print(f"    -> {item['file']}")
            print(f"    Expected: {item['expected']} (or rename file to {item['class']})")
    else:
        print("\n## Class name != filename: none")

    if not args.ignore_zero:
        if zero_class:
            print(f"\n## Files with 0 classes ({len(zero_class)} files)\n")
            for f in zero_class:
                print(f"  {f}")
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


if __name__ == "__main__":
    sys.exit(main())
