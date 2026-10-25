"""MannerMetrics — how clear, ordered and plainly written a document is.

Grice's Manner maxim asks for clarity: brief, orderly, unambiguous. Readability
formulas measure one narrow slice of that — sentence and word complexity — and
they only speak English. The structural metrics are language-neutral and carry
the rest: a heading tree that skips a level, sections so long they stop being
sections, and sentences that need three passes to parse.

Hedging and passive voice are counted from fixed word lists, which makes them
heuristics rather than grammar. They are still deterministic, which is the
property that matters here: the same text yields the same count on every run,
and the corpus percentile says whether this document hedges more than its
neighbours, not whether hedging is wrong.

The formulas come from ``textstat.textstat`` rather than from ``textstat``
itself: the package builds its public surface in a ``for attribute in
dir(textstat)`` loop and declares ``__all__ = ["textstat", "backend"]``, so
neither a type checker nor a reader can see what it exports.
"""

from __future__ import annotations

import re

from textstat.textstat import textstat as readability_formulas

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.structs.document_features import DocumentFeatures


class MannerMetrics:
    """Score one document on readability, hedging and structural order."""

    FINDING_CATEGORY = "grice"
    HIERARCHY_SEVERITY = "low"

    #: Words a sentence may carry before it stops being a sentence a reader
    #: gets through in one pass. 25 is the upper end of the plain-language
    #: range; it is a policy number, not a measurement.
    MAX_SENTENCE_WORDS = 25

    #: A section shorter than this is a stub, longer than this is a chapter.
    MIN_SECTION_WORDS = 20
    MAX_SECTION_WORDS = 400

    #: Below this word count a readability formula is fitting noise, and
    #: textstat itself returns nonsense for a two-sentence paragraph.
    MIN_READABILITY_WORDS = 20

    #: SMOG needs three sentences before it produces a number at all.
    MIN_SMOG_SENTENCES = 3

    HEDGES = frozenset(
        {
            "appear",
            "appears",
            "arguably",
            "approximately",
            "basically",
            "could",
            "essentially",
            "fairly",
            "generally",
            "likely",
            "may",
            "might",
            "often",
            "perhaps",
            "possibly",
            "presumably",
            "probably",
            "quite",
            "rather",
            "roughly",
            "seem",
            "seems",
            "sometimes",
            "somewhat",
            "usually",
        }
    )

    PASSIVE = re.compile(
        r"\b(?:is|are|was|were|be|been|being|am)\b\s+(?:\w+\s+){0,2}\w+(?:ed|en)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def evaluate(
        features: DocumentFeatures, language: str
    ) -> tuple[dict[str, float], list[Finding]]:
        """Measure Manner for one document.

        Args:
            features: The document being scored.
            language: ``documentation.language``. Anything but ``"en"`` drops
                the textstat and word-list metrics, which are English-only.

        Returns:
            The raw metric values on a 0-100 scale, and one finding per heading
            that skips a level.

        """
        metrics: dict[str, float] = {}
        if language == "en":
            metrics.update(MannerMetrics._english(features))
        hierarchy, findings = MannerMetrics._hierarchy(features)
        metrics["heading_hierarchy"] = hierarchy
        sentence_length = MannerMetrics._sentence_length(features)
        if sentence_length is not None:
            metrics["sentence_length"] = sentence_length
        section_structure = MannerMetrics._section_structure(features)
        if section_structure is not None:
            metrics["section_structure"] = section_structure
        return metrics, findings

    @staticmethod
    def _english(features: DocumentFeatures) -> dict[str, float]:
        """Compute the metrics that only an English document can carry.

        Args:
            features: The document being scored.

        Returns:
            Readability, both grade-level formulas, hedging and passive voice,
            or an empty mapping when the document is too short for a formula to
            mean anything.

        """
        if features.word_count < MannerMetrics.MIN_READABILITY_WORDS:
            return {}
        sentences = max(features.sentence_count, 1)
        metrics = {
            "readability": MannerMetrics._clamp(
                readability_formulas.flesch_reading_ease(features.prose)
            ),
            "grade_level": 100.0
            - MannerMetrics._clamp(readability_formulas.gunning_fog(features.prose) * 5.0),
            "hedging": 100.0
            * MannerMetrics._clamp(1.0 - MannerMetrics._hedge_count(features) / sentences),
            "passive_voice": 100.0
            * MannerMetrics._clamp(1.0 - MannerMetrics._passive_count(features) / sentences),
        }
        if features.sentence_count >= MannerMetrics.MIN_SMOG_SENTENCES:
            smog = readability_formulas.smog_index(features.prose)
            metrics["smog"] = 100.0 - MannerMetrics._clamp(smog * 5.0)
        return metrics

    @staticmethod
    def _hedge_count(features: DocumentFeatures) -> int:
        """Count the sentences that hedge.

        Args:
            features: The document being scored.

        Returns:
            How many sentences contain at least one word from
            :data:`HEDGES`. Counting sentences rather than words keeps one
            evasive paragraph from dominating the metric.

        """
        return sum(
            1
            for sentence in features.sentences
            if any(
                word.strip(".,;:!?()[]\"'`").lower() in MannerMetrics.HEDGES
                for word in sentence.split()
            )
        )

    @staticmethod
    def _passive_count(features: DocumentFeatures) -> int:
        """Count the sentences that read as passive voice.

        Args:
            features: The document being scored.

        Returns:
            How many sentences contain an auxiliary followed by a participle.

        """
        return sum(1 for sentence in features.sentences if MannerMetrics.PASSIVE.search(sentence))

    @staticmethod
    def _hierarchy(features: DocumentFeatures) -> tuple[float, list[Finding]]:
        """Measure how cleanly the heading tree descends.

        Args:
            features: The document being scored.

        Returns:
            The percentage of heading transitions that descend by exactly one
            level, and one finding per transition that skips a level. A
            document with fewer than two headings has no transition to break
            and scores ``100``.

        """
        levels = features.heading_levels
        if len(levels) < 2:
            return 100.0, []
        skips = [index for index in range(1, len(levels)) if levels[index] - levels[index - 1] > 1]
        findings = [
            Finding(
                file=features.path,
                line=features.heading_lines[index],
                category=MannerMetrics.FINDING_CATEGORY,
                severity=MannerMetrics.HIERARCHY_SEVERITY,
                description=(
                    f"heading '{features.headings[index]}' jumps from level "
                    f"{levels[index - 1]} to {levels[index]}"
                ),
            )
            for index in skips
        ]
        return 100.0 * (1.0 - len(skips) / (len(levels) - 1)), findings

    @staticmethod
    def _sentence_length(features: DocumentFeatures) -> float | None:
        """Measure the share of sentences a reader gets through in one pass.

        Args:
            features: The document being scored.

        Returns:
            The percentage of sentences within :data:`MAX_SENTENCE_WORDS`, or
            ``None`` when there are no sentences to measure.

        """
        if not features.sentences:
            return None
        readable = sum(
            1
            for sentence in features.sentences
            if len(sentence.split()) <= MannerMetrics.MAX_SENTENCE_WORDS
        )
        return 100.0 * readable / len(features.sentences)

    @staticmethod
    def _section_structure(features: DocumentFeatures) -> float | None:
        """Measure the share of sections sized like sections.

        Args:
            features: The document being scored.

        Returns:
            The percentage of sections between :data:`MIN_SECTION_WORDS` and
            :data:`MAX_SECTION_WORDS` words, or ``None`` when there are no
            sections.

        """
        if not features.sections:
            return None
        proportioned = sum(
            1
            for section in features.sections
            if MannerMetrics.MIN_SECTION_WORDS
            <= len(section.split())
            <= MannerMetrics.MAX_SECTION_WORDS
        )
        return 100.0 * proportioned / len(features.sections)

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp *value* into the 0-100 range the metrics share.

        Textstat formulas are not bounded: Flesch can exceed 100 on very simple
        prose and go negative on very dense prose, and a negative index would
        invert the ranking the normalizer builds.

        Args:
            value: A raw score.

        Returns:
            The score confined to ``0.0``-``100.0``.

        """
        return max(0.0, min(100.0, value))
