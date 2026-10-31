"""CorpusNormalizer — turn raw metric values into corpus-relative indices.

Every metric the maxim scorers produce is a raw number whose absolute scale
means nothing on its own: a Flesch score of 45 and a redundancy ratio of 0.45
are not comparable, and neither is comparable across two projects. Normalizing
inside the corpus makes one claim only — *this document is at percentile N of
the documents beside it* — which is the claim a reviewer can actually act on.

The transform is a z-score pushed through the normal CDF, so the output is a
percentile in 0-100 with 50 at the corpus mean. It is deliberately not a rank:
ranks discard distance, and two documents a hair apart would land 40 points
from each other just because the sample is small. Ties stay ties.
"""

from __future__ import annotations

import math
from collections.abc import Mapping


class CorpusNormalizer:
    """Normalize metric values across a corpus and aggregate them per document.

    A single-value corpus and a corpus where every document scores the same
    both yield :data:`NEUTRAL`: no document is above or below its peers, and
    inventing a ranking out of a flat sample would be noise dressed as signal.
    """

    NEUTRAL = 50.0

    @staticmethod
    def normalise(values: tuple[float, ...]) -> tuple[float, ...]:
        """Convert raw values into corpus percentiles.

        Args:
            values: One raw value per document that has this metric.

        Returns:
            One percentile in 0-100 per value, positionally aligned with
            *values*. A flat sample, or a sample of one, maps to
            :data:`NEUTRAL`.

        """
        count = len(values)
        if count == 0:
            return ()
        if count == 1:
            return (CorpusNormalizer.NEUTRAL,)
        mean = sum(values) / count
        variance = sum((value - mean) ** 2 for value in values) / count
        if variance <= 0:
            return tuple(CorpusNormalizer.NEUTRAL for _ in values)
        deviation = math.sqrt(variance)
        scale = deviation * math.sqrt(2.0)
        return tuple(100.0 * 0.5 * (1.0 + math.erf((value - mean) / scale)) for value in values)

    @staticmethod
    def normalise_rows(rows: tuple[dict[str, float], ...]) -> tuple[dict[str, float], ...]:
        """Normalize every metric independently across *rows*.

        Each metric is normalized over the documents that actually carry it, so
        a document where Manner could not run loses one metric rather than
        losing the whole maxim. The cursors make that mapping explicit instead
        of relying on the documents being in a particular order.

        Args:
            rows: One mapping per document, metric name to raw value. A metric
                a document does not have is simply absent from its mapping.

        Returns:
            One mapping per document, metric name to percentile.

        """
        names = sorted({name for row in rows for name in row})
        scored = {
            name: list(CorpusNormalizer.normalise(tuple(row[name] for row in rows if name in row)))
            for name in names
        }
        cursors = dict.fromkeys(names, 0)
        normalised: list[dict[str, float]] = []
        for row in rows:
            percentiles: dict[str, float] = {}
            for name in row:
                percentiles[name] = scored[name][cursors[name]]
                cursors[name] += 1
            normalised.append(percentiles)
        return tuple(normalised)

    @staticmethod
    def aggregate(values: tuple[float, ...]) -> float | None:
        """Average one document's metric percentiles into a maxim index.

        Args:
            values: The document's percentiles for one maxim.

        Returns:
            The mean in 0-100, or ``None`` when the maxim produced no metric
            for this document — "not measured" is not "measured zero".

        """
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def aggregate_maxim(
        normalised: Mapping[str, tuple[dict[str, float], ...]], key: str, index: int
    ) -> float | None:
        """Return document *index*'s aggregate for the maxim stored under *key*.

        Args:
            normalised: Maxim name to the per-document percentile mappings, in
                document order.
            key: The maxim to aggregate, e.g. ``"quantity"``.
            index: The document's position within the corpus.

        Returns:
            The maxim index in 0-100, or ``None`` when nothing was measured.

        """
        return CorpusNormalizer.aggregate(tuple(normalised[key][index].values()))
