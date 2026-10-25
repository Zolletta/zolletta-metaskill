#!/usr/bin/env python3
"""Score project documentation against Grice's four maxims.

The four maxims — Quantity, Quality, Relation, Manner — are computed as
deterministic metrics over the documentation corpus, normalized against that
corpus, and reported as indices in 0-100. The corpus is the documentor's:
``DocumentationFilesFinder`` names it, so ``documentation.dir`` plus
``README.md``, ``CONTRIBUTING.md`` and ``AGENTS.md``, with ``skills/``,
``SKILL.md`` and ``CHANGELOG.md`` out of scope.

**The indices are relative, and that is the whole design.** A ``grice_index`` of
50 means "the middle of this corpus", never "mediocre". Two consequences follow
and both are load-bearing: a corpus of uniformly excellent documents still
produces a spread of indices, and a single document cannot be scored at all —
there is nothing to be relative to. The scan therefore reports SKIPPED for a
corpus with no documents, and adds a noise note below five.

Findings are the exception to the relativity. A broken internal link or a
heading that skips a level is a defect in the document, not a rank among its
peers, so those are reported as ordinary findings with file and line.

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
from zolletta_metaskill.grice.manner_metrics import MannerMetrics
from zolletta_metaskill.grice.markdown_corpus import MarkdownCorpus
from zolletta_metaskill.grice.quality_metrics import QualityMetrics
from zolletta_metaskill.grice.quantity_metrics import QuantityMetrics
from zolletta_metaskill.grice.relation_metrics import RelationMetrics
from zolletta_metaskill.grice.structs import DocumentFeatures, GriceReport, MaximScores


class GriceScanner:
    """Orchestrate the four maxim scorers over the documentation corpus."""

    DEFAULT_ENABLED = False
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
    def is_enabled(settings: dict[str, Any]) -> bool:
        """Return whether ``documentation.check_grice`` is on.

        Args:
            settings: Parsed ``settings.json`` contents.

        Returns:
            The toggle, defaulting to :attr:`DEFAULT_ENABLED` — the scan is
            opt-in because it is a judgement about prose, and a project that has
            not asked for that judgement should not receive one.

        """
        return bool(
            ProjectConfig.setting(
                settings, "documentation.check_grice", GriceScanner.DEFAULT_ENABLED
            )
        )

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
        corpus = GriceScanner._corpus(settings, repo_path)
        if not corpus:
            return None
        language = str(ProjectConfig.setting(settings, "documentation.language", "en"))
        raw, findings = GriceScanner._raw(corpus, repo_path, language)
        return GriceReport(
            documents=GriceScanner._score(corpus, raw),
            findings=tuple(sorted(findings, key=lambda finding: (finding.file, finding.line))),
            disabled_metrics=GriceScanner._disabled_metrics(language),
            notes=GriceScanner._notes(len(corpus), language),
        )

    @staticmethod
    def _corpus(settings: dict[str, Any], repo_path: str) -> tuple[DocumentFeatures, ...]:
        """Parse every documentation file in scope.

        Args:
            settings: Parsed ``settings.json`` contents.
            repo_path: Absolute repository root.

        Returns:
            One feature set per readable document, sorted by path. A file that
            cannot be decoded is skipped rather than aborting the scan, because
            one unreadable document should not silence the other fifty-nine.

        """
        inventory = DocumentationFilesFinder.find(settings, repo_path)
        features: list[DocumentFeatures] = []
        for path in inventory.all_paths:
            try:
                text = (Path(repo_path) / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            features.append(MarkdownCorpus.parse(path, text))
        return tuple(features)

    @staticmethod
    def _raw(
        corpus: tuple[DocumentFeatures, ...], repo_path: str, language: str
    ) -> tuple[dict[str, tuple[dict[str, float], ...]], list[Finding]]:
        """Run the four maxim scorers over the corpus.

        Runs over every document once, so the cross-document metrics (corpus
        median, peer redundancy, pertinence) and the per-document ones are read
        from the same parse.

        Args:
            corpus: The parsed documents.
            repo_path: Absolute repository root.
            language: ``documentation.language``.

        Returns:
            Maxim name to one raw metric mapping per document, plus every
            finding the scorers raised.

        """
        source_text = GriceScanner._source_text(repo_path)
        rows: dict[str, list[dict[str, float]]] = {maxim: [] for maxim in GriceScanner.MAXIMS}
        findings: list[Finding] = []
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
            findings.extend(quality_findings)
            findings.extend(manner_findings)
        return {maxim: tuple(rows[maxim]) for maxim in GriceScanner.MAXIMS}, findings

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
    ) -> tuple[MaximScores, ...]:
        """Normalize every maxim across the corpus and build one row per document.

        Args:
            corpus: The parsed documents, used for row paths.
            raw: Maxim name to one raw metric mapping per document.

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
    def _notes(corpus_size: int, language: str) -> tuple[str, ...]:
        """Return the caveats that qualify the numbers.

        Args:
            corpus_size: How many documents were scored.
            language: ``documentation.language``.

        Returns:
            The caveats, always at least the relativity note — an index is
            meaningless without the statement it is relative to.

        """
        notes = [
            "Indices are relative to this corpus: 50 is the corpus mean, not a quality threshold.",
        ]
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
    def _cell(value: float | None) -> str:
        """Format one index for the markdown table.

        Args:
            value: The index, or ``None`` when the maxim was not measured.

        Returns:
            The index to one decimal place, or an em dash for "not measured" —
            never ``0``, which would read as "measured and worst".

        """
        return "—" if value is None else f"{value:.1f}"

    @staticmethod
    def _emit_json(report: GriceReport) -> None:
        """Print the JSON report.

        Args:
            report: The scored corpus.

        """
        print(json.dumps(report.to_dict(), indent=2))

    @staticmethod
    def _emit_text(report: GriceReport) -> None:
        """Print the markdown report.

        Args:
            report: The scored corpus.

        """
        print("=" * 70)
        print("GRICE — DOCUMENTATION MAXIMS REPORT")
        print("=" * 70)
        print(f"\nCorpus: {report.corpus_size} document(s)")
        print("\n| Document | Quantity | Quality | Relation | Manner | Grice |")
        print("|---|---|---|---|---|---|")
        for row in report.documents:
            print(
                f"| `{row.path}` | {GriceScanner._cell(row.quantity)} "
                f"| {GriceScanner._cell(row.quality)} "
                f"| {GriceScanner._cell(row.relation)} "
                f"| {GriceScanner._cell(row.manner)} "
                f"| {GriceScanner._cell(row.grice_index)} |"
            )
        print(f"\nCorpus index: {GriceScanner._cell(report.corpus_index)}")
        if report.disabled_metrics:
            print(f"\nDisabled metrics: {', '.join(report.disabled_metrics)}")
        if report.findings:
            print(f"\n## Findings ({len(report.findings)})\n")
            for finding in report.findings:
                print(
                    f"  {finding.file}:{finding.line}  [{finding.severity}] {finding.description}"
                )
        else:
            print("\n## Findings: none")
        print("\n## Notes\n")
        for note in report.notes:
            print(f"  - {note}")
        print()

    @staticmethod
    def main() -> int:
        """Run the Grice scanner CLI."""
        # pragma: no mutate start — help text is not a tested contract
        parser = argparse.ArgumentParser(
            description="Score project documentation against Grice's four maxims. "
            "Toggle and thresholds come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json", action="store_true", help="Output as JSON instead of markdown"
        )
        # pragma: no mutate end
        args = parser.parse_args()

        settings = ProjectConfig.load_settings(GriceScanner.DEFAULT_SETTINGS_PATH)
        if not GriceScanner.is_enabled(settings):
            ProjectConfig.emit_skipped(args.json, "check_grice disabled in settings.json")
            return 0

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
