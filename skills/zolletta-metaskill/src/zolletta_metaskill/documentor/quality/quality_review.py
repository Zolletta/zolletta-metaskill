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
from zolletta_metaskill.documentor.structs import DocumentationInventory
from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper
from zolletta_metaskill.documentor.utils.documentation_files_finder import DocumentationFilesFinder
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class QualityReview:
    """Orchestrates drift detection and staleness scoring for all docs."""

    CACHE_FILENAME = "quality.json"

    @staticmethod
    def _required_sections(
        inventory: DocumentationInventory,
        doc_settings: DocumentorSettings,
        doc_path: str,
    ) -> list[str]:
        """Return the README sections *doc_path* is scored for carrying.

        README sections describe a README. Applying them to every document that
        is not in a Diátaxis quadrant directory — which is what happens when the
        completeness scorer is simply handed them — scored ``AGENTS.md`` 0.0 for
        want of an installation section, and ``docs/index.md`` 80.0.

        The kind comes from the inventory rather than from where the file sits,
        so the gate is a fact about the document instead of an inference. It is
        applied here rather than inside the scorer because ``score_document``
        already declares five parameters and a sixth would break
        ``functions.1``; the number of section sets is a property of the
        document, which is what the inventory is for.
        """
        if inventory.kind_of(doc_path) == "readme":
            return list(doc_settings.required_sections)
        return []

    @staticmethod
    def run(repo_path: str, settings: dict[str, Any], cache_dir: Path) -> Path:
        """Run the unified review and write ``<cache_dir>/quality.json``.

        Returns the path to the written cache file. If no docs are found,
        an empty/skip record is still written so ``ReportAggregator`` can report it.
        """
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / QualityReview.CACHE_FILENAME

        inventory = DocumentationFilesFinder.find(settings, repo_path)
        doc_files = list(inventory.all_paths)

        # pragma: no mutate start — bool() normalizes None and False identically, so the
        # mutated default is unobservable
        readme_focus = bool(ProjectConfig.setting(settings, "documentation.readme_focus", False))
        # pragma: no mutate end
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
                "skipped_reason": inventory.skipped_reason or "No documentation files found",
            }
            cache_path.write_text(json.dumps(empty_data, indent=2) + "\n")
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
            # pragma: no mutate start — the next line remaps every falsy value to [""],
            # so a None or missing-arg default is unobservable
            associated_dirs = doc_code_map.get(doc, [""])
            # pragma: no mutate end
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
                    QualityReview._required_sections(inventory, doc_settings, doc),
                    doc_settings.quadrants,
                )
            )

        min_sev_map = DriftDetector.SEVERITY_ORDER
        min_sev = min_sev_map.get(min_severity, 3)
        # pragma: no mutate start — sentinel 99≈100: both exceed every threshold (min_sev ≤ 4);
        # a missing/None default crashes the run() call site, which the severity-filter test covers
        filtered_issues = [
            i for i in all_issues if min_sev_map.get(i.get("severity", "info"), 99) <= min_sev
        ]
        # pragma: no mutate end

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
        # pragma: no mutate start — argparse description/help text is not a tested contract
        parser = argparse.ArgumentParser(
            description="Run the unified drift + staleness quality review.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        # pragma: no mutate end
        args = parser.parse_args()

        repo_path = os.path.abspath(".")
        settings = ProjectConfig.load_settings()
        cache_dir = DocumentorSettings.resolve_cache_dir(settings)
        cache_path = QualityReview.run(repo_path, settings, cache_dir)

        data = json.loads(cache_path.read_text())
        if args.json:
            print(json.dumps(data, indent=2))
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
