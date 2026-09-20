#!/usr/bin/env python3
"""Flag source files that exceed a configurable maximum line count.

Language-agnostic sensor for the "file length" rule from Martin Fowler's
*Maintainability sensors for coding agents* ("Rules for typical AI
shortcomings"). Line count is trivial to compute for any language, so the
scanner does not parse code — it counts lines.

Which files are scanned:

- The project's language is read from ``.zolletta-metaskill/settings.json``
  (top-level ``language`` plus any ``<language>.code_style`` section), and
  mapped to file extensions via the engine registry (``python`` → ``.py``,
  ``php`` → ``.php``). When settings.json is absent or the language has no
  registered engine, every registered engine's extensions are scanned.
- Files ignored by git (``.gitignore``, ``.git/info/exclude``,
  ``core.excludesFile``) are skipped — this is what keeps ``vendor/``,
  ``node_modules/``, build output, etc. out of the report. Outside a git
  repository every file matching the extensions is scanned.

Usage:
    python3 file_length_scanner.py [directory] [--max-lines N]
        [--settings PATH] [--exclude pat1,pat2]
        [--strict] [--json] [--skip]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --max-lines N   Maximum allowed lines per file (default: 800). Read from
                    ``python.code_style.max_file_length`` or
                    ``php.code_style.max_file_length`` in settings.json.
    --settings      Path to settings.json to read the project language from
                    (default: .zolletta-metaskill/settings.json).
    --exclude       Comma-separated filename glob patterns to skip
                    (e.g. ``*_pb2.py``) — for generated code or other files
                    that legitimately exceed the limit.
    --strict        Exit with code 1 if violations are found.
    --json          Output as JSON instead of text.
    --skip          Skip this check entirely (exit 0 with 'skipped' message).

Exit code: 0 if no violations (or --strict not set or --skip), 1 if
           violations found with --strict.

"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.engine.python_engine import PythonEngine
from zolletta_metaskill.core.structs import Finding


class FileLengthScanner:
    """Flag files that exceed a configurable maximum line count."""

    DEFAULT_MAX_LINES = 800
    DEFAULT_SETTINGS_PATH = Path(".zolletta-metaskill/settings.json")

    @staticmethod
    def _ensure_engines() -> None:
        """Register the bundled engines so extensions can be resolved."""
        EngineRegistry.ensure(PythonEngine())
        EngineRegistry.ensure(PHPEngine())

    @staticmethod
    def _load_settings(settings_path: Path) -> dict[str, Any]:
        """Return parsed settings.json, or an empty dict if unreadable."""
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def resolve_extensions(settings_path: Path) -> set[str]:
        """Return the file extensions to scan for the project.

        Languages come from settings.json — the top-level ``language`` field
        plus each ``<language>`` section that has a registered engine (so
        polyglot projects scan every configured language). If no usable
        language is found, fall back to every registered engine's extensions.
        """
        FileLengthScanner._ensure_engines()
        settings = FileLengthScanner._load_settings(settings_path)
        registered = set(EngineRegistry.available_languages())

        languages: set[str] = set()
        language = settings.get("language")
        if isinstance(language, str) and language:
            languages.add(language)
        languages.update(lang for lang in registered if isinstance(settings.get(lang), dict))

        extensions: set[str] = set()
        for lang in sorted(languages & registered):
            extensions.update(EngineRegistry.get(lang).file_extensions())
        for lang in sorted(languages - registered):
            print(f"Warning: no engine for language '{lang}'", file=sys.stderr)

        if not extensions:
            for lang in sorted(registered):
                extensions.update(EngineRegistry.get(lang).file_extensions())
        return extensions

    @staticmethod
    def _git_files(root: Path) -> list[Path] | None:
        """Return non-ignored files under *root*, or ``None`` outside a git repo.

        Uses ``git ls-files`` so tracked files are always included and
        untracked files are filtered by every exclude source git honours
        (.gitignore, .git/info/exclude, core.excludesFile). Paths outside
        *root* (shown with ``../`` prefixes) are dropped.
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-c", "-o", "--exclude-standard", "-z"],
                capture_output=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0:
            return None
        files = []
        for rel in result.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
            if not rel or rel.startswith("../"):
                continue
            path = root / rel
            if path.is_file():
                files.append(path)
        return files

    @staticmethod
    def _iter_files(
        root: Path,
        extensions: set[str],
        exclude: Sequence[str],
    ) -> list[Path]:
        """Return files under *root* matching *extensions*, sorted by path.

        Git-ignored files are skipped when *root* is inside a repository;
        outside a repo every matching file is returned. Files whose name or
        root-relative path matches a glob in *exclude* are dropped.
        """
        candidates = FileLengthScanner._git_files(root)
        if candidates is None:
            candidates = [p for p in root.rglob("*") if p.is_file()]
        files = []
        for path in candidates:
            if path.suffix.lower() not in extensions:
                continue
            if exclude and any(
                fnmatch(path.name, pattern) or fnmatch(str(path.relative_to(root)), pattern)
                for pattern in exclude
            ):
                continue
            files.append(path)
        return sorted(files)

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
        max_lines: int = DEFAULT_MAX_LINES,
        exclude: Sequence[str] = (),
        extensions: set[str] | None = None,
        settings_path: Path | None = None,
    ) -> list[Finding]:
        """Scan matching files under *root* for file-length violations.

        When *extensions* is omitted it is resolved from *settings_path*
        (default ``.zolletta-metaskill/settings.json``). Files that cannot be
        read are skipped with a warning on stderr.
        """
        if extensions is None:
            extensions = FileLengthScanner.resolve_extensions(
                settings_path or FileLengthScanner.DEFAULT_SETTINGS_PATH
            )
        findings: list[Finding] = []
        for path in FileLengthScanner._iter_files(root, extensions, exclude):
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
            "(language-agnostic; counts lines)."
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default="src",
            help="Root directory to scan (default: src)",
        )
        parser.add_argument(
            "--max-lines",
            type=int,
            default=FileLengthScanner.DEFAULT_MAX_LINES,
            help="Maximum allowed lines per file (default: 800)",
        )
        parser.add_argument(
            "--settings",
            default=None,
            help="Path to settings.json to read the project language from "
            "(default: .zolletta-metaskill/settings.json)",
        )
        parser.add_argument(
            "--exclude",
            default="",
            help="Comma-separated filename glob patterns to skip (e.g. '*_pb2.py')",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with code 1 if violations are found",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON instead of text",
        )
        parser.add_argument(
            "--skip",
            action="store_true",
            help="Skip this check entirely (exit 0 with 'skipped' message)",
        )
        args = parser.parse_args()

        if args.skip:
            if not args.json:
                print("=" * 70)
                print("FILE LENGTH — VALIDATION REPORT")
                print("=" * 70)
                print("\nResult: SKIPPED (--skip flag)\n")
            return 0

        root = Path(args.directory)
        if not root.exists():
            print(f"Error: directory '{root}' does not exist", file=sys.stderr)
            return 1

        settings_path = (
            Path(args.settings) if args.settings else FileLengthScanner.DEFAULT_SETTINGS_PATH
        )
        extensions = FileLengthScanner.resolve_extensions(settings_path)
        exclude = [p.strip() for p in args.exclude.split(",") if p.strip()]

        files = FileLengthScanner._iter_files(root, extensions, exclude)
        violations: list[tuple[Path, int]] = []
        for path in files:
            try:
                lines = FileLengthScanner.count_lines(path)
            except OSError:
                print(f"Warning: could not read '{path}'", file=sys.stderr)
                continue
            if lines > args.max_lines:
                violations.append((path, lines))
        violations.sort(key=lambda item: item[1], reverse=True)

        if args.json:
            print(
                json.dumps(
                    {
                        "directory": str(root),
                        "scanned": len(files),
                        "max_lines": args.max_lines,
                        "violation_count": len(violations),
                        "violations": [
                            {
                                "file": str(path.relative_to(root)),
                                "lines": lines,
                                "over": lines - args.max_lines,
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
            print(f"\nScanned {len(files)} files under {root} (max {args.max_lines} lines)")

            if violations:
                print(f"\n## Files exceeding the limit ({len(violations)} files)\n")
                for path, lines in violations:
                    rel = path.relative_to(root)
                    print(f"  {lines:>6} lines  {rel}  (over by {lines - args.max_lines})")
                print(
                    "\n  Fix: split the file by responsibility, or raise "
                    "max_file_length / add an --exclude pattern if the size is justified."
                )
            else:
                print("\n## Files exceeding the limit: none")

            print()
            if violations and args.strict:
                print("Result: VIOLATIONS FOUND (strict mode)")
            elif violations:
                print("Result: violations found (report-only mode)")
            else:
                print("Result: all clear")

        if violations and args.strict:
            return 1
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(FileLengthScanner.main())
