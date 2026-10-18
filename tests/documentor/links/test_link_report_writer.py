"""Tests for link_report_writer.py."""

from __future__ import annotations

import json
from collections.abc import Callable

from zolletta_metaskill.documentor.links.link_report_writer import LinkReportWriter
from zolletta_metaskill.documentor.structs.link_info import LinkInfo


class TestLinkReportWriter:
    # --- generate_report ---

    def test_empty_report_json(self) -> None:
        report = LinkReportWriter.generate_report([], {}, as_json=True)
        data = json.loads(report)
        assert data["summary"]["total_links"] == 0
        assert data["summary"]["broken"] == 0

    def test_with_broken_links_json(self) -> None:
        link = LinkInfo("README.md", 5, "text", "missing.md", "local_file")
        link.is_valid = False
        link.error = "File not found"
        report = LinkReportWriter.generate_report([link], {}, as_json=True)
        data = json.loads(report)
        assert data["summary"]["broken"] == 1
        assert len(data["broken_links"]) == 1

    def test_human_readable_contains_missing_md(self) -> None:
        link = LinkInfo("README.md", 5, "text", "missing.md", "local_file")
        link.is_valid = False
        link.error = "File not found"
        report = LinkReportWriter.generate_report([link], {}, as_json=False)
        assert "Link Check Report" in report
        assert "BROKEN LINKS" in report
        assert "missing.md" in report

    def test_no_issues_human_readable(self) -> None:
        link = LinkInfo("README.md", 5, "text", "guide.md", "local_file")
        link.is_valid = True
        report = LinkReportWriter.generate_report([link], {}, as_json=False)
        assert "No issues found" in report

    def test_broken_only_json(self) -> None:
        valid_link = LinkInfo("README.md", 1, "text", "guide.md", "local_file")
        valid_link.is_valid = True
        broken_link = LinkInfo("README.md", 5, "text", "missing.md", "local_file")
        broken_link.is_valid = False
        broken_link.error = "File not found"
        report = LinkReportWriter.generate_report(
            [valid_link, broken_link], {}, broken_only=True, as_json=True
        )
        data = json.loads(report)
        assert "all_links" not in data
        assert len(data["broken_links"]) == 1

    def test_duplicate_anchors_in_report(self) -> None:
        report = LinkReportWriter.generate_report(
            [], {"README.md": [("dup-anchor", 10)]}, as_json=False
        )
        assert "DUPLICATE ANCHORS" in report
        assert "dup-anchor" in report

    def test_duplicate_anchors_json(self) -> None:
        report = LinkReportWriter.generate_report(
            [], {"README.md": [("dup-anchor", 10)]}, as_json=True
        )
        data = json.loads(report)
        assert data["summary"]["duplicate_anchors"] == 1

    def test_type_breakdown_included(self) -> None:
        link1 = LinkInfo("README.md", 1, "text", "guide.md", "local_file")
        link1.is_valid = True
        link2 = LinkInfo("README.md", 2, "text", "https://example.com", "external")
        link2.is_valid = True
        report = LinkReportWriter.generate_report([link1, link2], {}, as_json=False)
        assert "LINK TYPE BREAKDOWN" in report

    def test_skipped_links_counted(self) -> None:
        link = LinkInfo("README.md", 1, "text", "https://example.com", "external")
        # is_valid is None (skipped)
        report = LinkReportWriter.generate_report([link], {}, as_json=True)
        data = json.loads(report)
        assert data["summary"]["skipped"] == 1

    # --- generate_report_data ---

    def test_generate_report_data_structure(self) -> None:
        link = LinkInfo("README.md", 1, "text", "guide.md", "local_file")
        link.is_valid = True
        data = LinkReportWriter.generate_report_data([link], {})
        assert data["summary"]["total_links"] == 1
        assert data["summary"]["valid"] == 1
        assert "all_links" in data

    # --- Text Output Contract ---

    def test_generate_report_matches_committed_contract(
        self,
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The rendered report is a byte-for-byte contract.

        The comparison is exact on purpose and must not be loosened to a
        substring or regex check: a legitimate change to the rendered report is
        ``pytest --update-fixtures`` followed by a reviewed diff. The trailing
        newline keeps the committed fixture a POSIX text file.

        """
        valid_link = LinkInfo("docs/guide.md", 3, "Home", "index.md", "local_file")
        valid_link.is_valid = True
        broken_link = LinkInfo("docs/guide.md", 12, "API reference", "missing.md", "local_file")
        broken_link.is_valid = False
        broken_link.error = "File not found"
        skipped_link = LinkInfo("docs/guide.md", 20, "Docs", "https://example.com", "external")
        report = LinkReportWriter.generate_report(
            [valid_link, broken_link, skipped_link],
            {"docs/guide.md": [("duplicate-anchor", 30)]},
            as_json=False,
        )
        text_contract("documentor/links/link_report_writer.txt", f"{report}\n")
