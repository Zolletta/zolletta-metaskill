"""DocCodeMapper associates documentation files with corresponding source code files.

Handles code file discovery, document-to-code mapping heuristics, and doc reference extraction.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.utils.fenced_content import FencedContent


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
    def find_code_files(repo_path: str, scope: str = "") -> list[str]:
        """Find all code files in the repository.

        Enumeration goes through ``ProjectConfig.iter_files``, so git decides
        what is excluded: every exclude source it honours (``.gitignore``,
        ``.git/info/exclude``, ``core.excludesFile``) rather than the subset a
        hand-rolled reader of ``.gitignore`` could see. That reader is gone, and
        so is its identical twin in ``FileDiscovery`` — two parsers of the same
        file are two answers waiting to disagree.
        """
        root = Path(repo_path)
        # pragma: no mutate start — ``root / ""`` equals ``root``, so the truthiness check is
        # unobservable
        search_path = root / scope if scope else root
        # pragma: no mutate end
        if not search_path.is_dir():
            return []
        found = ProjectConfig.iter_files(search_path, set(DocCodeMapper.CODE_EXTENSIONS))
        return sorted(os.path.relpath(path, root) for path in found)

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
                with open(doc_full, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
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
            with open(full_path, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
                content = f.read()
        except OSError:
            return refs

        # A ```markdown block *illustrating* a link is documentation about a
        # link, not a reference to one. Stripping fences here — rather than
        # tracking them inline — is what makes this agree structurally with
        # link_checker instead of by coincidence.
        content = FencedContent.strip_fences(content)

        link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
        for match in link_pattern.finditer(content):
            target = match.group(2)
            if not target.startswith(("http://", "https://", "mailto:", "#")):
                refs["files"].add(target.split("#")[0])
            refs["links"].add(target)

        func_pattern = re.compile(r"`(\w+(?:\.\w+)*)\(`")
        for match in func_pattern.finditer(content):
            refs["functions"].add(match.group(1))

        # pragma: no mutate start — IGNORECASE makes literal casing in the pattern unobservable
        version_pattern = re.compile(r"(?:v|version[:\s]*)(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)
        # pragma: no mutate end
        for match in version_pattern.finditer(content):
            refs["versions"].add(match.group(1))

        code_ref_pattern = re.compile(r"`([^\s`]+\.\w{1,5})`")
        for match in code_ref_pattern.finditer(content):
            candidate = match.group(1)
            if Path(candidate).suffix.lower() in DocCodeMapper.CODE_EXTENSIONS:
                refs["files"].add(candidate)

        return refs
