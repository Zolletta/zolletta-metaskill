"""Tests for link_checker.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.link_checker import (
    LinkInfo,
    _check_case_insensitive,
    _get_headings,
    classify_link,
    extract_headings,
    extract_links,
    find_duplicate_anchors,
    find_markdown_files,
    generate_report,
    main,
    slugify_heading,
    validate_external_url,
    validate_link,
)

# ---------------------------------------------------------------------------
# LinkInfo
# ---------------------------------------------------------------------------


class TestLinkInfo:
    def test_init(self) -> None:
        link = LinkInfo("README.md", 5, "text", "target.md", "local_file")
        assert link.source_file == "README.md"
        assert link.line_number == 5
        assert link.link_text == "text"
        assert link.link_target == "target.md"
        assert link.link_type == "local_file"
        assert link.is_valid is None
        assert link.error is None

    def test_to_dict(self) -> None:
        link = LinkInfo("README.md", 5, "text", "target.md", "local_file")
        link.is_valid = True
        d = link.to_dict()
        assert d["source_file"] == "README.md"
        assert d["line"] == 5
        assert d["text"] == "text"
        assert d["target"] == "target.md"
        assert d["type"] == "local_file"
        assert d["valid"] is True
        assert d["error"] is None


# ---------------------------------------------------------------------------
# classify_link
# ---------------------------------------------------------------------------


class TestClassifyLink:
    def test_http(self) -> None:
        assert classify_link("http://example.com") == "external"

    def test_https(self) -> None:
        assert classify_link("https://example.com") == "external"

    def test_ftp(self) -> None:
        assert classify_link("ftp://example.com") == "external"

    def test_mailto(self) -> None:
        assert classify_link("mailto:test@test.com") == "external"

    def test_anchor(self) -> None:
        assert classify_link("#section") == "anchor"

    def test_local_file(self) -> None:
        assert classify_link("guide.md") == "local_file"

    def test_image(self) -> None:
        assert classify_link("image.png") == "image"

    def test_cross_doc_anchor(self) -> None:
        assert classify_link("guide.md#section") == "cross_doc_anchor"

    def test_image_with_anchor(self) -> None:
        assert classify_link("image.png#fragment") == "image"


# ---------------------------------------------------------------------------
# extract_links
# ---------------------------------------------------------------------------


class TestExtractLinks:
    def test_markdown_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("See [guide](guide.md) for more.", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 1
        assert links[0].link_text == "guide"
        assert links[0].link_target == "guide.md"
        assert links[0].link_type == "local_file"

    def test_external_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("Visit [site](https://example.com).", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 1
        assert links[0].link_type == "external"

    def test_anchor_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("See [section](#section).", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 1
        assert links[0].link_type == "anchor"

    def test_image_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("![alt text](image.png)", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 1
        assert links[0].link_type == "image"

    def test_external_image_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("![alt](https://example.com/img.png)", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 1
        assert links[0].link_type == "external"

    def test_reference_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("[ref]: guide.md\n\nSee [text][ref].", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        # The ref definition is captured; the [text][ref] usage is not matched by md_link
        ref_links = [lnk for lnk in links if lnk.link_text == "ref"]
        assert len(ref_links) == 1
        assert ref_links[0].link_target == "guide.md"

    def test_html_link(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text('<a href="guide.md">Guide</a>', encoding="utf-8")
        links = extract_links(str(f), "test.md")
        html_links = [lnk for lnk in links if lnk.link_target == "guide.md"]
        assert len(html_links) == 1

    def test_html_image(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text('<img src="image.png" alt="img">', encoding="utf-8")
        links = extract_links(str(f), "test.md")
        img_links = [lnk for lnk in links if lnk.link_type == "image"]
        assert len(img_links) == 1

    def test_html_image_external_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text('<img src="https://example.com/img.png">', encoding="utf-8")
        links = extract_links(str(f), "test.md")
        # External HTML images are not added as image type
        img_links = [lnk for lnk in links if lnk.link_type == "image"]
        assert len(img_links) == 0

    def test_code_block_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("```\n[link](guide.md)\n```", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 0

    def test_multiple_links(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("[a](a.md) and [b](b.md)", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert len(links) == 2

    def test_unreadable_file(self, tmp_path: Path) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            links = extract_links(str(tmp_path / "test.md"), "test.md")
        assert links == []

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("", encoding="utf-8")
        assert extract_links(str(f), "test.md") == []

    def test_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("Line 1\n[a](a.md)\nLine 3\n[b](b.md)\n", encoding="utf-8")
        links = extract_links(str(f), "test.md")
        assert links[0].line_number == 2
        assert links[1].line_number == 4


# ---------------------------------------------------------------------------
# slugify_heading
# ---------------------------------------------------------------------------


class TestSlugifyHeading:
    def test_simple(self) -> None:
        assert slugify_heading("Hello World") == "hello-world"

    def test_special_chars(self) -> None:
        assert slugify_heading("Hello, World!") == "hello-world"

    def test_code_backticks(self) -> None:
        assert slugify_heading("Hello `code`") == "hello-code"

    def test_multiple_spaces(self) -> None:
        assert slugify_heading("Hello   World") == "hello-world"

    def test_leading_trailing_hyphens(self) -> None:
        assert slugify_heading("-Hello-") == "hello"

    def test_empty(self) -> None:
        assert slugify_heading("") == ""


# ---------------------------------------------------------------------------
# extract_headings
# ---------------------------------------------------------------------------


class TestExtractHeadings:
    def test_simple_headings(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Title\n## Section\n### Sub", encoding="utf-8")
        headings = extract_headings(str(f))
        assert "title" in headings
        assert "section" in headings
        assert "sub" in headings

    def test_no_headings(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("Just text.", encoding="utf-8")
        assert extract_headings(str(f)) == set()

    def test_unreadable_file(self, tmp_path: Path) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            assert extract_headings(str(tmp_path / "test.md")) == set()

    def test_max_six_hashes(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("###### Deep\n####### Too deep", encoding="utf-8")
        headings = extract_headings(str(f))
        assert "deep" in headings
        # 7 hashes is not a valid heading (only up to 6)
        assert "too-deep" not in headings


# ---------------------------------------------------------------------------
# find_duplicate_anchors
# ---------------------------------------------------------------------------


class TestFindDuplicateAnchors:
    def test_no_duplicates(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Title\n## Section", encoding="utf-8")
        assert find_duplicate_anchors(str(f)) == []

    def test_duplicates(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Title\n# Title", encoding="utf-8")
        dups = find_duplicate_anchors(str(f))
        assert len(dups) == 1
        assert dups[0][0] == "title"
        assert dups[0][1] == 2

    def test_unreadable_file(self, tmp_path: Path) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            assert find_duplicate_anchors(str(tmp_path / "test.md")) == []

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("", encoding="utf-8")
        assert find_duplicate_anchors(str(f)) == []


# ---------------------------------------------------------------------------
# validate_link
# ---------------------------------------------------------------------------


class TestValidateLink:
    def test_external_skip(self) -> None:
        link = LinkInfo("README.md", 1, "text", "https://example.com", "external")
        validate_link(link, "/repo", {}, check_external=False)
        assert link.is_valid is True

    def test_external_check_success(self) -> None:
        link = LinkInfo("README.md", 1, "text", "https://example.com", "external")
        with patch(
            "zolletta_metaskill.documentor.link_checker.validate_external_url",
            return_value=(True, None),
        ):
            validate_link(link, "/repo", {}, check_external=True)
        assert link.is_valid is True

    def test_external_check_failure(self) -> None:
        link = LinkInfo("README.md", 1, "text", "https://example.com", "external")
        with patch(
            "zolletta_metaskill.documentor.link_checker.validate_external_url",
            return_value=(False, "HTTP 404"),
        ):
            validate_link(link, "/repo", {}, check_external=True)
        assert link.is_valid is False
        assert link.error == "HTTP 404"

    def test_anchor_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Section\n", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "#section", "anchor")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_anchor_invalid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Other\n", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "#nonexistent", "anchor")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is False
        assert "not found" in link.error

    def test_local_file_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "guide.md").write_text("Guide", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "guide.md", "local_file")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_local_file_invalid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "nonexistent.md", "local_file")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is False
        assert "not found" in link.error

    def test_local_file_from_repo_root(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "guide.md").write_text("Guide", encoding="utf-8")
        link = LinkInfo("docs/test.md", 1, "text", "guide.md", "local_file")
        # Create docs dir and the test file there
        (tmp_path / "docs").mkdir()
        f2 = tmp_path / "docs" / "test.md"
        f2.write_text("# Test", encoding="utf-8")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_cross_doc_anchor_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "guide.md").write_text("# Section\n", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "guide.md#section", "cross_doc_anchor")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_cross_doc_anchor_invalid_anchor(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "guide.md").write_text("# Other\n", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "guide.md#nonexistent", "cross_doc_anchor")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is False
        assert "anchor" in link.error.lower()

    def test_cross_doc_anchor_non_markdown_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "data.txt").write_text("data", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "data.txt#section", "cross_doc_anchor")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_image_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        link = LinkInfo("test.md", 1, "text", "image.png", "image")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_image_invalid(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "nonexistent.png", "image")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is False

    def test_case_sensitivity_mismatch(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        (tmp_path / "Guide.md").write_text("Guide", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "guide.md", "local_file")
        # On case-insensitive filesystems (macOS), os.path.exists returns True
        # for both cases. Mock it to simulate a case-sensitive filesystem.
        real_exists = os.path.exists

        def mock_exists(path: str) -> bool:
            # Only return True for the exact case "Guide.md", not "guide.md"
            if path.endswith("guide.md") and not path.endswith("Guide.md"):
                return False
            return real_exists(path)

        with patch("os.path.exists", side_effect=mock_exists):
            validate_link(link, str(tmp_path), {})
        assert link.is_valid is False
        assert "case" in link.error.lower()

    def test_empty_file_part_with_anchor(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Section\n", encoding="utf-8")
        link = LinkInfo("test.md", 1, "text", "#section", "cross_doc_anchor")
        validate_link(link, str(tmp_path), {})
        assert link.is_valid is True

    def test_heading_cache_used(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Section\n", encoding="utf-8")
        cache: dict[str, set[str]] = {str(f): {"section"}}
        link = LinkInfo("test.md", 1, "text", "#section", "anchor")
        validate_link(link, str(tmp_path), cache)
        assert link.is_valid is True


# ---------------------------------------------------------------------------
# _get_headings
# ---------------------------------------------------------------------------


class TestGetHeadings:
    def test_caches_result(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Title\n", encoding="utf-8")
        cache: dict[str, set[str]] = {}
        result1 = _get_headings(str(f), cache)
        assert "title" in result1
        assert str(f) in cache
        result2 = _get_headings(str(f), cache)
        assert result2 is result1


# ---------------------------------------------------------------------------
# _check_case_insensitive
# ---------------------------------------------------------------------------


class TestCheckCaseInsensitive:
    def test_finds_match(self, tmp_path: Path) -> None:
        (tmp_path / "Guide.md").write_text("guide", encoding="utf-8")
        result = _check_case_insensitive(str(tmp_path / "guide.md"))
        assert result is not None
        assert "Guide.md" in result

    def test_no_match(self, tmp_path: Path) -> None:
        (tmp_path / "other.md").write_text("other", encoding="utf-8")
        assert _check_case_insensitive(str(tmp_path / "guide.md")) is None

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        assert _check_case_insensitive(str(tmp_path / "nonexistent" / "guide.md")) is None

    def test_permission_error(self, tmp_path: Path) -> None:
        (tmp_path / "Guide.md").write_text("guide", encoding="utf-8")
        with patch("os.listdir", side_effect=PermissionError("denied")):
            assert _check_case_insensitive(str(tmp_path / "guide.md")) is None


# ---------------------------------------------------------------------------
# validate_external_url
# ---------------------------------------------------------------------------


class TestValidateExternalUrl:
    def test_success(self) -> None:
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            valid, error = validate_external_url("https://example.com")
        assert valid is True
        assert error is None

    def test_http_error_405_fallback_get(self) -> None:
        import urllib.error
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                urllib.error.HTTPError("url", 405, "Method Not Allowed", {}, None),
                mock_resp,
            ]
            valid, error = validate_external_url("https://example.com")
        assert valid is True

    def test_http_error_404(self) -> None:
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None),
        ):
            valid, error = validate_external_url("https://example.com")
        assert valid is False
        assert "404" in error

    def test_url_error(self) -> None:
        import urllib.error

        err = urllib.error.URLError("connection refused")
        err.reason = "connection refused"
        with patch("urllib.request.urlopen", side_effect=err):
            valid, error = validate_external_url("https://example.com")
        assert valid is False
        assert "connection refused" in error

    def test_generic_exception(self) -> None:
        with patch("urllib.request.urlopen", side_effect=Exception("boom")):
            valid, error = validate_external_url("https://example.com")
        assert valid is False
        assert "boom" in error

    def test_405_get_fallback_failure(self) -> None:
        import urllib.error

        # Both HEAD and GET fallback raise 405
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 405, "Method Not Allowed", {}, None),
        ):
            valid, error = validate_external_url("https://example.com")
        assert valid is False


# ---------------------------------------------------------------------------
# find_markdown_files
# ---------------------------------------------------------------------------


class TestFindMarkdownFiles:
    def test_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("a", encoding="utf-8")
        (tmp_path / "b.markdown").write_text("b", encoding="utf-8")
        (tmp_path / "c.txt").write_text("c", encoding="utf-8")
        result = find_markdown_files(str(tmp_path))
        assert any("a.md" in f for f in result)
        assert any("b.markdown" in f for f in result)
        assert all("c.txt" not in f for f in result)

    def test_single_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Test", encoding="utf-8")
        result = find_markdown_files(str(f))
        assert result == [str(f)]

    def test_single_non_markdown_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("text", encoding="utf-8")
        assert find_markdown_files(str(f)) == []

    def test_skips_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "README.md").write_text("git", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        result = find_markdown_files(str(tmp_path))
        assert all(".git" not in f for f in result)

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert find_markdown_files(str(tmp_path)) == []

    def test_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("b", encoding="utf-8")
        (tmp_path / "a.md").write_text("a", encoding="utf-8")
        result = find_markdown_files(str(tmp_path))
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_empty_report_json(self) -> None:
        report = generate_report([], {}, as_json=True)
        import json

        data = json.loads(report)
        assert data["summary"]["total_links"] == 0
        assert data["summary"]["broken"] == 0

    def test_with_broken_links_json(self) -> None:
        link = LinkInfo("README.md", 5, "text", "missing.md", "local_file")
        link.is_valid = False
        link.error = "File not found"
        report = generate_report([link], {}, as_json=True)
        import json

        data = json.loads(report)
        assert data["summary"]["broken"] == 1
        assert len(data["broken_links"]) == 1

    def test_human_readable(self) -> None:
        link = LinkInfo("README.md", 5, "text", "missing.md", "local_file")
        link.is_valid = False
        link.error = "File not found"
        report = generate_report([link], {}, as_json=False)
        assert "Link Check Report" in report
        assert "BROKEN LINKS" in report
        assert "missing.md" in report

    def test_no_issues_human_readable(self) -> None:
        link = LinkInfo("README.md", 5, "text", "guide.md", "local_file")
        link.is_valid = True
        report = generate_report([link], {}, as_json=False)
        assert "No issues found" in report

    def test_broken_only_json(self) -> None:
        valid_link = LinkInfo("README.md", 1, "text", "guide.md", "local_file")
        valid_link.is_valid = True
        broken_link = LinkInfo("README.md", 5, "text", "missing.md", "local_file")
        broken_link.is_valid = False
        broken_link.error = "File not found"
        report = generate_report([valid_link, broken_link], {}, broken_only=True, as_json=True)
        import json

        data = json.loads(report)
        assert "all_links" not in data
        assert len(data["broken_links"]) == 1

    def test_duplicate_anchors_in_report(self) -> None:
        report = generate_report([], {"README.md": [("dup-anchor", 10)]}, as_json=False)
        assert "DUPLICATE ANCHORS" in report
        assert "dup-anchor" in report

    def test_duplicate_anchors_json(self) -> None:
        report = generate_report([], {"README.md": [("dup-anchor", 10)]}, as_json=True)
        import json

        data = json.loads(report)
        assert data["summary"]["duplicate_anchors"] == 1

    def test_type_breakdown(self) -> None:
        link1 = LinkInfo("README.md", 1, "text", "guide.md", "local_file")
        link1.is_valid = True
        link2 = LinkInfo("README.md", 2, "text", "https://example.com", "external")
        link2.is_valid = True
        report = generate_report([link1, link2], {}, as_json=False)
        assert "LINK TYPE BREAKDOWN" in report

    def test_skipped_links(self) -> None:
        link = LinkInfo("README.md", 1, "text", "https://example.com", "external")
        # is_valid is None (skipped)
        report = generate_report([link], {}, as_json=True)
        import json

        data = json.loads(report)
        assert data["summary"]["skipped"] == 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_nonexistent_path(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_no_markdown_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "No markdown files found" in captured.out

    def test_no_markdown_files_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--json"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_valid_links_exit_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("# Title\n[link](guide.md)\n", encoding="utf-8")
        (tmp_path / "guide.md").write_text("# Guide\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_broken_links_exit_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("# Title\n[link](nonexistent.md)\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_duplicate_anchors_exit_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("# Title\n# Title\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("# Title\n[link](guide.md)\n", encoding="utf-8")
        (tmp_path / "guide.md").write_text("# Guide\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--json"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert "summary" in data

    def test_broken_only_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("# Title\n[link](nonexistent.md)\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--broken-only", "--json"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert "all_links" not in data

    def test_single_file_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "README.md"
        f.write_text("# Title\n[link](guide.md)\n", encoding="utf-8")
        (tmp_path / "guide.md").write_text("# Guide\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_check_external_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text(
            "# Title\n[link](https://example.com)\n", encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--check-external"])
        with patch(
            "zolletta_metaskill.documentor.link_checker.validate_external_url",
            return_value=(True, None),
        ), pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_empty_markdown_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
