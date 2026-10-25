"""QualityMetrics — whether the document's claims can be checked.

Grice's Quality maxim asks a writer not to say what they cannot support. In
documentation the support is usually a reference: a link, a path, a file name.
A document dense with references that all resolve is corroborated; one whose
references are broken asks the reader to trust it, and has no way to earn that
trust back.

Only resolvable references count. External URLs are excluded because validating
them needs the network and a network answer is not deterministic — the same
repository would score differently on two machines, or on one machine twice.
"""

from __future__ import annotations

import os

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.documentor.links.link_checker import LinkChecker
from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper
from zolletta_metaskill.grice.similarity import Similarity
from zolletta_metaskill.grice.structs.document_features import DocumentFeatures


class QualityMetrics:
    """Score one document on how well its references and vocabulary hold up."""

    FINDING_CATEGORY = "grice"
    LINK_SEVERITY = "medium"
    NON_FILE_PREFIXES = ("#", "/", "http://", "https://", "ftp://", "mailto:")

    @staticmethod
    def evaluate(
        features: DocumentFeatures, repo_path: str, source_text: str
    ) -> tuple[dict[str, float], list[Finding]]:
        """Measure Quality for one document.

        Args:
            features: The document being scored.
            repo_path: Absolute path of the repository root, used to resolve
                references and to hand :class:`LinkChecker` a working directory.
            source_text: Concatenated source files the project ships. Lexical
                alignment compares the document against the vocabulary of the
                code it documents.

        Returns:
            The raw metric values on a 0-100 scale, and one finding per
            unresolved internal link. Missing file references are scored but
            not reported: the reference extractor returns a set without line
            numbers, and a finding anchored on line 1 would point nowhere.

        """
        link_resolution, findings = QualityMetrics._links(features, repo_path)
        metrics = {
            "link_resolution": link_resolution,
            "reference_resolution": QualityMetrics._reference_resolution(features, repo_path),
            "lexical_alignment": 100.0 * Similarity.cosine(features.prose, source_text),
        }
        return metrics, findings

    @staticmethod
    def _links(features: DocumentFeatures, repo_path: str) -> tuple[float, list[Finding]]:
        """Validate every internal link in the document.

        Args:
            features: The document being scored.
            repo_path: Repository root.

        Returns:
            The percentage of internal links that resolve, and one finding per
            link that does not. A document with no internal links scores
            ``100``: nothing in it is broken, which is a weak signal but the
            honest one.

        """
        full_path = os.path.join(repo_path, features.path)
        headings: dict[str, set[str]] = {}
        verifiable = [
            link
            for link in LinkChecker.extract_links(full_path, features.path)
            if link.link_type != "external"
        ]
        for link in verifiable:
            LinkChecker.validate_link(link, repo_path, headings)
        if not verifiable:
            return 100.0, []
        broken = [link for link in verifiable if link.is_valid is False]
        # pragma: no mutate start — a broken link always carries link.error, so the
        # or-True and else-literal mutants in the description suffix are unobservable
        findings = [
            Finding(
                file=link.source_file,
                line=link.line_number,
                category=QualityMetrics.FINDING_CATEGORY,
                severity=QualityMetrics.LINK_SEVERITY,
                description=(
                    f"internal link '{link.link_target}' does not resolve"
                    f"{': ' + link.error if link.error else ''}"
                ),
            )
            for link in broken
        ]
        # pragma: no mutate end
        return 100.0 * (len(verifiable) - len(broken)) / len(verifiable), findings

    @staticmethod
    def _reference_resolution(features: DocumentFeatures, repo_path: str) -> float:
        """Measure how many of the document's file references exist on disk.

        Args:
            features: The document being scored.
            repo_path: Repository root.

        Returns:
            The percentage of references that resolve, or ``100.0`` when the
            document references no files.

        """
        references = DocCodeMapper.extract_references_from_doc(repo_path, features.path)["files"]
        targets = [target for target in references if QualityMetrics._is_file_reference(target)]
        if not targets:
            return 100.0
        resolved = sum(
            1 for target in targets if QualityMetrics._resolves(repo_path, features.path, target)
        )
        return 100.0 * resolved / len(targets)

    @staticmethod
    def _is_file_reference(target: str) -> bool:
        """Return whether *target* names a repository-relative file.

        Args:
            target: A reference extracted from the document.

        Returns:
            ``True`` for a relative path, ``False`` for an anchor, an absolute
            path or a URL — none of which a documentation scan can resolve
            without the network or a guess about the writer's machine.

        """
        return bool(target.strip()) and not target.startswith(QualityMetrics.NON_FILE_PREFIXES)

    @staticmethod
    def _resolves(repo_path: str, doc_path: str, target: str) -> bool:
        """Return whether *target* exists from any of the plausible roots.

        A reference is written relative to whichever directory the author had in
        mind: the repository root, the document's own directory, or the source
        tree. All three are checked, because a false "unresolved" is a finding
        against a document that is correct.

        Args:
            repo_path: Repository root.
            doc_path: Repository-relative path of the referencing document.
            target: The reference to resolve.

        Returns:
            ``True`` when the path exists from at least one root.

        """
        candidates = (
            os.path.join(repo_path, target),
            os.path.join(repo_path, os.path.dirname(doc_path), target),
            os.path.join(repo_path, "src", target),
        )
        return any(os.path.exists(candidate) for candidate in candidates)
