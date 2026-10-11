"""Resolved ``documentation.*`` configuration for the documentor package."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


@dataclass(frozen=True)
class DocumentorSettings:
    """The ``documentation.*`` configuration, resolved once.

    Built from *settings* by :meth:`from_settings` and then passed around
    unchanged, so each ``documentation.*`` key is read in exactly one place
    instead of being re-resolved — and re-derived — at each of the four entry
    points that used to call :meth:`resolve_cache_dir` independently.

    The alternative was passing the raw ``dict`` down. That is the pattern that
    produced 6-parameter signatures in the first place: a settings-derived value
    becomes indistinguishable from any other argument at the call site.

    Attributes:
        cache_dir: Directory for tool output; see :meth:`resolve_cache_dir`.
        documentation_rel_dir: Repository-relative docs root
            (``documentation.dir``).
        adrs_dir: Repository-relative ADR directory, or ``None``.
        doc_patterns: Glob patterns for doc discovery, or ``None`` for defaults.
        include_referential: Whether referential drift checks run.
        min_severity: Lowest severity to report.
        check_external: Whether external URLs are validated.
        quadrants: Effective Diátaxis quadrant mapping.

    """

    DEFAULT_CACHE_DIR = ".zolletta-metaskill/cache"

    #: Run folders are named ``YYYY-MM-DD-HH-MM`` by the review orchestrator.
    #: Anything else under ``runs_dir`` (notably a flat ``cache/`` directory) is
    #: not a run and must never be mistaken for the most recent one.
    RUN_FOLDER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")

    cache_dir: Path
    documentation_rel_dir: Path
    adrs_dir: Path | None
    doc_patterns: tuple[str, ...] | None
    include_referential: bool
    min_severity: str
    check_external: bool
    quadrants: dict[str, dict[str, Any]]

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> DocumentorSettings:
        """Resolve every ``documentation.*`` key into one immutable struct.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            The resolved settings, safe to share across a whole run.

        """
        # Imported here rather than at module scope: the quadrant resolver lives
        # in the sibling ``quality`` package, and a module-level import would
        # give ``utils`` a dependency on ``quality`` while ``quality`` already
        # depends on ``utils``.
        from zolletta_metaskill.documentor.quality.quality_scorer import QualityScorer

        raw_patterns = ProjectConfig.setting(settings, "documentation.doc_patterns", None)
        doc_patterns = (
            tuple(p for p in raw_patterns if isinstance(p, str))
            if isinstance(raw_patterns, list)
            else None
        )
        return cls(
            cache_dir=cls.resolve_cache_dir(settings),
            documentation_rel_dir=ProjectConfig.docs_dir(settings),
            adrs_dir=ProjectConfig.adrs_dir(settings),
            doc_patterns=doc_patterns,
            include_referential=bool(
                ProjectConfig.setting(settings, "documentation.include_referential", False)
            ),
            min_severity=str(ProjectConfig.setting(settings, "documentation.min_severity", "low")),
            check_external=bool(
                ProjectConfig.setting(settings, "documentation.check_external", False)
            ),
            quadrants=QualityScorer._resolve_diataxis_quadrants(settings),
        )

    @staticmethod
    def resolve_cache_dir(settings: dict[str, Any]) -> Path:
        """Return the cache directory for documentor tool outputs.

        Resolution order:

        1. ``documentation.cache_dir`` from *settings*, when set to a non-empty
           string. This is an explicit override and always wins.
        2. The ``cache/`` directory of the most recent review run folder under
           ``runs_dir``. Run folders are named ``YYYY-MM-DD-HH-MM``, so the
           greatest name is the most recent one. Keeping artifacts inside the run
           folder means each review keeps its own history instead of overwriting
           a single shared directory.
        3. ``<runs_dir>/cache`` when no run folder exists yet, i.e. before the
           first review has created one.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            Absolute path to the cache directory. The directory is not created
            here; callers write into it.

        """
        configured = ProjectConfig.setting(settings, "documentation.cache_dir", None)
        if isinstance(configured, str) and configured:
            return Path(os.path.abspath(configured))
        return DocumentorSettings._default_cache_dir(settings)

    @staticmethod
    def _default_cache_dir(settings: dict[str, Any]) -> Path:
        """Return the per-run cache directory, or the ``runs_dir`` fallback."""
        runs_dir = ProjectConfig.runs_dir(settings)
        latest_run = DocumentorSettings._latest_run_dir(runs_dir)
        if latest_run is not None:
            return latest_run / "cache"
        return Path(os.path.abspath(runs_dir / "cache"))

    @staticmethod
    def _latest_run_dir(runs_dir: Path) -> Path | None:
        """Return the most recent timestamped run folder under *runs_dir*.

        Only directories whose name matches :data:`RUN_FOLDER_PATTERN` are
        considered, so a sibling ``cache/`` directory is never selected — it
        would otherwise win the lexicographic comparison, since ``"cache"``
        sorts after any ``"YYYY-..."`` name.

        Returns:
            The greatest-named matching run folder, or ``None`` when *runs_dir*
            is absent or holds no run folders.

        """
        if not runs_dir.is_dir():
            return None
        candidates = [
            child
            for child in runs_dir.iterdir()
            if child.is_dir() and DocumentorSettings.RUN_FOLDER_PATTERN.match(child.name)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.name)
