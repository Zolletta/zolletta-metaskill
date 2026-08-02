"""Tests for detect_adrs.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from zolletta_metaskill.setup.detect_adrs import (
    _determine_adrs_path,
    _grep_adr_files,
    _scan_adr_headings,
    detect_adrs,
    main,
)

_ADR_TEMPLATE = """# ADR-{num}: {title}

## Status

Accepted

## Decision

{decision}
"""


def _write_adr(path: Path, num: str, title: str, status: str = "Accepted",
               decision: str = "We decided to do X.") -> None:
    """Write a minimal ADR file."""
    path.write_text(
        f"# ADR-{num}: {title}\n\n## Status\n\n{status}\n\n"
        f"## Decision\n\n{decision}\n",
        encoding="utf-8",
    )


class TestDetectAdrs:
    """Tests for detect_adrs()."""

    def test_adrs_in_subdir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "adr").mkdir(parents=True)
        _write_adr(docs / "adr" / "0001-use-postgres.md", "001", "Use Postgres")
        assert detect_adrs(docs) == "adr"

    def test_adrs_in_decisions_subdir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "decisions").mkdir(parents=True)
        _write_adr(docs / "decisions" / "0001-use-postgres.md", "001", "Use Postgres")
        assert detect_adrs(docs) == "decisions"

    def test_adrs_scattered_in_docs_root(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        _write_adr(docs / "0001-use-postgres.md", "001", "Use Postgres")
        _write_adr(docs / "0002-use-redis.md", "002", "Use Redis")
        assert detect_adrs(docs) == ""

    def test_no_adrs_returns_none(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "random.md").write_text("Just a regular doc.", encoding="utf-8")
        assert detect_adrs(docs) is None

    def test_no_docs_dir_returns_none(self, tmp_path: Path) -> None:
        assert detect_adrs(tmp_path / "nonexistent") is None

    def test_grep_false_positive_filtered(self, tmp_path: Path) -> None:
        """Files mentioning 'adr' but no ADR headings → None."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "notes.md").write_text(
            "We should write ADRs someday.\n", encoding="utf-8"
        )
        assert detect_adrs(docs) is None

    def test_adr_distilled_excluded_from_grep(self, tmp_path: Path) -> None:
        """adr-distilled.md should not be detected as an ADR source."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "adr-distilled.md").write_text(
            "- [ADR-001](adr/0001.md) Use Postgres.\n", encoding="utf-8"
        )
        assert detect_adrs(docs) is None

    def test_adrs_in_nested_subdir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "architecture" / "adr").mkdir(parents=True)
        _write_adr(
            docs / "architecture" / "adr" / "0001-use-postgres.md",
            "001", "Use Postgres",
        )
        # Common subdir is "architecture" (first path component)
        assert detect_adrs(docs) == "architecture"

    def test_adrs_in_multiple_subdirs_returns_empty(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "adr1").mkdir(parents=True)
        (docs / "adr2").mkdir(parents=True)
        _write_adr(docs / "adr1" / "0001.md", "001", "First")
        _write_adr(docs / "adr2" / "0002.md", "002", "Second")
        assert detect_adrs(docs) == ""

    def test_grep_unavailable_fallback_to_rglob(self, tmp_path: Path) -> None:
        """When grep is unavailable, fall back to scanning all .md files."""
        docs = tmp_path / "docs"
        (docs / "adr").mkdir(parents=True)
        _write_adr(docs / "adr" / "0001-test.md", "001", "Test")
        with patch(
            "zolletta_metaskill.setup.detect_adrs._grep_adr_files",
            return_value=None,
        ):
            assert detect_adrs(docs) == "adr"

    def test_grep_unlicable_no_adrs(self, tmp_path: Path) -> None:
        """When grep is unavailable and no ADRs exist, returns None."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "notes.md").write_text("Just notes.\n", encoding="utf-8")
        with patch(
            "zolletta_metaskill.setup.detect_adrs._grep_adr_files",
            return_value=None,
        ):
            assert detect_adrs(docs) is None


