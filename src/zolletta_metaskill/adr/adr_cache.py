"""ADR mtime cache management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zolletta_metaskill.adr.adr_record import ADRRecord


class ADRCache:
    """Load and save the ADR mtime cache as JSON."""

    CACHE_FILENAME = "adr-cache.json"

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path

    def load(self) -> dict[str, dict[str, Any]]:
        """Load the ADR mtime cache.

        Returns an empty dict if the cache does not exist or is invalid.
        """
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def save(self, cache: dict[str, dict[str, Any]]) -> None:
        """Save the ADR mtime cache as JSON."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def key(record: ADRRecord) -> str:
        """Generate the cache key for an ADR record."""
        return f"ADR-{record.number}"
