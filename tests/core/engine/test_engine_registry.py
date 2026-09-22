"""Tests for zolletta_metaskill.core.engine.engine_registry — register, get, file matching."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

from .stub_engine import StubEngine


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Ensure the registry is empty before and after each test."""
    EngineRegistry.clear()
    yield
    EngineRegistry.clear()


class TestEngineRegistry:
    # --- Tests for EngineRegistry.register. ---

    def test_stubengine_register_single_returns_engine(self) -> None:
        """A single engine can be registered and retrieved."""
        engine = StubEngine("python", [".py"])
        EngineRegistry.register(engine)
        assert EngineRegistry.get("python") is engine

    def test_stubengine_register_multiple_returns_php(self) -> None:
        """Multiple engines can be registered."""
        py = StubEngine("python", [".py"])
        php = StubEngine("php", [".php"])
        EngineRegistry.register(py)
        EngineRegistry.register(php)
        assert EngineRegistry.get("python") is py
        assert EngineRegistry.get("php") is php

    def test_stubengine_duplicate_raises_raises_valueerror(self) -> None:
        """Registering the same language twice raises ValueError."""
        EngineRegistry.register(StubEngine("python", [".py"]))
        with pytest.raises(ValueError, match="already registered"):
            EngineRegistry.register(StubEngine("python", [".py"]))

    # --- Tests for EngineRegistry.get. ---

    def test_stubengine_get_registered_returns_engine(self) -> None:
        """EngineRegistry.get returns the registered engine."""
        engine = StubEngine("python", [".py"])
        EngineRegistry.register(engine)
        assert EngineRegistry.get("python") is engine

    def test_get_unknown_raises_key_error(self) -> None:
        """EngineRegistry.get raises KeyError for an unknown language."""
        with pytest.raises(KeyError, match="No engine registered"):
            EngineRegistry.get("ruby")

    # --- Tests for EngineRegistry.get_for_file. ---

    def test_match_by_extension(self) -> None:
        """EngineRegistry.get_for_file returns the engine matching the file extension."""
        EngineRegistry.register(StubEngine("python", [".py"]))
        EngineRegistry.register(StubEngine("php", [".php"]))
        py_engine = EngineRegistry.get_for_file(Path("/tmp/foo.py"))
        assert py_engine is not None
        assert py_engine.language == "python"
        php_engine = EngineRegistry.get_for_file(Path("/tmp/bar.php"))
        assert php_engine is not None
        assert php_engine.language == "php"

    def test_no_match_returns_none(self) -> None:
        """EngineRegistry.get_for_file returns None for unknown extensions."""
        EngineRegistry.register(StubEngine("python", [".py"]))
        assert EngineRegistry.get_for_file(Path("/tmp/foo.rb")) is None

    def test_no_engines_registered(self) -> None:
        """EngineRegistry.get_for_file returns None when no engines are registered."""
        assert EngineRegistry.get_for_file(Path("/tmp/foo.py")) is None

    def test_first_registered_wins_on_conflict(self) -> None:
        """If two engines share an extension, the first registered one wins."""
        first = StubEngine("python", [".py"])
        second = StubEngine("cython", [".py"])
        EngineRegistry.register(first)
        EngineRegistry.register(second)
        assert EngineRegistry.get_for_file(Path("/tmp/foo.py")) is first

    def test_case_sensitive_extension(self) -> None:
        """File extension matching is case-sensitive."""
        EngineRegistry.register(StubEngine("python", [".py"]))
        assert EngineRegistry.get_for_file(Path("/tmp/foo.PY")) is None

    # --- Tests for EngineRegistry.available_languages. ---

    def test_available_languages_empty_input_returns_empty_list(self) -> None:
        """EngineRegistry.available_languages returns an empty list when nothing is registered."""
        assert EngineRegistry.available_languages() == []

    def test_stubengine_sorted_returns_multiple_items(self) -> None:
        """EngineRegistry.available_languages returns a sorted list."""
        EngineRegistry.register(StubEngine("php", [".php"]))
        EngineRegistry.register(StubEngine("python", [".py"]))
        EngineRegistry.register(StubEngine("javascript", [".js"]))
        assert EngineRegistry.available_languages() == ["javascript", "php", "python"]

    # --- Tests for EngineRegistry.clear. ---

    def test_stubengine_clear_returns_none(self) -> None:
        """EngineRegistry.clear removes all engines."""
        EngineRegistry.register(StubEngine("python", [".py"]))
        EngineRegistry.clear()
        assert EngineRegistry.available_languages() == []
        assert EngineRegistry.get_for_file(Path("/tmp/foo.py")) is None

    # --- Verify that stub engines satisfy the LanguageEngine protocol. ---

    def test_stub_is_language_engine(self) -> None:
        """The stub engine satisfies the runtime-checkable protocol."""
        from zolletta_metaskill.core.engine.language_engine import LanguageEngine

        engine = StubEngine("python", [".py"])
        assert isinstance(engine, LanguageEngine)