class TestGrepAdrFiles:
    """Tests for _grep_adr_files()."""

    def test_grep_finds_adr_mention(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "notes.md").write_text("Mention ADR here.\n", encoding="utf-8")
        result = _grep_adr_files(docs)
        assert result is not None
        assert len(result) >= 1

    def test_grep_returns_none_when_grep_missing(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        with patch("zolletta_metaskill.setup.detect_adrs.shutil.which", return_value=None):
            assert _grep_adr_files(docs) is None

    def test_grep_returns_none_on_timeout(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        with patch(
            "zolletta_metaskill.setup.detect_adrs.subprocess.run",
            side_effect=__import__("subprocess").TimeoutExpired("grep", 30),
        ):
            assert _grep_adr_files(docs) is None

    def test_grep_returns_none_on_os_error(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        with patch(
            "zolletta_metaskill.setup.detect_adrs.subprocess.run",
            side_effect=OSError("nope"),
        ):
            assert _grep_adr_files(docs) is None

    def test_grep_returns_none_on_bad_exit_code(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        mock_result = __import__("subprocess").CompletedProcess(
            ["grep"], returncode=2, stdout="", stderr="error"
        )
        with patch(
            "zolletta_metaskill.setup.detect_adrs.subprocess.run",
            return_value=mock_result,
        ):
            assert _grep_adr_files(docs) is None

    def test_grep_no_results(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        result = _grep_adr_files(docs)
        assert result is not None
        assert result == []


class TestScanAdrHeadings:
    """Tests for _scan_adr_headings()."""

    def test_finds_adr_heading(self, tmp_path: Path) -> None:
        f = tmp_path / "0001-test.md"
        f.write_text("# ADR-001: Test\n\n## Status\n\nAccepted\n", encoding="utf-8")
        result = _scan_adr_headings([f])
        assert len(result) == 1
        assert result[0] == f

    def test_no_adr_heading_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "notes.md"
        f.write_text("Just notes about ADRs.\n", encoding="utf-8")
        result = _scan_adr_headings([f])
        assert result == []

    def test_non_md_file_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "data.txt"
        f.write_text("# ADR-001: Test\n", encoding="utf-8")
        result = _scan_adr_headings([f])
        assert result == []

    def test_unreadable_file_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("# ADR-001: Test\n", encoding="utf-8")
        with patch("pathlib.Path.read_text", side_effect=OSError("nope")):
            result = _scan_adr_headings([f])
        assert result == []

    def test_multiple_formats(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f1.write_text("# ADR-001: Title\n", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("## ADR 002: Title\n", encoding="utf-8")
        f3 = tmp_path / "c.md"
        f3.write_text("### ADR-003: Title\n", encoding="utf-8")
        result = _scan_adr_headings([f1, f2, f3])
        assert len(result) == 3


class TestDetermineAdrsPath:
    """Tests for _determine_adrs_path()."""

    def test_single_subdir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        f1 = docs / "adr" / "0001.md"
        f1.parent.mkdir(parents=True)
        f1.write_text("# ADR-001\n", encoding="utf-8")
        f2 = docs / "adr" / "0002.md"
        f2.write_text("# ADR-002\n", encoding="utf-8")
        assert _determine_adrs_path([f1, f2], docs) == "adr"

    def test_docs_root(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        f1 = docs / "0001.md"
        f1.write_text("# ADR-001\n", encoding="utf-8")
        assert _determine_adrs_path([f1], docs) == ""

    def test_multiple_subdirs(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        f1 = docs / "adr1" / "0001.md"
        f1.parent.mkdir(parents=True)
        f1.write_text("# ADR-001\n", encoding="utf-8")
        f2 = docs / "adr2" / "0002.md"
        f2.parent.mkdir(parents=True)
        f2.write_text("# ADR-002\n", encoding="utf-8")
        assert _determine_adrs_path([f1, f2], docs) == ""

    def test_mixed_root_and_subdir(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        f1 = docs / "0001.md"
        f1.write_text("# ADR-001\n", encoding="utf-8")
        f2 = docs / "adr" / "0002.md"
        f2.parent.mkdir(parents=True)
        f2.write_text("# ADR-002\n", encoding="utf-8")
        assert _determine_adrs_path([f1, f2], docs) == ""


class TestMain:
    """Tests for main() CLI entry point."""

    def test_main_with_adrs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        (docs / "adr").mkdir(parents=True)
        _write_adr(docs / "adr" / "0001-test.md", "001", "Test")
        monkeypatch.setattr(sys, "argv", ["prog", str(docs)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["adrs_path"] == "adr"

    def test_main_no_adrs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(docs)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["adrs_path"] is None

    def test_main_nonexistent_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path / "nope")])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["adrs_path"] is None

    def test_main_default_docs_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.chdir(tmp_path)
        # No docs dir → adrs_path null
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["adrs_path"] is None
