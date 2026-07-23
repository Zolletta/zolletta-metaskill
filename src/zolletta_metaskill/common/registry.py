"""Engine registry — maps language names and file extensions to engines.

Scanners call :func:`get_engine_for_file` to obtain the correct engine
for a given file path, without knowing which languages are registered.
"""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.common.language_engine import LanguageEngine

_ENGINES: dict[str, LanguageEngine] = {}


def register_engine(engine: LanguageEngine) -> None:
    """Register *engine* under its ``language`` identifier.

    Args:
        engine: An instance implementing :class:`LanguageEngine`.

    Raises:
        ValueError: If an engine for the same language is already registered.

    """
    lang = engine.language
    if lang in _ENGINES:
        raise ValueError(f"Engine for language '{lang}' is already registered")
    _ENGINES[lang] = engine


def get_engine(language: str) -> LanguageEngine:
    """Return the registered engine for *language*.

    Args:
        language: The language identifier (e.g. ``"python"``).

    Returns:
        The :class:`LanguageEngine` instance for *language*.

    Raises:
        KeyError: If no engine is registered for *language*.

    """
    try:
        return _ENGINES[language]
    except KeyError:
        raise KeyError(f"No engine registered for language '{language}'") from None


def get_engine_for_file(path: Path) -> LanguageEngine | None:
    """Return the engine that handles *path*, or ``None`` if no engine matches.

    The match is based on the file extension. If multiple engines share
    the same extension, the first registered one wins.
    """
    suffix = path.suffix
    for engine in _ENGINES.values():
        if suffix in engine.file_extensions():
            return engine
    return None


def available_languages() -> list[str]:
    """Return a sorted list of registered language identifiers."""
    return sorted(_ENGINES.keys())


def ensure_engine(engine: LanguageEngine) -> None:
    """Register *engine* if its language is not already registered.

    Unlike :func:`register_engine`, this is idempotent: if an engine for
    the same language is already registered, it does nothing (and does not
    raise).  This makes it safe to call from scanner entry points every
    time, even after :func:`clear_registry` has been used in tests.

    Args:
        engine: An instance implementing :class:`LanguageEngine`.

    """
    if engine.language not in _ENGINES:
        _ENGINES[engine.language] = engine


def clear_registry() -> None:
    """Remove all registered engines (primarily for testing)."""
    _ENGINES.clear()
