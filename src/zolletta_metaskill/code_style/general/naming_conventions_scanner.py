#!/usr/bin/env python3
"""Check naming conventions for source files and test files.

Reports two categories of violations:

1. **Source file name != class name** — each source file containing exactly one
   class should have a filename that matches the class name (snake_case file ->
   PascalCase class). Files with 0 or 2+ classes are skipped (handled by
   ``one_class_per_file_scanner.py``).

2. **Test file naming** — every ``test_*.py`` file must follow the convention::

       test_<source_stem><eventual_suffix>.py

   where ``<source_stem>`` is the stem of a source file (or the snake_case form
   of a source class name) in the mirrored source directory, and ``<eventual_suffix>``
   is an optional ``_word`` suffix used when a single source file's tests are split
   across multiple files (e.g. ``test_cache_operations.py``, ``test_cache_init.py``).

   Test files whose name does not match any source file or class in the mirrored
   directory are reported as naming violations (orphan or misnamed tests).

Configuration comes from ``.zolletta-metaskill/settings.json``:

- Scan roots: ``python.paths.source`` / ``python.paths.tests`` (``src`` /
  ``tests`` when unconfigured), enumerated with git-ignore awareness.
- Mirror package: ``python.paths.package`` (auto-detected from the first
  source root when ``null``).
- ``python.code_style.check_filename_matches_class`` — when false for
  every configured language the run reports SKIPPED.

Usage:
    python3 naming_conventions_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 always (report-only); 1 on usage errors such as no
           configured source/test directory existing on disk.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig


class NamingConventionsScanner:
    """Check naming conventions for source files and test files."""

    @staticmethod
    def _snake_to_pascal(name: str) -> str:
        """Convert snake_case to PascalCase (e.g. my_class -> MyClass)."""
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def _pascal_to_snake(name: str) -> str:
        """Convert PascalCase to snake_case (e.g. MyClass -> my_class)."""
        return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")

    @staticmethod
    def _get_class_names(path: Path) -> list[str]:
        """Return top-level class names defined in a source file.

        Uses the registered language engine to parse the file, so no ``ast``
        import is needed here.
        """
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        if module.has_syntax_error:
            return []
        return [cls.name for cls in module.classes]

    @staticmethod
    def _auto_detect_package(src_root: Path) -> str | None:
        """Auto-detect the package path under src/ (first child dir with __init__.py)."""
        for child in sorted(src_root.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child.name
        for child in sorted(src_root.iterdir()):
            if child.is_dir():
                return child.name
        return None

    @staticmethod
    def _build_source_index(src_pkg: Path) -> dict[Path, set[str]]:
        """Build an index: relative_dir -> set of valid test-name prefixes.

        For each source file in a directory, the valid prefixes are:
          - ``test_<source_stem>`` (file-name based)
          - ``test_<snake_case_class_name>`` for each class in the file (class-name based)
        """
        index: dict[Path, set[str]] = {}
        for py in ProjectConfig.iter_files(src_pkg, {".py"}):
            if py.name == "__init__.py":
                continue

            rel_dir = py.relative_to(src_pkg).parent
            prefixes = index.setdefault(rel_dir, set())
            prefixes.add(f"test_{py.stem}")

            for cls_name in NamingConventionsScanner._get_class_names(py):
                prefixes.add(f"test_{NamingConventionsScanner._pascal_to_snake(cls_name)}")

        return index

    @staticmethod
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

    @staticmethod
    def main() -> int:
        """Entry point for the naming conventions checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check naming conventions: source file name == class name, "
            "test files named test_<source_stem><suffix>.py. Roots and package "
            "come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_filename_matches_class"
        )
        if not languages:
            if args.json:
                print(
                    json.dumps(
                        {
                            "skipped": True,
                            "reason": "check_filename_matches_class disabled in settings.json",
                        }
                    )
                )
            else:
                print("=" * 70)
                print("NAMING CONVENTIONS — VALIDATION REPORT")
                print("=" * 70)
                print(
                    "\nResult: SKIPPED "
                    "(check_filename_matches_class disabled in settings.json)\n"
                )
            return 0

        python_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        src_roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, python_langs)
        )
        test_roots = ProjectConfig.existing_roots(
            ProjectConfig.test_roots(settings, python_langs)
        )
        if not src_roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1
        if not test_roots:
            print(
                "Error: no configured test directories exist on disk",
                file=sys.stderr,
            )
            return 1

        pkg_name = ProjectConfig.package_name(
            settings, "python"
        ) or NamingConventionsScanner._auto_detect_package(src_roots[0])
        if not pkg_name:
            print("Error: could not auto-detect package under src/", file=sys.stderr)
            return 1

        src_pkgs = [root / pkg_name for root in src_roots if (root / pkg_name).is_dir()]
        test_pkgs = [root / pkg_name for root in test_roots if (root / pkg_name).is_dir()]
        if not src_pkgs:
            print(
                f"Error: source package '{pkg_name}' does not exist under any "
                "configured source root",
                file=sys.stderr,
            )
            return 1
        if not test_pkgs:
            print(
                f"Error: test package '{pkg_name}' does not exist under any "
                "configured test root",
                file=sys.stderr,
            )
            return 1

        # --- Check 1: source file name == class name ---
        name_mismatch: list[dict[str, Any]] = []
        for src_pkg in src_pkgs:
            for py in ProjectConfig.iter_files(src_pkg, {".py"}):
                if py.name == "__init__.py":
                    continue

                classes = NamingConventionsScanner._get_class_names(py)
                if len(classes) != 1:
                    continue

                cls_name = classes[0]
                expected_pascal = NamingConventionsScanner._snake_to_pascal(py.stem)
                if cls_name != expected_pascal and cls_name != py.stem:
                    name_mismatch.append(
                        {
                            "file": str(py.relative_to(src_pkg)),
                            "class": cls_name,
                            "expected": expected_pascal,
                        }
                    )

        # --- Check 2: test file naming convention ---
        source_index: dict[Path, set[str]] = {}
        for src_pkg in src_pkgs:
            for rel_dir, prefixes in NamingConventionsScanner._build_source_index(
                src_pkg
            ).items():
                source_index.setdefault(rel_dir, set()).update(prefixes)
        orphan_tests: list[dict[str, Any]] = []

        for test_pkg in test_pkgs:
            for test_py in ProjectConfig.iter_files(test_pkg, {".py"}):
                if not test_py.name.startswith("test_"):
                    continue
                if test_py.name == "conftest.py":  # pragma: no cover
                    continue

                rel_dir = test_py.relative_to(test_pkg).parent
                stem = test_py.stem  # e.g. "test_cache_operations"

                # Skip test files that don't start with "test_" (shouldn't happen)
                if not stem.startswith("test_"):  # pragma: no cover
                    continue

                test_stem_rest = stem[5:]  # e.g. "cache_operations"

                # Skip common non-SUT test files
                if test_stem_rest in {"", "conftest"}:
                    continue

                prefixes = source_index.get(rel_dir, set())
                if not prefixes:
                    orphan_tests.append(
                        {
                            "file": str(test_py.relative_to(test_pkg)),
                            "reason": f"no source directory at {rel_dir}/",
                        }
                    )
                    continue

                match = NamingConventionsScanner._matches_prefix(test_stem_rest, prefixes)
                if match is None:
                    orphan_tests.append(
                        {
                            "file": str(test_py.relative_to(test_pkg)),
                            "reason": f"no source file or class matching '{test_stem_rest}' "
                            f"in {rel_dir}/",
                        }
                    )

        has_violations = bool(name_mismatch or orphan_tests)

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": {
                            "source": [str(root) for root in src_roots],
                            "tests": [str(root) for root in test_roots],
                        },
                        "package": pkg_name,
                        "name_mismatch": name_mismatch,
                        "orphan_tests": orphan_tests,
                        "violation_count": len(name_mismatch) + len(orphan_tests),
                    },
                    indent=2,
                )
            )
            return 0

        print("=" * 70)
        print("NAMING CONVENTIONS — VALIDATION REPORT")
        print("=" * 70)
        print(f"\nSource packages: {', '.join(str(p) for p in src_pkgs)}")
        print(f"Test packages:   {', '.join(str(p) for p in test_pkgs)}")

        if name_mismatch:
            print(f"\n## Source file name != class name ({len(name_mismatch)} files)\n")
            for item in name_mismatch:
                print(f"  {item['class']}")
                print(f"    -> {item['file']}")
                print(f"    Expected: {item['expected']} (or rename file to match class)")
        else:
            print("\n## Source file name != class name: none")

        if orphan_tests:
            print(
                f"\n## Test files not matching naming convention ({len(orphan_tests)} files)\n"
            )
            for item in orphan_tests:
                print(f"  {item['file']}")
                print(f"    Reason: {item['reason']}")
                print("    Expected: test_<source_stem><eventual_suffix>.py")
        else:
            print("\n## Test files not matching naming convention: none")

        print()
        if has_violations:
            print("Result: violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(NamingConventionsScanner.main())
