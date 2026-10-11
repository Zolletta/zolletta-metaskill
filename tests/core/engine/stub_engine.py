"""Stub engine shared by engine registry tests."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.core.structs import ModuleInfo


class StubEngine:
    """Minimal engine stub for registry tests."""

    def __init__(self, lang: str, exts: list[str]) -> None:
        self._lang = lang
        self._exts = exts

    @property
    def language(self) -> str:
        return self._lang

    def parse_module(self, path: Path) -> ModuleInfo:  # pragma: no cover
        return ModuleInfo(path=path, language=self._lang)

    def file_extensions(self) -> list[str]:
        return self._exts
