"""GitHelper wraps common git commands used by documentor tools.

All methods are stateless static helpers.
"""

from __future__ import annotations

import subprocess
from datetime import datetime


class GitHelper:
    """Stateless git utilities for documentor review tools."""

    @staticmethod
    def run_git(repo_path: str, args: list[str], default: str = "") -> str:
        """Run a git command in *repo_path* and return stdout.

        Returns *default* when git is not available or the command fails.
        """
        try:
            result = subprocess.run(
                ["git", "-C", repo_path] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() if result.returncode == 0 else default
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return default

    @staticmethod
    def get_file_last_commit_date(repo_path: str, file_path: str) -> datetime | None:
        """Return the author date of the last commit that touched *file_path*."""
        output = GitHelper.run_git(repo_path, ["log", "-1", "--format=%aI", "--", file_path])
        if output:
            try:
                return datetime.fromisoformat(output)
            except ValueError:
                pass
        return None

    @staticmethod
    def get_files_changed_since(
        repo_path: str, since_date: str, scope: str = ""
    ) -> list[dict[str, str]]:
        """Return files changed since *since_date*, optionally scoped to *scope*."""
        args = [
            "log",
            "--since",
            since_date,
            "--name-status",
            "--pretty=format:",
            "--diff-filter=ACDMRT",
        ]
        if scope:
            args += ["--", scope]
        output = GitHelper.run_git(repo_path, args)
        changes: list[dict[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                changes.append({"status": parts[0][0], "file": parts[-1]})
        return changes

    @staticmethod
    def get_code_changes_since(repo_path: str, since_date: str, directory: str = "") -> int:
        """Count commits touching *directory* since *since_date*."""
        args = ["log", "--since", since_date, "--oneline", "--", directory or "."]
        output = GitHelper.run_git(repo_path, args)
        # pragma: no mutate start — output is a str; falsy means "", so both branches yield 0
        return len([line for line in output.splitlines() if line.strip()]) if output else 0
        # pragma: no mutate end

    @staticmethod
    def get_renamed_files(repo_path: str, since_date: str) -> list[tuple[str, str]]:
        """Return ``(old_path, new_path)`` tuples for files renamed since *since_date*."""
        output = GitHelper.run_git(
            repo_path,
            [
                "log",
                "--since",
                since_date,
                "--name-status",
                "--pretty=format:",
                "--diff-filter=R",
                "-M",
            ],
        )
        renames: list[tuple[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].startswith("R"):
                renames.append((parts[1], parts[2]))
        return renames

    @staticmethod
    def get_latest_tag(repo_path: str) -> str | None:
        """Return the latest git tag (``v`` prefix stripped), or ``None``."""
        output = GitHelper.run_git(repo_path, ["describe", "--tags", "--abbrev=0"])
        return output.lstrip("v") if output else None
