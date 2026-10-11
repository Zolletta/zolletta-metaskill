"""GitRunContext dataclass for run-scoped git facts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitRunContext:
    """Run-scoped git facts that are identical for every document in a review.

    These values are computed once in ``QualityReview.run`` and are
    loop-invariant, so bundling them keeps them out of every per-document
    signature. They are *not* settings-derived: ``repo_root`` is a runtime
    absolute path (settings only ever hold the relative ``documentation.dir``),
    and the rename list and latest tag come from the git history.

    Attributes:
        repo_root: Absolute path to the git repository root.
        renames: ``(old_name, new_name)`` pairs of renamed files/symbols.
        current_version: Latest project version string, or ``None``.

    """

    repo_root: str
    renames: tuple[tuple[str, str], ...] = ()
    current_version: str | None = None
