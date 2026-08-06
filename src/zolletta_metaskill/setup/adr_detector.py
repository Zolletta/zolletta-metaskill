#!/usr/bin/env python3
"""Detect the project's ADR (Architecture Decision Record) folder.

Scans the documentation directory for files matching the Nygard ADR
format (``# ADR-NNN: Title`` heading). Uses ``grep -ri -l adr`` as a
fast presence check, then confirms with a heading-pattern scan.

Returns the relative path within the docs directory where ADRs live
(e.g. ``"adr"``, ``"decisions"``, ``""`` if scattered in the docs root),
or ``None`` if no ADRs are found.

Usage:
    python3 adr_detector.py [docs_dir]

Exit code: 0 always. Prints JSON to stdout.

> ADR detection inspired by [Architectural Governance at AI Speed](
> https://www.infoq.com/articles/architectural-governance-ai-speed/)
> (InfoQ, 2026).

"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


class ADRDetector:
    """Detect the project's ADR (Architecture Decision Record) folder."""

    # Matches Nygard-format ADR headings: "# ADR-001: Title", "# ADR 001: Title",
    # "## ADR-001: Title", etc.
    _ADR_HEADING_RE = re.compile(r"^#+\s+ADR[-\s]?(\d+)", re.MULTILINE)

    @staticmethod
    def _grep_adr_files(docs_dir: Path) -> list[Path] | None:
        """Fast presence check via ``grep -ri -l adr``.

        Returns a list of file paths that mention "adr" (case-insensitive),
        or ``None`` if grep is unavailable or fails. The caller must confirm
        matches with the heading-pattern scan — grep matches any mention
        of "adr", not just ADR headings.

        ``adr-distilled.md`` is excluded to avoid circular matches.
        """
        if shutil.which("grep") is None:
            return None
        try:
            result = subprocess.run(
                [
                    "grep",
                    "-ri",
                    "-l",
                    "--exclude=adr-distilled.md",
                    "adr",
                    str(docs_dir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode not in (0, 1):
            return None
        return [Path(line) for line in result.stdout.splitlines() if line.strip()]

    @staticmethod
    def _scan_adr_headings(files: list[Path]) -> list[Path]:
        """Confirm which files contain ADR heading patterns.

        Filters the grep results to only files that have a ``# ADR-NNN``
        heading. This removes false positives where "adr" appears in prose
        but no actual ADRs exist.
        """
        confirmed: list[Path] = []
        for f in files:
            if f.suffix != ".md":
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if ADRDetector._ADR_HEADING_RE.search(content):
                confirmed.append(f)
        return confirmed

    @staticmethod
    def _determine_adrs_path(adr_files: list[Path], docs_dir: Path) -> str:
        """Determine the ADR subdirectory path relative to *docs_dir*.

        If all ADR files share a common subdirectory under *docs_dir*,
        return that subdirectory name. If they are scattered in the docs
        root or in multiple subdirectories, return ``""``.
        """
        parents: set[str] = set()
        for f in adr_files:
            rel = f.relative_to(docs_dir)
            parts = rel.parts
            if len(parts) == 1:
                # File is directly in docs_dir
                parents.add("")
            else:
                parents.add(parts[0])
        if len(parents) == 1:
            return next(iter(parents))
        return ""

    @staticmethod
    def detect_adrs(docs_dir: Path) -> str | None:
        """Detect the ADR folder within *docs_dir*.

        Args:
            docs_dir: Path to the project's documentation directory.

        Returns:
            The ADR subdirectory path relative to *docs_dir*
            (e.g. ``"adr"``, ``"decisions"``, ``""`` if scattered in docs
            root), or ``None`` if no ADRs are found.

        """
        if not docs_dir.is_dir():
            return None

        # Fast presence check via grep, fall back to scanning all .md files
        grep_results = ADRDetector._grep_adr_files(docs_dir)
        if grep_results is not None:
            candidate_files = grep_results
        else:
            # grep unavailable — scan all .md files in docs_dir
            candidate_files = list(docs_dir.rglob("*.md"))
            # Exclude adr-distilled.md
            candidate_files = [f for f in candidate_files if f.name != "adr-distilled.md"]

        if not candidate_files:
            return None

        # Confirm with heading-pattern scan
        adr_files = ADRDetector._scan_adr_headings(candidate_files)
        if not adr_files:
            return None

        return ADRDetector._determine_adrs_path(adr_files, docs_dir)

    @staticmethod
    def main() -> int:
        """Entry point for the ADR folder detector CLI."""
        parser = argparse.ArgumentParser(
            description="Detect the project's ADR folder within the docs directory."
        )
        parser.add_argument(
            "docs_dir",
            nargs="?",
            default="docs",
            help="Documentation directory to scan (default: docs)",
        )
        args = parser.parse_args()

        docs_dir = Path(args.docs_dir)
        if not docs_dir.is_dir():
            print(json.dumps({"adrs_path": None}))
            return 0

        adrs_path = ADRDetector.detect_adrs(docs_dir)
        print(json.dumps({"adrs_path": adrs_path}))
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(ADRDetector.main())
