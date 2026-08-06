"""Tests for zolletta_metaskill.core.engine.engine_registry — register, get, file matching."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.structs import ModuleInfo

# --- Test engine stubs ----------------------------------------------------


class _StubEngine:
    """Minimal engine stub for registry tests."""

    def __init__(self, lang: str, exts: list[str]) -> None:
        self._lang = lang
        self._exts = exts

    @property
    def language(self) -> str:
        return self._lang

    def parse_module(self, path: Path) -> ModuleInfo:  # pragma: no cover
        return ModuleInfo(path=path, language=self._lang)

    def is_test_file(self, path: Path) -> bool:  # pragma: no cover
        return path.stem.startswith("test_")

    def is_source_file(self, path: Path) -> bool:  # pragma: no cover
        return path.suffix in self._exts

    def file_extensions(self) -> list[str]:
        return self._exts

    def test_file_glob(self) -> str:  # pragma: no cover
        return f"test_*{self._exts[0]}"


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Ensure the registry is empty before and after each test."""
    EngineRegistry.clear()
    yield
    EngineRegistry.clear()


class TestRegisterEngine:
    """Tests for EngineRegistry.register."""

    def test_stubengine_register_single_returns_engine(self) -> None:
        """A single engine can be registered and retrieved."""
        engine = _StubEngine("python", [".py"])
        EngineRegistry.register(engine)
        assert EngineRegistry.get("python") is engine

    def test_stubengine_register_multiple_returns_php(self) -> None:
        """Multiple engines can be registered."""
        py = _StubEngine("python", [".py"])
        php = _StubEngine("php", [".php"])
        EngineRegistry.register(py)
        EngineRegistry.register(php)
        assert EngineRegistry.get("python") is py
        assert EngineRegistry.get("php") is php

    def test_stubengine_duplicate_raises_raises_valueerror(self) -> None:
        """Registering the same language twice raises ValueError."""
        EngineRegistry.register(_StubEngine("python", [".py"]))
        with pytest.raises(ValueError, match="already registered"):
            EngineRegistry.register(_StubEngine("python", [".py"]))


class TestGetEngine:
    """Tests for EngineRegistry.get."""

    def test_stubengine_get_registered_returns_engine(self) -> None:
        """EngineRegistry.get returns the registered engine."""
        engine = _StubEngine("python", [".py"])
        EngineRegistry.register(engine)
        assert EngineRegistry.get("python") is engine

    def test_get_unknown_raises_key_error(self) -> None:
        """EngineRegistry.get raises KeyError for an unknown language."""
        with pytest.raises(KeyError, match="No engine registered"):
            EngineRegistry.get("ruby")


class TestGetEngineForFile:
    """Tests for EngineRegistry.get_for_file."""

    def test_match_by_extension(self) -> None:
        """EngineRegistry.get_for_file returns the engine matching the file extension."""
        EngineRegistry.register(_StubEngine("python", [".py"]))
        EngineRegistry.register(_StubEngine("php", [".php"]))
        py_engine = EngineRegistry.get_for_file(Path("/tmp/foo.py"))
        assert py_engine is not None
        assert py_engine.language == "python"
        php_engine = EngineRegistry.get_for_file(Path("/tmp/bar.php"))
        assert php_engine is not None
        assert php_engine.language == "php"

    def test_no_match_returns_none(self) -> None:
        """EngineRegistry.get_for_file returns None for unknown extensions."""
        EngineRegistry.register(_StubEngine("python", [".py"]))
        assert EngineRegistry.get_for_file(Path("/tmp/foo.rb")) is None

    def test_no_engines_registered(self) -> None:
        """EngineRegistry.get_for_file returns None when no engines are registered."""
        assert EngineRegistry.get_for_file(Path("/tmp/foo.py")) is None

    def test_first_registered_wins_on_conflict(self) -> None:
        """If two engines share an extension, the first registered one wins."""
        first = _StubEngine("python", [".py"])
        second = _StubEngine("cython", [".py"])
        EngineRegistry.register(first)
        EngineRegistry.register(second)
        assert EngineRegistry.get_for_file(Path("/tmp/foo.py")) is first

    def test_case_sensitive_extension(self) -> None:
        """File extension matching is case-sensitive."""
        EngineRegistry.register(_StubEngine("python", [".py"]))
        assert EngineRegistry.get_for_file(Path("/tmp/foo.PY")) is None


class TestAvailableLanguages:
    """Tests for EngineRegistry.available_languages."""

    def test_available_languages_empty_input_returns_empty_list(self) -> None:
        """EngineRegistry.available_languages returns an empty list when nothing is registered."""
        assert EngineRegistry.available_languages() == []

    def test_stubengine_sorted_returns_multiple_items(self) -> None:
        """EngineRegistry.available_languages returns a sorted list."""
        EngineRegistry.register(_StubEngine("php", [".php"]))
        EngineRegistry.register(_StubEngine("python", [".py"]))
        EngineRegistry.register(_StubEngine("javascript", [".js"]))
        assert EngineRegistry.available_languages() == ["javascript", "php", "python"]


class TestClearRegistry:
    """Tests for EngineRegistry.clear."""

    def test_stubengine_clear_returns_none(self) -> None:
        """EngineRegistry.clear removes all engines."""
        EngineRegistry.register(_StubEngine("python", [".py"]))
        EngineRegistry.clear()
        assert EngineRegistry.available_languages() == []
        assert EngineRegistry.get_for_file(Path("/tmp/foo.py")) is None


class TestProtocolConformance:
    """Verify that stub engines satisfy the LanguageEngine protocol."""

    def test_stub_is_language_engine(self) -> None:
        """The stub engine satisfies the runtime-checkable protocol."""
        from zolletta_metaskill.core.engine.language_engine import LanguageEngine

        engine = _StubEngine("python", [".py"])
        assert isinstance(engine, LanguageEngine)
