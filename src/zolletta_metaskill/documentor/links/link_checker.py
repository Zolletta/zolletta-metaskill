#!/usr/bin/env python3
"""Markdown Link Checker.

Scans markdown files for links and validates them:
- Local file references (does the file exist?)
- Anchor references within documents (does the heading exist?)
- Cross-document anchors (does the file and heading exist?)
- Relative path correctness
- Case sensitivity issues
- Image references
- Duplicate anchors

Scans the repository root (current directory). External URL validation is
controlled by ``documentation.check_external`` in ``settings.json``
(default: off). File enumeration is git-ignore aware.

Usage:
    python link_checker.py [--json] [--broken-only]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.links.external_url_checker import ExternalUrlChecker
from zolletta_metaskill.documentor.links.link_report_writer import LinkReportWriter
from zolletta_metaskill.documentor.structs.link_info import LinkInfo
from zolletta_metaskill.documentor.utils.documentation_files_finder import DocumentationFilesFinder
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings
from zolletta_metaskill.documentor.utils.fenced_content import FencedContent


class LinkChecker:
    """Markdown link checker: extracts, validates, and reports on links."""

    # --- Constants ---

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}

    # --- Link Extraction ---

    @staticmethod
    def classify_link(target: str) -> str:
        """Classify a link target by type."""
        if target.startswith(("http://", "https://", "ftp://", "mailto:")):
            return "external"
        if target.startswith("#"):
            return "anchor"

        # Check if it has an anchor
        file_part = target.split("#")[0] if "#" in target else target

        # Check for image
        ext = Path(file_part).suffix.lower() if file_part else ""
        if ext in LinkChecker.IMAGE_EXTENSIONS:
            return "image"

        if "#" in target:
            return "cross_doc_anchor"

        return "local_file"

    @staticmethod
    def _extract_images(line: str, i: int, rel_path: str, links: list[LinkInfo]) -> None:
        """Extract image links from markdown line."""
        img_link = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        for match in img_link.finditer(line):
            alt_text = match.group(1)
            target = match.group(2).strip()
            link_type = LinkChecker.classify_link(target)
            if link_type == "external":
                links.append(LinkInfo(rel_path, i, alt_text, target, "external"))
            else:
                links.append(LinkInfo(rel_path, i, alt_text, target, "image"))

    @staticmethod
    def _extract_markdown_links(line: str, i: int, rel_path: str, links: list[LinkInfo]) -> None:
        """Extract standard markdown links from line, excluding code spans."""
        md_link = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
        line_for_links = re.sub(r"``.+?``", "", line)
        line_for_links = re.sub(r"`[^`]+`", "", line_for_links)
        for match in md_link.finditer(line_for_links):
            start = match.start()
            if start > 0 and line_for_links[start - 1] == "!":
                continue
            text = match.group(1)
            target = match.group(2).strip()
            link_type = LinkChecker.classify_link(target)
            links.append(LinkInfo(rel_path, i, text, target, link_type))

    @staticmethod
    def _extract_html_and_refs(
        line: str, stripped: str, i: int, rel_path: str, links: list[LinkInfo]
    ) -> None:
        """Extract reference-style definitions and HTML links/images."""
        ref_def = re.compile(r"^\[([^\]]+)\]:\s+(.+)$")
        html_link = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)
        html_img = re.compile(r'<img\s+[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)

        ref_match = ref_def.match(stripped)
        if ref_match:
            ref_name = ref_match.group(1)
            target = ref_match.group(2).strip()
            link_type = LinkChecker.classify_link(target)
            links.append(LinkInfo(rel_path, i, ref_name, target, link_type))

        for match in html_link.finditer(line):
            target = match.group(1).strip()
            link_type = LinkChecker.classify_link(target)
            links.append(LinkInfo(rel_path, i, "", target, link_type))

        for match in html_img.finditer(line):
            target = match.group(1).strip()
            if not target.startswith(("http://", "https://")):
                links.append(LinkInfo(rel_path, i, "", target, "image"))

    @staticmethod
    def extract_links(file_path: str, rel_path: str) -> list[LinkInfo]:
        """Extract all links from a markdown file."""
        links: list[LinkInfo] = []
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            return links

        in_code_block = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if FencedContent.is_fence(line):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            LinkChecker._extract_images(line, i, rel_path, links)
            LinkChecker._extract_markdown_links(line, i, rel_path, links)
            LinkChecker._extract_html_and_refs(line, stripped, i, rel_path, links)

        return links

    # --- Heading / Anchor Extraction ---

    @staticmethod
    def extract_headings(file_path: str) -> set[str]:
        """Extract all heading anchors from a markdown file."""
        headings: set[str] = set()
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return headings

        for line in content.splitlines():
            match = re.match(r"^#{1,6}\s+(.+)", line)
            if match:
                heading_text = match.group(1).strip()
                slug = LinkChecker.slugify_heading(heading_text)
                headings.add(slug)

        return headings

    @staticmethod
    def slugify_heading(text: str) -> str:
        """Convert heading text to GitHub-style anchor slug."""
        text = text.lower()
        # Remove inline code backticks
        text = text.replace("`", "")
        # Remove special characters except hyphens and spaces
        text = re.sub(r"[^\w\s-]", "", text)
        # Replace spaces with hyphens
        text = re.sub(r"[\s]+", "-", text)
        # Remove leading/trailing hyphens
        text = text.strip("-")
        return text

    @staticmethod
    def find_duplicate_anchors(file_path: str) -> list[tuple[str, int]]:
        """Find headings that produce duplicate anchors."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            return []

        seen: dict[str, int] = {}
        duplicates = []
        in_code_block = False

        for i, line in enumerate(lines, 1):
            # Skip code blocks — # comments inside code blocks are not headings
            if FencedContent.is_fence(line):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            match = re.match(r"^#{1,6}\s+(.+)", line)
            if match:
                slug = LinkChecker.slugify_heading(match.group(1).strip())
                if slug in seen:
                    duplicates.append((slug, i))
                else:
                    seen[slug] = i

        return duplicates

    # --- Validation ---

    @staticmethod
    def _resolve_target_file(
        repo_path: str, source_file: str, file_part: str
    ) -> tuple[str | None, str | None]:
        """Resolve target file path, checking doc dir, repo root, and case mismatch."""
        source_dir = os.path.dirname(source_file)
        resolved = os.path.normpath(os.path.join(repo_path, source_dir, file_part))
        if os.path.exists(resolved):
            return resolved, None

        resolved_root = os.path.normpath(os.path.join(repo_path, file_part))
        if os.path.exists(resolved_root):
            return resolved_root, None

        case_match = LinkChecker._check_case_insensitive(resolved)
        if case_match:
            error = (
                f"File not found at '{file_part}' (case mismatch? "
                f"found '{os.path.relpath(case_match, repo_path)}')"
            )
            return None, error
        return None, f"File not found: '{file_part}'"

    @staticmethod
    def _validate_target_anchor(
        link: LinkInfo,
        resolved: str,
        anchor_ref: str,
        file_part: str,
        heading_cache: dict[str, set[str]],
    ) -> None:
        """Validate anchor inside an existing resolved target file."""
        if not resolved.endswith(DocumentationFilesFinder.DOC_EXTENSIONS):
            link.is_valid = True
            return

        headings = LinkChecker._get_headings(resolved, heading_cache)
        slug = LinkChecker.slugify_heading(anchor_ref)
        if slug in headings:
            link.is_valid = True
        else:
            link.is_valid = False
            link.error = f"File exists but anchor '#{anchor_ref}' not found in '{file_part}'"

    @staticmethod
    def validate_link(
        link: LinkInfo,
        repo_path: str,
        heading_cache: dict[str, set[str]],
        check_external: bool = False,
    ) -> None:
        """Validate a single link and set is_valid and error."""
        if link.link_type != "external" and (
            "{{" in link.link_target or link.source_file.endswith("_template.md")
        ):
            link.is_valid = None
            return

        if link.link_type == "external":
            if check_external:
                link.is_valid, link.error = ExternalUrlChecker.validate(link.link_target)
            else:
                link.is_valid = True
            return

        if link.link_type == "anchor":
            anchor = link.link_target.lstrip("#")
            source_full = os.path.join(repo_path, link.source_file)
            headings = LinkChecker._get_headings(source_full, heading_cache)
            slug = LinkChecker.slugify_heading(anchor)
            if slug in headings:
                link.is_valid = True
            else:
                link.is_valid = False
                link.error = f"Anchor '#{anchor}' not found in {link.source_file}"
            return

        target = link.link_target
        anchor_ref: str | None = None
        if "#" in target:
            file_part, anchor_ref = target.split("#", 1)
        else:
            file_part = target

        if not file_part and anchor_ref:
            source_full = os.path.join(repo_path, link.source_file)
            headings = LinkChecker._get_headings(source_full, heading_cache)
            slug = LinkChecker.slugify_heading(anchor_ref)
            if slug in headings:
                link.is_valid = True
            else:
                link.is_valid = False
                link.error = f"Anchor '#{anchor_ref}' not found"
            return

        resolved, err = LinkChecker._resolve_target_file(repo_path, link.source_file, file_part)
        if not resolved:
            link.is_valid = False
            link.error = err
            return

        if anchor_ref:
            LinkChecker._validate_target_anchor(
                link, resolved, anchor_ref, file_part, heading_cache
            )
        else:
            link.is_valid = True

    @staticmethod
    def _get_headings(file_path: str, cache: dict[str, set[str]]) -> set[str]:
        """Get headings for a file, using cache."""
        if file_path not in cache:
            cache[file_path] = LinkChecker.extract_headings(file_path)
        return cache[file_path]

    @staticmethod
    def _check_case_insensitive(path: str) -> str | None:
        """Check if a file exists with different case. Returns the actual path if found."""
        directory = os.path.dirname(path)
        filename = os.path.basename(path)

        if not os.path.isdir(directory):
            return None

        try:
            for entry in os.listdir(directory):
                if entry.lower() == filename.lower() and entry != filename:
                    return os.path.join(directory, entry)
        except (OSError, PermissionError):
            pass

        return None

    # --- File Discovery ---

    @staticmethod
    def find_markdown_files(path: str) -> list[str]:
        """Find all markdown files under a path (git-ignore aware).

        Every markdown file in the repository, not only the documentation: a
        link is broken wherever it is written, and ``documentation.4`` holds
        ``skills/`` to the same relative-link rule as ``docs/``. Narrowing this
        to the documentation inventory would drop the 60 links under
        ``skills/`` and report them clean, and a false all-clear is the one
        failure mode a link checker must not have. The *extensions* are shared
        with :class:`DocumentationFilesFinder`; the *scope* is deliberately
        wider than the documentation it defines.
        """
        p = Path(path)
        if p.is_file():
            if p.suffix.lower() in DocumentationFilesFinder.DOC_EXTENSIONS:
                return [path]
            return []
        extensions = set(DocumentationFilesFinder.DOC_EXTENSIONS)
        return [str(f) for f in ProjectConfig.iter_files(p, extensions)]

    # --- Main ---

    @staticmethod
    def run(
        repo_path: str,
        settings: dict[str, Any],
        cache_dir: Path,
        broken_only: bool = False,
        as_json: bool = False,
    ) -> str:
        """Run the link checker and write the JSON cache file.

        Returns the report string (Markdown or JSON depending on *as_json*).
        """
        check_external = bool(
            ProjectConfig.setting(settings, "documentation.check_external", False)
        )

        md_files = LinkChecker.find_markdown_files(repo_path)
        if not md_files:
            empty_data: dict[str, Any] = {"error": "No markdown files found", "summary": {}}
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "link_checker.json"
            cache_path.write_text(json.dumps(empty_data, indent=2, default=str) + "\n")
            if as_json:
                return json.dumps(empty_data, indent=2)
            return "No markdown files found."

        all_links: list[LinkInfo] = []
        heading_cache: dict[str, set[str]] = {}
        duplicate_anchors: dict[str, list[tuple[str, int]]] = {}

        for md_file in md_files:
            rel_path = os.path.relpath(md_file, repo_path)
            links = LinkChecker.extract_links(md_file, rel_path)
            all_links.extend(links)

            dups = LinkChecker.find_duplicate_anchors(md_file)
            if dups:
                duplicate_anchors[rel_path] = dups

        for link in all_links:
            LinkChecker.validate_link(link, repo_path, heading_cache, check_external=check_external)

        report = LinkReportWriter.generate_report(
            all_links,
            duplicate_anchors,
            broken_only=broken_only,
            as_json=as_json,
        )

        cache_data = LinkReportWriter.generate_report_data(
            all_links,
            duplicate_anchors,
            broken_only=broken_only,
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "link_checker.json"
        cache_path.write_text(json.dumps(cache_data, indent=2, default=str) + "\n")

        return report

    @staticmethod
    def main() -> int:
        """Entry point for the markdown link checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check markdown links for validity. Scans the repository "
            "root (current directory).",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        parser.add_argument("--broken-only", action="store_true", help="Only show broken links")

        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        repo_path = os.path.abspath(".")
        cache_dir = DocumentorSettings.resolve_cache_dir(settings)
        print(
            LinkChecker.run(
                repo_path,
                settings,
                cache_dir,
                broken_only=args.broken_only,
                as_json=args.json,
            )
        )
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(LinkChecker.main())
