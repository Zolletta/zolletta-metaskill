#!/usr/bin/env python3
"""Ensure ``.zolletta-metaskill/`` is listed in the repo's ``.git/info/exclude``.

Repo-local alternative to a global ``~/.gitignore`` entry: ``info/exclude`` is
honoured by git but never committed, so the skill leaves no trace outside the
project. Idempotent: creates ``info/exclude`` if missing, appends the entry
only if it is not already present, never duplicates.

Usage:
    python3 git_exclude_ensurer.py [--path .git/info/exclude]

Exit code: 0 always (the operation is idempotent and non-fatal).

"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


class GitExcludeEnsurer:
    """Ensure ``.zolletta-metaskill/`` is listed in the repo's ``.git/info/exclude``."""

    ENTRY = ".zolletta-metaskill/"
    COMMENT = "# Zolletta-metaskill"

    @staticmethod
    def _default_exclude_path() -> Path | None:
        """Locate ``info/exclude`` for the current repo, or ``None`` outside a work tree."""
        try:
            # pragma: no mutate start — a mutated argv makes git fail; the .git
            # fallback below then resolves identically on a plain repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-common-dir"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # pragma: no mutate end
        except (subprocess.SubprocessError, FileNotFoundError):
            result = None
        if result is not None and result.returncode == 0 and result.stdout.strip():
            # pragma: no mutate start — case variants resolve identically on common filesystems
            return Path(result.stdout.strip()) / "info" / "exclude"
            # pragma: no mutate end
        # pragma: no mutate start — ".GIT" resolves identically on case-insensitive filesystems
        dot_git = Path(".git")
        return dot_git / "info" / "exclude" if dot_git.is_dir() else None
        # pragma: no mutate end

    @staticmethod
    def ensure_git_exclude(exclude_path: Path | None = None) -> bool | None:
        """Ensure ``.zolletta-metaskill/`` is in the repo's ``info/exclude``.

        Args:
            exclude_path: Path to the exclude file. Defaults to the current
                work tree's ``.git/info/exclude``.

        Returns:
            ``True`` if the entry was added, ``False`` if it was already
            present, ``None`` when no git directory was found.

        """
        if exclude_path is None:
            exclude_path = GitExcludeEnsurer._default_exclude_path()
            if exclude_path is None:
                return None

        if exclude_path.exists():
            content = exclude_path.read_text(encoding="utf-8")  # pragma: no mutate
            for line in content.splitlines():
                # pragma: no mutate start — only lines ending in "/" can match ENTRY anyway
                stripped = line.strip().rstrip("/")
                # pragma: no mutate end
                # pragma: no mutate start — ENTRY ends in "/", so the rstrip charset is unobservable
                if stripped == GitExcludeEnsurer.ENTRY.rstrip("/"):
                    # pragma: no mutate end
                    return False
            new_content = content
            if new_content and not new_content.endswith("\n"):
                new_content += "\n"
            new_content += f"\n{GitExcludeEnsurer.COMMENT}\n{GitExcludeEnsurer.ENTRY}\n"
            exclude_path.write_text(new_content, encoding="utf-8")
        else:
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            exclude_path.write_text(
                f"{GitExcludeEnsurer.COMMENT}\n{GitExcludeEnsurer.ENTRY}\n",
                encoding="utf-8",
            )
        return True

    @staticmethod
    def main() -> int:  # pragma: no mutate — help text is not a tested contract
        """Entry point for the git exclude ensurer CLI."""
        parser = argparse.ArgumentParser(
            description="Ensure .zolletta-metaskill/ is in the repo's .git/info/exclude."
        )
        # pragma: no mutate start — carried from inline pragma (was ineffective inside a multi-line
        # statement)
        parser.add_argument(
            "--path",
            type=Path,
            default=None,
            help="Path to the exclude file (default: <repo>/.git/info/exclude)",
        )
        # pragma: no mutate end
        args = parser.parse_args()

        exclude_path = args.path or GitExcludeEnsurer._default_exclude_path()
        if exclude_path is None:
            print("Not a git repository — skipping .git/info/exclude update")
            return 0
        if GitExcludeEnsurer.ensure_git_exclude(exclude_path):
            print(f"Added {GitExcludeEnsurer.ENTRY} to {exclude_path}")
        else:
            print(f"{GitExcludeEnsurer.ENTRY} already present in {exclude_path}")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(GitExcludeEnsurer.main())
