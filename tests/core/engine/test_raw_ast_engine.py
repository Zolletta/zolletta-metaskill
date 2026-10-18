"""Tests for raw_ast_engine.py."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from zolletta_metaskill.core.engine.raw_ast_engine import RawASTEngine


def _raw_ast_capable() -> Any:
    """Build an object exposing ``parse_raw``, which is the whole contract."""
    return SimpleNamespace(parse_raw=lambda path: (None, b""))


class TestRawASTEngine:
    """The protocol is runtime-checkable so scanners can gate on the capability."""

    # --- runtime_checkable membership ---

    def test_raw_ast_engine_with_parse_raw_satisfies_the_protocol(self) -> None:
        assert isinstance(_raw_ast_capable(), RawASTEngine)

    def test_raw_ast_engine_without_parse_raw_fails_the_protocol(self) -> None:
        assert not isinstance(SimpleNamespace(), RawASTEngine)

    def test_raw_ast_engine_with_other_parser_method_fails_the_protocol(self) -> None:
        engine = SimpleNamespace(parse=lambda path: (None, b""))
        assert not isinstance(engine, RawASTEngine)
