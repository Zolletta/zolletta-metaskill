"""Tests for detect_pyproject_sections.py."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.setup.detect_pyproject_sections import (
    detect_pyproject_sections,
)


class TestDetectPyprojectSections:
    """Tests for detect_pyproject_sections()."""

    def test_all_sections_present(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            "[tool.ruff]\n"
            "[tool.mypy]\n"
            "[tool.pytest.ini_options]\n"
            "[tool.vulture]\n"
            "[tool.ty]\n",
            encoding="utf-8",
        )
        result = detect_pyproject_sections(pyproject)
        assert result["ruff"]["available"] is True
        assert result["mypy"]["available"] is True
        assert result["pytest"]["available"] is True
        assert result["vulture"]["available"] is True
        assert result["ty"]["available"] is True
        assert result["uv"]["available"] is True

    def test_no_sections(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\n", encoding="utf-8")
        result = detect_pyproject_sections(pyproject)
        assert result["ruff"]["available"] is False
        assert result["mypy"]["available"] is False
        assert result["pytest"]["available"] is False
        assert result["vulture"]["available"] is False
        assert result["ty"]["available"] is False
        assert result["uv"]["available"] is False

    def test_missing_file(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "nonexistent.toml"
        result = detect_pyproject_sections(pyproject)
        assert result["ruff"]["available"] is False
        assert result["uv"]["available"] is False

    def test_uv_via_lock_file(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\n", encoding="utf-8")
        (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        result = detect_pyproject_sections(pyproject)
        assert result["uv"]["available"] is True

    def test_uv_via_project_section(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")
        result = detect_pyproject_sections(pyproject)
        assert result["uv"]["available"] is True

    def test_partial_sections(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\n[tool.ruff]\nline-length = 100\n", encoding="utf-8")
        result = detect_pyproject_sections(pyproject)
        assert result["ruff"]["available"] is True
        assert result["mypy"]["available"] is False
