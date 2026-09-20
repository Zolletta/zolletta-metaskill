"""Tests for python_paths_detector.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.setup.python_paths_detector import PythonPathsDetector


def _write_pyproject(root: Path, content: str) -> None:
    (root / "pyproject.toml").write_text(content)


def _make_package(root: Path, name: str) -> None:
    pkg = root / name
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")


class TestLoadPyproject:
    def test_missing_returns_empty(self, tmp_path: Path) -> None:
        assert PythonPathsDetector._load_pyproject(tmp_path) == {}

    def test_invalid_toml_returns_empty(self, tmp_path: Path) -> None:
        _write_pyproject(tmp_path, "[invalid toml ===")
        assert PythonPathsDetector._load_pyproject(tmp_path) == {}

    def test_non_dict_returns_empty(self, tmp_path: Path) -> None:
        assert PythonPathsDetector._load_pyproject(tmp_path) == {}

    def test_valid_pyproject(self, tmp_path: Path) -> None:
        _write_pyproject(tmp_path, '[project]\nname = "x"\n')
        data = PythonPathsDetector._load_pyproject(tmp_path)
        assert data["project"]["name"] == "x"


class TestDetectSource:
    def test_hatch_packages(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.hatch.build.targets.wheel]\npackages = ["src/mypkg"]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]

    def test_hatch_multiple_packages(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.hatch.build.targets.wheel]\npackages = ["src/a", "lib/b"]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["lib", "src"]

    def test_hatch_flat_package(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.hatch.build.targets.wheel]\npackages = ["mypkg"]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["."]

    def test_hatch_empty_packages_falls_through(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.hatch.build.targets.wheel]\npackages = []\n',
        )
        _make_package(tmp_path / "src", "mypkg")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]

    def test_setuptools_package_dir(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.setuptools.package-dir]\n"" = "lib"\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["lib"]

    def test_setuptools_find_where(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.setuptools.packages.find]\nwhere = ["src", "ext"]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src", "ext"]

    def test_setuptools_packages_list_ignored(self, tmp_path: Path) -> None:
        """Packages = ["a"] (list form, no find) falls through to layout."""
        _write_pyproject(tmp_path, '[tool.setuptools]\npackages = ["mypkg"]\n')
        _make_package(tmp_path / "src", "realpkg")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]

    def test_poetry_packages_from(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.poetry]\npackages = [{include = "mypkg", from = "lib"}]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["lib"]

    def test_poetry_packages_no_from(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.poetry]\npackages = [{include = "mypkg"}]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["."]

    def test_src_layout_detected(self, tmp_path: Path) -> None:
        _make_package(tmp_path / "src", "mypkg")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]
        assert result["package"] == "mypkg"

    def test_flat_layout_detected(self, tmp_path: Path) -> None:
        _make_package(tmp_path, "mypkg")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["."]
        assert result["package"] == "mypkg"

    def test_ignored_flat_dirs_skipped(self, tmp_path: Path) -> None:
        _make_package(tmp_path, "tests")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]

    def test_hidden_dirs_skipped(self, tmp_path: Path) -> None:
        _make_package(tmp_path, ".hidden")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]

    def test_no_layout_defaults_src(self, tmp_path: Path) -> None:
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["src"]
        assert result["package"] is None


class TestDetectTests:
    def test_pytest_testpaths(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.pytest.ini_options]\ntestpaths = ["tests", "spec"]\n',
        )
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["tests"] == ["tests", "spec"]

    def test_tests_dir_exists(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["tests"] == ["tests"]

    def test_no_tests_dir_defaults(self, tmp_path: Path) -> None:
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["tests"] == ["tests"]


class TestPackage:
    def test_package_from_first_source_root(self, tmp_path: Path) -> None:
        _write_pyproject(
            tmp_path,
            '[tool.setuptools.packages.find]\nwhere = ["lib", "src"]\n',
        )
        _make_package(tmp_path / "src", "mypkg")
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["source"] == ["lib", "src"]
        assert result["package"] == "mypkg"

    def test_package_none_when_no_package(self, tmp_path: Path) -> None:
        result = PythonPathsDetector.detect_python_paths(tmp_path)
        assert result["package"] is None


class TestMain:
    def test_main_prints_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_package(tmp_path / "src", "mypkg")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        rc = PythonPathsDetector.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["source"] == ["src"]
        assert out["package"] == "mypkg"

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = PythonPathsDetector.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["source"] == ["src"]
