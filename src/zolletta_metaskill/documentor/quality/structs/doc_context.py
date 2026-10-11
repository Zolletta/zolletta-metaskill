"""DocContext dataclass for per-document drift analysis."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocContext:
    """Per-document facts that a drift check needs, gathered once per document.

    Every value here varies on each iteration of the review loop, which is why
    they are bundled rather than threaded one by one through the checks.

    Naming is deliberate. ``file_rel_path`` is repo-*relative* — that is a
    precondition of the ``os.path.join(repo_root, ...)`` calls that resolve
    references, and an absolute path would silently misresolve because
    ``os.path.join`` discards everything left of an absolute component.
    ``documentation_rel_dir`` (the docs root, from settings) is a different
    thing entirely and is deliberately not spelled like this.

    Attributes:
        file_rel_path: Repo-relative path of the documentation file.
        refs: References extracted from the document, as returned by
            ``DocCodeMapper.extract_references_from_doc``.
        since_date: ``YYYY-MM-DD`` date of the document's last commit.
        associated_code_dirs: Directories of code associated with this document.

    """

    file_rel_path: str
    refs: dict[str, Any] = field(default_factory=dict)
    since_date: str = ""
    associated_code_dirs: tuple[str, ...] = ()

    @property
    def file_parent_dir(self) -> str:
        """Return the folder containing this document, derived — never stored.

        Derived rather than stored so the two cannot disagree: a caller able to
        pass a mismatched parent would make every consumer resolve references
        against the wrong base without any error.

        Returns ``''`` for a repository-root document such as ``README.md``.
        Callers that need a path should use ``os.path.join``, which tolerates
        the empty component.

        """
        return os.path.dirname(self.file_rel_path)
