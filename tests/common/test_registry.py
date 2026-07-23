"""Tests for zolletta_metaskill.common.registry — register, get, file matching."""

from __future__ import annotations

from pathlib import Path

import pytest

from zolletta_metaskill.common.models import ModuleInfo
from zolletta_metaskill.common.registry import (
    available_languages,
    clear_registry,
    get_engine,
    get_engine_for_file,
    register_engine,
)

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

    def test_file_pattern(self) -> str:  # pragma: no cover
        return f"test_*{self._exts[0]}"


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Ensure the registry is empty before and after each test."""
    clear_registry()
    yield
    clear_registry()


class TestRegisterEngine:
    """Tests for register_engine."""

    def test_register_single(self) -> None:
        """A single engine can be registered and retrieved."""
        engine = _StubEngine("python", [".py"])
        register_engine(engine)
        assert get_engine("python") is engine

    def test_register_multiple(self) -> None:
        """Multiple engines can be registered."""
        py = _StubEngine("python", [".py"])
        php = _StubEngine("php", [".php"])
        register_engine(py)
        register_engine(php)
        assert get_engine("python") is py
        assert get_engine("php") is php

    def test_duplicate_raises(self) -> None:
        """Registering the same language twice raises ValueError."""
        register_engine(_StubEngine("python", [".py"]))
        with pytest.raises(ValueError, match="already registered"):
            register_engine(_StubEngine("python", [".py"]))


class TestGetEngine:
    """Tests for get_engine."""

    def test_get_registered(self) -> None:
        """get_engine returns the registered engine."""
        engine = _StubEngine("python", [".py"])
        register_engine(engine)
        assert get_engine("python") is engine

    def test_get_unknown_raises_key_error(self) -> None:
        """get_engine raises KeyError for an unknown language."""
        with pytest.raises(KeyError, match="No engine registered"):
            get_engine("ruby")


class TestGetEngineForFile:
    """Tests for get_engine_for_file."""

    def test_match_by_extension(self) -> None:
        """get_engine_for_file returns the engine matching the file extension."""
        register_engine(_StubEngine("python", [".py"]))
        register_engine(_StubEngine("php", [".php"]))
        assert get_engine_for_file(Path("/tmp/foo.py")).language == "python"
        assert get_engine_for_file(Path("/tmp/bar.php")).language == "php"

    def test_no_match_returns_none(self) -> None:
        """get_engine_for_file returns None for unknown extensions."""
        register_engine(_StubEngine("python", [".py"]))
        assert get_engine_for_file(Path("/tmp/foo.rb")) is None

    def test_no_engines_registered(self) -> None:
        """get_engine_for_file returns None when no engines are registered."""
        assert get_engine_for_file(Path("/tmp/foo.py")) is None

    def test_first_registered_wins_on_conflict(self) -> None:
        """If two engines share an extension, the first registered one wins."""
        first = _StubEngine("python", [".py"])
        second = _StubEngine("cython", [".py"])
        register_engine(first)
        register_engine(second)
        assert get_engine_for_file(Path("/tmp/foo.py")) is first

    def test_case_sensitive_extension(self) -> None:
        """File extension matching is case-sensitive."""
        register_engine(_StubEngine("python", [".py"]))
        assert get_engine_for_file(Path("/tmp/foo.PY")) is None


class TestAvailableLanguages:
    """Tests for available_languages."""

    def test_empty(self) -> None:
        """available_languages returns an empty list when nothing is registered."""
        assert available_languages() == []

    def test_sorted(self) -> None:
        """available_languages returns a sorted list."""
        register_engine(_StubEngine("php", [".php"]))
        register_engine(_StubEngine("python", [".py"]))
        register_engine(_StubEngine("javascript", [".js"]))
        assert available_languages() == ["javascript", "php", "python"]


class TestClearRegistry:
    """Tests for clear_registry."""

    def test_clear(self) -> None:
        """clear_registry removes all engines."""
        register_engine(_StubEngine("python", [".py"]))
        clear_registry()
        assert available_languages() == []
        assert get_engine_for_file(Path("/tmp/foo.py")) is None


class TestProtocolConformance:
    """Verify that stub engines satisfy the LanguageEngine protocol."""

    def test_stub_is_language_engine(self) -> None:
        """The stub engine satisfies the runtime-checkable protocol."""
        from zolletta_metaskill.common.language_engine import LanguageEngine

        engine = _StubEngine("python", [".py"])
        assert isinstance(engine, LanguageEngine)
