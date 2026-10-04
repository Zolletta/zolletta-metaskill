#!/usr/bin/env python3
"""Documentation Staleness Scorer.

Scores documentation freshness on a 0-100 scale using five weighted dimensions:
- Last Updated (20%): How recently the doc was modified
- Code-Doc Alignment (30%): Whether documented items still match code
- Link Health (15%): Percentage of links that resolve
- Completeness (20%): Whether expected sections exist
- Accuracy (15%): Version strings, file paths, verifiable facts

Scores the repository at the current directory. Behavior is configured in
``.zolletta-metaskill/settings.json`` under ``documentation``:

- ``staleness_threshold`` — fail (exit 1) when the aggregate score is below
  this value (not set → report-only)
- ``readme_focus`` — only score README files (default: false)
- ``readme_sections`` — required sections for completeness scoring
- ``diataxis_translations`` — path to a JSON file with translated Diátaxis
  headings/directory names for non-English documentation
- ``staleness_weights`` — per-dimension weight overrides
  (``last_updated``, ``code_doc_alignment``, ``link_health``,
  ``completeness``, ``accuracy``)

Usage:
    python doc_staleness_scorer.py [--json] [--quiet]

Exit code: 0 normally; 1 when ``staleness_threshold`` is configured and the
aggregate score falls below it (the only gate-keeping exception).

"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.doc_accuracy_scorer import DocAccuracyScorer
from zolletta_metaskill.documentor.doc_completeness_scorer import DocCompletenessScorer
from zolletta_metaskill.documentor.doc_staleness_report_writer import DocStalenessReportWriter


class DocStalenessScorer:
    """Documentation Staleness Scorer."""

    # --- Constants ---

    DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
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
    SKIP_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        "dist",
        "build",
        ".zolletta-metaskill",
    }

    DEFAULT_WEIGHTS = {
        "last_updated": 0.20,
        "code_doc_alignment": 0.30,
        "link_health": 0.15,
        "completeness": 0.20,
        "accuracy": 0.15,
    }

    DEFAULT_README_SECTIONS = [
        "installation",
        "usage",
        "api",
        "contributing",
        "license",
    ]

    SCORE_LABELS = {
        (90, 100): "excellent",
        (70, 90): "good",
        (50, 70): "stale",
        (30, 50): "critical",
        (-1, 30): "abandoned",
    }

    @staticmethod
    def _load_gitignore_patterns(repo_path: str) -> set[str]:
        """Load directory/file names from .gitignore that should be skipped.

        Only extracts simple entries (no negation, no wildcards) — patterns like
        `.zolletta-metaskill/`, `.devin/`, `.pytest_cache/` etc. This is intentionally
        conservative: complex glob patterns are left to git itself.
        """
        patterns: set[str] = set()
        gitignore = os.path.join(repo_path, ".gitignore")
        if not os.path.exists(gitignore):
            return patterns
        try:
            with open(gitignore, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Skip negation patterns and wildcard patterns
                    if line.startswith("!") or "*" in line or "?" in line:
                        continue
                    # Strip leading / (root-relative) and trailing /
                    name = line.lstrip("/").rstrip("/")
                    # Only take the last path component — we filter by dir/file name
                    if "/" in name:
                        name = name.split("/")[-1]
                    if name:
                        patterns.add(name)
        except OSError:
            pass
        return patterns

    @staticmethod
    def get_label(score: float) -> str:
        """Return a human-readable label for a staleness score."""
        for (low, high), label in DocStalenessScorer.SCORE_LABELS.items():
            if low < score <= high:
                return label
        return "unknown"

    # --- Git Helpers ---

    @staticmethod
    def run_git(repo_path: str, args: list[str], default: str = "") -> str:
        """Run a git command in the given repo and return stdout (or default on failure)."""
        try:
            result = subprocess.run(
                ["git", "-C", repo_path] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() if result.returncode == 0 else default
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return default

    @staticmethod
    def get_file_last_commit_date(repo_path: str, file_path: str) -> datetime | None:
        """Return the date of the last commit that touched ``file_path``."""
        output = DocStalenessScorer.run_git(
            repo_path, ["log", "-1", "--format=%aI", "--", file_path]
        )
        if output:
            try:
                return datetime.fromisoformat(output)
            except ValueError:
                pass
        return None

    @staticmethod
    def get_code_changes_since(repo_path: str, since_date: str, directory: str = "") -> int:
        """Count code commits since ``since_date`` in the given directory."""
        args = ["log", "--since", since_date, "--oneline", "--", directory or "."]
        output = DocStalenessScorer.run_git(repo_path, args)
        return len([line for line in output.splitlines() if line.strip()]) if output else 0

    @staticmethod
    def get_latest_tag(repo_path: str) -> str | None:
        """Return the latest git tag (without leading ``v``) or ``None``."""
        output = DocStalenessScorer.run_git(repo_path, ["describe", "--tags", "--abbrev=0"])
        return output.lstrip("v") if output else None

    # --- File Discovery ---

    @staticmethod
    def find_doc_files(repo_path: str) -> list[str]:
        """Discover all documentation files (Markdown, RST) in the repository."""
        skip = DocStalenessScorer.SKIP_DIRS | DocStalenessScorer._load_gitignore_patterns(repo_path)
        doc_files = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in skip]
            for f in files:
                if f in skip:
                    continue
                if Path(f).suffix.lower() in DocStalenessScorer.DOC_EXTENSIONS:
                    doc_files.append(os.path.relpath(os.path.join(root, f), repo_path))
        return sorted(doc_files)

    # --- Scoring Dimensions ---

    @staticmethod
    def score_last_updated(repo_path: str, doc_path: str) -> tuple[float, dict[str, Any]]:
        """Score based on how recently the doc was modified. 0-100."""
        last_modified = DocStalenessScorer.get_file_last_commit_date(repo_path, doc_path)
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

        # Score: 100 if updated today, decays over time
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
            if (
                Path(candidate).suffix.lower()
                in DocStalenessScorer.CODE_EXTENSIONS | DocStalenessScorer.DOC_EXTENSIONS
            ):
                file_refs.add(candidate)
        return file_refs

    @staticmethod
    def _score_fallback_alignment(repo_path: str, doc_path: str, details: dict[str, Any]) -> float:
        """Score alignment based on code changes in the doc directory."""
        doc_dir = os.path.dirname(doc_path)
        last_mod = DocStalenessScorer.get_file_last_commit_date(repo_path, doc_path)
        if not last_mod:
            return 70.0
        since = last_mod.strftime("%Y-%m-%d")
        changes = DocStalenessScorer.get_code_changes_since(repo_path, since, doc_dir)
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
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return 50.0, details

        file_refs = DocStalenessScorer._extract_alignment_refs(content)
        if not file_refs:
            fallback = DocStalenessScorer._score_fallback_alignment(repo_path, doc_path, details)
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
                headings = DocStalenessScorer._extract_headings(content)
                if DocStalenessScorer._slugify(anchor) in headings:
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
                with open(resolved, encoding="utf-8", errors="ignore") as f:
                    target_content = f.read()
                headings = DocStalenessScorer._extract_headings(target_content)
                if DocStalenessScorer._slugify(anchor) in headings:
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
            with open(full_path, encoding="utf-8", errors="ignore") as f:
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
            if DocStalenessScorer._validate_one_link(repo_path, doc_dir, content, link, details)
        )

        details["valid_links"] = valid
        return (valid / len(links)) * 100.0, details

    # --- Helpers ---

    @staticmethod
    def _extract_headings(content: str) -> set[str]:
        """Extract heading slugs from markdown content."""
        slugs: set[str] = set()
        for line in content.splitlines():
            match = re.match(r"^#{1,6}\s+(.+)", line)
            if match:
                slugs.add(DocStalenessScorer._slugify(match.group(1).strip()))
        return slugs

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert heading text to anchor slug (GitHub-style)."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s]+", "-", text)
        text = text.strip("-")
        return text

    # --- Scoring Engine ---

    @staticmethod
    def score_document(
        repo_path: str,
        doc_path: str,
        weights: dict[str, float],
        required_sections: list[str],
    ) -> dict[str, Any]:
        """Score a single documentation file across all dimensions."""
        updated_score, updated_details = DocStalenessScorer.score_last_updated(repo_path, doc_path)
        alignment_score, alignment_details = DocStalenessScorer.score_code_doc_alignment(
            repo_path, doc_path
        )
        link_score, link_details = DocStalenessScorer.score_link_health(repo_path, doc_path)
        completeness_score, completeness_details = DocCompletenessScorer.score_completeness(
            repo_path, doc_path, required_sections
        )
        accuracy_score, accuracy_details = DocAccuracyScorer.score_accuracy(
            repo_path, doc_path, latest_tag=DocStalenessScorer.get_latest_tag(repo_path)
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
            "label": DocStalenessScorer.get_label(weighted_total),
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

    # --- Main ---

    @staticmethod
    def _resolve_weights(settings: dict[str, Any]) -> dict[str, float]:
        """Build and normalize staleness dimension weights from settings."""
        weights = dict(DocStalenessScorer.DEFAULT_WEIGHTS)
        raw_weights = ProjectConfig.setting(settings, "documentation.staleness_weights", None)
        if isinstance(raw_weights, dict):
            for key in weights:
                value = raw_weights.get(key)
                if isinstance(value, (int, float)):
                    weights[key] = float(value)
        total_weight = sum(weights.values())
        if total_weight > 0:
            return {k: v / total_weight for k, v in weights.items()}
        return weights

    @staticmethod
    def _resolve_required_sections(settings: dict[str, Any]) -> list[str]:
        """Resolve required sections from settings or Diátaxis translations."""
        raw_sections = ProjectConfig.setting(settings, "documentation.readme_sections", None)
        if isinstance(raw_sections, list):
            return [s.strip() for s in raw_sections if isinstance(s, str)]

        translations_path = ProjectConfig.setting(
            settings, "documentation.diataxis_translations", None
        )
        if isinstance(translations_path, str) and translations_path:
            translations = DocCompletenessScorer.load_diataxis_translations(translations_path)
            DocCompletenessScorer.merge_translations(translations)
            translated_readme = translations.get("readme_sections")
            if translated_readme:
                return [s.strip() for s in translated_readme]
        return DocStalenessScorer.DEFAULT_README_SECTIONS

    @staticmethod
    def main() -> int:
        """Entry point for the documentation staleness scorer CLI."""
        parser = argparse.ArgumentParser(
            description="Score documentation freshness on a 0-100 scale for the "
            "repository at the current directory. Configure via "
            "documentation.* in .zolletta-metaskill/settings.json.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        parser.add_argument("--quiet", action="store_true", help="Only output score number")
        args = parser.parse_args()

        repo_path = os.path.abspath(".")
        settings = ProjectConfig.load_settings()
        weights = DocStalenessScorer._resolve_weights(settings)
        required_sections = DocStalenessScorer._resolve_required_sections(settings)

        readme_focus = bool(ProjectConfig.setting(settings, "documentation.readme_focus", False))
        doc_files = DocStalenessScorer.find_doc_files(repo_path)
        if readme_focus:
            doc_files = [d for d in doc_files if os.path.basename(d).lower().startswith("readme")]

        if not doc_files:
            if args.quiet:
                print("0")
            elif args.json:
                print(json.dumps({"error": "No documentation files found"}, indent=2))
            else:
                print("No documentation files found.")
            return 0

        scores = [
            DocStalenessScorer.score_document(repo_path, doc, weights, required_sections)
            for doc in doc_files
        ]
        aggregate = sum(s["total_score"] for s in scores) / len(scores) if scores else 0

        if args.quiet:
            print(f"{aggregate:.1f}")
        else:
            report = DocStalenessReportWriter.generate_report(scores, as_json=args.json)
            print(report)

        raw_threshold = ProjectConfig.setting(settings, "documentation.staleness_threshold", None)
        threshold = float(raw_threshold) if isinstance(raw_threshold, (int, float)) else None
        if threshold is not None and aggregate < threshold:
            if not args.quiet:
                print(
                    f"\nFAILED: Aggregate score {aggregate:.1f} is below threshold {threshold}",
                    file=sys.stderr,
                )
            return 1
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(DocStalenessScorer.main())
