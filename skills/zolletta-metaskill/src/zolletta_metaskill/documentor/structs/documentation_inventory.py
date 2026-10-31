"""DocumentationInventory — the files that are documentation, split by origin."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentationInventory:
    """Every markdown file that is documentation, split by where it was found.

    Two groups rather than one list, because consumers treat them differently:
    a root document is named explicitly by the finder and belongs to no
    Diátaxis quadrant, while everything under ``documentation.dir`` is scoped
    by that directory and may sit in one. A single flat list would have to be
    re-split by every consumer to recover which is which.

    Attributes:
        documentation: Repo-relative paths under ``documentation.dir``, sorted.
        root_documents: Root document kind to repo-relative path. Only the
            kinds actually present in the repository are keys.
        skipped_reason: Why discovery produced nothing, or ``None``. Set only
            when ``documentation.dir`` is configured but is not a directory,
            which is a misconfiguration rather than an empty result.

    """

    documentation: tuple[str, ...] = ()
    root_documents: Mapping[str, str] = field(default_factory=dict)
    skipped_reason: str | None = None

    @property
    def all_paths(self) -> tuple[str, ...]:
        """Return both groups as one sorted tuple, without duplicates.

        Derived rather than stored, so the joined view cannot disagree with the
        groups it summarises. Duplicates are reachable in one configuration — a
        ``documentation.dir`` of ``.`` puts ``README.md`` in both groups — and
        would score that document twice, so the union drops them.
        """
        joined = dict.fromkeys((*self.documentation, *self.root_documents.values()))
        return tuple(sorted(joined))

    def kind_of(self, path: str) -> str | None:
        """Return the root-document kind of *path*, or ``None``.

        Only root documents have kinds. A file under ``documentation.dir`` is
        documentation, but it is not a *kind* of document: the kinds exist so a
        consumer can tell a README from the contract files beside it without
        inferring it from a directory name.
        """
        for kind, root_path in self.root_documents.items():
            if root_path == path:
                return kind
        return None
