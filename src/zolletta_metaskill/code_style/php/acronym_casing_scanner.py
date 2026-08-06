#!/usr/bin/env python3
"""Check that acronyms in PHP class names stay fully uppercase.

Reports PHP class names where a known acronym appears in mixed case or
lowercase instead of fully uppercase. For example, if ``API`` is a known
acronym, ``ApiGateway`` is flagged (should be ``APIGateway``).

The scanner is deterministic: the same input + acronym list always
produces the same output. This replaces manual review of acronym casing,
which was non-deterministic.

**Algorithm**:

1. Split each PascalCase class name into words (e.g. ``APIGateway``
   → ``["API", "Gateway"]``, ``HttpClientFactory`` →
   ``["Http", "Client", "Factory"]``).
2. For each word, check if it case-insensitively matches a known acronym.
3. If it matches but is not all-uppercase, flag it as a violation.

**Acronym list**: the shipped ``assets/acronyms.json`` (common SE acronyms)
is always loaded. Project-specific acronyms from ``settings.json`` are
**merged** with the shipped list (additive, not replacing). The
``--acronyms`` CLI flag fully replaces both (for testing/debugging).

Usage:
    python3 acronym_casing_scanner.py <directory> [--acronyms CI,MR,HTTP] \
[--strict] [--json] [--skip]

Arguments:
    directory       Root source directory to scan (default: src)

Options:
    --acronyms LIST    Comma-separated list of acronyms to check (default: built-in list)
    --settings PATH    Path to settings.json to read the acronym list from
    --strict           Exit with code 1 if violations are found
    --json             Output as JSON instead of markdown
    --skip             Skip this check entirely (exit 0 with 'skipped' message)

Exit code: 0 if no violations (or --strict not set or --skip),
           1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine, _have_tree_sitter_php


class AcronymCasingScanner:
    """Check that acronyms in PHP class names stay fully uppercase.

    All standalone functions are exposed as ``@staticmethod`` methods on
    this class. There are no module-level constants — all constants are
    class-level attributes.
    """

    # Minimal fallback acronym list used when the shipped JSON is missing.
    _FALLBACK_ACRONYMS = [
        "API",
        "AST",
        "CD",
        "CI",
        "CLI",
        "DI",
        "HTTP",
        "HTTPS",
        "JSON",
        "MR",
        "SQL",
        "URL",
        "XML",
        "YAML",
    ]

    # Directories to ignore when scanning (checked against relative path parts).
    _IGNORE_DIRS = {
        "vendor",
        "node_modules",
        "dist",
        "build",
        ".git",
    }

    # ------------------------------------------------------------------
    # Acronym loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_default_acronyms() -> list[str]:
        """Load the built-in acronym list.

        Returns the minimal hardcoded fallback list. The shipped
        ``acronyms.json`` is shared with the Python scanner; if it is
        available it is loaded, otherwise the fallback is used.
        """
        # Try the shared assets file (same location the Python scanner uses).
        script_dir = Path(__file__).resolve().parent
        candidates = [
            script_dir / "assets" / "acronyms.json",  # installed package layout
            script_dir.parents[3] / "python-code-style" / "assets" / "acronyms.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                    acronyms = data.get("acronyms", [])
                    if isinstance(acronyms, list) and acronyms:
                        return [a.upper() for a in acronyms if isinstance(a, str)]
                except (OSError, json.JSONDecodeError):
                    pass
        return list(AcronymCasingScanner._FALLBACK_ACRONYMS)

    @staticmethod
    def _load_acronyms_from_settings(settings_path: Path) -> list[str] | None:
        """Load the acronym list from settings.json if present.

        Reads the top-level ``acronyms`` array — a list of uppercase
        acronym strings. Returns None if the key is absent.
        """
        if not settings_path.exists():
            return None
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            acronyms = data.get("acronyms")
            if isinstance(acronyms, list) and acronyms:
                return [a.upper() for a in acronyms]
        except (json.JSONDecodeError, OSError):
            pass
        return None

    # ------------------------------------------------------------------
    # PascalCase splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_pascal_case(name: str) -> list[str]:
        """Split a PascalCase name into words.

        Handles acronyms correctly:
          - ``APIGateway`` → ``["API", "Gateway"]``
          - ``HTTPClientFactory`` → ``["HTTP", "Client", "Factory"]``
          - ``HttpClientFactory`` → ``["Http", "Client", "Factory"]``
          - ``MyDIProvider`` → ``["My", "DI", "Provider"]``
          - ``MRBranchResolver`` → ``["MR", "Branch", "Resolver"]``
        """
        if not name:
            return []

        # Insert boundary before uppercase-followed-by-lowercase when preceded
        # by uppercase: "HTTPClient" -> "HTTP|Client"
        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1|\2", name)
        # Insert boundary before uppercase after lowercase: "aB" -> "a|B"
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1|\2", s)
        # Insert boundary before digit after letter: "HTTP2" -> "HTTP|2"
        s = re.sub(r"([A-Za-z])([0-9])", r"\1|\2", s)

        return [w for w in s.split("|") if w]

    # ------------------------------------------------------------------
    # PHP class extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_php_engine() -> None:
        """Ensure the PHPEngine is registered (idempotent)."""
        EngineRegistry.ensure(PHPEngine())

    @staticmethod
    def _get_class_names(path: Path) -> list[tuple[str, int]]:
        """Return ``(class_name, line_number)`` for every class-like decl.

        Uses :class:`PHPEngine` to parse the PHP file via tree-sitter-php
        and extracts names from ``class``, ``interface``, and ``trait``
        declarations.

        Returns an empty list if tree-sitter-php is not installed, the
        file cannot be read, or the file has a syntax error.
        """
        if not _have_tree_sitter_php():
            return []
        AcronymCasingScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None or not isinstance(engine, PHPEngine):  # pragma: no cover
            return []
        try:
            module = engine.parse_module(path)
        except (OSError, ImportError):  # pragma: no cover
            return []
        if module.has_syntax_error:
            return []
        return [(cls.name, cls.lineno) for cls in module.classes]

    # ------------------------------------------------------------------
    # CLI entry point
    # ------------------------------------------------------------------

    @staticmethod
    def main() -> int:
        """Entry point for the PHP acronym casing checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check that acronyms in PHP class names stay fully uppercase. "
            "Splits PascalCase names into words and flags any word that "
            "case-insensitively matches a known acronym but isn't all-uppercase."
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default="src",
            help="Root source directory to scan (default: src)",
        )
        parser.add_argument(
            "--acronyms",
            default=None,
            help="Comma-separated list of acronyms to check (overrides settings.json and defaults)",
        )
        parser.add_argument(
            "--settings",
            default=None,
            help="Path to settings.json to read the acronym list from "
            "(reads the top-level acronyms array)",
        )
        parser.add_argument("--strict", action="store_true", help="Exit 1 if violations found")
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        parser.add_argument(
            "--skip",
            action="store_true",
            help="Skip this check entirely (exit 0 with 'skipped' message)",
        )
        args = parser.parse_args()

        if args.skip:
            if not args.json:
                print("=" * 70)
                print("PHP ACRONYM CASING — VALIDATION REPORT")
                print("=" * 70)
                print("\nResult: SKIPPED (--skip flag)\n")
            return 0

        # If tree-sitter-php is not installed, skip with a message.
        if not _have_tree_sitter_php():
            if not args.json:
                print("=" * 70)
                print("PHP ACRONYM CASING — VALIDATION REPORT")
                print("=" * 70)
                print(
                    "\nResult: SKIPPED (tree-sitter-php not installed. "
                    "Install with: uv add tree-sitter tree-sitter-php)\n"
                )
            else:
                print(
                    json.dumps(
                        {
                            "total_classes": 0,
                            "violation_count": 0,
                            "acronyms_checked": [],
                            "violations": [],
                            "skipped": "tree-sitter-php not installed",
                        },
                        indent=2,
                    )
                )
            return 0

        # Determine the acronym list.
        # - --acronyms CLI flag: fully replaces (for testing/debugging)
        # - settings.json: merged with shipped list (additive, sorted, unique)
        # - shipped acronyms.json: always loaded as the base
        defaults = AcronymCasingScanner._load_default_acronyms()
        if args.acronyms is not None:
            acronyms = [a.strip().upper() for a in args.acronyms.split(",") if a.strip()]
        else:
            # Start with the shipped list, then merge project-specific acronyms
            combined = set(defaults)
            settings_path = (
                Path(args.settings) if args.settings else Path(".zolletta-metaskill/settings.json")
            )
            project_acronyms = AcronymCasingScanner._load_acronyms_from_settings(settings_path)
            if project_acronyms:
                combined.update(project_acronyms)
            acronyms = sorted(combined)

        acronym_lower_map = {a.lower(): a for a in acronyms}

        src_root = Path(args.directory)
        if not src_root.exists():
            print(f"Error: directory '{src_root}' does not exist", file=sys.stderr)
            return 1

        violations: list[dict[str, Any]] = []
        total_classes = 0

        for php_file in sorted(src_root.rglob("*.php")):
            # Check only the relative path parts so that system temp
            # directories (e.g. /var/folders/...) are not mistaken for
            # ignored source directories.
            try:
                rel_parts = php_file.relative_to(src_root).parts
            except ValueError:  # pragma: no cover
                rel_parts = php_file.parts
            if any(part in AcronymCasingScanner._IGNORE_DIRS for part in rel_parts):
                continue

            classes = AcronymCasingScanner._get_class_names(php_file)
            for class_name, line_no in classes:
                total_classes += 1
                words = AcronymCasingScanner._split_pascal_case(class_name)
                for word in words:
                    word_lower = word.lower()
                    if word_lower in acronym_lower_map:
                        expected = acronym_lower_map[word_lower]
                        if word != expected:
                            violations.append(
                                {
                                    "file": str(php_file.relative_to(src_root)),
                                    "line": line_no,
                                    "class": class_name,
                                    "word": word,
                                    "expected": expected,
                                }
                            )

        if args.json:
            print(
                json.dumps(
                    {
                        "total_classes": total_classes,
                        "violation_count": len(violations),
                        "acronyms_checked": sorted(acronyms),
                        "violations": violations,
                    },
                    indent=2,
                )
            )
        else:
            print("=" * 70)
            print("PHP ACRONYM CASING — VALIDATION REPORT")
            print("=" * 70)
            print(f"\nSource directory: {src_root}")
            print(f"Acronyms checked: {', '.join(sorted(acronyms))}")
            print(f"Total classes scanned: {total_classes}")
            print(f"Violations: {len(violations)}")
            print()

            if violations:
                print(f"{'File':<55} {'Line':>5} {'Class':<35} {'Word':<10} {'Expected':<10}")
                print("-" * 120)
                for v in violations:
                    print(
                        f"{v['file']:<55} {v['line']:>5} {v['class']:<35} "
                        f"{v['word']:<10} {v['expected']:<10}"
                    )
                print()
                print("These class names contain an acronym in mixed case or lowercase.")
                print("The convention requires acronyms to stay fully uppercase.")
                print("Rename the class to use the uppercase acronym form.")
            else:
                print("All class names use acronyms in the correct uppercase form.\n")

        if args.strict and violations:
            return 1
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(AcronymCasingScanner.main())
