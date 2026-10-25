"""Similarity — the TF-IDF cosine primitives shared by the maxim scorers.

Quantity, Quality and Relation all ask the same underlying question in
different words: how much do two pieces of text talk about the same thing.
They used to be three copies of a vectorizer plus a cosine call, which is three
places for the tokenizer, the empty-vocabulary guard and the "no terms at all"
fallback to drift apart. One class means a change to any of them is a change to
all three.

The vectorizer is deliberately language-neutral — no stop-word list, no stemmer
— because ``documentation.language`` may name a language whose stop words this
class has never heard of. Dropping English stop words from Spanish prose would
quietly change every score rather than fail loudly.
"""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Similarity:
    """Cosine similarity over TF-IDF vectors, with the degenerate cases handled.

    Every method answers ``0.0`` rather than raising when the texts carry no
    terms: an empty section is a parsing reality, not a programming error, and
    a scorer that aborts on one empty heading would report nothing at all for
    the whole corpus.
    """

    @staticmethod
    def _usable(texts: tuple[str, ...]) -> tuple[str, ...]:
        """Return the texts that carry at least one non-whitespace character.

        Args:
            texts: Candidate texts, possibly including empty ones.

        Returns:
            The non-blank subset, order preserved.

        """
        return tuple(text for text in texts if text.strip())

    @staticmethod
    def _pairwise(texts: tuple[str, ...]) -> list[list[float]]:
        """Return the full cosine matrix of *texts*.

        Args:
            texts: Texts to compare with each other.

        Returns:
            A square matrix of cosines, or ``[]`` when the texts share no
            vocabulary at all — TF-IDF raises on an empty vocabulary, and an
            empty matrix says the same thing without an exception.

        """
        usable = Similarity._usable(texts)
        if not usable:
            return []
        try:
            matrix: Any = TfidfVectorizer().fit_transform(list(usable))
            scores = cosine_similarity(matrix)
        except ValueError:
            return []
        return [list(map(float, row)) for row in scores.tolist()]

    @staticmethod
    def max_pairwise(texts: tuple[str, ...]) -> float:
        """Return the highest cosine between any two distinct texts.

        Args:
            texts: Texts to compare. Fewer than two non-blank texts cannot
                repeat anything.

        Returns:
            The strongest similarity found, ``0.0`` when nothing is similar
            enough to have terms in common.

        """
        scores = Similarity._pairwise(texts)
        if len(scores) < 2:
            return 0.0
        return max(row[j] for i, row in enumerate(scores) for j in range(len(row)) if i != j)

    @staticmethod
    def max_against(text: str, others: tuple[str, ...]) -> float:
        """Return the highest cosine between *text* and any of *others*.

        Args:
            text: The text being compared.
            others: The texts to compare it against.

        Returns:
            The strongest similarity found, ``0.0`` when there is nothing to
            compare against.

        """
        scores = Similarity._pairwise((text, *others))
        if len(scores) < 2:
            return 0.0
        return max(scores[0][1:])

    @staticmethod
    def pair_scores(lefts: tuple[str, ...], rights: tuple[str, ...]) -> tuple[float, ...]:
        """Return the cosine of each positional ``(left, right)`` pair.

        Both sides are vectorised by one fitted model, so a term carries the
        same weight on either side of a pair. Pairs where both halves are blank
        are skipped, which keeps the result aligned with the pairs that carry
        terms rather than padding it with meaningless zeros.

        Args:
            lefts: Left-hand texts.
            rights: Right-hand texts, positionally aligned with *lefts*.

        Returns:
            One cosine per comparable pair; shorter than *lefts* when pairs
            were skipped, and empty when nothing could be vectorised.

        """
        # pragma: no mutate start — strict=None and omitted strict act as strict=False
        pairs = tuple(
            (left, right)
            for left, right in zip(lefts, rights, strict=False)
            if left.strip() or right.strip()
        )
        # pragma: no mutate end
        if not pairs:
            return ()
        left_docs = [left for left, _ in pairs]
        right_docs = [right for _, right in pairs]
        try:
            matrix: Any = TfidfVectorizer().fit_transform(left_docs + right_docs)
            scores = cosine_similarity(matrix[: len(left_docs)], matrix[len(left_docs) :])
        except ValueError:
            return ()
        return tuple(float(scores[index, index]) for index in range(len(left_docs)))

    @staticmethod
    def cosine(left: str, right: str) -> float:
        """Return the cosine between exactly two texts.

        Args:
            left: One text.
            right: The other text.

        Returns:
            The cosine in ``0.0``-``1.0``, or ``0.0`` when the texts share no
            terms or either one is blank.

        """
        scores = Similarity.pair_scores((left,), (right,))
        return scores[0] if scores else 0.0
