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
        rename_window_days: How far back rename drift is looked for.
        min_severity: Lowest severity to report.
        check_external: Whether external URLs are validated.
        quadrants: Effective Diátaxis quadrant mapping.
        staleness_weights: Normalized weights for the five staleness dimensions.
        required_sections: README sections a document must carry.

    """

    DEFAULT_CACHE_DIR = ".zolletta-metaskill/cache"

    #: Run folders are named ``YYYY-MM-DD-HH-MM`` by the review orchestrator.
    #: Anything else under ``runs_dir`` (notably a flat ``cache/`` directory) is
    #: not a run and must never be mistaken for the most recent one.
    RUN_FOLDER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")

    #: Weights applied to the five staleness dimensions when
    #: ``documentation.staleness_weights`` is unset. They live here rather than on
    #: ``QualityScorer`` because they are the default for a settings key, and this
    #: is the only place that reads settings keys.
    DEFAULT_WEIGHTS = {
        "last_updated": 0.20,
        "code_doc_alignment": 0.30,
        "link_health": 0.15,
        "completeness": 0.20,
        "accuracy": 0.15,
    }

    #: Sections a README must carry when ``documentation.readme_sections`` is
    #: unset and no translations file supplies its own list.
    DEFAULT_README_SECTIONS = (
        "installation",
        "usage",
        "api",
        "contributing",
        "license",
    )

    cache_dir: Path
    documentation_rel_dir: Path
    adrs_dir: Path | None
    doc_patterns: tuple[str, ...] | None
    include_referential: bool
    rename_window_days: int
    min_severity: str
    check_external: bool
    quadrants: dict[str, dict[str, Any]]
    staleness_weights: dict[str, float]
    required_sections: tuple[str, ...]

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
        # One read, two consumers: the quadrants and the required sections are both
        # derived from this file when it is configured.
        translations_path = cls._translations_path(settings)
        return cls(
            cache_dir=cls.resolve_cache_dir(settings),
            documentation_rel_dir=ProjectConfig.docs_dir(settings),
            adrs_dir=ProjectConfig.adrs_dir(settings),
            doc_patterns=doc_patterns,
            include_referential=bool(
                ProjectConfig.setting(settings, "documentation.include_referential", False)
            ),
            rename_window_days=cls._resolve_rename_window_days(settings),
            min_severity=str(ProjectConfig.setting(settings, "documentation.min_severity", "low")),
            check_external=bool(
                ProjectConfig.setting(settings, "documentation.check_external", False)
            ),
            quadrants=QualityScorer._resolve_diataxis_quadrants(translations_path),
            staleness_weights=cls._resolve_staleness_weights(settings),
            required_sections=cls._resolve_required_sections(settings, translations_path),
        )

    @staticmethod
    def _translations_path(settings: dict[str, Any]) -> str | None:
        """Return the configured Diátaxis translations file, or ``None``.

        Read once by :meth:`from_settings` and passed to both resolvers that
        depend on it, so ``documentation.diataxis_translations`` has one reader
        rather than one per consumer.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            The configured path, or ``None`` when unset or not a non-empty string.

        """
        configured = ProjectConfig.setting(settings, "documentation.diataxis_translations", None)
        if isinstance(configured, str) and configured:
            return configured
        return None

    @staticmethod
    def _resolve_staleness_weights(settings: dict[str, Any]) -> dict[str, float]:
        """Build and normalize the staleness dimension weights from *settings*.

        Only numeric overrides are honoured, and the result is renormalized to
        sum to 1 so a partial override cannot silently rescale the aggregate
        score. A zero total is returned unnormalized rather than raising: the
        weights are scoring policy, and a scoring run is not the place to abort.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            A fresh weight mapping — never the class attribute itself.

        """
        weights = dict(DocumentorSettings.DEFAULT_WEIGHTS)
        raw_weights = ProjectConfig.setting(settings, "documentation.staleness_weights", None)
        if isinstance(raw_weights, dict):
            for key in weights:
                value = raw_weights.get(key)
                if isinstance(value, (int, float)):
                    weights[key] = float(value)
        total_weight = sum(weights.values())
        if total_weight > 0:
            return {k: v / total_weight for k, v in weights.items()}
        return weights

    @classmethod
    def _resolve_required_sections(
        cls, settings: dict[str, Any], translations_path: str | None = None
    ) -> tuple[str, ...]:
        """Resolve the README sections a document must carry.

        Resolution order: an explicit ``documentation.readme_sections`` list,
        then the ``readme_sections`` of the configured translations file, then
        :data:`DEFAULT_README_SECTIONS`.

        Args:
            settings: Parsed ``settings.json`` contents.
            translations_path: Already-resolved translations file from
                :meth:`_translations_path`. Left optional so the method can be
                called standalone; ``from_settings`` always supplies it.

        Returns:
            Section names, stripped of surrounding whitespace.

        """
        raw_sections = ProjectConfig.setting(settings, "documentation.readme_sections", None)
        if isinstance(raw_sections, list):
            return tuple(s.strip() for s in raw_sections if isinstance(s, str))

        if translations_path is None:
            translations_path = cls._translations_path(settings)
        if translations_path:
            # Lazy for the same reason as in ``from_settings``: ``quality``
            # already imports ``utils``, so a module-scope import here would be
            # circular.
            from zolletta_metaskill.documentor.quality.doc_completeness_scorer import (
                DocCompletenessScorer,
            )

            translations = DocCompletenessScorer.load_diataxis_translations(translations_path)
            translated_readme = translations.get("readme_sections")
            if translated_readme:
                return tuple(s.strip() for s in translated_readme)
        return cls.DEFAULT_README_SECTIONS

    @staticmethod
    def _resolve_rename_window_days(settings: dict[str, Any]) -> int:
        """Return the rename-lookback window in days (default 90).

        Was a hardcoded ``"90 days ago"`` string at the git call site. How far
        back a rename still matters is policy, so it belongs in settings with
        everything else rather than baked into the caller.
        """
        value = ProjectConfig.setting(settings, "documentation.rename_window_days", 90)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return 90
        return value

    @staticmethod
    def resolve_cache_dir(settings: dict[str, Any]) -> Path:
        """Return the cache directory for documentor tool outputs.

        Resolution:

        1. The ``cache/`` directory of the most recent review run folder under
           ``runs_dir``. Run folders are named ``YYYY-MM-DD-HH-MM``, so the
           greatest name is the most recent one. Keeping artifacts inside the run
           folder means each review keeps its own history instead of overwriting
           a single shared directory.
        2. ``<runs_dir>/cache`` when no run folder exists yet, i.e. before the
           first review has created one.

        There is deliberately no override. A ``documentation.cache_dir`` key was
        honoured here for a while, but the settings schema closes
        ``documentation`` with ``additionalProperties: false`` and never declared
        it — so the branch was unreachable through any validated configuration. A
        feature nobody can configure is not a feature; it is a second description
        of the default that reads like an override.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            Absolute path to the cache directory. The directory is not created
            here; callers write into it.

        """
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
