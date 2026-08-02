"""Tests for ADRCache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from zolletta_metaskill.adr.adr_cache import ADRCache


class TestCacheManagement:
    """Tests for ADRCache."""

    def test_save_and_load_cache(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.json"
        cache = ADRCache(cache_path)
        data = {"ADR-001": {"path": "adr/001.md", "mtime": 123.0, "status": "Accepted"}}
        cache.save(data)
        loaded = cache.load()
        assert loaded == data

    def test_load_nonexistent_cache(self, tmp_path: Path) -> None:
        cache = ADRCache(tmp_path / "nope.json")
        assert cache.load() == {}

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("not json{", encoding="utf-8")
        cache = ADRCache(cache_path)
        assert cache.load() == {}

    def test_load_non_dict_json(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("[1, 2, 3]", encoding="utf-8")
        cache = ADRCache(cache_path)
        assert cache.load() == {}

    def test_load_oserror(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("{}", encoding="utf-8")
        cache = ADRCache(cache_path)
        with patch("pathlib.Path.read_text", side_effect=OSError("nope")):
            assert cache.load() == {}

    def test_save_creates_parent_dir(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "subdir" / "cache.json"
        cache = ADRCache(cache_path)
        cache.save({})
        assert cache_path.exists()
