#!/usr/bin/env python3
"""DocumentorClient runs the full documentation review and aggregates the results.

It coordinates three domain tools:
- ``quality/quality_review.py`` — unified drift + staleness review
- ``api_doc/api_doc_validator.py`` — Python API doc validation
- ``links/link_checker.py`` — link checking

Each tool writes its own JSON cache file under the configured cache directory,
and ``ReportAggregator`` combines those caches into a single report.

Usage:
    python documentor_client.py [--json]

Exit code: 0 normally; 1 if ``documentation.staleness_threshold`` is configured and
the aggregate staleness score is below it.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.api_doc.api_doc_validator import APIDocValidator
from zolletta_metaskill.documentor.links.link_checker import LinkChecker
from zolletta_metaskill.documentor.quality.quality_review import QualityReview
from zolletta_metaskill.documentor.report_aggregator import ReportAggregator
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings


class DocumentorClient:
    """Main CLI entry point for the documentor review."""

    @staticmethod
    def _python_configured(settings: dict[str, Any]) -> bool:
        """Return True when Python source roots are configured and exist."""
        languages = ProjectConfig.languages_for_extensions(
            ProjectConfig.configured_languages(settings), {".py"}
        )
        source_roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, languages))
        return bool(source_roots) and ProjectConfig.docs_dir(settings).exists()

    @staticmethod
    def main() -> int:
        """Run the full documentor review and print the aggregated report."""
        parser = argparse.ArgumentParser(
            description="Run the full documentation review (staleness, API docs, links).",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--json", action="store_true", help="Output as JSON"
        )  # pragma: no mutate — help text is not a tested contract  # noqa: E501
        args = parser.parse_args()

        repo_path = os.path.abspath(".")
        settings = ProjectConfig.load_settings()
        cache_dir = DocumentorSettings.resolve_cache_dir(settings)
        cache_dir.mkdir(parents=True, exist_ok=True)

        QualityReview.run(repo_path, settings, cache_dir)

        if DocumentorClient._python_configured(settings):
            APIDocValidator.run(settings, cache_dir)
        else:
            APIDocValidator._write_cache(
                cache_dir,
                {
                    "skipped_reason": "Python source roots or docs dir not configured/missing",
                    "summary": {},
                    "issues": [],
                    "suggestions": [],
                },
            )

        LinkChecker.run(repo_path, settings, cache_dir)

        report = ReportAggregator.aggregate(cache_dir, as_json=args.json)
        print(report)

        quality = ReportAggregator.read_quality_cache(cache_dir)
        quality_summary = quality.get("summary", {})
        aggregate_score = quality_summary.get("aggregate_score")
        if aggregate_score is not None:
            raw_threshold = ProjectConfig.setting(
                settings, "documentation.staleness_threshold", None
            )
            threshold = float(raw_threshold) if isinstance(raw_threshold, (int, float)) else None
            if threshold is not None and aggregate_score < threshold:
                if not args.json:
                    print(
                        f"\nFAILED: Aggregate score {aggregate_score:.1f} "
                        f"is below threshold {threshold}",
                        file=sys.stderr,
                    )
                return 1

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(DocumentorClient.main())
