#!/usr/bin/env python3
"""Flag source files that exceed a configurable maximum line count.

Language-agnostic sensor for the "file length" rule from Martin Fowler's
*Maintainability sensors for coding agents* ("Rules for typical AI
shortcomings"). Line count is trivial to compute for any language, so the
scanner does not parse code — it counts lines.

Which files are scanned and with what limit is driven entirely by
``.zolletta-metaskill/settings.json`` (created by the setup guard):

- The project's language(s) are read from settings.json — the top-level
  ``language`` field plus each populated ``<language>`` section — and
  mapped to file extensions via the engine registry (``python`` → ``.py``,
  ``php`` → ``.php``). Polyglot projects scan every configured language.
- Each language's ``code_style.check_file_length`` toggle is honoured:
  a language with the check disabled is not scanned, and when it is off
  for every configured language the run reports SKIPPED (exit 0).
- The limit is read from each enabled language's
  ``code_style.max_file_length`` (the smallest wins when several are
  configured); 800 is the default when none is configured.
- Scan roots come from settings: ``python.paths.source`` for Python,
  ``php.autoload.psr-4`` directories for PHP (``src`` when unconfigured).
- Files ignored by git (``.gitignore``, ``.git/info/exclude``,
  ``core.excludesFile``) are skipped — this is what keeps ``vendor/``,
  ``node_modules/``, build output, etc. out of the report. Outside a git
  repository every file matching the extensions is scanned.

Usage:
    python3 file_length_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 on success (violations are report-only); 1 on errors such
           as no configured source directory existing on disk.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding


class FileLengthScanner:
    """Flag files that exceed a configurable maximum line count."""

    DEFAULT_MAX_LINES = 800
    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH

    @staticmethod
    def resolve_extensions(settings_path: Path) -> set[str]:
        """Return the file extensions to scan for the project.

        Languages come from settings.json — the top-level ``language``
        field plus each populated ``<language>`` section — filtered to
        those whose ``code_style.check_file_length`` is not ``false`` (so
        a polyglot project only scans the languages with the check on).
        Returns an empty set when every configured language has the check
        disabled. When nothing usable is configured, falls back to every
        registered engine's extensions.
        """
        ProjectConfig.ensure_engines()
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(settings, "code_style.check_file_length")
        extensions = ProjectConfig.extensions_for(languages)
        if not extensions and languages:
            extensions = ProjectConfig.extensions_for(set(EngineRegistry.available_languages()))
        return extensions

    @staticmethod
    def resolve_max_lines(settings_path: Path) -> int:
        """Return the maximum allowed lines per file.

        The smallest ``<language>.code_style.max_file_length`` across the
        enabled languages configured in settings.json; falls back to
        ``DEFAULT_MAX_LINES`` when nothing is configured.
        """
        settings = ProjectConfig.load_settings(settings_path)
        langs = ProjectConfig.enabled_languages(settings, "code_style.check_file_length")
        limits = []
        for lang in sorted(langs):
            value = ProjectConfig.setting(settings, f"{lang}.code_style.max_file_length", None)
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        return min(limits) if limits else FileLengthScanner.DEFAULT_MAX_LINES

    @staticmethod
    def count_lines(path: Path) -> int:
        """Return the number of lines in *path*.

        Counts newline characters and adds one when the file is non-empty
        and does not end with a newline (the last partial line still counts).
        Reads bytes so non-UTF-8 content cannot fail the count.
        """
        data = path.read_bytes()
        if not data:
            return 0
        return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)

    @staticmethod
    def scan_file(path: Path, max_lines: int = DEFAULT_MAX_LINES) -> list[Finding]:
        """Return a ``file_length`` finding if *path* exceeds *max_lines*.

        The finding's ``line`` points at the first line beyond the limit.
        """
        lines = FileLengthScanner.count_lines(path)
        if lines <= max_lines:
            return []
        return [
            Finding(
                file=str(path),
                line=max_lines + 1,
                category="file_length",
                severity="medium",
                description=f"File has {lines} lines (max {max_lines})",
                fix_type="manual",
            )
        ]

    @staticmethod
    def scan_directory(
        root: Path,
        max_lines: int | None = None,
        extensions: set[str] | None = None,
        settings_path: Path | None = None,
    ) -> list[Finding]:
        """Scan matching files under *root* for file-length violations.

        When *extensions* or *max_lines* is omitted it is resolved from
        *settings_path* (default ``.zolletta-metaskill/settings.json``).
        Files that cannot be read are skipped with a warning on stderr.
        """
        path = settings_path or FileLengthScanner.DEFAULT_SETTINGS_PATH
        if extensions is None:
            extensions = FileLengthScanner.resolve_extensions(path)
        if max_lines is None:
            max_lines = FileLengthScanner.resolve_max_lines(path)
        findings: list[Finding] = []
        for path in ProjectConfig.iter_files(root, extensions):
            try:
                findings.extend(FileLengthScanner.scan_file(path, max_lines))
            except OSError:
                print(f"Warning: could not read '{path}'", file=sys.stderr)
        return findings

    @staticmethod
    def main() -> int:
        """Entry point for the file length scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Flag source files that exceed a maximum line count "
            "(language-agnostic; counts lines). Scan roots and limits come "
            "from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON instead of text",
        )
        args = parser.parse_args()

        settings_path = FileLengthScanner.DEFAULT_SETTINGS_PATH
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(settings, "code_style.check_file_length")
        if not languages:
            if args.json:
                print(
                    json.dumps(
                        {"skipped": True, "reason": "check_file_length disabled in settings.json"}
                    )
                )
            else:
                print("=" * 70)
                print("FILE LENGTH — VALIDATION REPORT")
                print("=" * 70)
                print("\nResult: SKIPPED (check_file_length disabled in settings.json)\n")
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, languages))
        if not roots:
            print(
                "Error: no configured source directories exist on disk "
                f"({', '.join(str(r) for r in ProjectConfig.source_roots(settings, languages))})",
                file=sys.stderr,
            )
            return 1

        extensions = ProjectConfig.extensions_for(languages)
        max_lines = FileLengthScanner.resolve_max_lines(settings_path)

        files: list[Path] = []
        for root in roots:
            files.extend(ProjectConfig.iter_files(root, extensions))
        violations: list[tuple[Path, int]] = []
        for path in files:
            try:
                lines = FileLengthScanner.count_lines(path)
            except OSError:
                print(f"Warning: could not read '{path}'", file=sys.stderr)
                continue
            if lines > max_lines:
                violations.append((path, lines))
        violations.sort(key=lambda item: item[1], reverse=True)

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "scanned": len(files),
                        "max_lines": max_lines,
                        "violation_count": len(violations),
                        "violations": [
                            {
                                "file": str(path),
                                "lines": lines,
                                "over": lines - max_lines,
                            }
                            for path, lines in violations
                        ],
                    },
                    indent=2,
                )
            )
        else:
            print("=" * 70)
            print("FILE LENGTH — VALIDATION REPORT")
            print("=" * 70)
            roots_str = ", ".join(str(root) for root in roots)
            print(f"\nScanned {len(files)} files under {roots_str} (max {max_lines} lines)")

            if violations:
                print(f"\n## Files exceeding the limit ({len(violations)} files)\n")
                for path, lines in violations:
                    print(f"  {lines:>6} lines  {path}  (over by {lines - max_lines})")
                print(
                    "\n  Fix: split the file by responsibility, or raise "
                    "max_file_length in settings.json if the size is justified."
                )
            else:
                print("\n## Files exceeding the limit: none")

            print()
            if violations:
                print("Result: violations found (report-only mode)")
            else:
                print("Result: all clear")

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(FileLengthScanner.main())
