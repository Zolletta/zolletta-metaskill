#!/usr/bin/env python3
"""Detect the project's documentation directory.

Checks for ``.backstage/`` first, then falls back to ``docs/`` (the
default — created by the ``documentor`` skill if needed).

Usage:
    python3 detect_doc_config.py [directory]

Exit code: 0 always. Prints the directory name to stdout.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def detect_doc_dir(project_root: Path) -> str:
    """Detect the documentation directory for the project.

    Args:
        project_root: Path to the project root directory.

    Returns:
        ``".backstage"`` if ``.backstage/`` exists, otherwise ``"docs"``.

    """
    if (project_root / ".backstage").is_dir():
        return ".backstage"
    return "docs"


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

    print(detect_doc_dir(Path(args.directory)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
