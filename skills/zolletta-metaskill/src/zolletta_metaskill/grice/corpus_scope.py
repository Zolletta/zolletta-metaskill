"""CorpusScope — leave the ADRs out of the Grice corpus before it is scored."""

from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class CorpusScope:
    """Split the documentor's inventory into the Grice corpus and the ADRs.

    An ADR is a decision record: hypothetical wording, a vocabulary of its own
    and few links are what the genre demands, so ranking ADRs against guides
    only produces expected false positives — and, worse, shifts every other
    document's percentile. They are therefore removed *before*
    normalisation, from two sources: the configured ``documentation.adrs``
    directory, and every directory named ``adr`` or ``adrs`` at any depth,
    because real corpora keep decision records in several places.
    """

    ADR_DIRECTORY_NAMES = frozenset({"adr", "adrs"})

    @staticmethod
    def split(
        paths: tuple[str, ...], settings: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Partition *paths* into the scored corpus and the excluded ADRs.

        Args:
            paths: Repository-relative documentation paths.
            settings: The project's ``settings.json`` contents.

        Returns:
            The paths to score and the ADR paths left out, each in input order.

        """
        configured = CorpusScope._configured_dir(settings)
        kept: list[str] = []
        excluded: list[str] = []
        for path in paths:
            (excluded if CorpusScope.is_adr(path, configured) else kept).append(path)
        return tuple(kept), tuple(excluded)

    @staticmethod
    def is_adr(path: str, configured: str | None) -> bool:
        """Return whether *path* lies in an ADR directory.

        Args:
            path: Repository-relative documentation path.
            configured: The configured ADR directory, repository-relative, or
                ``None`` when there is none to honour.

        Returns:
            ``True`` when a parent directory is named ``adr``/``adrs`` (any
            case) or the path is inside *configured*.

        """
        parts = PurePosixPath(path).parts
        if any(part.lower() in CorpusScope.ADR_DIRECTORY_NAMES for part in parts[:-1]):
            return True
        if configured is None:
            return False
        return path.startswith(configured + "/")

    @staticmethod
    def _configured_dir(settings: dict[str, Any]) -> str | None:
        """Return ``documentation.adrs`` resolved against the docs directory.

        An empty or dot value means "ADRs are scattered through the docs
        root"; excluding that directory would exclude the whole corpus, so it
        is ignored and only the ``adr``/``adrs`` directory names apply.

        Args:
            settings: The project's ``settings.json`` contents.

        Returns:
            The repository-relative POSIX directory, or ``None``.

        """
        adrs = ProjectConfig.setting(settings, "documentation.adrs", None)
        if not isinstance(adrs, str) or not adrs.strip("./"):
            return None
        joined = os.path.normpath(os.path.join(str(ProjectConfig.docs_dir(settings)), adrs))
        return PurePosixPath(joined).as_posix()
