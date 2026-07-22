"""Shared pytest fixtures for zolletta-metaskill tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_src(tmp_path: Path) -> Path:
    """Create a minimal src/ package structure under tmp_path."""
    src = tmp_path / "src"
    pkg = src / "myproject"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    return src


@pytest.fixture
def tmp_tests(tmp_path: Path) -> Path:
    """Create a minimal tests/ package structure under tmp_path."""
    tests = tmp_path / "tests"
    pkg = tests / "myproject"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    return tests
