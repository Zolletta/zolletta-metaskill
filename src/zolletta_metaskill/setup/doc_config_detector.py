#!/usr/bin/env python3
"""Detect the project's documentation directory.

Reads ``documentation.dir`` from ``.zolletta-metaskill/settings.json``.
Falls back to ``docs/`` if settings.json does not exist or the key is missing.

Usage:
    python3 doc_config_detector.py [directory]

Exit code: 0 always. Prints the directory name to stdout.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class DocConfigDetector:
    """Detect the project's documentation directory from settings.json."""

    @staticmethod
    def detect_doc_dir(project_root: Path) -> str:
        """Detect the documentation directory for the project.

        Args:
            project_root: Path to the project root directory.

        Returns:
            The documentation directory name from ``settings.json``
            (``documentation.dir``), or ``"docs"`` as fallback.

        """
        settings_path = project_root / ".zolletta-metaskill" / "settings.json"
        if settings_path.is_file():
            try:
                settings: dict[str, Any] = json.loads(settings_path.read_text())
                doc_dir = settings.get("documentation", {}).get("dir")
                if isinstance(doc_dir, str) and doc_dir:
                    return doc_dir
            except (json.JSONDecodeError, KeyError):
                pass
        return "docs"

    @staticmethod
    def main() -> int:
        """Entry point for the documentation directory detector CLI."""
        parser = argparse.ArgumentParser(
            description="Detect the project's documentation directory."
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default=".",
            help="Project root to check (default: current directory)",
        )
        args = parser.parse_args()

        print(DocConfigDetector.detect_doc_dir(Path(args.directory)))
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(DocConfigDetector.main())
