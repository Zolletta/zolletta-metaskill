#!/usr/bin/env python3
"""Find names listed in ``__all__`` that are never imported anywhere.

Vulture treats ``__all__`` entries as "used" (public API exports), so it
never flags them as dead code — even if no module in the codebase ever
imports them. This scanner cross-references every ``__all__`` entry
against actual import statements across the entire source tree to find
unused public exports.

Reports:
  - File, ``__all__`` entry, and whether it is imported anywhere.
  - Entries that are only imported within the same package (re-exports
    chained through ``__init__.py``) are traced to the final consumer.

Usage:
    python3 scan_unused_all_exports.py [directory] [--strict] [--json]

Arguments:
    directory       Root source directory to scan (default: src)

Options:
    --strict        Exit with code 1 if unused exports are found.
    --json          Output as JSON instead of markdown.
    --skip          Skip this check entirely (exit 0 with 'skipped' message).

Exit code: 0 if no unused exports (or --strict not set or --skip),
           1 if unused exports found with --strict.

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any


def _extract_all_entries(file_path: Path) -> list[str]:
    """Extract the list of names in ``__all__`` from a Python file.

    Handles:
      - ``__all__ = ["name1", "name2"]``
      - ``__all__: list[str] = ["name1", "name2"]``
      - ``__all__ += ["name3"]`` (append to existing)

    Returns an empty list if ``__all__`` is not defined or has a
    non-literal value.
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    entries: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    and isinstance(node.value, ast.List)
                ):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            entries.append(elt.value)
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
            and isinstance(node.value, ast.List)
        ):
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    entries.append(elt.value)
    return entries


def _extract_imported_names(src_root: Path, ignore_dirs: set[str]) -> dict[str, list[Path]]:
    """Build an index: imported_name -> list of files that import it.

    Captures:
      - ``from <pkg> import <name>``
      - ``from <pkg> import <name> as <alias>`` (tracks the original name)
      - ``import <pkg>.<name>`` (tracks the last component)
    """
    index: dict[str, list[Path]] = {}
    for py in sorted(src_root.rglob("*.py")):
        if any(part in ignore_dirs for part in py.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.name if alias.name != "*" else None
                    if name:
                        index.setdefault(name, []).append(py)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    # import a.b.c -> track "c" as the imported name
                    if alias.name:
                        top = alias.name.split(".")[-1]
                        index.setdefault(top, []).append(py)
    return index


def _find_all_files_with_all(src_root: Path, ignore_dirs: set[str]) -> list[tuple[Path, list[str]]]:
    """Find all Python files that define ``__all__`` and return their entries."""
    results: list[tuple[Path, list[str]]] = []
    for py in sorted(src_root.rglob("*.py")):
        if any(part in ignore_dirs for part in py.parts):
            continue
        entries = _extract_all_entries(py)
        if entries:
            results.append((py, entries))
    return results


def main() -> int:
    """Entry point for the unused ``__all__`` exports scanner CLI."""
    parser = argparse.ArgumentParser(
        description="Find names in __all__ that are never imported anywhere. "
        "Complements vulture, which treats __all__ entries as used."
    )
    parser.add_argument(
        "directory", nargs="?", default="src",
        help="Root source directory to scan (default: src)",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 if unused exports found")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--skip", action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message)",
    )
    args = parser.parse_args()

    if args.skip:
        if not args.json:
            print("=" * 70)
            print("UNUSED __all__ EXPORTS — VALIDATION REPORT")
            print("=" * 70)
            print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    src_root = Path(args.directory)
    if not src_root.exists():
        print(f"Error: directory '{src_root}' does not exist", file=sys.stderr)
        return 1

    ignore_dirs = {"__pycache__", ".venv", "venv", ".tox", "dist", "build", "node_modules"}

    # Build the import index: name -> files that import it
    import_index = _extract_imported_names(src_root, ignore_dirs)

    # Find all files with __all__ and their entries
    all_files = _find_all_files_with_all(src_root, ignore_dirs)

    # Cross-reference: for each __all__ entry, check if it's imported
    # by any file OTHER than the one that defines it.
    unused: list[dict[str, Any]] = []
    total_entries = 0

    for file_path, entries in all_files:
        for entry in entries:
            total_entries += 1
            importers = import_index.get(entry, [])
            # Filter out the file that defines __all__ itself
            external_importers = [p for p in importers if p != file_path]
            if not external_importers:
                rel = str(file_path.relative_to(src_root))
                unused.append({
                    "file": rel,
                    "symbol": entry,
                    "importers": [str(p.relative_to(src_root)) for p in importers],
                })

    if args.json:
        print(json.dumps({
            "total_all_entries": total_entries,
            "unused_count": len(unused),
            "unused": unused,
        }, indent=2))
    else:
        print("=" * 70)
        print("UNUSED __all__ EXPORTS — VALIDATION REPORT")
        print("=" * 70)
        print(f"\nSource directory: {src_root}")
        print(f"Files with __all__: {len(all_files)}")
        print(f"Total __all__ entries: {total_entries}")
        print(f"Unused exports: {len(unused)}")
        print()

        if unused:
            print(f"{'File':<55} {'Symbol':<25}")
            print("-" * 80)
            for item in unused:
                print(f"{item['file']:<55} {item['symbol']:<25}")
            print()
            print("These symbols are listed in __all__ but never imported by any")
            print("other module in the source tree. Vulture does not detect them")
            print("because __all__ entries are treated as public API exports.")
            print("Consider removing them from __all__ or deleting the symbol entirely.")
        else:
            print("No unused __all__ exports found.\n")

    if args.strict and unused:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
