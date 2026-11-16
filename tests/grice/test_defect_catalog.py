"""Tests for defect_catalog.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.defect_catalog import DefectCatalog
from zolletta_metaskill.grice.document_grouper import DocumentGrouper
from zolletta_metaskill.grice.structs import DefectLocation


def _link(file: str, line: int, target: str) -> Finding:
    return Finding(
        file=file,
        line=line,
        category="grice",
        severity="medium",
        description=f"internal link '{target}' does not resolve",
    )


def _skip(file: str, line: int) -> Finding:
    return Finding(
        file=file,
        line=line,
        category="grice",
        severity="low",
        description="heading 'Deep' jumps from level 1 to 3",
    )


def _group(path: str) -> str:
    return DocumentGrouper.group_of(path, "docs")


class TestDefectCatalog:
    # --- build ---

    def test_build_same_target_from_many_pages_returns_one_defect(self) -> None:
        findings = [
            _link("docs/old/b.md", 9, "../current/x.md#tenants"),
            _link("docs/current/a.md", 4, "x.md#tenants"),
        ]
        (defect,) = DefectCatalog.build(findings, [], _group, "")
        assert defect.target == "docs/current/x.md#tenants"
        assert defect.locations == (
            DefectLocation("docs/current/a.md", 4, "current"),
            DefectLocation("docs/old/b.md", 9, "old"),
        )
        assert defect.groups == ("current", "old")

    def test_build_every_heading_skip_returns_its_own_defect(self) -> None:
        skips = [_skip("docs/a/x.md", 3), _skip("docs/a/x.md", 9), _skip("README.md", 2)]
        defects = DefectCatalog.build([], skips, _group, "")
        assert [(d.kind, d.locations[0].file, d.locations[0].line) for d in defects] == [
            ("heading_skip", "README.md", 2),
            ("heading_skip", "docs/a/x.md", 3),
            ("heading_skip", "docs/a/x.md", 9),
        ]
        assert all(d.target is None for d in defects)

    def test_build_links_and_skips_numbers_by_severity_then_location(self) -> None:
        defects = DefectCatalog.build(
            [_link("docs/b/y.md", 5, "gone.md"), _link("docs/a/x.md", 1, "#missing")],
            [_skip("docs/a/a.md", 2)],
            _group,
            "",
        )
        assert [(d.id, d.kind, d.target) for d in defects] == [
            ("G1", "broken_link", "docs/a/x.md#missing"),
            ("G2", "broken_link", "docs/b/gone.md"),
            ("G3", "heading_skip", None),
        ]

    def test_build_unparseable_description_keeps_the_finding_apart(self) -> None:
        finding = Finding("docs/a/x.md", 3, "grice", "medium", "something else")
        (defect,) = DefectCatalog.build([finding], [], _group, "")
        assert defect.target == "docs/a/x.md:3"

    def test_build_unknown_severity_sorts_last(self) -> None:
        odd = Finding("docs/a/a.md", 1, "grice", "weird", "heading 'X' jumps from level 1 to 3")
        defects = DefectCatalog.build([], [odd, _skip("docs/a/z.md", 1)], _group, "")
        assert [d.severity for d in defects] == ["low", "weird"]

    def test_build_no_findings_returns_empty_tuple(self) -> None:
        assert DefectCatalog.build([], [], _group, "") == ()

    # --- resolve_target ---

    def test_resolve_target_root_relative_link_returns_root_path(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "x.md").write_text("# X\n")
        resolved = DefectCatalog.resolve_target("docs/a/b.md", "docs/x.md#gone", str(tmp_path))
        assert resolved == "docs/x.md#gone"

    def test_resolve_target_existing_sibling_wins_over_root(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "a" / "docs").mkdir(parents=True)
        (tmp_path / "docs" / "a" / "docs" / "x.md").write_text("# X\n")
        (tmp_path / "docs" / "x.md").write_text("# X\n")
        resolved = DefectCatalog.resolve_target("docs/a/b.md", "docs/x.md#gone", str(tmp_path))
        assert resolved == "docs/a/docs/x.md#gone"

    @pytest.mark.parametrize(
        ("source", "target", "expected"),
        [
            ("docs/a/x.md", "#anchor", "docs/a/x.md#anchor"),
            ("docs/a/x.md", "../b/y.md", "docs/b/y.md"),
            ("docs/a/x.md", "./y.md#s", "docs/a/y.md#s"),
            ("docs/a/x.md", "/docs/c.md", "docs/c.md"),
            ("README.md", "docs/index.md#top", "docs/index.md#top"),
        ],
        ids=[
            "anchor_only_resolves_to_source",
            "parent_relative_is_normalised",
            "dot_relative_keeps_anchor",
            "root_absolute_strips_slash",
            "root_document_link",
        ],
    )
    def test_resolve_target_link_returns_repository_path(
        self, source: str, target: str, expected: str
    ) -> None:
        assert DefectCatalog.resolve_target(source, target, "") == expected
