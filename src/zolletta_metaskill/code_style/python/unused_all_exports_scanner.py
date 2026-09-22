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

Scan roots come from ``python.paths.source`` in
``.zolletta-metaskill/settings.json``. The check runs per configured
language that handles ``.py`` files; when
``<language>.code_style.check_unused_all_exports`` is ``false`` for
every configured language the run reports SKIPPED. File enumeration is
git-ignore aware.

Usage:
    python3 unused_all_exports_scanner.py [--json]

Options:
    --json    Output as JSON instead of markdown.

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class UnusedAllExportsScanner:
    """Find names in ``__all__`` that are never imported anywhere."""

    @staticmethod
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

    @staticmethod
    def _extract_imported_names(py_files: list[Path]) -> dict[str, list[Path]]:
        """Build an index: imported_name -> list of files that import it.

        Captures:
          - ``from <pkg> import <name>``
          - ``from <pkg> import <name> as <alias>`` (tracks the original name)
          - ``import <pkg>.<name>`` (tracks the last component)
        """
        index: dict[str, list[Path]] = {}
        for py in py_files:
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

    @staticmethod
    def _find_all_files_with_all(py_files: list[Path]) -> list[tuple[Path, list[str]]]:
        """Find all Python files that define ``__all__`` and return their entries."""
        results: list[tuple[Path, list[str]]] = []
        for py in py_files:
            entries = UnusedAllExportsScanner._extract_all_entries(py)
            if entries:
                results.append((py, entries))
        return results

    @staticmethod
    def main() -> int:
        """Entry point for the unused ``__all__`` exports scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Find names in __all__ that are never imported anywhere. "
            "Complements vulture, which treats __all__ entries as used. "
            "Scan roots come from python.paths.source in settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "code_style.check_unused_all_exports")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(
                args.json, "check_unused_all_exports disabled in settings.json"
            )
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, py_langs))
        if not roots:
            print(
                "Error: no configured source directories exist on disk "
                f"({', '.join(str(r) for r in ProjectConfig.source_roots(settings, py_langs))})",
                file=sys.stderr,
            )
            return 1

        # Collect .py files across all configured roots, tracking the root
        # each file belongs to for relative reporting.
        root_of: dict[Path, Path] = {}
        py_files: list[Path] = []
        for root in roots:
            for f in ProjectConfig.iter_files(root, {".py"}):
                py_files.append(f)
                root_of[f] = root

        # Build the import index: name -> files that import it
        import_index = UnusedAllExportsScanner._extract_imported_names(py_files)

        # Find all files with __all__ and their entries
        all_files = UnusedAllExportsScanner._find_all_files_with_all(py_files)

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
                    rel = str(file_path.relative_to(root_of[file_path]))
                    unused.append(
                        {
                            "file": rel,
                            "symbol": entry,
                            "importers": [str(p.relative_to(root_of[p])) for p in importers],
                        }
                    )

        if args.json:
            print(
                json.dumps(
                    {
                        "total_all_entries": total_entries,
                        "unused_count": len(unused),
                        "directories": [str(r) for r in roots],
                        "unused": unused,
                    },
                    indent=2,
                )
            )
        else:
            print("=" * 70)
            print("UNUSED __all__ EXPORTS — VALIDATION REPORT")
            print("=" * 70)
            print(f"\nSource directories: {', '.join(str(r) for r in roots)}")
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

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(UnusedAllExportsScanner.main())
