"""ADR CLI — argument parsing, report formatting, and entry point.

Extracted from ADROrchestrator to separate orchestration logic from CLI
concerns.  ADROrchestrator handles ADR discovery, distillation, and cache
management; ADRCLI handles argument parsing, output formatting, and the
``__main__`` entry point.

Directories come from ``.zolletta-metaskill/settings.json``:

- ``documentation.dir`` — documentation root (default: ``docs``)
- ``documentation.adrs`` — ADR path relative to ``documentation.dir``
  (``null`` = no ADRs, ``""`` = docs root)
- ``runs_dir`` — mtime cache root (default: ``.zolletta-metaskill``)

The only CLI option is ``--json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zolletta_metaskill.adr.adr_cache import ADRCache
from zolletta_metaskill.adr.adr_orchestrator import ADROrchestrator
from zolletta_metaskill.adr.structs.distill_report import DistillReport
from zolletta_metaskill.core.project_config import ProjectConfig


class ADRCLI:
    """CLI wrapper for the ADR distiller."""

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build the CLI argument parser."""
        parser = argparse.ArgumentParser(
            description="Distill Accepted ADRs into architectural directives. "
            "Directories come from documentation.dir / documentation.adrs / "
            "runs_dir in .zolletta-metaskill/settings.json."
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

        settings = ProjectConfig.load_settings()
        docs_dir = ProjectConfig.docs_dir(settings)
        if not docs_dir.is_dir():
            msg = ADRCLI.missing_docs_error(docs_dir, args.json)
            if args.json:
                print(msg)
            else:
                print(msg, file=sys.stderr)
            return 1

        adrs_path = ProjectConfig.setting(settings, "documentation.adrs", None)
        cache_path = ProjectConfig.runs_dir(settings) / ADRCache.CACHE_FILENAME
        orchestrator = ADROrchestrator(docs_dir, adrs_path, cache_path)
        report = orchestrator.refresh()

        print(ADRCLI.format_report(report, args.json))
        return 0

    @staticmethod
    def main() -> int:
        """Entry point for the ADR distiller CLI."""
        return ADRCLI.run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(ADRCLI.main())
