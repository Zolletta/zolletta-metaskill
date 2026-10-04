"""FileDiscovery provides git-ignore aware file enumeration for documentor tools."""

from __future__ import annotations

import os
from pathlib import Path


class FileDiscovery:
    """Discovers documentation and code files while respecting ``.gitignore``."""

    DEFAULT_SKIP_DIRS: set[str] = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        "dist",
        "build",
        ".zolletta-metaskill",
    }

    DEFAULT_DOC_EXTENSIONS: set[str] = {".md", ".rst", ".txt", ".adoc"}

    @staticmethod
    def _load_gitignore_patterns(repo_path: str) -> set[str]:
        """Load simple directory/file names from ``.gitignore``.

        Only extracts literal entries (no negation, no wildcards).
        """
        patterns: set[str] = set()
        gitignore = os.path.join(repo_path, ".gitignore")
        if not os.path.exists(gitignore):
            return patterns
        try:
            with open(gitignore, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("!") or "*" in line or "?" in line:
                        continue
                    name = line.lstrip("/").rstrip("/")
                    if "/" in name:
                        name = name.split("/")[-1]
                    if name:
                        patterns.add(name)
        except OSError:
            pass
        return patterns

    @staticmethod
    def _extensions_from_patterns(patterns: list[str]) -> set[str]:
        """Derive file extensions from glob-style patterns."""
        extensions: set[str] = set()
        for p in patterns:
            if p.startswith("*."):
                extensions.add(p[1:])
            elif p.startswith("."):
                extensions.add(p)
            else:
                extensions.add("." + p)
        return extensions

    @staticmethod
    def find_doc_files(
        repo_path: str,
        patterns: list[str] | None = None,
        extensions: set[str] | None = None,
        skip_dirs: set[str] | None = None,
    ) -> list[str]:
        """Find documentation files under *repo_path*.

        *patterns* take precedence over *extensions*. If neither is provided,
        the default doc extensions are used.
        """
        if patterns is not None:
            ext_set = FileDiscovery._extensions_from_patterns(patterns)
        elif extensions is not None:
            ext_set = extensions
        else:
            ext_set = set(FileDiscovery.DEFAULT_DOC_EXTENSIONS)

        skip = set(FileDiscovery.DEFAULT_SKIP_DIRS) | FileDiscovery._load_gitignore_patterns(
            repo_path
        )
        if skip_dirs is not None:
            skip |= skip_dirs

        doc_files: list[str] = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in skip]
            for f in files:
                if f in skip:
                    continue
                if Path(f).suffix.lower() in ext_set:
                    doc_files.append(os.path.relpath(os.path.join(root, f), repo_path))
        return sorted(doc_files)

    @staticmethod
    def find_code_files(
        repo_path: str,
        scope: str = "",
        extensions: set[str] | None = None,
        skip_dirs: set[str] | None = None,
    ) -> list[str]:
        """Find code files under *repo_path*, optionally scoped to *scope*."""
        from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper

        ext_set = set(extensions) if extensions else set(DocCodeMapper.CODE_EXTENSIONS)
        search_path = os.path.join(repo_path, scope) if scope else repo_path

        skip = set(FileDiscovery.DEFAULT_SKIP_DIRS) | FileDiscovery._load_gitignore_patterns(
            repo_path
        )
        if skip_dirs is not None:
            skip |= skip_dirs

        code_files: list[str] = []
        if not os.path.isdir(search_path):
            return code_files

        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in skip]
            for f in files:
                if Path(f).suffix.lower() in ext_set:
                    rel_path = os.path.relpath(os.path.join(root, f), repo_path)
                    code_files.append(rel_path)
        return sorted(code_files)
