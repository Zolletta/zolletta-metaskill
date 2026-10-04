"""Tests for documentor_settings.py."""

from __future__ import annotations

import os
from pathlib import Path

from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings


class TestDocumentorSettings:
    # --- resolve_cache_dir ---

    def test_resolve_cache_dir_configured_path_returns_absolute(self, tmp_path: Path) -> None:
        settings = {"documentation": {"cache_dir": str(tmp_path / "mycache")}}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == Path(os.path.abspath(str(tmp_path / "mycache")))

    def test_resolve_cache_dir_unset_falls_back_to_default(self) -> None:
        result = DocumentorSettings.resolve_cache_dir({})
        assert result == Path(os.path.abspath(DocumentorSettings.DEFAULT_CACHE_DIR))

    def test_resolve_cache_dir_empty_string_falls_back_to_default(self) -> None:
        result = DocumentorSettings.resolve_cache_dir({"documentation": {"cache_dir": ""}})
        assert result == Path(os.path.abspath(DocumentorSettings.DEFAULT_CACHE_DIR))

    def test_resolve_cache_dir_non_string_falls_back_to_default(self) -> None:
        result = DocumentorSettings.resolve_cache_dir({"documentation": {"cache_dir": 42}})
        assert result == Path(os.path.abspath(DocumentorSettings.DEFAULT_CACHE_DIR))

    def test_resolve_cache_dir_relative_path_is_resolved(self) -> None:
        settings = {"documentation": {"cache_dir": "custom-cache"}}
        result = DocumentorSettings.resolve_cache_dir(settings)
        assert result == Path(os.path.abspath("custom-cache"))
