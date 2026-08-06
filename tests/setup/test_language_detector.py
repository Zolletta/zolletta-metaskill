"""Tests for language_detector.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.language_detector import LanguageDetector


class TestDetectLanguage:
    """Tests for LanguageDetector.detect_language()."""

    def test_detect_language_python_pyproject_returns_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "python"

    def test_python_setup_py(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").write_text("# setup", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "python"

    def test_python_requirements_glob(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "python"

    def test_python_requirements_dev_glob(self, tmp_path: Path) -> None:
        (tmp_path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "python"

    def test_detect_language_typescript_returns_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "typescript"

    def test_detect_language_php_returns_php(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text("{}", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "php"

    def test_detect_language_go_returns_go(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "go"

    def test_detect_language_rust_returns_rust(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "rust"

    def test_detect_language_java_returns_java(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "java"

    def test_detect_language_ruby_gemfile_returns_ruby(self, tmp_path: Path) -> None:
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "ruby"

    def test_ruby_gemspec_glob(self, tmp_path: Path) -> None:
        (tmp_path / "myapp.gemspec").write_text("Gem::Specification.new\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "ruby"

    def test_c_cpp_cmake(self, tmp_path: Path) -> None:
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.0)\n", encoding="utf-8"
        )
        assert LanguageDetector.detect_language(tmp_path) == "c-cpp"

    def test_c_cpp_makefile_with_c(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("all:\n", encoding="utf-8")
        (tmp_path / "main.c").write_text("int LanguageDetector.main() {}\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "c-cpp"

    def test_c_cpp_makefile_without_c(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("all:\n", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) is None

    def test_detect_language_no_markers_returns_none(self, tmp_path: Path) -> None:
        assert LanguageDetector.detect_language(tmp_path) is None

    def test_priority_python_over_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert LanguageDetector.detect_language(tmp_path) == "python"


class TestMain:
    """Tests for LanguageDetector.main()."""

    def test_main_detects_python(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = LanguageDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "python" in out

    def test_main_no_markers(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = LanguageDetector.main()
        assert rc == 1

    def test_main_not_a_directory(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(missing)])
        rc = LanguageDetector.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "not a directory" in err

    def test_main_default_directory(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.chdir(tmp_path)
        rc = LanguageDetector.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "python" in out
