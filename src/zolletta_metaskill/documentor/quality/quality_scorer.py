"""QualityScorer computes per-document freshness scores."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zolletta_metaskill.documentor.quality.doc_accuracy_scorer import DocAccuracyScorer
from zolletta_metaskill.documentor.quality.doc_completeness_scorer import DocCompletenessScorer
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class QualityScorer:
    """Scores documentation freshness on a 0-100 scale across five dimensions."""

    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".php",
    }

    SCORE_LABELS = {
        (90, 100): "excellent",
        (70, 90): "good",
        (50, 70): "stale",
        (30, 50): "critical",
        (-1, 30): "abandoned",
    }

    @staticmethod
    def get_label(score: float) -> str:
        """Return a human-readable label for a staleness score."""
        for (low, high), label in QualityScorer.SCORE_LABELS.items():
            if low < score <= high:
                return label
        return "unknown"

    @staticmethod
    def score_last_updated(repo_path: str, doc_path: str) -> tuple[float, dict[str, Any]]:
        """Score based on how recently the doc was modified. 0-100."""
        last_modified = GitHelper.get_file_last_commit_date(repo_path, doc_path)
        details: dict[str, Any] = {}

        if not last_modified:
            details["reason"] = "No git history found"
            return 50.0, details

        now = datetime.now(UTC)
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=UTC)

        days_ago = (now - last_modified).days
        details["last_modified"] = last_modified.strftime("%Y-%m-%d")
        details["days_ago"] = days_ago

        if days_ago <= 7:
            score = 100.0
        elif days_ago <= 30:
            score = 90.0 - (days_ago - 7) * 0.4
        elif days_ago <= 90:
            score = 80.0 - (days_ago - 30) * 0.5
        elif days_ago <= 180:
            score = 50.0 - (days_ago - 90) * 0.3
        elif days_ago <= 365:
            score = 25.0 - (days_ago - 180) * 0.1
        else:
            score = max(0.0, 10.0 - (days_ago - 365) * 0.02)

        return max(0.0, min(100.0, score)), details

    @staticmethod
    def _extract_alignment_refs(content: str) -> set[str]:
        """Extract markdown link and backtick file references."""
        file_refs: set[str] = set()
        for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content):
            target = match.group(2).split("#")[0]
            if not target.startswith(("http://", "https://", "mailto:")) and target:
                file_refs.add(target)
        for match in re.finditer(r"`([^\s`]+\.\w{1,5})`", content):
            candidate = match.group(1)
            if Path(candidate).suffix.lower() in QualityScorer.CODE_EXTENSIONS | {
                ".md",
                ".rst",
                ".txt",
                ".adoc",
            }:
                file_refs.add(candidate)
        return file_refs

    @staticmethod
    def _score_fallback_alignment(repo_path: str, doc_path: str, details: dict[str, Any]) -> float:
        """Score alignment based on code changes in the doc directory."""
        doc_dir = os.path.dirname(doc_path)
        last_mod = GitHelper.get_file_last_commit_date(repo_path, doc_path)
        if not last_mod:
            return 70.0
        since = last_mod.strftime("%Y-%m-%d")
        changes = GitHelper.get_code_changes_since(repo_path, since, doc_dir)
        details["code_changes_since_update"] = changes
        if changes == 0:
            return 100.0
        if changes < 5:
            return 80.0
        if changes < 20:
            return 60.0
        return 40.0

    @staticmethod
    def score_code_doc_alignment(repo_path: str, doc_path: str) -> tuple[float, dict[str, Any]]:
        """Score based on whether documented items still exist in code. 0-100."""
        full_path = os.path.join(repo_path, doc_path)
        details = {"referenced_files": 0, "existing_files": 0, "referenced_functions": 0}

        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
                content = f.read()
        except OSError:
            return 50.0, details

        file_refs = QualityScorer._extract_alignment_refs(content)
        if not file_refs:
            fallback = QualityScorer._score_fallback_alignment(repo_path, doc_path, details)
            return fallback, details

        doc_dir = os.path.dirname(doc_path)
        existing = 0
        for ref in file_refs:
            resolved = os.path.normpath(os.path.join(repo_path, doc_dir, ref))
            if os.path.exists(resolved):
                existing += 1
                continue
            resolved_root = os.path.normpath(os.path.join(repo_path, ref))
            if os.path.exists(resolved_root):
                existing += 1

        details["referenced_files"] = len(file_refs)
        details["existing_files"] = existing

        ratio = existing / len(file_refs)
        return ratio * 100.0, details

    @staticmethod
    def _validate_one_link(
        repo_path: str,
        doc_dir: str,
        content: str,
        link: str,
        details: dict[str, Any],
    ) -> bool:
        """Validate a single internal markdown link target."""
        anchor = None
        if "#" in link:
            file_part, anchor = link.split("#", 1)
        else:
            file_part = link

        if not file_part:
            if anchor:
                headings = QualityScorer._extract_headings(content)
                if QualityScorer._slugify(anchor) in headings:
                    return True
                details["broken_links"].append(f"#{anchor}")
                return False
            return True

        resolved = os.path.normpath(os.path.join(repo_path, doc_dir, file_part))
        if not os.path.exists(resolved):
            resolved = os.path.normpath(os.path.join(repo_path, file_part))

        if not os.path.exists(resolved):
            details["broken_links"].append(link)
            return False

        if anchor and resolved.endswith((".md", ".rst")):
            try:
                with open(resolved, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
                    target_content = f.read()
                headings = QualityScorer._extract_headings(target_content)
                if QualityScorer._slugify(anchor) in headings:
                    return True
                details["broken_links"].append(link)
                return False
            except OSError:  # pragma: no cover
                return True
        return True

    @staticmethod
    def score_link_health(repo_path: str, doc_path: str) -> tuple[float, dict[str, Any]]:
        """Score based on percentage of valid internal links. 0-100."""
        full_path = os.path.join(repo_path, doc_path)
        details: dict[str, Any] = {"total_links": 0, "valid_links": 0, "broken_links": []}

        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
                content = f.read()
        except OSError:
            return 100.0, details

        doc_dir = os.path.dirname(doc_path)
        links = [
            match.group(2)
            for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content)
            if not match.group(2).startswith(("http://", "https://", "mailto:"))
        ]

        if not links:
            return 100.0, details

        details["total_links"] = len(links)
        valid = sum(
            1
            for link in links
            if QualityScorer._validate_one_link(repo_path, doc_dir, content, link, details)
        )

        details["valid_links"] = valid
        return (valid / len(links)) * 100.0, details

    @staticmethod
    def _extract_headings(content: str) -> set[str]:
        """Extract heading slugs from markdown content."""
        slugs: set[str] = set()
        for line in content.splitlines():
            match = re.match(r"^#{1,6}\s+(.+)", line)
            if match:
                slugs.add(QualityScorer._slugify(match.group(1).strip()))
        return slugs

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert heading text to anchor slug (GitHub-style)."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s]+", "-", text)
        text = text.strip("-")
        return text

    @staticmethod
    def score_document(
        repo_path: str,
        doc_path: str,
        weights: dict[str, float],
        required_sections: list[str],
        quadrants: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Score a single documentation file across all dimensions.

        Args:
            repo_path: Absolute path to the repository root.
            doc_path: Repo-relative path of the document.
            weights: Normalised dimension weights.
            required_sections: README sections to look for outside quadrants.
            quadrants: Effective Diátaxis quadrant mapping, or ``None`` to use
                the built-in one.

        """
        updated_score, updated_details = QualityScorer.score_last_updated(repo_path, doc_path)
        alignment_score, alignment_details = QualityScorer.score_code_doc_alignment(
            repo_path, doc_path
        )
        link_score, link_details = QualityScorer.score_link_health(repo_path, doc_path)
        completeness_score, completeness_details = DocCompletenessScorer.score_completeness(
            repo_path, doc_path, required_sections, quadrants
        )
        accuracy_score, accuracy_details = DocAccuracyScorer.score_accuracy(
            repo_path, doc_path, latest_tag=GitHelper.get_latest_tag(repo_path)
        )

        weighted_total = (
            updated_score * weights["last_updated"]
            + alignment_score * weights["code_doc_alignment"]
            + link_score * weights["link_health"]
            + completeness_score * weights["completeness"]
            + accuracy_score * weights["accuracy"]
        )

        return {
            "file": doc_path,
            "total_score": round(weighted_total, 1),
            "label": QualityScorer.get_label(weighted_total),
            "dimensions": {
                "last_updated": {
                    "score": round(updated_score, 1),
                    "weight": weights["last_updated"],
                    "weighted": round(updated_score * weights["last_updated"], 1),
                    "details": updated_details,
                },
                "code_doc_alignment": {
                    "score": round(alignment_score, 1),
                    "weight": weights["code_doc_alignment"],
                    "weighted": round(alignment_score * weights["code_doc_alignment"], 1),
                    "details": alignment_details,
                },
                "link_health": {
                    "score": round(link_score, 1),
                    "weight": weights["link_health"],
                    "weighted": round(link_score * weights["link_health"], 1),
                    "details": link_details,
                },
                "completeness": {
                    "score": round(completeness_score, 1),
                    "weight": weights["completeness"],
                    "weighted": round(completeness_score * weights["completeness"], 1),
                    "details": completeness_details,
                },
                "accuracy": {
                    "score": round(accuracy_score, 1),
                    "weight": weights["accuracy"],
                    "weighted": round(accuracy_score * weights["accuracy"], 1),
                    "details": accuracy_details,
                },
            },
        }

    @staticmethod
    def _resolve_diataxis_quadrants(translations_path: str | None) -> dict[str, dict[str, Any]]:
        """Resolve the effective Diátaxis quadrant mapping from a translations path.

        Takes the already-resolved path rather than *settings*, so the
        ``documentation.diataxis_translations`` key is read exactly once per run —
        by :meth:`DocumentorSettings.from_settings` — instead of independently
        here and for the required sections.

        Pure: returns a fresh mapping and never mutates
        ``DocCompletenessScorer.DIATAXIS_QUADRANTS``. When *translations_path* is
        unset the built-in mapping is returned as-is, so the default path costs no
        extra file read.

        Args:
            translations_path: Configured translations file, or ``None``.

        Returns:
            The effective quadrant mapping.

        """
        if translations_path:
            translations = DocCompletenessScorer.load_diataxis_translations(translations_path)
            return DocCompletenessScorer.merged_quadrants(translations)
        return DocCompletenessScorer.DIATAXIS_QUADRANTS
