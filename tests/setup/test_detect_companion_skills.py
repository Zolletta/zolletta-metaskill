"""Tests for detect_companion_skills.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.detect_companion_skills import (
    detect_companion_skills,
    main,
)


class TestDetectCompanionSkills:
    """Tests for detect_companion_skills()."""

    def test_neither_installed(self, tmp_path: Path) -> None:
        php_pro = tmp_path / "php-pro" / "SKILL.md"
        python_dev = tmp_path / "python-development" / "SKILL.md"
        result = detect_companion_skills(
            php_pro_path=php_pro, python_dev_path=python_dev
        )
        assert result["php_pro"]["available"] is False
        assert result["python_development"]["available"] is False

    def test_php_pro_installed(self, tmp_path: Path) -> None:
        php_pro = tmp_path / "php-pro" / "SKILL.md"
        php_pro.parent.mkdir(parents=True)
        php_pro.write_text("---\nname: php-pro\n", encoding="utf-8")
        python_dev = tmp_path / "python-development" / "SKILL.md"
        result = detect_companion_skills(
            php_pro_path=php_pro, python_dev_path=python_dev
        )
        assert result["php_pro"]["available"] is True
        assert result["python_development"]["available"] is False

    def test_python_development_installed(self, tmp_path: Path) -> None:
        php_pro = tmp_path / "php-pro" / "SKILL.md"
        python_dev = tmp_path / "python-development" / "SKILL.md"
        python_dev.parent.mkdir(parents=True)
        python_dev.write_text("---\nname: python-development\n", encoding="utf-8")
        result = detect_companion_skills(
            php_pro_path=php_pro, python_dev_path=python_dev
        )
        assert result["php_pro"]["available"] is False
        assert result["python_development"]["available"] is True

    def test_both_installed(self, tmp_path: Path) -> None:
        php_pro = tmp_path / "php-pro" / "SKILL.md"
        python_dev = tmp_path / "python-development" / "SKILL.md"
        for p in (php_pro, python_dev):
            p.parent.mkdir(parents=True)
            p.write_text("---\n", encoding="utf-8")
        result = detect_companion_skills(
            php_pro_path=php_pro, python_dev_path=python_dev
        )
        assert result["php_pro"]["available"] is True
        assert result["python_development"]["available"] is True


class TestMain:
    """Tests for main()."""

    def test_main_prints_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert "php_pro" in data
        assert "python_development" in data
