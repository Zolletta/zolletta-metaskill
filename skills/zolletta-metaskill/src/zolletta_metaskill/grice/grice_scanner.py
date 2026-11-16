#!/usr/bin/env python3
"""Score project documentation against Grice's four maxims.

The four maxims — Quantity, Quality, Relation, Manner — are computed as
deterministic metrics over the documentation corpus, normalized against that
corpus, and reported as indices in 0-100. The corpus is the documentor's:
``DocumentationFilesFinder`` names it, so ``documentation.dir`` plus
``README.md``, ``CONTRIBUTING.md`` and ``AGENTS.md``, with ``skills/``,
``SKILL.md`` and ``CHANGELOG.md`` out of scope — minus every ADR, which
``CorpusScope`` removes before anything is normalised.

**The indices are relative, and that is the whole design.** A ``grice_index`` of
50 means "the middle of this corpus", never "mediocre". Two consequences follow
and both are load-bearing: a corpus of uniformly excellent documents still
produces a spread of indices, and a single document cannot be scored at all —
there is nothing to be relative to. The scan therefore reports SKIPPED for a
corpus with no documents, and adds a noise note below five.

Findings are the exception to the relativity. A broken internal link or a
heading that skips a level is a defect in the document, not a rank among its
peers, so those are reported as ordinary findings with file and line, and
numbered ``G1``, ``G2``… with broken links deduplicated per target.

Everything the report shows is computed here, deterministically: the
presentation groups (first-level children of ``documentation.dir``), the
Executive Summary rows, and per group the outliers selected by
``subcommands.grice.outlier_threshold`` and the positive benchmarks — the
best ``balanced`` document and the top document on each maxim — with the
rule-based diagnosis of each. Groups never enter the normalisation, which
stays corpus-wide.

Usage:
    python3 grice_scanner.py [--json]

Options:
    --json          Output as JSON instead of markdown.

Exit code: 0 always — the scan is report-only, and a low index is a measurement
rather than a failure.

"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper
from zolletta_metaskill.documentor.utils.documentation_files_finder import (
    DocumentationFilesFinder,
)
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.grice.corpus_normalizer import CorpusNormalizer
from zolletta_metaskill.grice.corpus_scope import CorpusScope
from zolletta_metaskill.grice.defect_catalog import DefectCatalog
from zolletta_metaskill.grice.document_grouper import DocumentGrouper
from zolletta_metaskill.grice.grice_text_renderer import GriceTextRenderer
from zolletta_metaskill.grice.group_summarizer import GroupSummarizer
from zolletta_metaskill.grice.manner_metrics import MannerMetrics
from zolletta_metaskill.grice.markdown_corpus import MarkdownCorpus
from zolletta_metaskill.grice.quality_metrics import QualityMetrics
from zolletta_metaskill.grice.quantity_metrics import QuantityMetrics
from zolletta_metaskill.grice.relation_metrics import RelationMetrics
from zolletta_metaskill.grice.structs import (
    DocumentFeatures,
    GriceReport,
    GriceSettings,
    MaximScores,
)
from zolletta_metaskill.grice.triage_selector import TriageSelector


class GriceScanner:
    """Orchestrate the four maxim scorers over the documentation corpus."""

    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH

    #: Below this many documents a corpus percentile is describing individual
    #: quirks rather than a distribution, so the report says so out loud.
    MIN_CORPUS = 5

    #: How many source files lexical alignment reads. A ceiling, not a target:
    #: the vectorizer's cost grows with the vocabulary, and a thousandth file
    #: adds no signal a reviewer would act on.
    MAX_SOURCE_FILES = 500

    MAXIMS = ("quantity", "quality", "relation", "manner")

    @staticmethod
    def build(settings: dict[str, Any], repo_path: str) -> GriceReport | None:
        """Scan the documentation corpus and return its report.

        Args:
            settings: Parsed ``settings.json`` contents.
            repo_path: Absolute repository root.

        Returns:
            The scored report, or ``None`` when the corpus has no readable
            document — an empty corpus has nothing to be relative to.

        """
        corpus, excluded = GriceScanner._corpus(settings, repo_path)
        if not corpus:
            return None
        language = str(ProjectConfig.setting(settings, "documentation.language", "en"))
        docs_dir = str(ProjectConfig.docs_dir(settings))
        raw, link_findings, heading_findings = GriceScanner._raw(corpus, repo_path, language)
        documents = GriceScanner._score(corpus, raw, docs_dir)
        thresholds = GriceSettings.from_settings(settings)
        outliers = TriageSelector.outliers(documents, thresholds.outlier_threshold)
        defects = DefectCatalog.build(
            link_findings,
            heading_findings,
            lambda path: DocumentGrouper.group_of(path, docs_dir),
            repo_path,
        )
        return GriceReport(
            documents=documents,
            findings=tuple(
                sorted(link_findings + heading_findings, key=lambda item: (item.file, item.line))
            ),
            disabled_metrics=GriceScanner._disabled_metrics(language),
            notes=GriceScanner._notes(len(corpus), language, len(excluded)),
            excluded_adrs=tuple(sorted(excluded)),
            groups=GroupSummarizer.summarise(documents, outliers, defects),
            defects=defects,
            outliers=outliers,
            triage=TriageSelector.by_group(documents, outliers, thresholds.outlier_threshold),
            settings=thresholds,
        )

    @staticmethod
    def _corpus(
        settings: dict[str, Any], repo_path: str
    ) -> tuple[tuple[DocumentFeatures, ...], tuple[str, ...]]:
        """Parse every documentation file in scope, ADRs left out.

        Args:
            settings: Parsed ``settings.json`` contents.
            repo_path: Absolute repository root.

        Returns:
            One feature set per readable document, sorted by path. A file that
            cannot be decoded is skipped rather than aborting the scan, because
            one unreadable document should not silence the other fifty-nine.
            Also returns the ADR paths that :class:`CorpusScope` excluded.

        """
        inventory = DocumentationFilesFinder.find(settings, repo_path)
        paths, excluded = CorpusScope.split(inventory.all_paths, settings)
        features: list[DocumentFeatures] = []
        for path in paths:
            try:
                text = (Path(repo_path) / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            features.append(MarkdownCorpus.parse(path, text))
        return tuple(features), excluded

    @staticmethod
    def _raw(
        corpus: tuple[DocumentFeatures, ...], repo_path: str, language: str
    ) -> tuple[dict[str, tuple[dict[str, float], ...]], list[Finding], list[Finding]]:
        """Run the four maxim scorers over the corpus.

        Runs over every document once, so the cross-document metrics (corpus
        median, peer redundancy, pertinence) and the per-document ones are read
        from the same parse.

        Args:
            corpus: The parsed documents.
            repo_path: Absolute repository root.
            language: ``documentation.language``.

        Returns:
            Maxim name to one raw metric mapping per document, then the
            broken-link findings (Quality) and the heading-skip findings
            (Manner).

        """
        source_text = GriceScanner._source_text(repo_path)
        rows: dict[str, list[dict[str, float]]] = {maxim: [] for maxim in GriceScanner.MAXIMS}
        link_findings: list[Finding] = []
        heading_findings: list[Finding] = []
        for features in corpus:
            quantity, _ = QuantityMetrics.evaluate(features, corpus)
            quality, quality_findings = QualityMetrics.evaluate(features, repo_path, source_text)
            relation, _ = RelationMetrics.evaluate(features, corpus)
            manner, manner_findings = MannerMetrics.evaluate(features, language)
            for maxim, metrics in (
                ("quantity", quantity),
                ("quality", quality),
                ("relation", relation),
                ("manner", manner),
            ):
                rows[maxim].append(metrics)
            link_findings.extend(quality_findings)
            heading_findings.extend(manner_findings)
        rows_by_maxim = {maxim: tuple(rows[maxim]) for maxim in GriceScanner.MAXIMS}
        return rows_by_maxim, link_findings, heading_findings

    @staticmethod
    def _source_text(repo_path: str) -> str:
        """Concatenate the project's source files for lexical alignment.

        Args:
            repo_path: Absolute repository root.

        Returns:
            The first :data:`MAX_SOURCE_FILES` source files joined by newlines,
            or ``""`` when the project ships no code.

        """
        chunks: list[str] = []
        for relative in DocCodeMapper.find_code_files(repo_path)[: GriceScanner.MAX_SOURCE_FILES]:
            try:
                chunks.append(
                    (Path(repo_path) / relative).read_text(encoding="utf-8", errors="ignore")
                )
            except OSError:
                continue
        return "\n".join(chunks)

    @staticmethod
    def _score(
        corpus: tuple[DocumentFeatures, ...],
        raw: dict[str, tuple[dict[str, float], ...]],
        docs_dir: str,
    ) -> tuple[MaximScores, ...]:
        """Normalize every maxim across the corpus and build one row per document.

        Args:
            corpus: The parsed documents, used for row paths.
            raw: Maxim name to one raw metric mapping per document.
            docs_dir: ``documentation.dir``, which names each row's group.

        Returns:
            One :class:`MaximScores` per document, in corpus order.

        """
        normalised = {
            maxim: CorpusNormalizer.normalise_rows(raw[maxim]) for maxim in GriceScanner.MAXIMS
        }
        return tuple(
            MaximScores(
                path=features.path,
                quantity=CorpusNormalizer.aggregate_maxim(normalised, "quantity", index),
                quality=CorpusNormalizer.aggregate_maxim(normalised, "quality", index),
                relation=CorpusNormalizer.aggregate_maxim(normalised, "relation", index),
                manner=CorpusNormalizer.aggregate_maxim(normalised, "manner", index),
                group=DocumentGrouper.group_of(features.path, docs_dir),
            )
            for index, features in enumerate(corpus)
        )

    @staticmethod
    def _disabled_metrics(language: str) -> tuple[str, ...]:
        """Return the metrics that did not run, by name.

        Args:
            language: ``documentation.language``.

        Returns:
            The English-only metrics when the documentation is not English,
            otherwise an empty tuple.

        """
        if language == "en":
            return ()
        return ("readability", "grade_level", "smog", "hedging", "passive_voice")

    @staticmethod
    def _notes(corpus_size: int, language: str, excluded_adrs: int) -> tuple[str, ...]:
        """Return the caveats that qualify the numbers.

        Args:
            corpus_size: How many documents were scored.
            language: ``documentation.language``.
            excluded_adrs: How many ADR files were left out.

        Returns:
            The caveats, always at least the relativity note — an index is
            meaningless without the statement it is relative to.

        """
        notes = [
            "Indices are relative to this corpus: 50 is the corpus mean, not a quality threshold.",
        ]
        if excluded_adrs:
            notes.append(
                f"{excluded_adrs} ADR file(s) excluded before normalisation: decision records "
                "are not ranked against documentation."
            )
        if corpus_size < GriceScanner.MIN_CORPUS:
            notes.append(
                f"Corpus has {corpus_size} document(s); percentiles over fewer than "
                f"{GriceScanner.MIN_CORPUS} documents are noisy."
            )
        if language != "en":
            notes.append(
                f"documentation.language is '{language}': readability, grade level, "
                "SMOG, hedging and passive voice did not run."
            )
        return tuple(notes)

    @staticmethod
    def _emit_json(report: GriceReport) -> None:
        """Print the JSON report.

        Args:
            report: The scored corpus.

        """
        print(json.dumps(report.to_dict(), indent=2))

    @staticmethod
    def _emit_text(report: GriceReport) -> None:
        """Print the report as markdown.

        Args:
            report: The scanned corpus.

        """
        print(GriceTextRenderer.render(report), end="")

    @staticmethod
    def main() -> int:
        """Run the Grice scanner CLI."""
        # pragma: no mutate start — help text is not a tested contract
        parser = argparse.ArgumentParser(
            description="Score project documentation against Grice's four maxims. "
            "Paths and language come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json", action="store_true", help="Output as JSON instead of markdown"
        )
        # pragma: no mutate end
        args = parser.parse_args()

        settings = ProjectConfig.load_settings(GriceScanner.DEFAULT_SETTINGS_PATH)
        repo_path = os.path.abspath(".")
        report = GriceScanner.build(settings, repo_path)
        if report is None:
            ProjectConfig.emit_skipped(args.json, "no documentation files found")
            return 0

        cache_dir = DocumentorSettings.resolve_cache_dir(settings)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "grice.json"
        cache_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

        if args.json:
            GriceScanner._emit_json(report)
        else:
            GriceScanner._emit_text(report)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(GriceScanner.main())
