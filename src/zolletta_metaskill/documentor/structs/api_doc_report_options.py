"""APIDocReportOptions dataclass for API-doc report rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APIDocReportOptions:
    """Report-level values the writer cannot derive from its inputs.

    ``generate_report`` received six parameters, one over the configured
    ``max_arguments`` of 5. The obvious trim was to drop ``source_count`` and
    ``doc_count`` as ``len(issues)`` and ``len(suggestions)`` — but that would
    be wrong: the two counts describe the *whole* corpus, while issues and
    suggestions are the filtered output of validation. Private items are
    excluded, and only genuine mismatches become issues, so the totals are not
    recoverable from the lists that were derived from them. Bundling keeps both
    counts and the two rendering flags together rather than dropping data to
    satisfy a threshold.

    Attributes:
        source_count: Total source signatures discovered.
        doc_count: Total documented items found.
        as_json: Return JSON rather than Markdown.
        suggest_coverage: Include prioritised suggestions in full.

    """

    source_count: int = 0
    doc_count: int = 0
    as_json: bool = False
    suggest_coverage: bool = False
