"""Tests for detect_php_tools.py."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.setup.detect_php_tools import (
    detect_php_tools,
    detect_php_tools_from_composer,
    detect_php_tools_from_config_files,
)


class TestDetectPhpToolsFromComposer:
    """Tests for detect_php_tools_from_composer()."""

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
        result = detect_php_tools_from_composer(composer)
        assert result["phpunit"] is True
        assert result["phpstan"] is True
        assert result["psalm"] is True
        assert result["php_cs_fixer"] is True
        assert result["phpcs"] is True

    def test_no_packages(self, tmp_path: Path) -> None:
        composer = tmp_path / "composer.json"
        composer.write_text('{"require-dev": {}}', encoding="utf-8")
        result = detect_php_tools_from_composer(composer)
        assert all(v is False for v in result.values())

    def test_missing_file(self, tmp_path: Path) -> None:
        result = detect_php_tools_from_composer(tmp_path / "nonexistent.json")
        assert all(v is False for v in result.values())


class TestDetectPhpToolsFromConfigFiles:
    """Tests for detect_php_tools_from_config_files()."""

    def test_phpunit_xml(self, tmp_path: Path) -> None:
        (tmp_path / "phpunit.xml").write_text("<phpunit/>", encoding="utf-8")
        result = detect_php_tools_from_config_files(tmp_path)
        assert result["phpunit"] is True
        assert result["phpstan"] is False

    def test_phpunit_dist_xml(self, tmp_path: Path) -> None:
        (tmp_path / "phpunit.dist.xml").write_text("<phpunit/>", encoding="utf-8")
        result = detect_php_tools_from_config_files(tmp_path)
        assert result["phpunit"] is True

    def test_phpstan_neon(self, tmp_path: Path) -> None:
        (tmp_path / "phpstan.neon").write_text("level: 6\n", encoding="utf-8")
        result = detect_php_tools_from_config_files(tmp_path)
        assert result["phpstan"] is True

    def test_no_config_files(self, tmp_path: Path) -> None:
        result = detect_php_tools_from_config_files(tmp_path)
        assert all(v is False for v in result.values())


class TestDetectPhpTools:
    """Tests for detect_php_tools() — combined detection."""

    def test_composer_only(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require-dev": {"phpunit/phpunit": "^9"}}', encoding="utf-8"
        )
        result = detect_php_tools(tmp_path)
        assert result["phpunit"]["available"] is True
        assert result["phpstan"]["available"] is False

    def test_config_file_only(self, tmp_path: Path) -> None:
        (tmp_path / "phpstan.neon").write_text("level: 6\n", encoding="utf-8")
        result = detect_php_tools(tmp_path)
        assert result["phpstan"]["available"] is True
        assert result["phpunit"]["available"] is False

    def test_both_sources(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require-dev": {"phpunit/phpunit": "^9"}}', encoding="utf-8"
        )
        (tmp_path / "phpstan.neon").write_text("level: 6\n", encoding="utf-8")
        result = detect_php_tools(tmp_path)
        assert result["phpunit"]["available"] is True
        assert result["phpstan"]["available"] is True

    def test_neither_source(self, tmp_path: Path) -> None:
        result = detect_php_tools(tmp_path)
        assert all(not v["available"] for v in result.values())
