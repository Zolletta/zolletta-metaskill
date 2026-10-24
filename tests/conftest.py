"""Shared pytest fixtures for zolletta-metaskill tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ``--update-fixtures`` for regenerating text-output contracts."""
    parser.addoption(
        "--update-fixtures",
        action="store_true",
        default=False,
        help="Rewrite tests/fixtures/**/ text-output contracts instead of asserting.",
    )


@pytest.fixture
def text_contract(request: pytest.FixtureRequest) -> Callable[[str, str], None]:
    """Return a checker that compares captured text output to a committed fixture.

    The path is relative to ``tests/fixtures/``. With ``--update-fixtures`` the
    file is rewritten instead of asserted, so a legitimate output change is a
    regeneration plus a diff review rather than a hand-edit. A missing fixture
    fails the test, naming the flag that creates it.

    """
    update = request.config.getoption("--update-fixtures")
    fixtures_root = Path(__file__).parent / "fixtures"

    def check(rel_path: str, actual: str) -> None:
        path = fixtures_root / rel_path
        if update:  # pragma: no cover — runs only under --update-fixtures
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
        if not path.exists():  # pragma: no cover — failure path
            raise AssertionError(f"missing fixture {path}; run pytest --update-fixtures")
        expected = path.read_text(encoding="utf-8")
        assert actual == expected, (
            f"{rel_path} drifted from its committed contract; if the change is "
            "intended, run pytest --update-fixtures and review the diff"
        )

    return check


@pytest.fixture
def tmp_src(tmp_path: Path) -> Path:  # pragma: no cover
    """Create a minimal src/ package structure under tmp_path."""
    src = tmp_path / "src"
    pkg = src / "myproject"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    return src


@pytest.fixture
def tmp_tests(tmp_path: Path) -> Path:  # pragma: no cover
    """Create a minimal tests/ package structure under tmp_path."""
    tests = tmp_path / "tests"
    pkg = tests / "myproject"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    return tests
