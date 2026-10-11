"""Shared settings helpers for documentor tools."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class DocumentorSettings:
    """Resolves documentor-specific settings such as cache directories."""

    DEFAULT_CACHE_DIR = ".zolletta-metaskill/cache"

    #: Run folders are named ``YYYY-MM-DD-HH-MM`` by the review orchestrator.
    #: Anything else under ``runs_dir`` (notably a flat ``cache/`` directory) is
    #: not a run and must never be mistaken for the most recent one.
    RUN_FOLDER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")

    @staticmethod
    def resolve_cache_dir(settings: dict[str, Any]) -> Path:
        """Return the cache directory for documentor tool outputs.

        Resolution order:

        1. ``documentation.cache_dir`` from *settings*, when set to a non-empty
           string. This is an explicit override and always wins.
        2. The ``cache/`` directory of the most recent review run folder under
           ``runs_dir``. Run folders are named ``YYYY-MM-DD-HH-MM``, so the
           lexicographically greatest name is the most recent one. Keeping
           artifacts inside the run folder means each review keeps its own
           history instead of overwriting a single shared directory.
        3. ``<runs_dir>/cache`` when no run folder exists yet, i.e. before the
           first review has created one.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            Absolute path to the cache directory. The directory is not created
            here; callers write into it.

        """
        configured = ProjectConfig.setting(settings, "documentation.cache_dir", None)
        if isinstance(configured, str) and configured:
            return Path(os.path.abspath(configured))
        return DocumentorSettings._default_cache_dir(settings)

    @staticmethod
    def _default_cache_dir(settings: dict[str, Any]) -> Path:
        """Return the per-run cache directory, or the ``runs_dir`` fallback."""
        runs_dir = ProjectConfig.runs_dir(settings)
        latest_run = DocumentorSettings._latest_run_dir(runs_dir)
        if latest_run is not None:
            return latest_run / "cache"
        return Path(os.path.abspath(runs_dir / "cache"))

    @staticmethod
    def _latest_run_dir(runs_dir: Path) -> Path | None:
        """Return the most recent timestamped run folder under *runs_dir*.

        Only directories whose name matches :attr:`RUN_FOLDER_PATTERN` are
        considered, so a sibling ``cache/`` directory is never selected — it
        would otherwise win the lexicographic comparison, since ``"cache"``
        sorts after any ``"YYYY-..."`` name.

        Returns:
            The greatest-named matching run folder, or ``None`` when *runs_dir*
            is absent or holds no run folders.

        """
        if not runs_dir.is_dir():
            return None
        candidates = [
            child
            for child in runs_dir.iterdir()
            if child.is_dir() and DocumentorSettings.RUN_FOLDER_PATTERN.match(child.name)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.name)
