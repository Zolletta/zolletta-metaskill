"""Tests for grice_scanner.py."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from zolletta_metaskill.core.structs import Finding
from zolletta_metaskill.grice.grice_scanner import GriceScanner
from zolletta_metaskill.grice.grice_text_renderer import GriceTextRenderer
from zolletta_metaskill.grice.manner_metrics import MannerMetrics
from zolletta_metaskill.grice.structs import DocumentFeatures

FIXTURE_CORPUS = Path(__file__).resolve().parent.parent / "fixtures" / "grice" / "corpus"


def _copy_corpus(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE_CORPUS, repo)
    return repo


def _write_settings(repo: Path, settings: dict[str, object]) -> Path:
    path = repo / ".zolletta-metaskill" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings), encoding="utf-8")
    return path


def _enable(repo: Path, **documentation: object) -> Path:
    return _write_settings(repo, {"documentation": {"dir": "docs", **documentation}})


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _copy_corpus(tmp_path)


@pytest.fixture(autouse=True)
def _argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["grice_scanner.py"])


class TestGriceScanner:
    # --- build: corpus ---

    def test_build_fixture_corpus_returns_one_row_per_document(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert [row.path for row in report.documents] == [
            "CONTRIBUTING.md",
            "README.md",
            "docs/guide/usage.md",
            "docs/index.md",
            "docs/reference/api.md",
        ]

    def test_build_fixture_corpus_measures_all_four_maxims(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        for row in report.documents:
            assert row.quantity is not None
            assert row.quality is not None
            assert row.relation is not None
            assert row.manner is not None

    def test_build_fixture_corpus_returns_indices_within_bounds(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        for row in report.documents:
            for index in row.available:
                assert 0.0 <= index <= 100.0

    def test_build_empty_repository_returns_none(self, tmp_path: Path) -> None:
        assert GriceScanner.build({"documentation": {"dir": "docs"}}, str(tmp_path)) is None

    def test_build_custom_documentation_dir_scans_that_dir(self, repo: Path) -> None:
        (repo / "docs").rename(repo / "handbook")
        report = GriceScanner.build({"documentation": {"dir": "handbook"}}, str(repo))
        assert report is not None
        assert [row.path for row in report.documents] == [
            "CONTRIBUTING.md",
            "README.md",
            "handbook/guide/usage.md",
            "handbook/index.md",
            "handbook/reference/api.md",
        ]

    # --- build: findings ---

    def test_build_fixture_corpus_returns_no_findings(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert report.findings == ()

    def test_build_broken_link_returns_a_finding_for_the_document(self, repo: Path) -> None:
        (repo / "docs" / "broken.md").write_text(
            "# Broken\n\nSee [gone](gone.md).\n", encoding="utf-8"
        )
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert [finding.file for finding in report.findings] == ["docs/broken.md"]

    def test_build_two_defective_documents_returns_findings_sorted_by_path(
        self, repo: Path
    ) -> None:
        (repo / "docs" / "zeta.md").write_text("# Zeta\n\n### Deep\n", encoding="utf-8")
        (repo / "docs" / "alpha.md").write_text("# Alpha\n\n### Deep\n", encoding="utf-8")
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert [finding.file for finding in report.findings] == ["docs/alpha.md", "docs/zeta.md"]

    # --- build: language ---

    def test_build_default_language_reports_no_disabled_metrics(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert report.disabled_metrics == ()
        assert report.notes == (
            "Indices are relative to this corpus: 50 is the corpus mean, not a quality threshold.",
        )

    def test_build_passes_language_to_manner_metrics(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        languages: list[str] = []
        evaluate = MannerMetrics.evaluate

        def spy(
            features: DocumentFeatures, language: str
        ) -> tuple[dict[str, float], list[Finding]]:
            languages.append(language)
            return evaluate(features, language)

        monkeypatch.setattr(MannerMetrics, "evaluate", spy)
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert languages == ["en"] * 5

    def test_build_configured_language_reaches_manner_metrics(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        languages: list[str] = []
        evaluate = MannerMetrics.evaluate

        def spy(
            features: DocumentFeatures, language: str
        ) -> tuple[dict[str, float], list[Finding]]:
            languages.append(language)
            return evaluate(features, language)

        monkeypatch.setattr(MannerMetrics, "evaluate", spy)
        report = GriceScanner.build({"documentation": {"dir": "docs", "language": "it"}}, str(repo))
        assert report is not None
        assert languages == ["it"] * 5

    # --- build: notes ---

    def test_build_corpus_at_minimum_size_omits_noise_note(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert report.corpus_size == GriceScanner.MIN_CORPUS
        assert not any("noisy" in note for note in report.notes)

    def test_build_corpus_below_minimum_size_adds_noise_note(self, repo: Path) -> None:
        for name in ("CONTRIBUTING.md", "docs/guide/usage.md", "docs/reference/api.md"):
            (repo / name).unlink()
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert any("noisy" in note for note in report.notes)

    def test_build_any_corpus_notes_the_relativity_of_the_indices(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert report.notes[0].startswith("Indices are relative to this corpus")

    def test_build_non_english_corpus_disables_english_metrics(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs", "language": "it"}}, str(repo))
        assert report is not None
        assert report.disabled_metrics == (
            "readability",
            "grade_level",
            "smog",
            "hedging",
            "passive_voice",
        )

    def test_build_non_english_corpus_notes_the_skipped_metrics(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs", "language": "it"}}, str(repo))
        assert report is not None
        assert any("'it'" in note for note in report.notes)

    # --- build: scope, groups and triage ---

    def test_build_adr_directories_are_excluded_before_scoring(
        self, repo: Path, tmp_path: Path
    ) -> None:
        for relative in ("docs/guide/adr/0001-a.md", "docs/adrs/0002-b.md", "docs/decisions/3.md"):
            (repo / relative).parent.mkdir(parents=True, exist_ok=True)
            (repo / relative).write_text("# Decision\n\nWe might do it.\n", encoding="utf-8")
        settings = {"documentation": {"dir": "docs", "adrs": "decisions"}}
        report = GriceScanner.build(settings, str(repo))
        baseline = GriceScanner.build(
            {"documentation": {"dir": "docs"}}, str(_copy_corpus(tmp_path / "baseline"))
        )
        assert report is not None and baseline is not None
        assert report.excluded_adrs == (
            "docs/adrs/0002-b.md",
            "docs/decisions/3.md",
            "docs/guide/adr/0001-a.md",
        )
        assert report.documents == baseline.documents
        assert any(note.startswith("3 ADR file(s) excluded") for note in report.notes)

    def test_build_only_adrs_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "adr").mkdir(parents=True)
        (tmp_path / "docs" / "adr" / "0001.md").write_text("# A\n", encoding="utf-8")
        assert GriceScanner.build({"documentation": {"dir": "docs"}}, str(tmp_path)) is None

    def test_build_fixture_corpus_groups_by_first_level_child(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert {row.path: row.group for row in report.documents} == {
            "CONTRIBUTING.md": "(root)",
            "README.md": "(root)",
            "docs/guide/usage.md": "guide",
            "docs/index.md": "(root)",
            "docs/reference/api.md": "reference",
        }
        assert [group.name for group in report.groups] == ["guide", "reference", "(root)"]
        assert sum(group.documents for group in report.groups) == report.corpus_size

    def test_build_configured_thresholds_select_outliers_and_benchmarks(self, repo: Path) -> None:
        settings = {
            "documentation": {"dir": "docs"},
            "subcommands": {"grice": {"outlier_threshold": 100}},
        }
        report = GriceScanner.build(settings, str(repo))
        assert report is not None
        assert report.settings.outlier_threshold == 100.0
        assert len(report.outliers) == report.corpus_size
        assert all(group.benchmarks == () for group in report.triage)

    def test_build_default_threshold_triages_every_group(self, repo: Path) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert [group.name for group in report.triage] == [group.name for group in report.groups]
        assert sum(len(group.outliers) for group in report.triage) == len(report.outliers)
        for group in report.triage:
            assert 1 <= len(group.benchmarks) <= 5
            assert all(entry.scores.group == group.name for entry in group.benchmarks)
            assert sum(len(entry.strengths) for entry in group.benchmarks) <= 5

    def test_build_shared_broken_target_returns_one_defect_many_locations(self, repo: Path) -> None:
        (repo / "docs" / "guide" / "a.md").write_text(
            "# A\n\nSee [x](../reference/api.md#nope).\n", encoding="utf-8"
        )
        (repo / "docs" / "b.md").write_text(
            "# B\n\nSee [x](reference/api.md#nope).\n\n### Deep\n", encoding="utf-8"
        )
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        assert [(d.id, d.kind, d.target, len(d.locations)) for d in report.defects] == [
            ("G1", "broken_link", "docs/reference/api.md#nope", 2),
            ("G2", "heading_skip", None, 1),
        ]
        assert len(report.findings) == 3

    # --- _corpus ---

    def test_corpus_undecodable_document_skips_only_that_document(self, repo: Path) -> None:
        (repo / "docs" / "aaa_bad.md").write_bytes(b"\xff\xfe\x00\x01")
        corpus, _ = GriceScanner._corpus({"documentation": {"dir": "docs"}}, str(repo))
        assert [features.path for features in corpus] == [
            "CONTRIBUTING.md",
            "README.md",
            "docs/guide/usage.md",
            "docs/index.md",
            "docs/reference/api.md",
        ]

    def test_corpus_reads_every_document_as_utf8(self, repo: Path) -> None:
        calls: list[dict[str, Any]] = []
        real_read_text = Path.read_text

        def spy(self: Path, *args: Any, **kwargs: Any) -> str:
            calls.append(kwargs)
            return real_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", spy):
            corpus, _ = GriceScanner._corpus({"documentation": {"dir": "docs"}}, str(repo))
        assert len(corpus) == 5
        assert calls == [{"encoding": "utf-8"}] * 5

    # --- _source_text ---

    def test_source_text_two_python_files_returns_both_bodies(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "alpha.py").write_text("alpha = 1\n", encoding="utf-8")
        (tmp_path / "src" / "bravo.py").write_text("bravo = 2\n", encoding="utf-8")
        assert GriceScanner._source_text(str(tmp_path)) == "alpha = 1\n\nbravo = 2\n"

    def test_source_text_undecodable_file_ignores_bad_bytes(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "bad.py").write_bytes(b"bad = '\xff\xfe'\n")
        assert GriceScanner._source_text(str(tmp_path)) == "bad = ''\n"

    def test_source_text_unreadable_file_skips_it_and_reads_the_rest(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "aaa.py").write_text("aaa = 1\n", encoding="utf-8")
        (tmp_path / "src" / "zzz.py").write_text("zzz = 1\n", encoding="utf-8")
        real_read_text = Path.read_text

        def fake_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
            if self.name == "aaa.py":
                raise OSError("unreadable")
            return real_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", fake_read_text):
            assert GriceScanner._source_text(str(tmp_path)) == "zzz = 1\n"

    def test_source_text_repository_without_code_returns_empty_string(self, tmp_path: Path) -> None:
        assert GriceScanner._source_text(str(tmp_path)) == ""

    def test_source_text_reads_files_as_utf8_ignoring_bad_bytes(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "alpha.py").write_text("alpha = 1\n", encoding="utf-8")
        calls: list[dict[str, Any]] = []
        real_read_text = Path.read_text

        def spy(self: Path, *args: Any, **kwargs: Any) -> str:
            calls.append(kwargs)
            return real_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", spy):
            assert GriceScanner._source_text(str(tmp_path)) == "alpha = 1\n"
        assert calls == [{"encoding": "utf-8", "errors": "ignore"}]

    # --- _disabled_metrics ---

    def test_disabled_metrics_english_returns_empty_tuple(self) -> None:
        assert GriceScanner._disabled_metrics("en") == ()

    def test_disabled_metrics_non_english_returns_english_only_metrics(self) -> None:
        assert GriceScanner._disabled_metrics("it") == (
            "readability",
            "grade_level",
            "smog",
            "hedging",
            "passive_voice",
        )

    # --- _notes ---

    def test_notes_english_corpus_returns_only_the_relativity_note(self) -> None:
        assert GriceScanner._notes(5, "en", 0) == (
            "Indices are relative to this corpus: 50 is the corpus mean, not a quality threshold.",
        )

    def test_notes_small_corpus_appends_the_noise_note(self) -> None:
        assert GriceScanner._notes(3, "en", 0) == (
            "Indices are relative to this corpus: 50 is the corpus mean, not a quality threshold.",
            f"Corpus has 3 document(s); percentiles over fewer than "
            f"{GriceScanner.MIN_CORPUS} documents are noisy.",
        )

    def test_notes_non_english_corpus_appends_the_disabled_metrics_note(self) -> None:
        assert GriceScanner._notes(5, "it", 0) == (
            "Indices are relative to this corpus: 50 is the corpus mean, not a quality threshold.",
            "documentation.language is 'it': readability, grade level, "
            "SMOG, hedging and passive voice did not run.",
        )

    def test_notes_excluded_adrs_appends_the_exclusion_note(self) -> None:
        assert GriceScanner._notes(5, "en", 3)[1] == (
            "3 ADR file(s) excluded before normalisation: decision records "
            "are not ranked against documentation."
        )

    # --- _emit_json ---

    def test_emit_json_pretty_prints_the_report(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        GriceScanner._emit_json(report)
        assert capsys.readouterr().out == json.dumps(report.to_dict(), indent=2) + "\n"

    # --- _emit_text ---

    def test_emit_text_report_prints_the_rendered_markdown(
        self, repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report = GriceScanner.build({"documentation": {"dir": "docs"}}, str(repo))
        assert report is not None
        GriceScanner._emit_text(report)
        assert capsys.readouterr().out == GriceTextRenderer.render(report)

    # --- main ---

    def test_main_with_settings_prints_markdown_report(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _enable(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        output = capsys.readouterr().out
        assert output.startswith("# Grice Documentation Analysis\n")
        assert "- **Corpus:** 5 document(s)" in output.splitlines()
        assert "Grade" not in output

    def test_main_enabled_toggle_writes_the_cache(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _enable(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        GriceScanner.main()
        cache = repo / ".zolletta-metaskill" / "cache" / "grice.json"
        assert json.loads(cache.read_text(encoding="utf-8"))["corpus_size"] == 5

    def test_main_json_flag_prints_parsable_report(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _enable(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        monkeypatch.setattr("sys.argv", ["grice_scanner.py", "--json"])
        assert GriceScanner.main() == 0
        assert json.loads(capsys.readouterr().out)["corpus_size"] == 5

    def test_main_empty_corpus_prints_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"documentation": {"dir": "docs"}}), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        assert capsys.readouterr().out.strip() == "Result: SKIPPED (no documentation files found)"

    def test_main_empty_corpus_json_flag_prints_json_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"documentation": {"dir": "docs"}}), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        monkeypatch.setattr("sys.argv", ["grice_scanner.py", "--json"])
        assert GriceScanner.main() == 0
        assert json.loads(capsys.readouterr().out) == {
            "skipped": True,
            "reason": "no documentation files found",
        }

    def test_main_custom_documentation_dir_scans_that_dir(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (repo / "docs").rename(repo / "handbook")
        path = _enable(repo, dir="handbook")
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        lines = capsys.readouterr().out.splitlines()
        assert "- **Corpus:** 5 document(s)" in lines
        assert any(line.startswith("| `handbook/index.md` |") for line in lines)

    def test_main_nested_runs_dir_creates_the_cache_tree(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _write_settings(
            repo,
            {
                "runs_dir": "deep/runs",
                "documentation": {"dir": "docs"},
            },
        )
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        assert (repo / "deep" / "runs" / "cache" / "grice.json").is_file()

    def test_main_existing_cache_dir_is_reused(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _write_settings(
            repo,
            {
                "runs_dir": "runs",
                "documentation": {"dir": "docs"},
            },
        )
        (repo / "runs" / "cache").mkdir(parents=True)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        assert (repo / "runs" / "cache" / "grice.json").is_file()

    def test_main_enabled_toggle_writes_cache_named_grice_json(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _enable(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        cache_dir = repo / ".zolletta-metaskill" / "cache"
        assert [entry.name for entry in cache_dir.iterdir()] == ["grice.json"]

    def test_main_enabled_toggle_writes_pretty_printed_cache(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _enable(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        assert GriceScanner.main() == 0
        cache = repo / ".zolletta-metaskill" / "cache" / "grice.json"
        content = cache.read_text(encoding="utf-8")
        assert content == json.dumps(json.loads(content), indent=2) + "\n"

    def test_main_writes_the_cache_as_utf8(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _enable(repo)
        monkeypatch.chdir(repo)
        monkeypatch.setattr(GriceScanner, "DEFAULT_SETTINGS_PATH", path)
        calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        real_write_text = Path.write_text

        def spy(self: Path, *args: Any, **kwargs: Any) -> int:
            calls.append((args, kwargs))
            return real_write_text(self, *args, **kwargs)

        with patch.object(Path, "write_text", spy):
            assert GriceScanner.main() == 0
        assert [kwargs for _, kwargs in calls] == [{"encoding": "utf-8"}]
