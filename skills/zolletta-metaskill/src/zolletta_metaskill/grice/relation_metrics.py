"""RelationMetrics — whether a document stays on its own subject.

Grice's Relation maxim asks a speaker to be relevant. A document can fail it in
three places: a heading that promises something its section does not deliver, a
frontmatter block that describes a different document than the one beneath it,
and a page that sits in a corpus it has nothing to do with. Each is a cosine
between two texts that are supposed to be about the same thing.
"""

from __future__ import annotations

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.similarity import Similarity
from zolletta_metaskill.grice.structs.document_features import DocumentFeatures


class RelationMetrics:
    """Score one document on how well its parts stay on subject."""

    @staticmethod
    def evaluate(
        features: DocumentFeatures, corpus: tuple[DocumentFeatures, ...]
    ) -> tuple[dict[str, float], list[Finding]]:
        """Measure Relation for one document.

        Args:
            features: The document being scored.
            corpus: Every document in the scan, including *features* itself.

        Returns:
            The raw metric values on a 0-100 scale, and always an empty finding
            list — relevance is a continuous judgement, and the only discrete
            defect in it (a broken anchor) already belongs to Quality.

        """
        metrics: dict[str, float] = {}
        if features.headings:
            pairs = Similarity.pair_scores(features.headings, features.sections)
            metrics["heading_body"] = 100.0 * sum(pairs) / len(pairs) if pairs else 0.0
        if features.frontmatter.strip():
            metrics["frontmatter_content"] = 100.0 * Similarity.cosine(
                features.frontmatter, features.prose
            )
        others = "\n".join(other.prose for other in corpus if other.path != features.path)
        metrics["corpus_pertinence"] = 100.0 * Similarity.cosine(features.prose, others)
        return metrics, []
