"""Fixtures shared by the grice tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from zolletta_metaskill.grice.structs import DocumentFeatures


@pytest.fixture
def make_features() -> Callable[..., DocumentFeatures]:
    """Return a factory that builds a :class:`DocumentFeatures` from defaults.

    Every scorer reads a handful of the ten fields and ignores the rest, so a
    test states only the fields its metric depends on. A fully spelled-out
    document in each test would bury the one value under test in nine defaults.
    """

    def build(path: str = "docs/index.md", **overrides: Any) -> DocumentFeatures:
        defaults: dict[str, Any] = {
            "path": path,
            "prose": "",
            "frontmatter": "",
            "sections": (),
            "sentences": (),
            "headings": (),
            "heading_levels": (),
            "heading_lines": (),
            "code_spans": (),
            "boilerplate_words": 0,
        }
        defaults.update(overrides)
        return DocumentFeatures(**defaults)

    return build
