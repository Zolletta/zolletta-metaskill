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

from zolletta_metaskill.core.name_conventions import NameConventions
from zolletta_metaskill.core.project_config import ProjectConfig


class NamingConventionsScanner:
    """Check naming conventions for source files and test files."""

    # The shipped acronym list — skill folder first, then the source layout.
    # Source layout: _SCRIPT_DIR is <repo>/src/zolletta_metaskill/code_style/general/,
    # so parents[3] is the repo root. Same two-path lookup the acronym casing scanners use.
    _SCRIPT_DIR = Path(__file__).resolve().parent
    _ACRONYMS_JSON = (
        _SCRIPT_DIR / "assets" / "acronyms.json"  # installed package layout
        if (_SCRIPT_DIR / "assets" / "acronyms.json").exists()
        else _SCRIPT_DIR.parents[3]
        / "skills"
        / "zolletta-metaskill-python-code-style"
        / "assets"
        / "acronyms.json"
    )

    @staticmethod
    def _known_acronyms() -> frozenset[str]:
        """Return the uppercase acronym set the filename↔class rule accepts.

        Loaded from the shipped ``assets/acronyms.json``. The list already
        carried ``ADR``, ``PHP``, ``API`` and ``CLI`` — the filename rule simply
        never consulted it, which is why ``ADRCache`` in ``adr_cache.py`` was
        reported as a violation against an expected ``AdrCache``.
        """
        try:
            # pragma: no mutate start — equivalent on UTF-8 locales
            data = json.loads(NamingConventionsScanner._ACRONYMS_JSON.read_text(encoding="utf-8"))
            # pragma: no mutate end
            # pragma: no mutate start — [] and None both hit the isinstance/empty fallback
            acronyms = data.get("acronyms", [])
            # pragma: no mutate end
            if isinstance(acronyms, list) and acronyms:
                return frozenset(a.upper() for a in acronyms if isinstance(a, str))
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        return frozenset({"ADR", "API", "CLI", "HTTP", "JSON", "PHP", "URL"})

    @staticmethod
    def _acceptable_class_names(stem: str, acronyms: frozenset[str]) -> set[str]:
        """Return every class name *stem* may legitimately hold.

        Each snake word is either a plain capitalised word, or — when it matches
        a known acronym case-insensitively — the acronym's own spelling. So
        ``adr_client`` legitimately yields ``ADRClient``, ``AdrCLI`` and ``ADRCli``,
        and ``php_engine`` yields ``PHPEngine`` and ``PhpEngine``.

        Narrowing must stay narrow: a class that matches none of these is still
        a violation, which is what keeps the rule usable as rename evidence.
        """
        variants = {""}
        for word in stem.split("_"):
            options = {word.capitalize()}
            if word.upper() in acronyms:
                options.add(word.upper())
            variants = {prefix + option for prefix in variants for option in options}
        return variants

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
            classes = NameConventions.get_class_names(py)
            index.setdefault(rel_dir, set()).update(NameConventions.test_prefixes(py.stem, classes))

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
        # pragma: no mutate start — longest prefix is always the lexicographic max among prefix
        # matches
        return max(matches, key=len)
        # pragma: no mutate end

    @staticmethod
    def main() -> int:
        """Entry point for the naming conventions checker CLI."""
        # pragma: no mutate start — help text is not a tested contract
        parser = argparse.ArgumentParser(
            description="Check naming conventions: source file name == class name, "
            "test files named test_<source_stem><suffix>.py. Roots and package "
            "come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        # pragma: no mutate end
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
                    "\nResult: SKIPPED (check_filename_matches_class disabled in settings.json)\n"
                )
            return 0

        python_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        resolved = NamingConventionsScanner._resolve_packages(settings, python_langs)
        if resolved is None:
            return 1
        src_roots, test_roots, pkg_name, src_pkgs, test_pkgs = resolved

        name_mismatch = NamingConventionsScanner._check_name_mismatches(src_pkgs)
        orphan_tests = NamingConventionsScanner._check_orphan_tests(test_pkgs, src_pkgs)

        if args.json:
            NamingConventionsScanner._emit_json(
                src_roots, test_roots, pkg_name, name_mismatch, orphan_tests
            )
            return 0
        NamingConventionsScanner._emit_text(src_pkgs, test_pkgs, name_mismatch, orphan_tests)
        return 0

    @staticmethod
    def _resolve_packages(
        settings: dict[str, Any], python_langs: set[str]
    ) -> tuple[list[Path], list[Path], str, list[Path], list[Path]] | None:
        """Resolve source/test roots and the package dir, printing an error on failure."""
        src_roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, python_langs))
        test_roots = ProjectConfig.existing_roots(ProjectConfig.test_roots(settings, python_langs))
        if not src_roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return None
        if not test_roots:
            print(
                "Error: no configured test directories exist on disk",
                file=sys.stderr,
            )
            return None

        pkg_name = ProjectConfig.package_name(
            settings, "python"
        ) or NameConventions.auto_detect_package(src_roots[0])
        if not pkg_name:
            print("Error: could not auto-detect package under src/", file=sys.stderr)
            return None

        src_pkgs = [root / pkg_name for root in src_roots if (root / pkg_name).is_dir()]
        if not src_pkgs:
            print(
                f"Error: source package '{pkg_name}' does not exist under any "
                "configured source root",
                file=sys.stderr,
            )
            return None
        # Tests may mirror the source with or without the package directory level:
        #   src/<pkg>/core/config.py -> tests/<pkg>/core/test_config.py  (packaged)
        #   src/<pkg>/core/config.py -> tests/core/test_config.py        (flat)
        # Both layouts are valid; `structural-conventions.md` documents the flat
        # form (``src/.../cache.py -> tests/.../test_cache*.py``). Fall back to
        # the test roots themselves when no package directory is present. The
        # ``test_roots`` guard above already errors when none exist on disk, and
        # `existing_roots` filtered them to directories, so this is never empty.
        test_pkgs = [root / pkg_name for root in test_roots if (root / pkg_name).is_dir()]
        if not test_pkgs:
            test_pkgs = list(test_roots)
        return src_roots, test_roots, pkg_name, src_pkgs, test_pkgs

    @staticmethod
    def _check_name_mismatches(src_pkgs: list[Path]) -> list[dict[str, Any]]:
        """Check 1: source file name == class name."""
        name_mismatch: list[dict[str, Any]] = []
        acronyms = NamingConventionsScanner._known_acronyms()
        for src_pkg in src_pkgs:
            for py in ProjectConfig.iter_files(src_pkg, {".py"}):
                if py.name == "__init__.py":
                    continue

                classes = NameConventions.get_class_names(py)
                if len(classes) != 1:
                    continue

                cls_name = classes[0]
                expected_pascal = NameConventions.snake_to_pascal(py.stem)
                acceptable = NamingConventionsScanner._acceptable_class_names(py.stem, acronyms)
                if cls_name not in acceptable and cls_name != py.stem:
                    name_mismatch.append(
                        {
                            "file": str(py.relative_to(src_pkg)),
                            "class": cls_name,
                            "expected": expected_pascal,
                        }
                    )
        return name_mismatch

    @staticmethod
    def _check_orphan_tests(test_pkgs: list[Path], src_pkgs: list[Path]) -> list[dict[str, Any]]:
        """Check 2: test file naming convention against the source index."""
        source_index: dict[Path, set[str]] = {}
        for src_pkg in src_pkgs:
            for rel_dir, prefixes in NamingConventionsScanner._build_source_index(src_pkg).items():
                source_index.setdefault(rel_dir, set()).update(prefixes)
        orphan_tests: list[dict[str, Any]] = []

        for test_pkg in test_pkgs:
            for test_py in ProjectConfig.iter_files(test_pkg, {".py"}):
                entry = NamingConventionsScanner._check_one_test_file(
                    test_py, test_pkg, source_index
                )
                if entry:
                    orphan_tests.append(entry)
        return orphan_tests

    @staticmethod
    def _check_one_test_file(
        test_py: Path, test_pkg: Path, source_index: dict[Path, set[str]]
    ) -> dict[str, Any] | None:
        """Check one test file's naming; return an orphan entry or None."""
        if not test_py.name.startswith("test_"):
            return None
        # pragma: no mutate start — unreachable: test_ guard returns first
        if test_py.name == "conftest.py":  # pragma: no cover — unreachable defensive guard
            return None
        # pragma: no mutate end

        rel_dir = test_py.relative_to(test_pkg).parent
        stem = test_py.stem  # e.g. "test_cache_operations"

        # Skip test files that don't start with "test_" (shouldn't happen)
        if not stem.startswith("test_"):  # pragma: no cover
            return None

        test_stem_rest = stem[5:]  # e.g. "cache_operations"

        # Skip common non-SUT test files
        if test_stem_rest in {"", "conftest"}:  # pragma: no mutate — degenerate name
            return None

        # pragma: no mutate start — None default lands in the same `if not prefixes` branch
        prefixes = source_index.get(rel_dir, set())
        # pragma: no mutate end
        if not prefixes:
            return {
                "file": str(test_py.relative_to(test_pkg)),
                "reason": f"no source directory at {rel_dir}/",
            }

        match = NamingConventionsScanner._matches_prefix(test_stem_rest, prefixes)
        if match is None:
            return {
                "file": str(test_py.relative_to(test_pkg)),
                "reason": f"no source file or class matching '{test_stem_rest}' in {rel_dir}/",
            }
        return None

    @staticmethod
    def _emit_json(
        src_roots: list[Path],
        test_roots: list[Path],
        pkg_name: str,
        name_mismatch: list[dict[str, Any]],
        orphan_tests: list[dict[str, Any]],
    ) -> None:
        """Emit the JSON report."""
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

    @staticmethod
    def _emit_text(
        src_pkgs: list[Path],
        test_pkgs: list[Path],
        name_mismatch: list[dict[str, Any]],
        orphan_tests: list[dict[str, Any]],
    ) -> None:
        """Emit the text report."""
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
            print(f"\n## Test files not matching naming convention ({len(orphan_tests)} files)\n")
            for item in orphan_tests:
                print(f"  {item['file']}")
                print(f"    Reason: {item['reason']}")
                print("    Expected: test_<source_stem><eventual_suffix>.py")
        else:
            print("\n## Test files not matching naming convention: none")

        print()
        if name_mismatch or orphan_tests:
            print("Result: violations found (report-only mode)")
        else:
            print("Result: all clear")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(NamingConventionsScanner.main())
