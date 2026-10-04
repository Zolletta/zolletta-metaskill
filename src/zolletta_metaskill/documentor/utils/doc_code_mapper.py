"""DocCodeMapper associates documentation files with corresponding source code files.

Handles code file discovery, document-to-code mapping heuristics, and doc reference extraction.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path


class DocCodeMapper:
    """Discovers code files and maps documentation files to code directories."""

    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".xml",
        ".css",
        ".scss",
        ".html",
    }

    @staticmethod
    def _load_gitignore_patterns(repo_path: str) -> set[str]:
        """Load directory/file names from .gitignore that should be skipped."""
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
    def find_code_files(repo_path: str, scope: str = "") -> list[str]:
        """Find all code files in the repository."""
        code_files: list[str] = []
        search_path = os.path.join(repo_path, scope) if scope else repo_path
        skip_dirs = {
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
        skip_dirs |= DocCodeMapper._load_gitignore_patterns(repo_path)

        if not os.path.isdir(search_path):
            return code_files

        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if Path(f).suffix.lower() in DocCodeMapper.CODE_EXTENSIONS:
                    rel_path = os.path.relpath(os.path.join(root, f), repo_path)
                    code_files.append(rel_path)
        return sorted(code_files)

    @staticmethod
    def map_docs_to_code(
        repo_path: str, doc_files: list[str], code_files: list[str]
    ) -> dict[str, list[str]]:
        """Map documentation files to the code directories they likely describe."""
        mapping: dict[str, list[str]] = defaultdict(list)
        code_dirs = {os.path.dirname(c) for c in code_files}

        DocCodeMapper._map_by_proximity(doc_files, code_dirs, mapping)
        DocCodeMapper._map_by_content_refs(repo_path, doc_files, code_files, mapping)
        DocCodeMapper._map_by_naming_convention(doc_files, mapping)

        return dict(mapping)

    @staticmethod
    def _map_by_proximity(
        doc_files: list[str], code_dirs: set[str], mapping: dict[str, list[str]]
    ) -> None:
        """Map docs by directory proximity (same or parent dir)."""
        for doc in doc_files:
            doc_dir = os.path.dirname(doc)
            if doc_dir in code_dirs:
                mapping[doc].append(doc_dir)
            parent = os.path.dirname(doc_dir)
            if parent in code_dirs and parent not in mapping[doc]:
                mapping[doc].append(parent)

    @staticmethod
    def _map_by_content_refs(
        repo_path: str,
        doc_files: list[str],
        code_files: list[str],
        mapping: dict[str, list[str]],
    ) -> None:
        """Map docs by referenced code file names in doc content."""
        for doc in doc_files:
            doc_full = os.path.join(repo_path, doc)
            try:
                with open(doc_full, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue

            for code in code_files:
                code_basename = os.path.basename(code)
                if code_basename in content:
                    code_dir = os.path.dirname(code)
                    if code_dir and code_dir not in mapping[doc]:
                        mapping[doc].append(code_dir)

    @staticmethod
    def _map_by_naming_convention(doc_files: list[str], mapping: dict[str, list[str]]) -> None:
        """Map README / index docs to their containing directory."""
        for doc in doc_files:
            doc_lower = os.path.basename(doc).lower()
            if doc_lower in ("readme.md", "readme.rst", "readme.txt", "index.md"):
                doc_dir = os.path.dirname(doc)
                if doc_dir not in mapping[doc]:
                    mapping[doc].append(doc_dir)

    @staticmethod
    def extract_references_from_doc(repo_path: str, doc_path: str) -> dict[str, set[str]]:
        """Extract file references, function names, and version strings from a doc."""
        full_path = os.path.join(repo_path, doc_path)
        refs: dict[str, set[str]] = {
            "files": set(),
            "functions": set(),
            "versions": set(),
            "links": set(),
        }
        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return refs

        link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
        for match in link_pattern.finditer(content):
            target = match.group(2)
            if not target.startswith(("http://", "https://", "mailto:", "#")):
                refs["files"].add(target.split("#")[0])
            refs["links"].add(target)

        func_pattern = re.compile(r"`(\w+(?:\.\w+)*)\(`")
        for match in func_pattern.finditer(content):
            refs["functions"].add(match.group(1))

        version_pattern = re.compile(r"(?:v|version[:\s]*)(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)
        for match in version_pattern.finditer(content):
            refs["versions"].add(match.group(1))

        code_ref_pattern = re.compile(r"`([^\s`]+\.\w{1,5})`")
        for match in code_ref_pattern.finditer(content):
            candidate = match.group(1)
            if Path(candidate).suffix.lower() in DocCodeMapper.CODE_EXTENSIONS:
                refs["files"].add(candidate)

        return refs
