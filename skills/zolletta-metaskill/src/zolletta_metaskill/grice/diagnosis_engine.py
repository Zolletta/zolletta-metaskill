"""DiagnosisEngine — read a document's four maxim indices as a recommendation."""

from __future__ import annotations

from zolletta_metaskill.grice.structs.diagnosis import Diagnosis
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores


class DiagnosisEngine:
    """A fixed rule table over the four sub-scores — nothing else is consulted.

    The rules are tried in order and the first that matches wins, so the
    same profile always reads the same way. The thresholds are on the
    corpus-relative 0-100 scale: ``LOW`` marks a maxim far below the median,
    ``HIGH`` one well above it.
    """

    MAXIMS = ("quantity", "quality", "relation", "manner")
    LOW = 20.0
    WEAK = 35.0
    HIGH = 60.0
    UNIFORM_CEILING = 40.0
    OUTLIER_RULES = {
        "uniform_deficit": (
            "Uniformly weak: every maxim is below the corpus",
            "Rework the page as a whole; compare it with a benchmark of the same group.",
        ),
        "dense_isolated": (
            "Dense text with low cohesion with the rest of the corpus",
            "Add cross-links to and from the pages it relates to.",
        ),
        "isolated": (
            "Isolated page: weakly connected to the rest of the corpus",
            "Link it from the pages of its flow and align its terminology with theirs.",
        ),
        "verbose_unreferenced": (
            "Verbose and poorly referenced",
            "Condense the redundant sections and check the internal references.",
        ),
        "weak_quantity": (
            "Information density out of line with the corpus (stub or wall of text)",
            "Fill in the missing content or split the page.",
        ),
        "weak_quality": (
            "Weakly verifiable: unresolved references, hedging or no anchors to the code",
            "Fix the links and anchors and back the claims with references.",
        ),
        "weak_relation": (
            "Below-median cohesion with the rest of the corpus",
            "Add internal links and align the terminology.",
        ),
        "weak_manner": (
            "Form problem: heading structure, lists or sentence length",
            "Review the heading hierarchy, the lists and the sentence length.",
        ),
        "unmeasured": ("No maxim could be measured", ""),
    }
    STRENGTHS = {
        "balanced": "Above the corpus on every maxim",
        "strong_quantity": "Well-balanced information density",
        "strong_quality": "Links and references resolve; claims are anchored",
        "strong_relation": "High semantic cohesion with the rest of the corpus",
        "strong_manner": "Clear structure and highly readable prose",
    }
    BENCHMARK_ACTION = "Use as a style model when refactoring the outliers."

    @staticmethod
    def diagnose(scores: MaximScores) -> Diagnosis:
        """Return the outlier reading of *scores*.

        Args:
            scores: The document's indices.

        Returns:
            The first matching rule's diagnosis.

        """
        measured = DiagnosisEngine.measured(scores)
        if not measured:
            return DiagnosisEngine._outlier("unmeasured", None)
        weakest = min(
            measured, key=lambda maxim: (measured[maxim], DiagnosisEngine.MAXIMS.index(maxim))
        )
        quantity = measured.get("quantity", 50.0)
        quality = measured.get("quality", 50.0)
        relation = measured.get("relation", 50.0)
        if len(measured) > 1 and max(measured.values()) < DiagnosisEngine.UNIFORM_CEILING:
            return DiagnosisEngine._outlier("uniform_deficit", weakest)
        if relation < DiagnosisEngine.LOW:
            code = "dense_isolated" if quantity > DiagnosisEngine.HIGH else "isolated"
            return DiagnosisEngine._outlier(code, "relation")
        if quantity > DiagnosisEngine.HIGH and quality < DiagnosisEngine.WEAK:
            return DiagnosisEngine._outlier("verbose_unreferenced", "quality")
        return DiagnosisEngine._outlier(f"weak_{weakest}", weakest)

    @staticmethod
    def strength(scores: MaximScores) -> Diagnosis:
        """Return the benchmark reading of *scores* — what makes it a model.

        Args:
            scores: The document's indices.

        Returns:
            ``balanced`` when every measured maxim is above ``HIGH``, otherwise
            the strongest maxim.

        """
        measured = DiagnosisEngine.measured(scores)
        if not measured:
            return Diagnosis("unmeasured", None, DiagnosisEngine.OUTLIER_RULES["unmeasured"][0], "")
        strongest = max(
            measured, key=lambda maxim: (measured[maxim], -DiagnosisEngine.MAXIMS.index(maxim))
        )
        if len(measured) > 1 and min(measured.values()) > DiagnosisEngine.HIGH:
            return Diagnosis(
                "balanced",
                strongest,
                DiagnosisEngine.STRENGTHS["balanced"],
                DiagnosisEngine.BENCHMARK_ACTION,
            )
        return DiagnosisEngine.strong(strongest)

    @staticmethod
    def strong(maxim: str) -> Diagnosis:
        """Return the benchmark reading of a document that leads on *maxim*.

        Args:
            maxim: One of :attr:`MAXIMS`.

        Returns:
            The ``strong_<maxim>`` diagnosis.

        """
        code = f"strong_{maxim}"
        return Diagnosis(
            code, maxim, DiagnosisEngine.STRENGTHS[code], DiagnosisEngine.BENCHMARK_ACTION
        )

    @staticmethod
    def measured(scores: MaximScores) -> dict[str, float]:
        """Return the maxims of *scores* that produced an index.

        Args:
            scores: The document's indices.

        Returns:
            Maxim name to index, omitting ``None``.

        """
        values = {
            "quantity": scores.quantity,
            "quality": scores.quality,
            "relation": scores.relation,
            "manner": scores.manner,
        }
        return {maxim: value for maxim, value in values.items() if value is not None}

    @staticmethod
    def _outlier(code: str, maxim: str | None) -> Diagnosis:
        """Build the outlier diagnosis for rule *code*.

        Args:
            code: Key of :attr:`OUTLIER_RULES`.
            maxim: The maxim the rule turned on.

        Returns:
            The diagnosis with the rule's wording.

        """
        summary, action = DiagnosisEngine.OUTLIER_RULES[code]
        return Diagnosis(code, maxim, summary, action)
