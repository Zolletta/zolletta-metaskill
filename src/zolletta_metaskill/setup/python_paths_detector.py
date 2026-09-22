#!/usr/bin/env python3
"""Detect the Python source/test layout for ``settings.json`` ``python.paths``.

The source/test roots that PHP projects get for free via composer
``autoload`` mappings have no Python equivalent, so setup detects them
from ``pyproject.toml`` and the directory layout:

- ``source``: ``[tool.hatch.build.targets.wheel] packages`` →
  ``[tool.setuptools] package-dir`` / ``packages.find where`` →
  ``[tool.poetry] packages`` → ``src/`` if it contains a package →
  ``.`` if a package lives flat in the project root → ``["src"]``.
- ``tests``: ``[tool.pytest.ini_options] testpaths`` → ``tests/`` if it
  exists → ``["tests"]``.
- ``package``: basename of the first directory under a source root that
  contains ``__init__.py``, else ``null``.

Usage:
    python3 python_paths_detector.py [directory]

Exit code: 0 always. Prints JSON to stdout:
``{"source": ["src"], "tests": ["tests"], "package": "myproject"}``

"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

_IGNORED_FLAT_DIRS = {"tests", "docs", "doc", "examples", "scripts"}


class PythonPathsDetector:
    """Detect Python source roots, test roots, and the package name."""

    @staticmethod
    def _load_pyproject(project_root: Path) -> dict[str, Any]:
        """Return parsed ``pyproject.toml``, or an empty dict if unreadable."""
        path = project_root / "pyproject.toml"
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _str_list(value: Any) -> list[str]:
        """Return *value* as a list of strings, or ``[]``."""
        if not isinstance(value, list):
            return []
        return [v for v in value if isinstance(v, str)]

    @staticmethod
    def _first_package(root: Path) -> str | None:
        """Return the first dir under *root* containing ``__init__.py``."""
        if not root.is_dir():
            return None
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child.name
        return None

    @staticmethod
    def _detect_source(pyproject: dict[str, Any], project_root: Path) -> list[str]:
        """Return detected source roots for the project."""
        tool_raw = pyproject.get("tool")
        tool: dict[str, Any] = tool_raw if isinstance(tool_raw, dict) else {}

        # 1. Hatch: [tool.hatch.build.targets.wheel] packages = ["src/pkg"]
        wheel = (
            tool.get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
            if isinstance(tool.get("hatch"), dict)
            else {}
        )
        hatch_packages = PythonPathsDetector._str_list(wheel.get("packages"))
        if hatch_packages:
            roots = {str(Path(pkg).parent) for pkg in hatch_packages}
            return sorted(roots)

        # 2. setuptools: package-dir / packages.find where
        setuptools_raw = tool.get("setuptools")
        setuptools: dict[str, Any] = setuptools_raw if isinstance(setuptools_raw, dict) else {}
        package_dir = setuptools.get("package-dir")
        if isinstance(package_dir, dict):
            root = package_dir.get("")
            if isinstance(root, str) and root:
                return [root]
        packages = setuptools.get("packages")
        find = packages.get("find") if isinstance(packages, dict) else None
        if isinstance(find, dict):
            where = PythonPathsDetector._str_list(find.get("where"))
            if where:
                return where

        # 3. Poetry: [tool.poetry] packages = [{include = "pkg", from = "src"}]
        poetry_raw = tool.get("poetry")
        poetry: dict[str, Any] = poetry_raw if isinstance(poetry_raw, dict) else {}
        poetry_packages = poetry.get("packages")
        if isinstance(poetry_packages, list) and poetry_packages:
            poetry_roots = sorted(
                {
                    pkg["from"]
                    for pkg in poetry_packages
                    if isinstance(pkg, dict) and isinstance(pkg.get("from"), str)
                }
            )
            if poetry_roots:
                return poetry_roots
            return ["."]

        # 4. src/ contains a package
        if PythonPathsDetector._first_package(project_root / "src") is not None:
            return ["src"]

        # 5. Flat layout: a package dir lives directly in the project root
        if project_root.is_dir():
            for child in sorted(project_root.iterdir()):
                if (
                    child.is_dir()
                    and child.name not in _IGNORED_FLAT_DIRS
                    and not child.name.startswith(".")
                    and (child / "__init__.py").exists()
                ):
                    return ["."]

        return ["src"]

    @staticmethod
    def _detect_tests(pyproject: dict[str, Any], project_root: Path) -> list[str]:
        """Return detected test roots for the project."""
        tool_raw = pyproject.get("tool")
        tool: dict[str, Any] = tool_raw if isinstance(tool_raw, dict) else {}
        pytest_cfg = tool.get("pytest", {}).get("ini_options", {})
        if isinstance(pytest_cfg, dict):
            testpaths = PythonPathsDetector._str_list(pytest_cfg.get("testpaths"))
            if testpaths:
                return testpaths
        if (project_root / "tests").is_dir():
            return ["tests"]
        return ["tests"]

    @staticmethod
    def detect_python_paths(project_root: Path) -> dict[str, Any]:
        """Detect ``python.paths`` for settings.json.

        Args:
            project_root: Path to the project root directory.

        Returns:
            ``{"source": [...], "tests": [...], "package": str|None}``.

        """
        pyproject = PythonPathsDetector._load_pyproject(project_root)
        source = PythonPathsDetector._detect_source(pyproject, project_root)
        package: str | None = None
        for root in source:
            package = PythonPathsDetector._first_package(project_root / root)
            if package is not None:
                break
        return {
            "source": source,
            "tests": PythonPathsDetector._detect_tests(pyproject, project_root),
            "package": package,
        }

    @staticmethod
    def main() -> int:
        """Entry point for the Python paths detector CLI."""
        parser = argparse.ArgumentParser(
            description="Detect Python source/test roots and package name "
            "from pyproject.toml and the directory layout."
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default=".",
            help="Project root to check (default: current directory)",
        )
        args = parser.parse_args()

        result = PythonPathsDetector.detect_python_paths(Path(args.directory))
        print(json.dumps(result, indent=2))
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(PythonPathsDetector.main())
