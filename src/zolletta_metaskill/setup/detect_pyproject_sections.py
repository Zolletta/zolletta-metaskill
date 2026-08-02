#!/usr/bin/env python3
"""Detect which ``[tool.*]`` sections exist in ``pyproject.toml``.

Checks for the configuration sections used by the setup skill to determine
Python tool availability: ``[tool.ruff]``, ``[tool.mypy]``,
``[tool.pytest.ini_options]``, ``[tool.vulture]``, ``[tool.ty]``, and
``[project]`` (for uv).

Usage:
    python3 detect_pyproject_sections.py [pyproject.toml]

Exit code: 0 always. Prints JSON to stdout.

"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# (tool_name, section_header_regex)
_SECTIONS: list[tuple[str, str]] = [
    ("ruff", r"^\[tool\.ruff\]"),
    ("mypy", r"^\[tool\.mypy\]"),
    ("pytest", r"^\[tool\.pytest\.ini_options\]"),
    ("vulture", r"^\[tool\.vulture\]"),
    ("ty", r"^\[tool\.ty\]"),
    ("uv_project", r"^\[project\]"),
]


def detect_pyproject_sections(pyproject_path: Path) -> dict[str, Any]:
    """Detect which tool sections exist in ``pyproject.toml``.

    Args:
        pyproject_path: Path to the ``pyproject.toml`` file.

    Returns:
        A dict mapping tool names to ``{"available": bool}`` objects.
        For ``uv``, ``available`` is ``True`` if either ``[project]`` exists
        or ``uv.lock`` is present in the same directory.

    """
    result: dict[str, Any] = {}
    content = ""
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")

    for tool, pattern in _SECTIONS:
        if tool == "uv_project":
            continue
        found = bool(re.search(pattern, content, re.MULTILINE))
        result[tool] = {"available": found}

    # uv: [project] section OR uv.lock file
    uv_available = bool(re.search(r"^\[project\]", content, re.MULTILINE))
    if not uv_available:
        uv_available = (pyproject_path.parent / "uv.lock").exists()
    result["uv"] = {"available": uv_available}

    return result


def main() -> int:
    """Entry point for the pyproject sections detector CLI."""
    parser = argparse.ArgumentParser(
        description="Detect which [tool.*] sections exist in pyproject.toml."
    )
    parser.add_argument(
        "pyproject",
        nargs="?",
        default="pyproject.toml",
        help="Path to pyproject.toml (default: pyproject.toml)",
    )
    args = parser.parse_args()

    result = detect_pyproject_sections(Path(args.pyproject))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
