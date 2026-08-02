"""Tests for detect_language.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.detect_language import detect_language, main


class TestDetectLanguage:
    """Tests for detect_language()."""

    def test_python_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        assert detect_language(tmp_path) == "python"

    def test_python_setup_py(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").write_text("# setup", encoding="utf-8")
        assert detect_language(tmp_path) == "python"

    def test_python_requirements_glob(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        assert detect_language(tmp_path) == "python"

    def test_python_requirements_dev_glob(self, tmp_path: Path) -> None:
        (tmp_path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
        assert detect_language(tmp_path) == "python"

    def test_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert detect_language(tmp_path) == "typescript"

    def test_php(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text("{}", encoding="utf-8")
        assert detect_language(tmp_path) == "php"

    def test_go(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
        assert detect_language(tmp_path) == "go"

    def test_rust(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        assert detect_language(tmp_path) == "rust"

    def test_java(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        assert detect_language(tmp_path) == "java"

    def test_ruby_gemfile(self, tmp_path: Path) -> None:
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
        assert detect_language(tmp_path) == "ruby"

    def test_ruby_gemspec_glob(self, tmp_path: Path) -> None:
        (tmp_path / "myapp.gemspec").write_text("Gem::Specification.new\n", encoding="utf-8")
        assert detect_language(tmp_path) == "ruby"

    def test_c_cpp_cmake(self, tmp_path: Path) -> None:
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.0)\n", encoding="utf-8"
        )
        assert detect_language(tmp_path) == "c-cpp"

    def test_c_cpp_makefile_with_c(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("all:\n", encoding="utf-8")
        (tmp_path / "main.c").write_text("int main() {}\n", encoding="utf-8")
        assert detect_language(tmp_path) == "c-cpp"

    def test_c_cpp_makefile_without_c(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("all:\n", encoding="utf-8")
        assert detect_language(tmp_path) is None

    def test_no_markers(self, tmp_path: Path) -> None:
        assert detect_language(tmp_path) is None

    def test_priority_python_over_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert detect_language(tmp_path) == "python"


class TestMain:
    """Tests for main()."""

    def test_main_detects_python(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "python" in out

    def test_main_no_markers(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = main()
        assert rc == 1

    def test_main_not_a_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(missing)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "not a directory" in err

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.chdir(tmp_path)
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "python" in out
