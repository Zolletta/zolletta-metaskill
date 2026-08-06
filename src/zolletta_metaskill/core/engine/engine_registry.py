"""Engine registry — maps language names and file extensions to engines.

Scanners call :meth:`EngineRegistry.get_for_file` to obtain the correct engine
for a given file path, without knowing which languages are registered.
"""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.core.engine.language_engine import LanguageEngine


class EngineRegistry:
    """Registry mapping language names and file extensions to engines.

    All methods are class-level — the registry is a process-wide singleton
    backed by a class-level ``_ENGINES`` dict. Use :meth:`clear` in tests
    to reset the registry between test runs.
    """

    _ENGINES: dict[str, LanguageEngine] = {}

    @classmethod
    def register(cls, engine: LanguageEngine) -> None:
        """Register *engine* under its ``language`` identifier.

        Args:
            engine: An instance implementing :class:`LanguageEngine`.

        Raises:
            ValueError: If an engine for the same language is already registered.

        """
        lang = engine.language
        if lang in cls._ENGINES:
            raise ValueError(f"Engine for language '{lang}' is already registered")
        cls._ENGINES[lang] = engine

    @classmethod
    def get(cls, language: str) -> LanguageEngine:
        """Return the registered engine for *language*.

        Args:
            language: The language identifier (e.g. ``"python"``).

        Returns:
            The :class:`LanguageEngine` instance for *language*.

        Raises:
            KeyError: If no engine is registered for *language*.

        """
        try:
            return cls._ENGINES[language]
        except KeyError:
            raise KeyError(f"No engine registered for language '{language}'") from None

    @classmethod
    def get_for_file(cls, path: Path) -> LanguageEngine | None:
        """Return the engine that handles *path*, or ``None`` if no engine matches.

        The match is based on the file extension. If multiple engines share
        the same extension, the first registered one wins.
        """
        suffix = path.suffix
        for engine in cls._ENGINES.values():
            if suffix in engine.file_extensions():
                return engine
        return None

    @classmethod
    def available_languages(cls) -> list[str]:
        """Return a sorted list of registered language identifiers."""
        return sorted(cls._ENGINES.keys())

    @classmethod
    def ensure(cls, engine: LanguageEngine) -> None:
        """Register *engine* if its language is not already registered.

        Unlike :meth:`register`, this is idempotent: if an engine for the
        same language is already registered, it does nothing (and does not
        raise).  This makes it safe to call from scanner entry points every
        time, even after :meth:`clear` has been used in tests.

        Args:
            engine: An instance implementing :class:`LanguageEngine`.

        """
        if engine.language not in cls._ENGINES:
            cls._ENGINES[engine.language] = engine

    @classmethod
    def clear(cls) -> None:
        """Remove all registered engines (primarily for testing)."""
        cls._ENGINES.clear()
