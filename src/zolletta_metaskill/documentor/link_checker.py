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
import urllib.error
import urllib.request
from pathlib import Path

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.structs.link_info import LinkInfo


class LinkChecker:
    """Markdown link checker: extracts, validates, and reports on links."""

    # --- Constants ---

    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "dist", "build"}
    MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
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
            if stripped.startswith("```"):
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
            stripped = line.strip()
            # Skip code blocks — # comments inside code blocks are not headings
            if stripped.startswith("```"):
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
        if not resolved.endswith(tuple(LinkChecker.MARKDOWN_EXTENSIONS)):
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
                link.is_valid, link.error = LinkChecker.validate_external_url(link.link_target)
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

    @staticmethod
    def validate_external_url(url: str) -> tuple[bool, str | None]:
        """Validate an external URL with a HEAD request."""
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "zolletta-documentor/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 400:
                    return True, None
                return False, f"HTTP {resp.status}"  # pragma: no cover
        except urllib.error.HTTPError as e:
            # Some servers don't support HEAD
            if e.code == 405:
                try:
                    req = urllib.request.Request(url, method="GET")
                    req.add_header("User-Agent", "zolletta-documentor/1.0")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return (
                            resp.status < 400,
                            None if resp.status < 400 else f"HTTP {resp.status}",
                        )
                except Exception:
                    return False, f"HTTP {e.code}"
            return False, f"HTTP {e.code}"
        except urllib.error.URLError as e:
            return False, str(e.reason)
        except Exception as e:
            return False, str(e)

    # --- File Discovery ---

    @staticmethod
    def find_markdown_files(path: str) -> list[str]:
        """Find all markdown files under a path (git-ignore aware)."""
        p = Path(path)
        if p.is_file():
            if p.suffix.lower() in LinkChecker.MARKDOWN_EXTENSIONS:
                return [path]
            return []
        return [
            str(f)
            for f in ProjectConfig.iter_files(p, LinkChecker.MARKDOWN_EXTENSIONS)
            if not any(part in LinkChecker.SKIP_DIRS for part in f.parts)
        ]

    # --- Report ---

    @staticmethod
    def _report_broken(lines: list[str], broken: list[LinkInfo]) -> None:
        """Append broken links section grouped by file."""
        lines.append("BROKEN LINKS:")
        lines.append("-" * 60)
        by_file: dict[str, list[LinkInfo]] = {}
        for link in broken:
            by_file.setdefault(link.source_file, []).append(link)

        for source_file, file_links in sorted(by_file.items()):
            lines.append(f"\n  {source_file}:")
            for link in sorted(file_links, key=lambda lnk: lnk.line_number):
                lines.append(f"    Line {link.line_number}: [{link.link_text}]({link.link_target})")
                lines.append(f"      Error: {link.error}")
        lines.append("")

    @staticmethod
    def _report_dups(lines: list[str], duplicate_anchors: dict[str, list[tuple[str, int]]]) -> None:
        """Append duplicate anchors section."""
        lines.append("DUPLICATE ANCHORS:")
        lines.append("-" * 60)
        for file, dups in sorted(duplicate_anchors.items()):
            lines.append(f"\n  {file}:")
            for anchor, line_num in dups:
                lines.append(f"    Line {line_num}: duplicate anchor '#{anchor}'")
        lines.append("")

    @staticmethod
    def _report_type_breakdown(
        lines: list[str], all_links: list[LinkInfo], broken: list[LinkInfo]
    ) -> None:
        """Append link type breakdown section."""
        type_counts: dict[str, int] = {}
        broken_type_counts: dict[str, int] = {}
        for link in all_links:
            type_counts[link.link_type] = type_counts.get(link.link_type, 0) + 1
        for link in broken:
            broken_type_counts[link.link_type] = broken_type_counts.get(link.link_type, 0) + 1

        lines.append("LINK TYPE BREAKDOWN:")
        lines.append("-" * 40)
        for ltype in sorted(type_counts.keys()):
            broken_count = broken_type_counts.get(ltype, 0)
            total = type_counts[ltype]
            lines.append(f"  {ltype:<25} {total:>4} total, {broken_count:>4} broken")

    @staticmethod
    def generate_report(
        all_links: list[LinkInfo],
        duplicate_anchors: dict[str, list[tuple[str, int]]],
        broken_only: bool = False,
        as_json: bool = False,
    ) -> str:
        """Generate a link check report."""
        broken = [lnk for lnk in all_links if lnk.is_valid is False]
        valid = [lnk for lnk in all_links if lnk.is_valid is True]
        skipped = [lnk for lnk in all_links if lnk.is_valid is None]

        report_data = {
            "summary": {
                "total_links": len(all_links),
                "valid": len(valid),
                "broken": len(broken),
                "skipped": len(skipped),
                "duplicate_anchors": sum(len(v) for v in duplicate_anchors.values()),
            },
            "broken_links": [lnk.to_dict() for lnk in broken],
            "duplicate_anchors": {
                file: [{"anchor": anchor, "line": line} for anchor, line in dups]
                for file, dups in duplicate_anchors.items()
            },
        }

        if not broken_only:
            report_data["all_links"] = [lnk.to_dict() for lnk in all_links]

        if as_json:
            return json.dumps(report_data, indent=2, default=str)

        lines: list[str] = [
            "Link Check Report",
            "=" * 60,
            f"Total links:      {len(all_links)}",
            f"Valid:            {len(valid)}",
            f"Broken:           {len(broken)}",
            f"Skipped:          {len(skipped)}",
            f"Duplicate anchors: {sum(len(v) for v in duplicate_anchors.values())}",
            "",
        ]

        if broken:
            LinkChecker._report_broken(lines, broken)
        if duplicate_anchors:
            LinkChecker._report_dups(lines, duplicate_anchors)
        if not broken and not duplicate_anchors:
            lines.append("No issues found. All links are valid.")

        LinkChecker._report_type_breakdown(lines, all_links, broken)
        return "\n".join(lines)

    # --- Main ---

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
        check_external = bool(
            ProjectConfig.setting(settings, "documentation.check_external", False)
        )
        repo_path = os.path.abspath(".")

        # Find markdown files
        md_files = LinkChecker.find_markdown_files(repo_path)
        if not md_files:
            if args.json:
                print(json.dumps({"error": "No markdown files found"}, indent=2))
            else:
                print("No markdown files found.")
            return 0

        # Extract and validate links
        all_links: list[LinkInfo] = []
        heading_cache: dict[str, set[str]] = {}
        duplicate_anchors: dict[str, list[tuple[str, int]]] = {}

        for md_file in md_files:
            rel_path = os.path.relpath(md_file, repo_path)
            links = LinkChecker.extract_links(md_file, rel_path)
            all_links.extend(links)

            # Check for duplicate anchors
            dups = LinkChecker.find_duplicate_anchors(md_file)
            if dups:
                duplicate_anchors[rel_path] = dups

        # Validate all links
        for link in all_links:
            LinkChecker.validate_link(link, repo_path, heading_cache, check_external=check_external)

        # Report
        report = LinkChecker.generate_report(
            all_links,
            duplicate_anchors,
            broken_only=args.broken_only,
            as_json=args.json,
        )
        print(report)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(LinkChecker.main())
