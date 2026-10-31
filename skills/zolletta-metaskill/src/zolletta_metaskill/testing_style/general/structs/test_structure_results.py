"""TestStructureResults dataclass for the test-structure scanner's findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TestStructureResults:
    """The five finding buckets the test-structure scanner reports.

    ``_emit_summary``, ``_emit_text`` and ``_emit_json`` each took five or six
    parameters, one over the configured ``max_arguments`` of 5, and five of those
    were all ``list[dict[str, Any]]``. Because the element types are identical,
    only the parameter *name* distinguished misnamed from misplaced from orphaned
    from missing from indirect — so a positional call site could transpose them
    silently and nothing would complain. One already did: ``classified`` was a
    ``dict[str, Any]`` bag holding three of the five, so the same values were
    being threaded both ways at once.

    Attributes:
        misnamed: Test files whose name matches no source stem.
        misplaced: Test files outside their mirrored directory.
        orphaned: Test files with no source counterpart.
        orphaned_dirs: Directories holding only git-ignored artefacts.
        missing: Source files with classes but no test.
        indirect_refs: Test files that indirectly cover another source file.

    """

    misnamed: list[dict[str, Any]] = field(default_factory=list)
    misplaced: list[dict[str, Any]] = field(default_factory=list)
    orphaned: list[dict[str, Any]] = field(default_factory=list)
    orphaned_dirs: list[dict[str, Any]] = field(default_factory=list)
    missing: list[dict[str, Any]] = field(default_factory=list)
    indirect_refs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Return ``True`` when any bucket is non-empty.

        Computed rather than passed: the three emitters each received it as a
        seventh parameter, which is one more thing to keep in step with the
        buckets it summarises.

        """
        return bool(
            self.misnamed
            or self.misplaced
            or self.orphaned
            or self.orphaned_dirs
            or self.missing
            or self.indirect_refs
        )
