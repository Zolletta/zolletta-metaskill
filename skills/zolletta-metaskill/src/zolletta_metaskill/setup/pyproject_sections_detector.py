#!/usr/bin/env python3
"""Detect which ``[tool.*]`` sections exist in ``pyproject.toml``.

Checks for the configuration sections used by the setup skill to determine
Python tool availability: ``[tool.ruff]``, ``[tool.mypy]``,
``[tool.pytest.ini_options]``, ``[tool.vulture]``, ``[tool.ty]``,
``[tool.mutmut]``, and ``[project]`` (for uv).

``mutmut`` has no required configuration section, so it is additionally
detected as a quoted dependency specifier (e.g. ``"mutmut>=3"``) in
``[dependency-groups]``, ``[project.optional-dependencies]``, or
``[project.dependencies]``.

Usage:
    python3 pyproject_sections_detector.py [pyproject.toml]

Exit code: 0 always. Prints JSON to stdout.

"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


class PyprojectSectionsDetector:
    """Detect which ``[tool.*]`` sections exist in ``pyproject.toml``."""

    # (tool_name, section_header_regex)
    _SECTIONS: list[tuple[str, str]] = [
        ("ruff", r"^\[tool\.ruff\]"),
        ("mypy", r"^\[tool\.mypy\]"),
        ("pytest", r"^\[tool\.pytest\.ini_options\]"),
        ("vulture", r"^\[tool\.vulture\]"),
        ("ty", r"^\[tool\.ty\]"),
        ("mutmut", r"^\[tool\.mutmut\]"),
        ("uv_project", r"^\[project\]"),
    ]

    # (tool_name, quoted-dependency regex) — tools that are also detectable as
    # dependency specifiers ("mutmut>=3") even without a [tool.*] section.
    _DEPENDENCY_PACKAGES: list[tuple[str, str]] = [
        ("mutmut", r"[\"']mutmut(?:[^\w-]|$)"),
    ]

    @staticmethod
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
        # pragma: no mutate start — the literal is a fallback placeholder; no pattern can match it
        content = ""
        # pragma: no mutate end
        if pyproject_path.exists():
            content = pyproject_path.read_text(encoding="utf-8")  # pragma: no mutate

        for tool, pattern in PyprojectSectionsDetector._SECTIONS:
            if tool == "uv_project":
                # pragma: no mutate start — uv_project is the last entry, so break is equivalent
                # here
                continue
                # pragma: no mutate end
            found = bool(re.search(pattern, content, re.MULTILINE))
            result[tool] = {"available": found}

        # Fallback: quoted dependency specifiers (e.g. "mutmut>=3" in
        # dependency-groups / optional-dependencies / project.dependencies).
        for tool, pattern in PyprojectSectionsDetector._DEPENDENCY_PACKAGES:
            if not result[tool]["available"]:
                result[tool]["available"] = bool(re.search(pattern, content))

        # uv: [project] section OR uv.lock file
        uv_available = bool(re.search(r"^\[project\]", content, re.MULTILINE))
        if not uv_available:
            uv_available = (pyproject_path.parent / "uv.lock").exists()
        result["uv"] = {"available": uv_available}

        return result

    @staticmethod
    def main() -> int:  # pragma: no mutate — help text is not a tested contract
        """Entry point for the pyproject sections detector CLI."""
        parser = argparse.ArgumentParser(
            description="Detect which [tool.*] sections exist in pyproject.toml."
        )
        # pragma: no mutate start — carried from inline pragma (was ineffective inside a multi-line
        # statement)
        parser.add_argument(
            "pyproject",
            nargs="?",
            default="pyproject.toml",
            help="Path to pyproject.toml (default: pyproject.toml)",
        )
        # pragma: no mutate end
        args = parser.parse_args()

        result = PyprojectSectionsDetector.detect_pyproject_sections(Path(args.pyproject))
        print(json.dumps(result, indent=2))
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(PyprojectSectionsDetector.main())
