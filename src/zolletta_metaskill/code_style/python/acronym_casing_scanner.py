#!/usr/bin/env python3
"""Check that acronyms in class names stay fully uppercase.

Reports class names where a known acronym appears in mixed case or
lowercase instead of fully uppercase. For example, if ``CI`` is a known
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
is always loaded. Project-specific acronyms from ``settings.json``
(top-level ``acronyms`` array) are **merged** with the shipped list
(additive, not replacing).

Scan roots come from ``python.paths.source`` in
``.zolletta-metaskill/settings.json``. The check runs per configured
language that handles ``.py`` files; when
``<language>.code_style.check_acronym_casing`` is ``false`` for every
configured language the run reports SKIPPED. File enumeration is
git-ignore aware.

Usage:
    python3 acronym_casing_scanner.py [--json]

Options:
    --json    Output as JSON instead of markdown

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class AcronymCasingScanner:
    """Check that acronyms in class names stay fully uppercase."""

    # Path to the shipped acronym list — check skill folder first, then src/.
    _SCRIPT_DIR = Path(__file__).resolve().parent
    _ACRONYMS_JSON = (
        _SCRIPT_DIR / "assets" / "acronyms.json"  # installed package layout
        if (_SCRIPT_DIR / "assets" / "acronyms.json").exists()
        else _SCRIPT_DIR.parents[3]
        / "python-code-style"
        / "assets"
        / "acronyms.json"  # source layout
    )

    @staticmethod
    def _load_default_acronyms() -> list[str]:
        """Load the built-in acronym list from ``assets/acronyms.json``.

        Falls back to a minimal hardcoded list if the JSON file is missing
        (e.g. the script was copied without the assets directory).
        """
        try:
            data = json.loads(AcronymCasingScanner._ACRONYMS_JSON.read_text(encoding="utf-8"))
            acronyms = data.get("acronyms", [])
            if isinstance(acronyms, list) and acronyms:
                return [a.upper() for a in acronyms if isinstance(a, str)]
        except (OSError, json.JSONDecodeError):
            pass
        # Minimal fallback if the JSON is unavailable
        return [
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

    @staticmethod
    def _split_pascal_case(name: str) -> list[str]:
        """Split a PascalCase name into words.

        Handles acronyms correctly:
          - ``APIGateway`` → ``["API", "Gateway"]``
          - ``HTTPClientFactory`` → ``["HTTP", "Client", "Factory"]``
          - ``HttpClientFactory`` → ``["Http", "Client", "Factory"]``
          - ``MyDIProvider`` → ``["My", "DI", "Provider"]``
          - ``MRBranchResolver`` → ``["MR", "Branch", "Resolver"]``

        Algorithm:
          - Insert a boundary before an uppercase letter that is followed by
            a lowercase letter, if the previous character is also uppercase
            (handles ``HTTPClient`` → ``HTTP`` | ``Client``).
          - Insert a boundary before any uppercase letter that follows a
            lowercase letter (handles ``myClass`` → ``my`` | ``Class``,
            but class names are PascalCase so this is for safety).
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

    @staticmethod
    def _get_class_names(path: Path) -> list[tuple[str, int]]:
        """Return (class_name, line_number) for every class in a .py file."""
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            return []
        results: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                results.append((node.name, node.lineno))
        return results

    @staticmethod
    def _project_acronyms(settings: dict[str, Any]) -> list[str]:
        """Return the project acronym list from parsed settings.json.

        Reads the top-level ``acronyms`` array — a list of acronym
        strings, returned uppercased. Empty list when the key is absent
        or not a list.
        """
        acronyms = settings.get("acronyms")
        if isinstance(acronyms, list) and acronyms:
            return [a.upper() for a in acronyms if isinstance(a, str)]
        return []

    @staticmethod
    def main() -> int:
        """Entry point for the acronym casing checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check that acronyms in class names stay fully uppercase. "
            "Splits PascalCase names into words and flags any word that "
            "case-insensitively matches a known acronym but isn't all-uppercase. "
            "Scan roots come from python.paths.source in settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_acronym_casing"
        )
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(
                args.json, "check_acronym_casing disabled in settings.json"
            )
            return 0

        roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, py_langs)
        )
        if not roots:
            print(
                "Error: no configured source directories exist on disk "
                f"({', '.join(str(r) for r in ProjectConfig.source_roots(settings, py_langs))})",
                file=sys.stderr,
            )
            return 1

        # Shipped acronyms.json merged with project-specific settings acronyms.
        combined = set(AcronymCasingScanner._load_default_acronyms())
        combined.update(AcronymCasingScanner._project_acronyms(settings))
        acronyms = sorted(combined)
        acronym_lower_map = {a.lower(): a for a in acronyms}

        violations: list[dict[str, Any]] = []
        total_classes = 0

        for root in roots:
            for py in ProjectConfig.iter_files(root, {".py"}):
                if py.name == "__init__.py":
                    continue
                classes = AcronymCasingScanner._get_class_names(py)
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
                                        "file": str(py.relative_to(root)),
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
                        "acronyms_checked": acronyms,
                        "directories": [str(r) for r in roots],
                        "violations": violations,
                    },
                    indent=2,
                )
            )
        else:
            print("=" * 70)
            print("ACRONYM CASING — VALIDATION REPORT")
            print("=" * 70)
            print(f"\nSource directories: {', '.join(str(r) for r in roots)}")
            print(f"Acronyms checked: {', '.join(acronyms)}")
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

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(AcronymCasingScanner.main())
