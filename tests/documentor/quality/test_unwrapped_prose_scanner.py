"""Tests for unwrapped_prose_scanner.py."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.quality.unwrapped_prose_scanner import UnwrappedProseScanner


class TestUnwrappedProseScanner:
    # --- paragraph_runs ---

    def test_single_line_paragraph_is_not_a_run(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("One line.\n") == []

    def test_two_line_paragraph_returns_one_run(self) -> None:
        runs = UnwrappedProseScanner.paragraph_runs("A sentence that\nwraps here.\n")
        assert runs == [(1, 2)]

    def test_run_line_numbers_are_one_based_inclusive(self) -> None:
        text = "First.\n\nA sentence that\nwraps over\nthree lines.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(3, 5)]

    def test_paragraph_running_to_eof_returns_run(self) -> None:
        runs = UnwrappedProseScanner.paragraph_runs("A sentence that\nwraps at EOF")
        assert runs == [(1, 2)]

    def test_blank_line_separates_runs(self) -> None:
        text = "One that\nwraps.\n\nTwo that\nalso wraps.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 2), (4, 5)]

    def test_heading_does_not_join_into_a_paragraph(self) -> None:
        text = "Some prose.\n\n## A heading\n\nMore prose.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_fenced_code_is_excluded(self) -> None:
        text = "```python\ndef f():\n    return 1\n```\n\nProse.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_table_rows_are_excluded(self) -> None:
        text = "| a | b |\n|---|---|\n| 1 | 2 |\n\nProse.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_frontmatter_is_excluded(self) -> None:
        text = "---\ntitle: a long\ndescription: also long\n---\n\nProse.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_blockquote_is_excluded(self) -> None:
        text = "> a quoted line\n> that wraps.\n\nProse.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_html_comment_is_excluded(self) -> None:
        text = "<!-- a comment\nthat wraps -->\n\nProse.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_thematic_break_ends_a_run(self) -> None:
        text = "A sentence\nthat wraps.\n\n---\n\nMore.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 2)]

    # --- sentence-terminated runs are not wraps ---

    def test_two_complete_sentences_are_not_a_wrap(self) -> None:
        text = (
            "That's it — no setup guard, no config check.\nThis subcommand is always available.\n"
        )
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_run_is_a_wrap_when_only_the_last_line_terminates(self) -> None:
        text = "A first sentence that runs on\nand finishes here.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 2)]

    def test_emphasis_marker_counts_as_a_terminator(self) -> None:
        text = "**Positive:**\n- a bullet that wraps\n  across two lines.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(2, 3)]

    def test_trailing_code_span_counts_as_a_terminator(self) -> None:
        text = "Set `documentation.dir` in settings.json.\nAnother complete sentence.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    # --- list items ---

    def test_list_item_and_its_continuations_join(self) -> None:
        text = "- A bullet that wraps across lines.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_top_level_bullet_broken_mid_sentence_is_a_wrap(self) -> None:
        text = "- If a subagent fails, note it in the report and\n  continue with the next one.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 2)]

    def test_two_adjacent_bullets_are_not_merged(self) -> None:
        text = "- First bullet\n  wraps here.\n- Second bullet\n  wraps too.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 2), (3, 4)]

    def test_single_line_bullets_are_clean(self) -> None:
        text = "- First bullet is long and unwrapped.\n- Second bullet likewise.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_nested_list_is_skipped(self) -> None:
        text = (
            "1. **Write the file** containing:\n"
            "   - **Settings**: the fields\n"
            "   - **Directives**: the digest\n"
            "   Keep this to ~30 lines — only the criteria.\n"
        )
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    # --- scan_text ---

    def test_scan_text_returns_one_finding_per_paragraph(self) -> None:
        text = "A sentence that\nwraps here.\n\nAnother that\nwraps too.\n"
        findings = UnwrappedProseScanner.scan_text("doc.md", text)
        assert [f.line for f in findings] == [1, 4]

    def test_scan_text_finding_names_the_full_span(self) -> None:
        findings = UnwrappedProseScanner.scan_text("doc.md", "A sentence\nwraps over\nlines.\n")
        assert len(findings) == 1
        assert "1-3" in findings[0].description

    def test_scan_text_finding_carries_category_and_severity(self) -> None:
        finding = UnwrappedProseScanner.scan_text("doc.md", "A sentence\nwraps.\n")[0]
        assert finding.category == "unwrapped_prose"
        assert finding.severity == "low"
        assert finding.file == "doc.md"

    def test_scan_text_on_clean_text_returns_empty(self) -> None:
        assert UnwrappedProseScanner.scan_text("doc.md", "One line only.\n") == []

    # --- scan_file / scan_roots ---

    def test_scan_file_reads_from_disk(self, tmp_path: Path) -> None:
        target = tmp_path / "doc.md"
        target.write_text("A sentence that\nwraps.\n", encoding="utf-8")
        assert len(UnwrappedProseScanner.scan_file(target)) == 1

    def test_scan_file_missing_returns_empty(self, tmp_path: Path) -> None:
        assert UnwrappedProseScanner.scan_file(tmp_path / "absent.md") == []

    def test_scan_roots_skips_missing_directory(self, tmp_path: Path) -> None:
        assert UnwrappedProseScanner.scan_roots([tmp_path / "absent"]) == []

    def test_scan_roots_deduplicates_overlapping_roots(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("A sentence\nthat wraps.\n", encoding="utf-8")
        findings = UnwrappedProseScanner.scan_roots([tmp_path, tmp_path])
        assert len(findings) == 1

    def test_scan_roots_orders_by_file_then_line(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("A sentence\nthat wraps.\n", encoding="utf-8")
        (tmp_path / "a.md").write_text("One line.\n\nA sentence\nthat wraps.\n", encoding="utf-8")
        findings = UnwrappedProseScanner.scan_roots([tmp_path])
        assert [f.file for f in findings] == [str(tmp_path / "a.md"), str(tmp_path / "b.md")]

    # --- resolve_roots ---

    def test_resolve_roots_uses_documentation_dir(self, tmp_path: Path) -> None:
        roots = UnwrappedProseScanner.resolve_roots(
            {"documentation": {"dir": str(tmp_path / "docs")}}
        )
        assert roots == [tmp_path / "docs"]

    def test_resolve_roots_does_not_widen_beyond_the_docs_root(self, tmp_path: Path) -> None:
        """The skill's scope rule: markdown outside documentation.dir is out of scope."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "skills").mkdir()
        roots = UnwrappedProseScanner.resolve_roots(
            {"documentation": {"dir": str(tmp_path / "docs")}}
        )
        assert roots == [tmp_path / "docs"]

    def test_resolve_roots_defaults_to_docs_when_unconfigured(self) -> None:
        assert UnwrappedProseScanner.resolve_roots({}) == [Path(ProjectConfig.DEFAULT_DOCS_DIR)]

    # --- is_enabled ---

    def test_is_enabled_defaults_to_false(self) -> None:
        assert UnwrappedProseScanner.is_enabled({}) is False

    def test_is_enabled_true_when_configured(self) -> None:
        settings = {"documentation": {"check_unwrapped_prose": True}}
        assert UnwrappedProseScanner.is_enabled(settings) is True

    def test_is_enabled_false_when_explicitly_off(self) -> None:
        settings = {"documentation": {"check_unwrapped_prose": False}}
        assert UnwrappedProseScanner.is_enabled(settings) is False

    def test_is_enabled_ignores_unrelated_documentation_keys(self) -> None:
        assert (
            UnwrappedProseScanner.is_enabled({"documentation": {"check_external": True}}) is False
        )

    # --- CLI output ---

    def test_emit_json_shape(self, capsys: pytest.CaptureFixture[str]) -> None:
        findings = UnwrappedProseScanner.scan_text("doc.md", "A sentence\nthat wraps.\n")
        UnwrappedProseScanner._emit_json([Path("docs")], 3, findings)
        data = json.loads(capsys.readouterr().out)
        assert data["violation_count"] == 1
        assert data["violations"][0]["category"] == "unwrapped_prose"

    def test_emit_text_reports_all_clear(self, capsys: pytest.CaptureFixture[str]) -> None:
        UnwrappedProseScanner._emit_text([Path("docs")], 3, [])
        assert "Result: all clear" in capsys.readouterr().out

    def test_emit_text_names_the_span(self, capsys: pytest.CaptureFixture[str]) -> None:
        findings = UnwrappedProseScanner.scan_text("doc.md", "A sentence\nthat wraps.\n")
        UnwrappedProseScanner._emit_text([Path("docs")], 1, findings)
        assert "lines 1-2" in capsys.readouterr().out

    # --- main() toggle handling ---

    def test_main_reports_skipped_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["unwrapped_prose_scanner.py"], raising=False)
        monkeypatch.setattr(
            ProjectConfig, "load_settings", staticmethod(lambda path: {"documentation": {}})
        )
        assert UnwrappedProseScanner.main() == 0
        assert (
            capsys.readouterr().out
            == "Result: SKIPPED (check_unwrapped_prose disabled in settings.json)\n"
        )

    def test_main_emits_skipped_json_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["unwrapped_prose_scanner.py", "--json"], raising=False)
        monkeypatch.setattr(
            ProjectConfig, "load_settings", staticmethod(lambda path: {"documentation": {}})
        )
        assert UnwrappedProseScanner.main() == 0
        assert json.loads(capsys.readouterr().out) == {
            "skipped": True,
            "reason": "check_unwrapped_prose disabled in settings.json",
        }

    # --- Text contract ---

    def test_emit_text_matches_committed_contract(
        self,
        capsys: pytest.CaptureFixture[str],
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The captured text report is a byte-for-byte contract.

        Do not loosen this assertion: it pins the exact text output. A
        legitimate change is ``pytest --update-fixtures`` plus a reviewed
        diff, never a hand-edit or a weaker matcher.
        """
        findings = UnwrappedProseScanner.scan_text("docs/guide.md", "A sentence that\nwraps.\n")
        UnwrappedProseScanner._emit_text([Path("docs")], 3, findings)
        text_contract("documentor/quality/unwrapped_prose_scanner.txt", capsys.readouterr().out)

    def test_unterminated_frontmatter_scans_as_body(self) -> None:
        """An unclosed ``---`` block is not frontmatter; lines are scanned."""
        text = "---\ntitle: x\nA sentence that\nwraps here.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(2, 4)]

    def test_indented_continuation_is_not_a_run(self) -> None:
        text = "Normal line.\n    indented continuation line\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    # --- main ---

    def test_main_disabled_settings_emits_skipped(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(lambda *a, **k: {"documentation": {"check_unwrapped_prose": False}}),
        )
        assert UnwrappedProseScanner.main() == 0
        out = capsys.readouterr()
        assert "SKIPPED" in out.out

    def test_main_no_doc_roots_returns_one(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(lambda *a, **k: {"documentation": {"dir": str(tmp_path / "nope")}}),
        )
        monkeypatch.setattr(
            UnwrappedProseScanner, "resolve_roots", staticmethod(lambda s: [tmp_path / "nope"])
        )
        monkeypatch.setattr(UnwrappedProseScanner, "is_enabled", staticmethod(lambda s: True))
        assert UnwrappedProseScanner.main() == 1

    def test_main_scans_and_reports(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.md").write_text("A sentence that\nwraps here.\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(lambda *a, **k: {"documentation": {"dir": str(docs)}}),
        )
        monkeypatch.setattr(UnwrappedProseScanner, "is_enabled", staticmethod(lambda s: True))
        monkeypatch.setattr(UnwrappedProseScanner, "resolve_roots", staticmethod(lambda s: [docs]))
        assert UnwrappedProseScanner.main() == 0
        assert json.loads(capsys.readouterr().out)

    def test_main_scans_text_report(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.md").write_text("One line.\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(lambda *a, **k: {"documentation": {"dir": str(docs)}}),
        )
        monkeypatch.setattr(UnwrappedProseScanner, "is_enabled", staticmethod(lambda s: True))
        monkeypatch.setattr(UnwrappedProseScanner, "resolve_roots", staticmethod(lambda s: [docs]))
        assert UnwrappedProseScanner.main() == 0

    def test_fence_break_inside_run_flushes_the_run(self) -> None:
        text = "A sentence that\nwraps here.\n```\ncode\n```\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 2)]

    # --- frontmatter edge cases ---

    def test_empty_frontmatter_with_later_break_still_scans_body(self) -> None:
        r"""An empty ``---\\n---`` frontmatter ends at line 2, not the next ``---``."""
        text = "---\n---\nWrap a\nwraps b.\n\n---\nMore.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(3, 4)]

    def test_fence_as_last_frontmatter_line_does_not_swallow_body(self) -> None:
        """The line before the closing ``---`` must not re-enter the scan as a fence opener."""
        text = "---\n```\n---\nWrap one\nwraps two.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(4, 5)]

    # --- block boundaries ---

    def test_asterisk_thematic_break_ends_a_run(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("Prose.\n***\nMore.\n") == []

    def test_underscore_thematic_break_ends_a_run(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("Prose.\n___\nMore.\n") == []

    def test_heading_without_blank_lines_still_breaks_a_run(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("Prose.\n## Heading\nMore.\n") == []

    # --- sentence termination ---

    def test_space_before_closing_emphasis_counts_as_terminated(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("Done. **\nNext.\n") == []

    def test_trailing_emphasis_counts_as_terminated(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("Done.**\nNext.\n") == []

    def test_line_ending_in_uppercase_letter_is_unterminated(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("Wraps.X\nends here.\n") == [(1, 2)]

    def test_middle_line_must_also_terminate_a_sentence(self) -> None:
        text = "Done.\nMid wraps\nDone.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(1, 3)]

    # --- fenced code ---

    def test_fenced_code_contents_are_never_scanned(self) -> None:
        text = "```\ncode line one\ncode line two\n```\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == []

    def test_run_after_closing_fence_is_reported(self) -> None:
        text = "```\ncode\n```\nWrap a\nwraps.\n"
        assert UnwrappedProseScanner.paragraph_runs(text) == [(4, 5)]

    def test_single_space_indented_run_is_not_a_violation(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs(" Wraps mid\nends here.\n") == []

    def test_three_line_run_is_reported(self) -> None:
        assert UnwrappedProseScanner.paragraph_runs("A wraps\nB wraps\nC ends.\n") == [(1, 3)]

    # --- is_enabled ---

    def test_is_enabled_rejects_non_boolean_value(self) -> None:
        settings = {"documentation": {"check_unwrapped_prose": "yes"}}
        assert UnwrappedProseScanner.is_enabled(settings) is False

    # --- scan_roots ordering and continuation ---

    def test_scan_roots_continues_past_missing_root(self, tmp_path: Path) -> None:
        real = tmp_path / "real"
        real.mkdir()
        (real / "a.md").write_text("Wraps\nhere.\n", encoding="utf-8")
        findings = UnwrappedProseScanner.scan_roots([tmp_path / "absent", real])
        assert [f.file for f in findings] == [str(real / "a.md")]

    def test_scan_roots_scans_files_after_a_duplicate(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("Wraps\nhere.\n", encoding="utf-8")
        (tmp_path / "z.md").write_text("Wraps\nhere.\n", encoding="utf-8")
        findings = UnwrappedProseScanner.scan_roots([sub, tmp_path])
        assert [f.file for f in findings] == [str(sub / "b.md"), str(tmp_path / "z.md")]

    # --- report output contracts ---

    def test_emit_json_matches_exact_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        findings = UnwrappedProseScanner.scan_text("docs/guide.md", "A sentence\nthat wraps.\n")
        UnwrappedProseScanner._emit_json([Path("docs")], 3, findings)
        expected = {
            "directories": ["docs"],
            "scanned": 3,
            "violation_count": 1,
            "violations": [
                {
                    "file": "docs/guide.md",
                    "line": 1,
                    "category": "unwrapped_prose",
                    "severity": "low",
                    "description": (
                        "paragraph wraps across lines 1-2; "
                        "join it into one line (no artificial line breaks)"
                    ),
                }
            ],
        }
        assert capsys.readouterr().out == json.dumps(expected, indent=2) + "\n"

    def test_emit_text_joins_multiple_roots_with_comma(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        findings = UnwrappedProseScanner.scan_text("a/x.md", "A sentence\nthat wraps.\n")
        UnwrappedProseScanner._emit_text([Path("a"), Path("b")], 1, findings)
        assert "Scanned 1 files under a, b" in capsys.readouterr().out.splitlines()

    def test_emit_text_all_clear_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        UnwrappedProseScanner._emit_text([Path("docs")], 3, [])
        lines = capsys.readouterr().out.splitlines()
        assert "## Wrapped paragraphs: none" in lines
        assert "Result: all clear" in lines

    # --- main: enabled path ---

    def test_main_json_report_is_exact(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.md").write_text("A sentence that\nwraps here.\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(
                lambda *a, **k: {"documentation": {"dir": str(docs), "check_unwrapped_prose": True}}
            ),
        )
        assert UnwrappedProseScanner.main() == 0
        assert json.loads(capsys.readouterr().out) == {
            "directories": [str(docs)],
            "scanned": 1,
            "violation_count": 1,
            "violations": [
                {
                    "file": str(docs / "a.md"),
                    "line": 1,
                    "category": "unwrapped_prose",
                    "severity": "low",
                    "description": (
                        "paragraph wraps across lines 1-2; "
                        "join it into one line (no artificial line breaks)"
                    ),
                }
            ],
        }

    def test_main_text_report_names_scanned_count(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.md").write_text("A sentence that\nwraps here.\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(
                lambda *a, **k: {"documentation": {"dir": str(docs), "check_unwrapped_prose": True}}
            ),
        )
        assert UnwrappedProseScanner.main() == 0
        lines = capsys.readouterr().out.splitlines()
        assert f"Scanned 1 files under {docs}" in lines
        assert "Result: violations found (report-only mode)" in lines

    def test_main_no_doc_roots_prints_exact_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        missing = tmp_path / "nope"
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(
                lambda *a, **k: {
                    "documentation": {"dir": str(missing), "check_unwrapped_prose": True}
                }
            ),
        )
        assert UnwrappedProseScanner.main() == 1
        out = capsys.readouterr()
        assert out.out == ""
        assert (
            out.err == f"Error: no configured documentation directory exists on disk ({missing})\n"
        )

    def test_main_no_doc_roots_lists_each_candidate(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        first, second = tmp_path / "a", tmp_path / "b"
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(UnwrappedProseScanner, "is_enabled", staticmethod(lambda s: True))
        monkeypatch.setattr(
            UnwrappedProseScanner, "resolve_roots", staticmethod(lambda s: [first, second])
        )
        assert UnwrappedProseScanner.main() == 1
        assert capsys.readouterr().err == (
            f"Error: no configured documentation directory exists on disk ({first}, {second})\n"
        )
