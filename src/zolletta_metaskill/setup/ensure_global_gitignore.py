#!/usr/bin/env python3
"""Ensure ``.zolletta-metaskill/`` is listed in the user's global ``~/.gitignore``.

Idempotent: creates ``~/.gitignore`` if missing, appends the entry only if
it is not already present, never duplicates.

Usage:
    python3 ensure_global_gitignore.py [--path ~/.gitignore]

Exit code: 0 always (the operation is idempotent and non-fatal).

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ENTRY = ".zolletta-metaskill/"
COMMENT = "# Zolletta-metaskill"


def ensure_global_gitignore(gitignore_path: Path | None = None) -> bool:
    """Ensure ``.zolletta-metaskill/`` is in the global gitignore.

    Args:
        gitignore_path: Path to the global gitignore file. Defaults to
            ``~/.gitignore``.

    Returns:
        ``True`` if the entry was added, ``False`` if it was already present.

    """
    if gitignore_path is None:
        gitignore_path = Path.home() / ".gitignore"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip().rstrip("/")
            if stripped == ENTRY.rstrip("/"):
                return False
        new_content = content
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"
        new_content += f"\n{COMMENT}\n{ENTRY}\n"
        gitignore_path.write_text(new_content, encoding="utf-8")
    else:
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text(f"{COMMENT}\n{ENTRY}\n", encoding="utf-8")
    return True


def main() -> int:
    """Entry point for the global gitignore ensurer CLI."""
    parser = argparse.ArgumentParser(
        description="Ensure .zolletta-metaskill/ is in the global ~/.gitignore."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to the gitignore file (default: ~/.gitignore)",
    )
    args = parser.parse_args()

    added = ensure_global_gitignore(args.path)
    if added:
        print(f"Added {ENTRY} to {args.path or Path.home() / '.gitignore'}")
    else:
        print(f"{ENTRY} already present in {args.path or Path.home() / '.gitignore'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
