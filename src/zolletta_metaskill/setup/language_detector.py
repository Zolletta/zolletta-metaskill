#!/usr/bin/env python3
"""Detect the project's primary language from marker files.

Checks for language markers in the project root in priority order and
returns the first match. Supports glob patterns for ``requirements*.txt``
and ``*.gemspec``.

Usage:
    python3 language_detector.py [directory]

Arguments:
    directory       Project root to check (default: current directory)

Exit code: 0 if a language was detected, 1 if no marker was found.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


class LanguageDetector:
    """Detect the project's primary language from marker files."""

    # (language, exact filenames, glob patterns)
    # Checked in this order — first match wins.
    _MARKERS: list[tuple[str, list[str], list[str]]] = [
        (
            "python",
            ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "uv.lock"],
            ["requirements*.txt"],
        ),
        ("typescript", ["package.json", "tsconfig.json", "deno.json"], []),
        ("php", ["composer.json"], []),
        ("go", ["go.mod"], []),
        ("rust", ["Cargo.toml"], []),
        ("java", ["pom.xml", "build.gradle"], []),
        ("ruby", ["Gemfile"], ["*.gemspec"]),
        ("c-cpp", ["CMakeLists.txt"], []),
    ]

    @staticmethod
    def detect_language(project_root: Path) -> str | None:
        """Detect the primary language of the project at *project_root*.

        Args:
            project_root: Path to the project root directory.

        Returns:
            The detected language identifier (e.g. ``"python"``, ``"php"``),
            or ``None`` if no marker was found.

        """
        for lang, exact_files, glob_patterns in LanguageDetector._MARKERS:
            for name in exact_files:
                if (project_root / name).exists():
                    return lang
            for pattern in glob_patterns:
                if list(project_root.glob(pattern)):
                    return lang

        # C/C++ special case: Makefile with .c/.cpp sources
        if (project_root / "Makefile").exists():
            for ext in ("*.c", "*.cpp"):
                if list(project_root.glob(ext)):
                    return "c-cpp"

        return None

    @staticmethod
    def main() -> int:
        """Entry point for the language detector CLI."""
        parser = argparse.ArgumentParser(
            description="Detect the project's primary language from marker files."
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default=".",
            help="Project root to check (default: current directory)",
        )
        args = parser.parse_args()

        root = Path(args.directory)
        if not root.is_dir():
            print(f"Error: '{root}' is not a directory", file=sys.stderr)
            return 1

        lang = LanguageDetector.detect_language(root)
        if lang is not None:
            print(lang)
            return 0
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(LanguageDetector.main())
