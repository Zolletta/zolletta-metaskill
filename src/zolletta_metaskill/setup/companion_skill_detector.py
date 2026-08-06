#!/usr/bin/env python3
"""Detect companion implementation skills.

Checks whether the companion implementation skills (``php-pro`` and
``python-development``) are installed under ``~/.agents/skills/``.

Usage:
    python3 companion_skill_detector.py

Exit code: 0 always. Prints JSON to stdout.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class CompanionSkillDetector:
    """Detect companion implementation skills."""

    _PHP_PRO_PATH = Path.home() / ".agents" / "skills" / "php-pro" / "SKILL.md"
    _PYTHON_DEV_PATH = Path.home() / ".agents" / "skills" / "python-development" / "SKILL.md"

    @staticmethod
    def detect_companion_skills(
        php_pro_path: Path | None = None,
        python_dev_path: Path | None = None,
    ) -> dict[str, Any]:
        """Detect whether companion implementation skills are installed.

        Args:
            php_pro_path: Override path for the php-pro skill. Defaults to
                ``~/.agents/skills/php-pro/SKILL.md``.
            python_dev_path: Override path for the python-development skill.
                Defaults to ``~/.agents/skills/python-development/SKILL.md``.

        Returns:
            A dict with ``php_pro`` and ``python_development`` keys, each
            mapping to ``{"available": bool}``.

        """
        if php_pro_path is None:
            php_pro_path = CompanionSkillDetector._PHP_PRO_PATH
        if python_dev_path is None:
            python_dev_path = CompanionSkillDetector._PYTHON_DEV_PATH

        return {
            "php_pro": {"available": php_pro_path.exists()},
            "python_development": {"available": python_dev_path.exists()},
        }

    @staticmethod
    def main() -> int:
        """Entry point for the companion skills detector CLI."""
        parser = argparse.ArgumentParser(description="Detect companion implementation skills.")
        parser.parse_args()

        result = CompanionSkillDetector.detect_companion_skills()
        print(json.dumps(result, indent=2))
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(CompanionSkillDetector.main())
