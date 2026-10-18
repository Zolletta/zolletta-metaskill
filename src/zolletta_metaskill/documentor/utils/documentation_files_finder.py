"""DocumentationFilesFinder — the single definition of project documentation."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.structs import DocumentationInventory


class DocumentationFilesFinder:
    """The single definition of which files count as project documentation.

    Contracts and generated markdown are out of scope by construction:
    ``skills/``, ``SKILL.md`` and ``CHANGELOG.md`` are never returned. They are
    hand-maintained contracts and release output, so drift-scoring them
    produces findings no author can act on.

    Markdown only, and deliberately so. The reference extractors are
    markdown-shaped, so an ``.rst`` file would be scanned, yield nothing, and
    report clean — a false all-clear is worse than an honest gap. Widening
    ``DOC_EXTENSIONS`` is a decision to take alongside an extractor that
    understands the added syntax, which is why the list lives in code rather
    than in a settings key that looks like it can be edited safely.

    """

    DOC_EXTENSIONS: tuple[str, ...] = (".md", ".markdown", ".mdown", ".mkd")

    ROOT_DOCUMENT_KINDS: Mapping[str, str] = {
        "readme": "README.md",
        "contributing": "CONTRIBUTING.md",
        "agents": "AGENTS.md",
    }

    @staticmethod
    def find(settings: dict[str, Any], repo_path: str) -> DocumentationInventory:
        """Return the documentation inventory of *repo_path*.

        Settings in, paths out: this reads no settings file itself, so it stays
        a pure function of its arguments while the directory it scopes to still
        comes from ``settings.json`` and never from a command-line flag.

        An empty ``documentation.dir`` beside a ``README.md`` is one document,
        not zero: root documents are always in scope, so a project without a
        docs tree still gets a review instead of a skipped run.
        """
        root = Path(repo_path)
        docs_root = root / ProjectConfig.docs_dir(settings)

        return DocumentationInventory(
            documentation=DocumentationFilesFinder._documentation_paths(root, docs_root),
            root_documents=DocumentationFilesFinder._match_root_documents(root),
            skipped_reason=DocumentationFilesFinder._skipped_reason(settings, docs_root),
        )

    @staticmethod
    def _documentation_paths(root: Path, docs_root: Path) -> tuple[str, ...]:
        """Return the markdown under *docs_root* as repo-relative paths, sorted."""
        if not docs_root.is_dir():
            return ()
        extensions = set(DocumentationFilesFinder.DOC_EXTENSIONS)
        paths = ProjectConfig.iter_files(docs_root, extensions)
        return tuple(sorted(os.path.relpath(path, root) for path in paths))

    @staticmethod
    def _match_root_documents(root: Path) -> dict[str, str]:
        """Map each root document kind to the file present at *root*, ignoring case.

        One directory listing rather than one per kind. An absent document is
        simply not a key, so a repository without an ``AGENTS.md`` is not an
        error and needs no placeholder.
        """
        try:
            entries = os.listdir(root)
        except OSError:
            return {}
        present = {entry.lower(): entry for entry in entries}
        matched: dict[str, str] = {}
        for kind, filename in sorted(DocumentationFilesFinder.ROOT_DOCUMENT_KINDS.items()):
            entry = present.get(filename.lower())
            if entry is not None:
                matched[kind] = entry
        return matched

    @staticmethod
    def _skipped_reason(settings: dict[str, Any], docs_root: Path) -> str | None:
        """Return why discovery is empty, or ``None`` when it is a real zero.

        Only a *configured* directory that is missing is a misconfiguration. An
        unconfigured default that is absent means the project keeps its
        documentation elsewhere, and an empty directory is a legitimate zero;
        neither is reported as a problem.
        """
        configured = ProjectConfig.setting(settings, "documentation.dir", None)
        if configured is None or docs_root.is_dir():
            return None
        return f"documentation.dir '{configured}' is not a directory"
