"""DocstringStripOptions dataclass for the docstring strip toggles."""

from __future__ import annotations

from dataclasses import dataclass

from zolletta_metaskill.core.project_config import ProjectConfig


@dataclass(frozen=True)
class DocstringStripOptions:
    """The four ``docstring_strip_*`` toggles, resolved once per run.

    These are four ``python.code_style`` keys that are always resolved together
    and always travel together. Passed as loose booleans they produced calls
    like ``_analyze_function(node, path, False, False, False, True)``, where the
    positional booleans are unreadable and easy to transpose.

    The defaults mirror :meth:`ProjectConfig.any_enabled`, which contributes its
    own ``default=True`` when a language section or key is absent — so an
    unconfigured project strips by default. Declaring ``False`` here would make
    a directly-constructed instance disagree with the same instance resolved
    from empty settings.

    Attributes:
        strip_private: Remove docstrings from private members.
        strip_tests: Remove docstrings from ``test_*`` functions.
        strip_nested: Remove docstrings from nested or local functions.
        strip_obvious_init: Remove ``__init__`` docstrings when every parameter
            is documented.

    """

    strip_private: bool = True
    strip_tests: bool = True
    strip_nested: bool = True
    strip_obvious_init: bool = True

    @classmethod
    def from_settings(
        cls, settings: dict[str, object], py_langs: set[str]
    ) -> DocstringStripOptions:
        """Resolve every ``docstring_strip_*`` toggle from *settings*.

        Args:
            settings: Parsed ``settings.json`` contents.
            py_langs: Configured language keys, as ``ProjectConfig`` expects.

        Returns:
            The four toggles, resolved once for the whole run.

        """
        return cls(
            strip_private=ProjectConfig.any_enabled(
                settings, py_langs, "code_style.docstring_strip_private"
            ),
            strip_tests=ProjectConfig.any_enabled(
                settings, py_langs, "code_style.docstring_strip_tests"
            ),
            strip_nested=ProjectConfig.any_enabled(
                settings, py_langs, "code_style.docstring_strip_nested"
            ),
            strip_obvious_init=ProjectConfig.any_enabled(
                settings, py_langs, "code_style.docstring_strip_obvious_init"
            ),
        )
