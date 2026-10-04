"""Shared settings helpers for documentor tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class DocumentorSettings:
    """Resolves documentor-specific settings such as cache directories."""

    DEFAULT_CACHE_DIR = ".zolletta-metaskill/cache"

    @staticmethod
    def resolve_cache_dir(settings: dict[str, Any]) -> Path:
        """Return the cache directory for documentor tool outputs.

        Reads ``documentation.cache_dir`` from *settings*. Falls back to
        ``.zolletta-metaskill/cache`` relative to the current working directory.
        """
        configured = ProjectConfig.setting(settings, "documentation.cache_dir", None)
        if isinstance(configured, str) and configured:
            return Path(os.path.abspath(configured))
        return Path(os.path.abspath(DocumentorSettings.DEFAULT_CACHE_DIR))
