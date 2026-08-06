"""Tests for php_tools_detector.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.php_tools_detector import PHPToolsDetector


class TestDetectPhpToolsFromComposer:
    """Tests for PHPToolsDetector.detect_php_tools_from_composer()."""

    def test_all_packages_present(self, tmp_path: Path) -> None:
        composer = tmp_path / "composer.json"
        composer.write_text(
            '{"require-dev": {'
            '"phpunit/phpunit": "^9", '
            '"phpstan/phpstan": "^1", '
            '"vimeo/psalm": "^5", '
            '"friendsofphp/php-cs-fixer": "^3", '
            '"squizlabs/php_codesniffer": "^3"'
            "}}",
            encoding="utf-8",
        )
        result = PHPToolsDetector.detect_php_tools_from_composer(composer)
        assert result["phpunit"] is True
        assert result["phpstan"] is True
        assert result["psalm"] is True
        assert result["php_cs_fixer"] is True
        assert result["phpcs"] is True

    def test_detect_php_tools_from_composer_no_packages_is_valid(self, tmp_path: Path) -> None:
        composer = tmp_path / "composer.json"
        composer.write_text('{"require-dev": {}}', encoding="utf-8")
        result = PHPToolsDetector.detect_php_tools_from_composer(composer)
        assert all(v is False for v in result.values())

    def test_detect_php_tools_from_composer_missing_file_is_valid(self, tmp_path: Path) -> None:
        result = PHPToolsDetector.detect_php_tools_from_composer(tmp_path / "nonexistent.json")
        assert all(v is False for v in result.values())


class TestDetectPhpToolsFromConfigFiles:
    """Tests for PHPToolsDetector.detect_php_tools_from_config_files()."""

    def test_detect_php_tools_from_config_files_phpunit_xml_returns_false(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "phpunit.xml").write_text("<phpunit/>", encoding="utf-8")
        result = PHPToolsDetector.detect_php_tools_from_config_files(tmp_path)
        assert result["phpunit"] is True
        assert result["phpstan"] is False

    def test_phpunit_dist_xml(self, tmp_path: Path) -> None:
        (tmp_path / "phpunit.dist.xml").write_text("<phpunit/>", encoding="utf-8")
        result = PHPToolsDetector.detect_php_tools_from_config_files(tmp_path)
        assert result["phpunit"] is True

    def test_detect_php_tools_from_config_files_phpstan_neon_returns_true(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "phpstan.neon").write_text("level: 6\n", encoding="utf-8")
        result = PHPToolsDetector.detect_php_tools_from_config_files(tmp_path)
        assert result["phpstan"] is True

    def test_no_config_files(self, tmp_path: Path) -> None:
        result = PHPToolsDetector.detect_php_tools_from_config_files(tmp_path)
        assert all(v is False for v in result.values())


class TestDetectPhpTools:
    """Tests for PHPToolsDetector.detect_php_tools() — combined detection."""

    def test_detect_php_tools_composer_only_returns_false(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require-dev": {"phpunit/phpunit": "^9"}}', encoding="utf-8"
        )
        result = PHPToolsDetector.detect_php_tools(tmp_path)
        assert result["phpunit"]["available"] is True
        assert result["phpstan"]["available"] is False

    def test_config_file_only(self, tmp_path: Path) -> None:
        (tmp_path / "phpstan.neon").write_text("level: 6\n", encoding="utf-8")
        result = PHPToolsDetector.detect_php_tools(tmp_path)
        assert result["phpstan"]["available"] is True
        assert result["phpunit"]["available"] is False

    def test_detect_php_tools_both_sources_returns_true(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require-dev": {"phpunit/phpunit": "^9"}}', encoding="utf-8"
        )
        (tmp_path / "phpstan.neon").write_text("level: 6\n", encoding="utf-8")
        result = PHPToolsDetector.detect_php_tools(tmp_path)
        assert result["phpunit"]["available"] is True
        assert result["phpstan"]["available"] is True

    def test_detect_php_tools_neither_source_is_valid(self, tmp_path: Path) -> None:
        result = PHPToolsDetector.detect_php_tools(tmp_path)
        assert all(not v["available"] for v in result.values())


class TestMain:
    """Tests for PHPToolsDetector.main()."""

    def test_main_prints_json(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require-dev": {"phpunit/phpunit": "^9"}}', encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = PHPToolsDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["phpunit"]["available"] is True

    def test_main_default_directory(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.chdir(tmp_path)
        rc = PHPToolsDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert all(not v["available"] for v in data.values())
