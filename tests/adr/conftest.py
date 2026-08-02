"""Shared fixtures and helpers for ADR distiller tests."""

from __future__ import annotations

from pathlib import Path

_ADR_TEMPLATE = """# ADR-{num}: {title}

## Status

{status}

## Decision

{decision}

## Consequences

Some consequences.
"""


def write_adr(
    path: Path,
    num: str,
    title: str,
    status: str = "Accepted",
    decision: str = "We decided to use PostgreSQL for the primary database.",
) -> float:
    """Write an ADR file and return its mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _ADR_TEMPLATE.format(num=num, title=title, status=status, decision=decision),
        encoding="utf-8",
    )
    return path.stat().st_mtime
