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

    def is_test_file(self, path: Path) -> bool:  # pragma: no cover
        return path.stem.startswith("test_")

    def is_source_file(self, path: Path) -> bool:  # pragma: no cover
        return path.suffix in self._exts

    def file_extensions(self) -> list[str]:
        return self._exts

    def test_file_glob(self) -> str:  # pragma: no cover
        return f"test_*{self._exts[0]}"
