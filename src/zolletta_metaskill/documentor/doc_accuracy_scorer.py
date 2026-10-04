"""DocAccuracyScorer evaluates factual accuracy of documentation files.

Checks version strings, package manifest consistency, referenced file paths, and dates.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC, datetime
from typing import Any


class DocAccuracyScorer:
    """Evaluates factual accuracy of documentation files on a 0-100 scale."""

    @staticmethod
    def get_latest_tag(repo_path: str) -> str | None:
        """Get the latest git tag in the repository."""
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            tag = result.stdout.strip() if result.returncode == 0 else ""
            return tag if tag else None
        except (subprocess.SubprocessError, OSError):
            return None

    @staticmethod
    def score_accuracy(
        repo_path: str, doc_path: str, latest_tag: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Score based on accuracy of verifiable facts (versions, dates, paths). 0-100."""
        full_path = os.path.join(repo_path, doc_path)
        details: dict[str, Any] = {"checks": [], "issues": []}

        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return 50.0, details

        checks_passed = 0.0
        checks_total = 0

        # Check 1: Version strings match latest tag
        passed, total = DocAccuracyScorer._check_version_match(
            repo_path, content, details, latest_tag
        )
        checks_passed += passed
        checks_total += total

        # Check 2: Package version from manifests
        passed, total = DocAccuracyScorer._check_manifest_versions(repo_path, content, details)
        checks_passed += passed
        checks_total += total

        # Check 3: Referenced file paths exist
        passed, total = DocAccuracyScorer._check_file_paths(repo_path, doc_path, content, details)
        checks_passed += passed
        checks_total += total

        # Check 4: Dates are not in the future and not suspiciously old
        passed, total = DocAccuracyScorer._check_dates(content, details)
        checks_passed += passed
        checks_total += total

        if checks_total == 0:
            return 75.0, details

        return (checks_passed / checks_total) * 100.0, details

    @staticmethod
    def _version_refs(content: str) -> list[str]:
        """Extract version-like strings (``v1.2.3``, ``version: 1.2``) from content."""
        return re.findall(r"(?:v|version[:\s]*)(\d+\.\d+(?:\.\d+)?)", content, re.IGNORECASE)

    @staticmethod
    def _check_version_match(
        repo_path: str,
        content: str,
        details: dict[str, Any],
        latest_tag: str | None = None,
    ) -> tuple[float, int]:
        """Check that documented versions match the latest git tag."""
        git_version = (
            latest_tag if latest_tag is not None else DocAccuracyScorer.get_latest_tag(repo_path)
        )
        version_refs = DocAccuracyScorer._version_refs(content)
        if not git_version or not version_refs:
            return 0.0, 0
        if any(v == git_version for v in version_refs):
            details["checks"].append("version_match: PASS")
            return 1.0, 1
        details["checks"].append(
            f"version_match: FAIL (doc has {version_refs}, git has {git_version})"
        )
        details["issues"].append(f"Version mismatch: doc={version_refs}, git={git_version}")
        return 0.0, 1

    @staticmethod
    def _check_manifest_versions(
        repo_path: str, content: str, details: dict[str, Any]
    ) -> tuple[float, int]:
        """Check that documented versions match package manifests."""
        checks_passed = 0.0
        checks_total = 0
        for manifest in ["package.json", "pyproject.toml", "setup.py", "Cargo.toml"]:
            manifest_path = os.path.join(repo_path, manifest)
            if not os.path.exists(manifest_path):
                continue
            manifest_version = DocAccuracyScorer._extract_version_from_manifest(
                manifest_path, manifest
            )
            version_refs = DocAccuracyScorer._version_refs(content)
            if manifest_version and version_refs:
                checks_total += 1
                if manifest_version in version_refs:
                    checks_passed += 1
                    details["checks"].append(f"manifest_version ({manifest}): PASS")
                else:
                    details["checks"].append(
                        f"manifest_version ({manifest}): FAIL "
                        f"(doc={version_refs}, manifest={manifest_version})"
                    )
                    details["issues"].append(
                        f"Manifest version mismatch: {manifest} has {manifest_version}"
                    )
        return checks_passed, checks_total

    @staticmethod
    def _check_file_paths(
        repo_path: str, doc_path: str, content: str, details: dict[str, Any]
    ) -> tuple[float, int]:
        """Check that referenced file paths exist (partial credit)."""
        file_refs = re.findall(r"`([^\s`]+/[^\s`]+\.\w{1,5})`", content)
        if not file_refs:
            return 0.0, 0
        doc_dir = os.path.dirname(doc_path)
        existing_count = 0
        for ref in file_refs:
            resolved = os.path.normpath(os.path.join(repo_path, doc_dir, ref))
            if os.path.exists(resolved):
                existing_count += 1
            else:
                resolved_root = os.path.normpath(os.path.join(repo_path, ref))
                if os.path.exists(resolved_root):
                    existing_count += 1
        if existing_count == len(file_refs):
            details["checks"].append(f"file_paths: PASS ({existing_count}/{len(file_refs)})")
            return 1.0, 1
        ratio = existing_count / len(file_refs)
        details["checks"].append(f"file_paths: PARTIAL ({existing_count}/{len(file_refs)})")
        details["issues"].append(
            f"{len(file_refs) - existing_count} referenced file paths not found"
        )
        return ratio, 1

    @staticmethod
    def _check_dates(content: str, details: dict[str, Any]) -> tuple[float, int]:
        """Check that documented dates are not in the future."""
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
        dates_found = date_pattern.findall(content)
        if not dates_found:
            return 0.0, 0
        now = datetime.now(UTC)
        all_ok = True
        for date_str in dates_found:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                if d > now:
                    details["issues"].append(f"Future date found: {date_str}")
                    all_ok = False
            except ValueError:  # pragma: no cover
                pass
        if all_ok:
            details["checks"].append("dates: PASS")
            return 1.0, 1
        details["checks"].append("dates: FAIL")
        return 0.0, 1

    @staticmethod
    def _extract_version_from_manifest(path: str, filename: str) -> str | None:
        """Extract version string from a package manifest."""
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return None

        if filename == "package.json":
            match = re.search(r'"version"\s*:\s*"([^"]+)"', content)
            return match.group(1) if match else None
        if filename == "pyproject.toml":
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            return match.group(1) if match else None
        if filename == "setup.py":
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            return match.group(1) if match else None
        if filename == "Cargo.toml":
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            return match.group(1) if match else None
        return None
