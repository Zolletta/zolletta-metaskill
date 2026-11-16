"""DocumentGrouper — assign each document the presentation group it belongs to."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import PurePosixPath


class DocumentGrouper:
    """Group documents by the first-level child of ``documentation.dir``.

    The grouping reads only the directory layout, never the path's meaning:
    ``docs/current/php/x.md`` belongs to ``current`` whatever ``current``
    means in that project. Files directly in the docs directory and the root
    documents (``README.md``, ``CONTRIBUTING.md``, ``AGENTS.md``) form
    :attr:`ROOT`. A group exists only when it holds a scored document, so an
    empty child directory never shows up.
    """

    ROOT = "(root)"

    @staticmethod
    def group_of(path: str, docs_dir: str) -> str:
        """Return the group of *path*.

        Args:
            path: Repository-relative documentation path.
            docs_dir: Repository-relative ``documentation.dir``.

        Returns:
            The first-level child of *docs_dir* holding *path*, or
            :attr:`ROOT`.

        """
        docs = PurePosixPath(os.path.normpath(docs_dir)).parts
        parts = PurePosixPath(path).parts
        if parts[: len(docs)] != docs:
            return DocumentGrouper.ROOT
        rest = parts[len(docs) :]
        return rest[0] if len(rest) > 1 else DocumentGrouper.ROOT

    @staticmethod
    def order(groups: Iterable[str]) -> tuple[str, ...]:
        """Return *groups* deduplicated, alphabetical, with :attr:`ROOT` last.

        Args:
            groups: Group names, possibly repeated.

        Returns:
            The report order of the groups.

        """
        return tuple(sorted(set(groups), key=lambda name: (name == DocumentGrouper.ROOT, name)))
