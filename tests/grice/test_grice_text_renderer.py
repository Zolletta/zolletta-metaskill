"""Tests for grice_text_renderer.py."""

from __future__ import annotations

from zolletta_metaskill.grice.grice_text_renderer import GriceTextRenderer
from zolletta_metaskill.grice.structs import (
    BenchmarkEntry,
    DefectLocation,
    Diagnosis,
    GriceReport,
    GroupSummary,
    GroupTriage,
    MaximScores,
    StructuralDefect,
    TriageEntry,
)

OUTLIER = MaximScores("docs/old/x.md", 30.0, 30.0, 30.0, None, group="old")
BENCHMARK = MaximScores("docs/new/y.md", 70.0, 70.0, 70.0, 70.0, group="new")


OUTLIER_ENTRY = TriageEntry(OUTLIER, Diagnosis("uniform_deficit", "quantity", "Weak", "Fix."))
BENCHMARK_ENTRY = BenchmarkEntry(
    BENCHMARK,
    (
        Diagnosis("balanced", "quantity", "Good", "Copy."),
        Diagnosis("strong_relation", "relation", "Cohesive", "Copy."),
    ),
)


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
        outliers=(OUTLIER_ENTRY,),
        triage=(
            GroupTriage("new", (), (BENCHMARK_ENTRY,)),
            GroupTriage("old", (OUTLIER_ENTRY,), ()),
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

    def test_render_outliers_one_table_per_group_with_full_metric_names(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        start = lines.index("## 2. Outliers (`grice_index < 40`)")
        end = lines.index("## 3. Positive Benchmarks")
        assert lines[start:end] == [
            "## 2. Outliers (`grice_index < 40`)",
            "",
            "### `old`",
            "",
            "| Document | Quantity | Quality | Relation | Manner | Index "
            "| Diagnosis & recommended action |",
            "|---|---|---|---|---|---|---|",
            "| `docs/old/x.md` | 30.0 | 30.0 | 30.0 | — | **30.0** | **Weak:** Fix. |",
            "",
        ]

    def test_render_benchmarks_one_table_per_group_lists_every_slot(self) -> None:
        lines = GriceTextRenderer.render(_report()).splitlines()
        start = lines.index("## 3. Positive Benchmarks")
        end = lines.index("## Corpus")
        assert lines[start:end] == [
            "## 3. Positive Benchmarks",
            "",
            "### `new`",
            "",
            "| Document | Quantity | Quality | Relation | Manner | Index | Strength |",
            "|---|---|---|---|---|---|---|",
            "| `docs/new/y.md` | 70.0 | 70.0 | 70.0 | 70.0 | **70.0** "
            "| **Balanced:** Good; **Top Relation (70.0):** Cohesive |",
            "",
        ]

    def test_render_several_groups_are_separated_by_a_blank_line(self) -> None:
        other = TriageEntry(
            MaximScores("docs/new/z.md", 20.0, 20.0, 20.0, 20.0, group="new"),
            Diagnosis("uniform_deficit", "quantity", "Weak", "Fix."),
        )
        report = GriceReport(
            documents=(),
            findings=(),
            disabled_metrics=(),
            notes=(),
            triage=(
                GroupTriage("new", (other,), (BENCHMARK_ENTRY,)),
                GroupTriage("old", (OUTLIER_ENTRY,), (BENCHMARK_ENTRY,)),
            ),
        )
        lines = GriceTextRenderer.render(report).splitlines()
        assert lines.count("### `new`") == 2
        assert lines.count("### `old`") == 2
        old = lines.index("### `old`")
        assert lines[old - 2 : old] == [
            "| `docs/new/z.md` | 20.0 | 20.0 | 20.0 | 20.0 | **20.0** | **Weak:** Fix. |",
            "",
        ]

    def test_render_strength_without_maxim_reads_as_balanced(self) -> None:
        entry = BenchmarkEntry(BENCHMARK, (Diagnosis("unmeasured", None, "None", ""),))
        report = GriceReport(
            documents=(),
            findings=(),
            disabled_metrics=(),
            notes=(),
            triage=(GroupTriage("new", (), (entry,)),),
        )
        assert "| **Balanced:** None |" in GriceTextRenderer.render(report)

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
