"""QuantityMetrics — how much a document says against how much it repeats.

Grice's Quantity maxim asks for enough information and not more. Read as a
documentation rule it has two failure modes: a section so thin it says nothing,
and a document that keeps saying the same thing in new words. Both are measured
here, and both are measured *relative to the corpus* — a two-hundred-word
section is generous in a changelog and stingy in a tutorial, and only the
corpus knows which one it is looking at.
"""

from __future__ import annotations

import statistics

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.similarity import Similarity
from zolletta_metaskill.grice.structs.document_features import DocumentFeatures


class QuantityMetrics:
    """Score one document on how much it says against how much it repeats."""

    #: How many sentences a redundancy check looks at. The check is quadratic,
    #: and the longest documents in a real corpus carry hundreds of sentences;
    #: the first 200 are a deterministic sample of the same shape, and a
    #: document does not become less repetitive further down.
    SENTENCE_SAMPLE = 200

    @staticmethod
    def evaluate(
        features: DocumentFeatures, corpus: tuple[DocumentFeatures, ...]
    ) -> tuple[dict[str, float], list[Finding]]:
        """Measure Quantity for one document.

        Every metric is on a 0-100 scale and oriented so that higher is better,
        which lets the normalizer treat all five identically.

        Args:
            features: The document being scored.
            corpus: Every document in the scan, including *features* itself.
                The corpus median and the peer comparison both need it.

        Returns:
            The raw metric values, and always an empty finding list — Quantity
            is a relative judgement with no defect to point at.

        """
        others = tuple(other.prose for other in corpus if other.path != features.path)
        sampled = features.sentences[: QuantityMetrics.SENTENCE_SAMPLE]
        metrics = {
            "section_balance": QuantityMetrics._section_balance(features, corpus),
            "section_redundancy": 100.0 * (1.0 - Similarity.max_pairwise(features.sections)),
            "sentence_redundancy": 100.0 * (1.0 - Similarity.max_pairwise(sampled)),
            "corpus_duplication": 100.0 * (1.0 - Similarity.max_against(features.prose, others)),
            "content_ratio": QuantityMetrics._content_ratio(features),
        }
        return metrics, []

    @staticmethod
    def _section_balance(features: DocumentFeatures, corpus: tuple[DocumentFeatures, ...]) -> float:
        """Return how close the document's section size is to the corpus median.

        A section far from typical is either starved or sprawling, and neither
        can be read on its own: the same length is fine in one document type
        and wrong in another. The result is already corpus-relative, and the
        normalizer then ranks it against its peers — which is why the docs call
        this the one double-relative metric in the set.

        Args:
            features: The document being scored.
            corpus: Every document in the scan.

        Returns:
            ``100`` at the median, falling towards ``0`` as the deviation grows.

        """
        positive = tuple(other.words_per_section for other in corpus if other.words_per_section > 0)
        if not positive:
            return 0.0
        median = statistics.median(positive)
        length = features.words_per_section
        if length <= 0:
            return 0.0
        return 100.0 / (1.0 + abs(length - median) / median)

    @staticmethod
    def _content_ratio(features: DocumentFeatures) -> float:
        """Return the share of the document's words that carry prose.

        Args:
            features: The document being scored.

        Returns:
            The percentage of words that are not badges, rules or comments, or
            ``100.0`` for a document with no words at all — nothing decorative
            is being measured there, and ``0`` would read as a full document of
            boilerplate.

        """
        words = features.word_count
        if words <= 0:
            return 100.0
        prose = max(words - features.boilerplate_words, 0)
        return 100.0 * prose / words
