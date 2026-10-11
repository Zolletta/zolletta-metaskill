"""Tests for docstring_strip_options.py."""

from __future__ import annotations

import dataclasses
from typing import Any

from zolletta_metaskill.code_style.python.structs import DocstringStripOptions


class TestDocstringStripOptions:
    # --- Defaults ---

    def test_defaults_match_any_enabled_semantics(self) -> None:
        """any_enabled contributes default=True for an absent key, so these do too."""
        options = DocstringStripOptions()
        assert options.strip_private is True
        assert options.strip_tests is True
        assert options.strip_nested is True
        assert options.strip_obvious_init is True

    def test_positional_order_is_private_tests_nested_init(self) -> None:
        options = DocstringStripOptions(False, False, False, False)
        assert options.strip_private is False
        assert options.strip_tests is False
        assert options.strip_nested is False
        assert options.strip_obvious_init is False

    # --- Immutability ---

    def test_is_frozen(self) -> None:
        options = DocstringStripOptions()
        try:
            options.strip_private = True  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("DocstringStripOptions should be frozen")

    # --- Settings resolution ---

    def test_from_settings_defaults_when_unset(self) -> None:
        options = DocstringStripOptions.from_settings({}, {"python"})
        assert options == DocstringStripOptions()

    def test_from_settings_reads_every_toggle(self) -> None:
        settings: dict[str, Any] = {
            "python": {
                "code_style": {
                    "docstring_strip_private": True,
                    "docstring_strip_tests": True,
                    "docstring_strip_nested": False,
                    "docstring_strip_obvious_init": True,
                }
            }
        }
        options = DocstringStripOptions.from_settings(settings, {"python"})
        assert options.strip_private is True
        assert options.strip_tests is True
        assert options.strip_nested is False
        assert options.strip_obvious_init is True

    # --- Role in the call chain ---

    def test_replaces_four_positional_booleans(self) -> None:
        """The shape this exists to remove: _analyze_function(node, path, F, F, F, F)."""
        import inspect

        from zolletta_metaskill.code_style.python.docstring_streamliner import DocstringStreamliner

        params = list(inspect.signature(DocstringStreamliner._analyze_function).parameters)
        assert params == ["node", "path", "options"]

    def test_field_names_match_the_settings_keys(self) -> None:
        names = {f.name for f in dataclasses.fields(DocstringStripOptions)}
        assert names == {
            "strip_private",
            "strip_tests",
            "strip_nested",
            "strip_obvious_init",
        }
