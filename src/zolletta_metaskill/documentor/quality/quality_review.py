#!/usr/bin/env python3
"""QualityReview runs the unified drift + staleness review and writes its cache file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.quality.drift_detector import DriftDetector
from zolletta_metaskill.documentor.quality.quality_report_writer import QualityReportWriter
from zolletta_metaskill.documentor.quality.quality_scorer import QualityScorer
from zolletta_metaskill.documentor.quality.structs import GitRunContext
from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.file_discovery import FileDiscovery
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class QualityReview:
    """Orchestrates drift detection and staleness scoring for all docs."""

    CACHE_FILENAME = "quality.json"

    @staticmethod
    def _configured_doc_patterns(settings: dict[str, Any]) -> list[str] | None:
        """Resolve ``documentation.doc_patterns`` to a list of patterns."""
        raw_patterns = ProjectConfig.setting(settings, "documentation.doc_patterns", None)
        if isinstance(raw_patterns, list):
            return [p for p in raw_patterns if isinstance(p, str)]
        return None

    @staticmethod
    def run(repo_path: str, settings: dict[str, Any], cache_dir: Path) -> Path:
        """Run the unified review and write ``<cache_dir>/quality.json``.

        Returns the path to the written cache file. If no docs are found,
        an empty/skip record is still written so ``ReportAggregator`` can report it.
        """
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / QualityReview.CACHE_FILENAME

        patterns = QualityReview._configured_doc_patterns(settings)
        doc_files = FileDiscovery.find_doc_files(repo_path, patterns=patterns)

        readme_focus = bool(ProjectConfig.setting(settings, "documentation.readme_focus", False))
        if readme_focus:
            doc_files = [d for d in doc_files if os.path.basename(d).lower().startswith("readme")]

        if not doc_files:
            empty_data: dict[str, Any] = {
                "repository": os.path.abspath(repo_path),
                "scan_date": None,
                "summary": {
                    "total_docs": 0,
                    "aggregate_score": 0.0,
                    "aggregate_label": "unknown",
                    "drifted_docs": 0,
                    "total_issues": 0,
                    "by_severity": {},
                    "by_category": {},
                    "by_fix_type": {},
                },
                "documents": [],
                "issues": [],
                "skipped_reason": "No documentation files found",
            }
            cache_path.write_text(json.dumps(empty_data, indent=2, default=str) + "\n")
            return cache_path

        doc_settings = DocumentorSettings.from_settings(settings)
        min_severity = doc_settings.min_severity

        languages = ProjectConfig.configured_languages(settings)
        source_dirs = [
            str(r)
            for r in ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, languages))
        ]
        scopes = source_dirs or [""]

        code_files: list[str] = []
        seen: set[str] = set()
        for scope in scopes:
            for f in DocCodeMapper.find_code_files(repo_path, scope):
                if f not in seen:
                    seen.add(f)
                    code_files.append(f)
        code_files.sort()

        doc_code_map = DocCodeMapper.map_docs_to_code(repo_path, doc_files, code_files)
        since = f"{doc_settings.rename_window_days} days ago"
        renames = GitHelper.get_renamed_files(repo_path, since)
        current_version = GitHelper.get_latest_tag(repo_path)
        git_ctx = GitRunContext(
            repo_root=repo_path,
            renames=tuple(renames),
            current_version=current_version,
        )

        all_scores: list[dict[str, Any]] = []
        all_issues: list[dict[str, Any]] = []

        for doc in doc_files:
            associated_dirs = doc_code_map.get(doc, [""])
            if not associated_dirs:
                associated_dirs = [""]

            issues = DriftDetector.detect_drift_for_doc(
                git_ctx,
                doc_settings,
                doc,
                associated_dirs,
            )
            all_issues.extend(issues)
            all_scores.append(
                QualityScorer.score_document(
                    repo_path,
                    doc,
                    doc_settings.staleness_weights,
                    list(doc_settings.required_sections),
                    doc_settings.quadrants,
                )
            )

        min_sev_map = DriftDetector.SEVERITY_ORDER
        min_sev = min_sev_map.get(min_severity, 3)
        filtered_issues = [
            i for i in all_issues if min_sev_map.get(i.get("severity", "info"), 99) <= min_sev
        ]

        report = QualityReportWriter.generate_report(
            repo_path, all_scores, filtered_issues, as_json=True
        )
        cache_path.write_text(report + "\n")
        return cache_path

    @staticmethod
    def main() -> int:
        """Entry point for the standalone quality review CLI.

        Writes ``<cache_dir>/quality.json`` and prints a short summary.
        Exit code is 1 when ``documentation.staleness_threshold`` is configured
        and the aggregate score is below it.
        """
        parser = argparse.ArgumentParser(
            description="Run the unified drift + staleness quality review.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        repo_path = os.path.abspath(".")
        settings = ProjectConfig.load_settings()
        cache_dir = DocumentorSettings.resolve_cache_dir(settings)
        cache_path = QualityReview.run(repo_path, settings, cache_dir)

        data = json.loads(cache_path.read_text())
        if args.json:
            print(json.dumps(data, indent=2, default=str))
        else:
            summary = data.get("summary", {})
            skipped = data.get("skipped_reason")
            if skipped:
                print(skipped)
            else:
                print(
                    f"Aggregate score: {summary.get('aggregate_score')}/100 "
                    f"({summary.get('aggregate_label')}) — "
                    f"{summary.get('total_issues', 0)} drift issue(s) "
                    f"across {summary.get('total_docs', 0)} doc(s)"
                )
            print(f"Cache written to {cache_path}")

        raw_threshold = ProjectConfig.setting(settings, "documentation.staleness_threshold", None)
        aggregate_score = data.get("summary", {}).get("aggregate_score")
        threshold = float(raw_threshold) if isinstance(raw_threshold, (int, float)) else None
        if threshold is not None and aggregate_score is not None and aggregate_score < threshold:
            if not args.json:
                print(
                    f"FAILED: Aggregate score {aggregate_score:.1f} is below threshold {threshold}",
                    file=sys.stderr,
                )
            return 1
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(QualityReview.main())
