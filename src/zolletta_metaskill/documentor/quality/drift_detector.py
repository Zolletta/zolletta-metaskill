"""DriftDetector finds documentation drift by comparing docs to git history."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zolletta_metaskill.documentor.quality.structs import DocContext, GitRunContext
from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.git_helper import GitHelper


class DriftDetector:
    """Detect drift issues for individual documentation files."""

    SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    @staticmethod
    def detect_drift_for_doc(
        git_ctx: GitRunContext,
        doc_settings: DocumentorSettings,
        file_rel_path: str,
        associated_code_dirs: list[str],
    ) -> list[dict[str, Any]]:
        """Detect drift issues for a single documentation file.

        Args:
            git_ctx: Run-scoped git facts (repo root, renames, current version).
            doc_settings: Resolved ``documentation.*`` configuration.
            file_rel_path: Repo-relative path of the documentation file.
            associated_code_dirs: Code directories associated with this doc.

        Returns:
            The drift issues found for this document.

        """
        issues: list[dict[str, Any]] = []
        repo_root = git_ctx.repo_root

        doc_modified = GitHelper.get_file_last_commit_date(repo_root, file_rel_path)
        if not doc_modified:
            issues.append(
                {
                    "file": file_rel_path,
                    "severity": "info",
                    "category": "temporal",
                    "description": "Documentation file has no git history (untracked or new)",
                    "fix_type": "manual",
                }
            )
            return issues

        doc_ctx = DocContext(
            file_rel_path=file_rel_path,
            refs=DocCodeMapper.extract_references_from_doc(repo_root, file_rel_path),
            since_date=doc_modified.strftime("%Y-%m-%d"),
            associated_code_dirs=tuple(associated_code_dirs),
        )

        issues.extend(DriftDetector._check_factual_drift(git_ctx, doc_ctx))
        issues.extend(DriftDetector._check_rename_drift(git_ctx, doc_settings, doc_ctx))
        if doc_settings.include_referential:
            issues.extend(DriftDetector._check_broken_refs(git_ctx, doc_ctx))
        issues.extend(DriftDetector._check_version_drift(git_ctx, doc_ctx))
        issues.extend(DriftDetector._check_temporal_drift(doc_ctx, doc_modified))

        basename = os.path.basename(file_rel_path).lower()
        if basename.startswith("readme") and not file_rel_path.startswith("docs"):
            issues.extend(DriftDetector.check_readme_structure(git_ctx, doc_ctx))

        return issues

    @staticmethod
    def _resolve_referenced_files(git_ctx: GitRunContext, doc_ctx: DocContext) -> list[str]:
        """Resolve the code files a doc references to repo-relative paths."""
        referenced_source_files: list[str] = []
        repo_root = git_ctx.repo_root
        doc_dir = doc_ctx.file_parent_dir
        for ref_file in doc_ctx.refs["files"]:
            if Path(ref_file).suffix.lower() not in DocCodeMapper.CODE_EXTENSIONS:
                continue
            resolved_doc = os.path.normpath(os.path.join(repo_root, doc_dir, ref_file))
            resolved_root = os.path.normpath(os.path.join(repo_root, ref_file))
            if os.path.exists(resolved_doc):
                referenced_source_files.append(os.path.relpath(resolved_doc, repo_root))
            elif os.path.exists(resolved_root):
                referenced_source_files.append(os.path.relpath(resolved_root, repo_root))
        return referenced_source_files

    @staticmethod
    def _check_factual_drift(git_ctx: GitRunContext, doc_ctx: DocContext) -> list[dict[str, Any]]:
        """Flag referenced source files that changed since the doc was updated."""
        repo_root = git_ctx.repo_root
        doc_path = doc_ctx.file_rel_path
        since_date = doc_ctx.since_date
        referenced_source_files = DriftDetector._resolve_referenced_files(git_ctx, doc_ctx)
        if referenced_source_files:
            changed_referenced: list[str] = []
            for src_file in referenced_source_files:
                changes = GitHelper.get_files_changed_since(repo_root, since_date, src_file)
                if changes:
                    changed_referenced.append(src_file)

            if changed_referenced:
                count = len(changed_referenced)
                if count > 5:
                    severity = "high"
                elif count > 2:
                    severity = "medium"
                else:
                    severity = "low"
                return [
                    {
                        "file": doc_path,
                        "severity": severity,
                        "category": "factual",
                        "description": (
                            f"{count} referenced source file(s) changed "
                            f"since doc was last updated: "
                            f"{', '.join(changed_referenced[:5])}"
                        ),
                        "fix_type": "semi",
                        "details": {"changed_files": changed_referenced, "change_count": count},
                    }
                ]
            return []
        return DriftDetector._check_factual_fallback(git_ctx, doc_ctx)

    @staticmethod
    def _check_factual_fallback(
        git_ctx: GitRunContext, doc_ctx: DocContext
    ) -> list[dict[str, Any]]:
        """Fallback factual check: flag heavy change in associated code dirs."""
        repo_root = git_ctx.repo_root
        doc_path = doc_ctx.file_rel_path
        since_date = doc_ctx.since_date
        total_code_changes = 0
        changed_dirs: set[str] = set()
        for code_dir in doc_ctx.associated_code_dirs:
            changes = GitHelper.get_files_changed_since(repo_root, since_date, code_dir)
            code_changes = [
                c
                for c in changes
                if Path(c["file"]).suffix.lower() in DocCodeMapper.CODE_EXTENSIONS
            ]
            total_code_changes += len(code_changes)
            if code_changes:
                changed_dirs.add(code_dir)

        if total_code_changes > 20:
            return [
                {
                    "file": doc_path,
                    "severity": "low",
                    "category": "factual",
                    "description": (
                        f"{total_code_changes} code files changed in "
                        f"associated directories since doc was last "
                        f"updated (no specific source files referenced "
                        f"in doc — needs review)"
                    ),
                    "fix_type": "manual",
                    "details": {
                        "changed_dirs": list(changed_dirs),
                        "change_count": total_code_changes,
                    },
                }
            ]
        return []

    @staticmethod
    def _check_rename_drift(
        git_ctx: GitRunContext,
        doc_settings: DocumentorSettings,
        doc_ctx: DocContext,
    ) -> list[dict[str, Any]]:
        """Flag references to renamed files (stale-name edge case, or broad rename)."""
        issues: list[dict[str, Any]] = []
        repo_root = git_ctx.repo_root
        doc_path = doc_ctx.file_rel_path
        doc_dir = doc_ctx.file_parent_dir
        for old_name, new_name in git_ctx.renames:
            old_base = os.path.basename(old_name)
            new_base = os.path.basename(new_name)
            if old_base in {os.path.basename(r) for r in doc_ctx.refs["files"]}:
                old_resolved = os.path.normpath(os.path.join(repo_root, doc_dir, old_name))
                old_resolved_root = os.path.normpath(os.path.join(repo_root, old_name))
                old_still_exists = os.path.exists(old_resolved) or os.path.exists(old_resolved_root)

                if old_still_exists:
                    issues.append(
                        {
                            "file": doc_path,
                            "severity": "high",
                            "category": "referential",
                            "description": (
                                f"References '{old_base}' which was renamed to '{new_base}', "
                                f"but '{old_base}' still exists as a different file "
                                "— reference may be stale"
                            ),
                            "fix_type": "manual",
                            "details": {"old_path": old_name, "new_path": new_name},
                        }
                    )
                elif doc_settings.include_referential:
                    issues.append(
                        {
                            "file": doc_path,
                            "severity": "medium",
                            "category": "referential",
                            "description": (
                                f"References '{old_base}' which was renamed to '{new_base}'"
                            ),
                            "fix_type": "auto",
                            "details": {"old_path": old_name, "new_path": new_name},
                        }
                    )
        return issues

    @staticmethod
    def _check_broken_refs(git_ctx: GitRunContext, doc_ctx: DocContext) -> list[dict[str, Any]]:
        """Flag references to files that no longer exist (referential mode only)."""
        issues: list[dict[str, Any]] = []
        repo_root = git_ctx.repo_root
        doc_path = doc_ctx.file_rel_path
        doc_dir = doc_ctx.file_parent_dir
        for ref_file in doc_ctx.refs["files"]:
            resolved = os.path.normpath(os.path.join(repo_root, doc_dir, ref_file))
            if not os.path.exists(resolved):
                resolved_root = os.path.normpath(os.path.join(repo_root, ref_file))
                if not os.path.exists(resolved_root):
                    issues.append(
                        {
                            "file": doc_path,
                            "severity": "medium",
                            "category": "referential",
                            "description": f"References non-existent file: {ref_file}",
                            "fix_type": "auto",
                        }
                    )
        return issues

    @staticmethod
    def _check_version_drift(git_ctx: GitRunContext, doc_ctx: DocContext) -> list[dict[str, Any]]:
        """Flag version strings older than the current project version."""
        issues: list[dict[str, Any]] = []
        doc_path = doc_ctx.file_rel_path
        refs = doc_ctx.refs
        current_version = git_ctx.current_version
        if current_version and refs["versions"]:
            for doc_version in refs["versions"]:
                if doc_version != current_version and DriftDetector._version_is_older(
                    doc_version, current_version
                ):
                    issues.append(
                        {
                            "file": doc_path,
                            "severity": "medium",
                            "category": "temporal",
                            "description": (
                                f"References version {doc_version}, current is {current_version}"
                            ),
                            "fix_type": "auto",
                            "details": {
                                "doc_version": doc_version,
                                "current_version": current_version,
                            },
                        }
                    )
        return issues

    @staticmethod
    def _check_temporal_drift(doc_ctx: DocContext, doc_modified: datetime) -> list[dict[str, Any]]:
        """Flag docs untouched for a long time."""
        doc_path = doc_ctx.file_rel_path
        since_date = doc_ctx.since_date
        now = datetime.now(UTC)
        if doc_modified.tzinfo is None:
            doc_modified_utc = doc_modified.replace(tzinfo=UTC)
        else:
            doc_modified_utc = doc_modified.astimezone(UTC)
        days_since = (now - doc_modified_utc).days
        if days_since > 365:
            return [
                {
                    "file": doc_path,
                    "severity": "high",
                    "category": "temporal",
                    "description": f"Documentation not updated in {days_since} days",
                    "fix_type": "manual",
                    "details": {"days_since_update": days_since, "last_updated": since_date},
                }
            ]
        if days_since > 180:
            return [
                {
                    "file": doc_path,
                    "severity": "medium",
                    "category": "temporal",
                    "description": f"Documentation not updated in {days_since} days",
                    "fix_type": "manual",
                    "details": {"days_since_update": days_since, "last_updated": since_date},
                }
            ]
        return []

    @staticmethod
    def check_readme_structure(git_ctx: GitRunContext, doc_ctx: DocContext) -> list[dict[str, Any]]:
        """Check if a README has expected sections."""
        issues: list[dict[str, Any]] = []
        doc_path = doc_ctx.file_rel_path
        full_path = os.path.join(git_ctx.repo_root, doc_path)
        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return issues

        headings: set[str] = set()
        for line in content.splitlines():
            match = re.match(r"^#{1,3}\s+(.+)", line)
            if match:
                headings.add(match.group(1).strip().lower())

        expected = {"installation", "usage", "license"}
        heading_words: set[str] = set()
        for h in headings:
            heading_words.update(h.split())

        for section in expected:
            if section not in heading_words and section not in headings:
                found = any(section in h for h in headings)
                if not found:
                    issues.append(
                        {
                            "file": doc_path,
                            "severity": "low",
                            "category": "structural",
                            "description": f"README missing recommended section: {section.title()}",
                            "fix_type": "manual",
                        }
                    )

        return issues

    @staticmethod
    def _parse_version_part(part: str) -> int:
        """Extract numeric value from a version part, stripping pre-release tags."""
        cleaned = re.sub(r"[^0-9].*$", "", part)
        try:
            return int(cleaned) if cleaned else 0
        except ValueError:  # pragma: no cover
            return 0

    @staticmethod
    def _version_is_older(v1: str, v2: str) -> bool:
        """Check if v1 is older than v2 using semantic version comparison."""
        try:
            parts1 = [DriftDetector._parse_version_part(x) for x in v1.split(".")]
            parts2 = [DriftDetector._parse_version_part(x) for x in v2.split(".")]
            max_len = max(len(parts1), len(parts2))
            while len(parts1) < max_len:
                parts1.append(0)
            while len(parts2) < max_len:
                parts2.append(0)
            return tuple(parts1) < tuple(parts2)
        except (ValueError, AttributeError, TypeError):  # pragma: no cover
            return False
