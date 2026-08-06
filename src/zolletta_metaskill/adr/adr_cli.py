"""ADR CLI — argument parsing, report formatting, and entry point.

Extracted from ADROrchestrator to separate orchestration logic from CLI
concerns.  ADROrchestrator handles ADR discovery, distillation, and cache
management; ADRCLI handles argument parsing, output formatting, and the
``__main__`` entry point.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zolletta_metaskill.adr.adr_cache import ADRCache
from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator
from zolletta_metaskill.adr.structs.distill_report import DistillReport


class ADRCLI:
    """CLI wrapper for the ADR distiller."""

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build the CLI argument parser."""
        parser = argparse.ArgumentParser(
            description="Distill Accepted ADRs into architectural directives."
        )
        parser.add_argument(
            "--docs-dir",
            default="docs",
            help="Documentation directory (default: docs)",
        )
        parser.add_argument(
            "--adrs-path",
            default=None,
            help="Relative path within docs-dir where ADRs live "
            '(e.g. "adr", "" for docs root, or omit/null for no ADRs)',
        )
        parser.add_argument(
            "--cache-dir",
            default=".zolletta-metaskill",
            help="Directory for the mtime cache (default: .zolletta-metaskill)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output JSON report instead of plain text",
        )
        return parser

    @staticmethod
    def format_report(report: DistillReport, as_json: bool) -> str:
        """Format a DistillReport for CLI output."""
        if as_json:
            return json.dumps(report.to_dict())
        if report.has_adrs:
            return (
                f"ADR distiller: {len(report.new)} new, "
                f"{len(report.stale)} stale, {len(report.removed)} removed"
            )
        return "ADR distiller: no ADRs found"

    @staticmethod
    def missing_docs_error(docs_dir: Path, as_json: bool) -> str:
        """Format the error message when --docs-dir does not exist."""
        if as_json:
            return json.dumps(
                {
                    "new": [],
                    "stale": [],
                    "removed": [],
                    "has_adrs": False,
                }
            )
        return f"Error: '{docs_dir}' is not a directory"

    @staticmethod
    def run(argv: list[str] | None = None) -> int:
        """Parse args, run the distiller, and print the report.

        Returns the CLI exit code (0 on success, 1 on error).
        """
        parser = ADRCLI.build_parser()
        args = parser.parse_args(argv)

        docs_dir = Path(args.docs_dir)
        if not docs_dir.is_dir():
            msg = ADRCLI.missing_docs_error(docs_dir, args.json)
            if args.json:
                print(msg)
            else:
                print(msg, file=sys.stderr)
            return 1

        cache_path = Path(args.cache_dir) / ADRCache.CACHE_FILENAME
        orchestrator = ADROrchestrator(docs_dir, args.adrs_path, cache_path)
        report = orchestrator.refresh()

        print(ADRCLI.format_report(report, args.json))
        return 0


def main() -> int:
    """Entry point for the ADR distiller CLI."""
    return ADRCLI.run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
