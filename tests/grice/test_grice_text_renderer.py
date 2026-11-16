"""Tests for grice_text_renderer.py."""

from __future__ import annotations

from zolletta_metaskill.grice.grice_text_renderer import GriceTextRenderer
from zolletta_metaskill.grice.structs import (
    DefectLocation,
    Diagnosis,
    GriceReport,
    GroupSummary,
    MaximScores,
    StructuralDefect,
    TriageEntry,
)

OUTLIER = MaximScores("docs/old/x.md", 30.0, 30.0, 30.0, None, group="old")
BENCHMARK = MaximScores("docs/new/y.md", 70.0, 70.0, 70.0, 70.0, group="new")


def _report() -> GriceReport:
    return GriceReport(
        documents=(BENCHMARK, OUTLIER),
        findings=(),
        disabled_metrics=("readability",),
        notes=("Indices are relative.",),
        excluded_adrs=("docs/adr/1.md",),
        groups=(GroupSummary("new", 1, 70.0, 0, 1), GroupSummary("old", 1, 30.0, 1, 1)),
        defects=(
            StructuralDefect(
                "G1",
                "broken_link",
                "medium",
                "d",
                "docs/z.md#a",
                (
                    DefectLocation("docs/new/y.md", 3, "new"),
                    DefectLocation("docs/old/x.md", 4, "old"),
                ),
            ),
            StructuralDefect(
                "G2",
                "heading_skip",
                "low",
                "heading 'D' jumps from level 1 to 3",
                None,
                (DefectLocation("docs/old/x.md", 9, "old"),),
            ),
        ),
        outliers=(
            TriageEntry(
                OUTLIER,
                Diagnosis("uniform_deficit", "quantity", "Weak", "Fix."),
            ),
        ),
        benchmarks=(
            TriageEntry(
                BENCHMARK,
                Diagnosis("balanced", "quantity", "Good", "Copy."),
            ),
        ),
    )


class TestGriceTextRenderer:
    # --- render ---

    def test_render_header_states_corpus_adrs_and_median_without_grade(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        assert lines[:6] == [
            "# Grice Documentation Analysis",
            "",
            "- **Corpus:** 2 document(s)",
            "- **ADR files excluded:** 1",
            "- **Corpus median (`grice_index`):** 50.0",
            "- **Disabled metrics:** readability",
        ]
        assert not any("Grade" in line for line in lines)

    def test_render_executive_summary_has_one_row_per_group_and_total(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        start = lines.index("| Group | Docs | Median index | Outliers | Defects |")
        assert lines[start + 2 : start + 5] == [
            "| `new` | 1 | 70.0 | 0 | 1 |",
            "| `old` | 1 | 30.0 | 1 | 1 |",
            "| **Corpus** | 2 | 50.0 | 1 | 2 |",
        ]

    def test_render_defects_list_skips_and_deduplicated_links(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        assert (
            "| `G2` | `docs/old/x.md` | 9 | `old` | heading 'D' jumps from level 1 to 3 |" in lines
        )
        assert "| `G1` | `docs/z.md#a` | 2 | `docs/new/y.md:3`, `docs/old/x.md:4` |" in lines

    def test_render_outliers_and_benchmarks_carry_group_and_diagnosis(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        assert "## 2. Outliers (`grice_index < 40`)" in lines
        assert (
            "| `docs/old/x.md` | `old` | 30.0 | 30.0 | 30.0 | — | **30.0** | **Weak:** Fix. |"
            in lines
        )
        assert "| `docs/new/y.md` | `new` | **70.0** | Good |" in lines

    def test_render_corpus_table_lists_every_document_with_its_group(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        assert "| `docs/old/x.md` | `old` | 30.0 | 30.0 | 30.0 | — | 30.0 |" in lines
        assert lines[-2:] == ["", "- Indices are relative."]

    def test_render_empty_sections_print_none(self) -> None:
        report = GriceReport(documents=(OUTLIER,), findings=(), disabled_metrics=(), notes=())
        text = GriceTextRenderer.render(report)
        assert text.count(GriceTextRenderer.NONE) == 4
        assert text.endswith("\n")
        assert "Disabled metrics" not in text

    # --- cell ---

    def test_cell_unmeasured_index_returns_em_dash(self) -> None:
        assert GriceTextRenderer.cell(None) == "—"

    def test_cell_measured_index_returns_one_decimal(self) -> None:
        assert GriceTextRenderer.cell(50.04) == "50.0"
