#!/usr/bin/env python3
"""Detect PHP tool availability from ``composer.json`` and config files.

Checks ``composer.json`` ``require-dev`` for tool packages, then checks
for tool config files in the project root. A tool is marked available if
either source finds it.

Usage:
    python3 detect_php_tools.py [directory]

Exit code: 0 always. Prints JSON to stdout.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# (tool_name, composer_package, config_files)
_TOOLS: list[tuple[str, str, list[str]]] = [
    ("phpunit", "phpunit/phpunit", ["phpunit.xml", "phpunit.dist.xml"]),
    ("phpstan", "phpstan/phpstan", ["phpstan.neon", "phpstan.dist.neon"]),
    ("psalm", "vimeo/psalm", ["psalm.xml", "psalm.dist.xml"]),
    ("php_cs_fixer", "friendsofphp/php-cs-fixer",
     [".php-cs-fixer.php", ".php-cs-fixer.dist.php"]),
    ("phpcs", "squizlabs/php_codesniffer",
     [".phpcs.xml", "phpcs.xml.dist", ".phpcs.xml.dist"]),
]


def detect_php_tools_from_composer(composer_path: Path) -> dict[str, bool]:
    """Check which PHP tools are listed in ``composer.json`` ``require-dev``.

    Args:
        composer_path: Path to ``composer.json``.

    Returns:
        A dict mapping tool names to booleans.

    """
    result: dict[str, bool] = {}
    if not composer_path.exists():
        return {tool: False for tool, _, _ in _TOOLS}

    content = composer_path.read_text(encoding="utf-8")
    for tool, package, _ in _TOOLS:
        result[tool] = f'"{package}"' in content
    return result


def detect_php_tools_from_config_files(project_root: Path) -> dict[str, bool]:
    """Check which PHP tools have config files in the project root.

    Args:
        project_root: Path to the project root directory.

    Returns:
        A dict mapping tool names to booleans.

    """
    result: dict[str, bool] = {}
    for tool, _, config_files in _TOOLS:
        result[tool] = any((project_root / f).exists() for f in config_files)
    return result


def detect_php_tools(project_root: Path) -> dict[str, Any]:
    """Detect PHP tool availability from both composer.json and config files.

    A tool is marked available if found in either source.

    Args:
        project_root: Path to the project root directory.

    Returns:
        A dict mapping tool names to ``{"available": bool}`` objects.

    """
    composer = detect_php_tools_from_composer(project_root / "composer.json")
    config = detect_php_tools_from_config_files(project_root)
    return {
        tool: {"available": composer.get(tool, False) or config.get(tool, False)}
        for tool, _, _ in _TOOLS
    }


def main() -> int:
    """Entry point for the PHP tools detector CLI."""
    parser = argparse.ArgumentParser(
        description="Detect PHP tool availability from composer.json and config files."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Project root to check (default: current directory)",
    )
    args = parser.parse_args()

    result = detect_php_tools(Path(args.directory))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
