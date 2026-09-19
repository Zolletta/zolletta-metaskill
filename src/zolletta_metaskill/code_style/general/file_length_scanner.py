#!/usr/bin/env python3
"""Flag source files that exceed a configurable maximum line count.

Language-agnostic sensor for the "file length" rule from Martin Fowler's
*Maintainability sensors for coding agents* ("Rules for typical AI
shortcomings"). Line count is trivial to compute for any language, so the
scanner does not use a parsing engine — it selects files by extension and
counts lines.

Usage:
    python3 file_length_scanner.py [directory] [--max-lines N]
        [--extensions .py,.php] [--exclude pat1,pat2]
        [--ignore-dirs d1,d2] [--strict] [--json] [--skip]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --max-lines N   Maximum allowed lines per file (default: 300). Read from
                    ``python.code_style.max_file_length`` or
                    ``php.code_style.max_file_length`` in settings.json.
    --extensions    Comma-separated file extensions to scan (default: .py).
                    Pass ``.php`` for PHP projects.
    --exclude       Comma-separated filename glob patterns to skip
                    (e.g. ``*_pb2.py,generated_*.py``) — for generated code or
                    other files that legitimately exceed the limit.
    --ignore-dirs   Comma-separated directory names to skip.
                    ``__pycache__`` and common dependency/build directories
                    are always skipped.
    --strict        Exit with code 1 if violations are found.
    --json          Output as JSON instead of text.
    --skip          Skip this check entirely (exit 0 with 'skipped' message).

Exit code: 0 if no violations (or --strict not set or --skip), 1 if
           violations found with --strict.

"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path

from zolletta_metaskill.core.structs import Finding


class FileLengthScanner:
    """Flag files that exceed a configurable maximum line count."""

    DEFAULT_MAX_LINES = 300
    DEFAULT_IGNORE_DIRS = frozenset(
        {"__pycache__", ".venv", "venv", ".tox", "dist", "build", "node_modules", "vendor"}
    )

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
    def _parse_extensions(raw: str) -> set[str]:
        """Normalize a comma-separated extension list to dot-prefixed lowercase.

        Accepts entries with or without a leading dot (``"py,.php"``).
        Returns ``{".py"}`` when the list is empty.
        """
        extensions = set()
        for part in raw.split(","):
            part = part.strip().lower()
            if part:
                extensions.add(part if part.startswith(".") else f".{part}")
        return extensions or {".py"}

    @staticmethod
    def _iter_files(
        root: Path,
        extensions: set[str],
        ignore_dirs: set[str] | None,
        exclude: Sequence[str],
    ) -> list[Path]:
        """Return matching files under *root*, sorted by path.

        ``__pycache__`` and the entries of ``DEFAULT_IGNORE_DIRS`` are always
        skipped, along with any directory named in *ignore_dirs* and any file
        whose name or root-relative path matches a glob in *exclude*.
        """
        ignored = FileLengthScanner.DEFAULT_IGNORE_DIRS | (ignore_dirs or set())
        files = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if any(part in ignored for part in path.parts):
                continue
            if exclude and any(
                fnmatch(path.name, pattern) or fnmatch(str(path.relative_to(root)), pattern)
                for pattern in exclude
            ):
                continue
            files.append(path)
        return sorted(files)

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
        extensions: set[str] | None = None,
        ignore_dirs: set[str] | None = None,
        exclude: Sequence[str] = (),
    ) -> list[Finding]:
        """Scan all matching files under *root* for file-length violations.

        Files that cannot be read are skipped with a warning on stderr.
        """
        findings: list[Finding] = []
        for path in FileLengthScanner._iter_files(
            root, extensions or {".py"}, ignore_dirs, exclude
        ):
            try:
                findings.extend(FileLengthScanner.scan_file(path, max_lines))
            except OSError:
                print(f"Warning: could not read '{path}'", file=sys.stderr)
        return findings

    @staticmethod
    def main() -> int:
        """Entry point for the file length scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Flag files that exceed a maximum line count "
            "(language-agnostic; selects files by extension)."
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
            help="Maximum allowed lines per file (default: 300)",
        )
        parser.add_argument(
            "--extensions",
            default=".py",
            help="Comma-separated file extensions to scan (default: .py; use .php for PHP)",
        )
        parser.add_argument(
            "--exclude",
            default="",
            help="Comma-separated filename glob patterns to skip (e.g. '*_pb2.py,generated_*.py')",
        )
        parser.add_argument(
            "--ignore-dirs",
            default="",
            help="Comma-separated directory names to skip "
            "(__pycache__ and dependency/build dirs are always skipped)",
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

        extensions = FileLengthScanner._parse_extensions(args.extensions)
        ignore_dirs = set(args.ignore_dirs.split(",")) if args.ignore_dirs else set()
        exclude = [p.strip() for p in args.exclude.split(",") if p.strip()]

        files = FileLengthScanner._iter_files(root, extensions, ignore_dirs, exclude)
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
            print(
                f"\nScanned {len(files)} files under {root} "
                f"(extensions: {', '.join(sorted(extensions))}; max {args.max_lines} lines)"
            )

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
