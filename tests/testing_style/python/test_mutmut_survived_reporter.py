"""Tests for ``mutmut_survived_reporter`` — the survived-mutant report extractor.

Covers the public ``main`` entry point, the subprocess wrappers (``_run_mutmut``,
``_results_stdout``, ``_show_stdout``), the parsers (``_parse_results``,
``_split_mutant_name``, ``_parse_show``), path resolution, report assembly, and
the text renderer. All mutmut invocations are mocked — mutmut is not a test
dependency.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.testing_style.python.mutmut_survived_reporter import (
    MutmutSurvivedReporter,
)

# ---------------------------------------------------------------------------
# Settings + runner helpers
# ---------------------------------------------------------------------------


def _write_settings(tmp_path: Path, python_overrides: dict[str, Any] | None = None) -> None:
    """Write a minimal settings.json under ``tmp_path/.zolletta-metaskill``."""
    python: dict[str, Any] = {
        "tools": {"mutmut": {"available": True}},
        "testing": {"check_mutation_testing": True},
        "paths": {"source": ["src"], "tests": ["tests"]},
    }
    for key, value in (python_overrides or {}).items():
        if isinstance(value, dict) and isinstance(python.get(key), dict):
            python[key].update(value)
        else:
            python[key] = value
    meta = tmp_path / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "settings.json").write_text(json.dumps({"language": "python", "python": python}))


def test_write_settings_replaces_non_dict_python_value(tmp_path: Path) -> None:
    """A non-dict ``python`` override value replaces the base value."""
    _write_settings(tmp_path, {"tools": "none"})
    written = json.loads((tmp_path / ".zolletta-metaskill" / "settings.json").read_text())
    assert written["python"]["tools"] == "none"


def _proc(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    """Return a fake ``CompletedProcess`` for a mutmut invocation."""
    return subprocess.CompletedProcess(args=["mutmut"], returncode=returncode, stdout=stdout)


def _install_mutmut(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[tuple[str, ...], subprocess.CompletedProcess[str] | BaseException],
) -> None:
    """Patch ``subprocess.run`` so ``mutmut <args>`` returns/raises per *responses*.

    Unmatched invocations return a failing process so drift in the reporter's
    argument spelling surfaces in tests.
    """

    def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        response = responses.get(tuple(cmd[1:]), _proc("", 1))
        if isinstance(response, BaseException):
            raise response
        return response

    monkeypatch.setattr(subprocess, "run", _run)


def _main_with_argv(argv: list[str]) -> int:
    """Run ``MutmutSurvivedReporter.main()`` with a mocked ``sys.argv``."""
    saved = sys.argv
    sys.argv = argv
    try:
        return MutmutSurvivedReporter.main()
    finally:
        sys.argv = saved


def _run_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Chdir into *tmp_path* and run ``main()`` with *argv*."""
    monkeypatch.chdir(tmp_path)
    return _main_with_argv(["reporter", *argv])


RESULTS_ALL_TRUE = ("results", "--all", "true")
RESULTS_ALL = ("results", "--all")
RESULTS_PLAIN = ("results",)

RESULTS_STDOUT = """\
Browsing results...
    user.x_adult__mutmut_1: killed
    user.x_adult__mutmut_2: survived
    user.x_adult__mutmut_3: timeout
    user.xǁUserǁvalid__mutmut_1: no tests
    user.xǁUserǁvalid__mutmut_2: not checked
    user.xǁUserǁvalid__mutmut_3: skipped
"""

SHOW_STDOUT = """\
# user.x_adult__mutmut_2: survived
--- src/user.py
+++ src/user.py
@@ -10,3 +10,3 @@ def adult(age):
-    return age >= 18
+    return age > 18
"""


class TestMutmutSurvivedReporter:
    # --- ``_run_mutmut`` wraps subprocess with timeout/missing-tool safety. ---

    def test_run_mutmut_with_success_returns_process(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(monkeypatch, {RESULTS_PLAIN: _proc("ok")})
        proc = MutmutSurvivedReporter._run_mutmut(["results"])
        assert proc is not None
        assert proc.returncode == 0

    def test_run_mutmut_with_timeout_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(
            monkeypatch,
            {RESULTS_PLAIN: subprocess.TimeoutExpired(cmd="mutmut", timeout=600)},
        )
        assert MutmutSurvivedReporter._run_mutmut(["results"]) is None

    def test_run_mutmut_with_missing_binary_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(monkeypatch, {RESULTS_PLAIN: FileNotFoundError("mutmut")})
        assert MutmutSurvivedReporter._run_mutmut(["results"]) is None

    # --- ``_results_stdout`` tries the ``--all`` spellings then bare ``results``. ---

    def test_results_stdout_first_spelling_succeeds_returns_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(monkeypatch, {RESULTS_ALL_TRUE: _proc(RESULTS_STDOUT)})
        assert MutmutSurvivedReporter._results_stdout() == RESULTS_STDOUT

    def test_results_stdout_second_spelling_succeeds_returns_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(
            monkeypatch,
            {RESULTS_ALL_TRUE: _proc("unsupported", 2), RESULTS_ALL: _proc(RESULTS_STDOUT)},
        )
        assert MutmutSurvivedReporter._results_stdout() == RESULTS_STDOUT

    def test_results_stdout_plain_fallback_succeeds_returns_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(
            monkeypatch,
            {
                RESULTS_ALL_TRUE: _proc("unsupported", 2),
                RESULTS_ALL: _proc("unsupported", 2),
                RESULTS_PLAIN: _proc(RESULTS_STDOUT),
            },
        )
        assert MutmutSurvivedReporter._results_stdout() == RESULTS_STDOUT

    def test_results_stdout_all_fail_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(
            monkeypatch,
            {
                RESULTS_ALL_TRUE: _proc("err", 1),
                RESULTS_ALL: _proc("err", 1),
                RESULTS_PLAIN: _proc("err", 1),
            },
        )
        assert MutmutSurvivedReporter._results_stdout() is None

    def test_results_stdout_process_cannot_run_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(monkeypatch, {RESULTS_ALL_TRUE: FileNotFoundError("mutmut")})
        assert MutmutSurvivedReporter._results_stdout() is None

    # --- ``_show_stdout`` returns stdout only on a clean exit. ---

    def test_show_stdout_success_returns_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_mutmut(monkeypatch, {("show", "m.x_f__mutmut_1"): _proc(SHOW_STDOUT)})
        assert MutmutSurvivedReporter._show_stdout("m.x_f__mutmut_1") == SHOW_STDOUT

    def test_show_stdout_failure_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_mutmut(monkeypatch, {("show", "m.x_f__mutmut_1"): _proc("err", 1)})
        assert MutmutSurvivedReporter._show_stdout("m.x_f__mutmut_1") is None

    def test_show_stdout_process_cannot_run_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(
            monkeypatch, {("show", "m.x_f__mutmut_1"): FileNotFoundError("mutmut")}
        )
        assert MutmutSurvivedReporter._show_stdout("m.x_f__mutmut_1") is None

    # --- ``_parse_results`` maps ``    <name>: <status>`` lines. ---

    def test_parse_results_extracts_statuses(self) -> None:
        statuses = MutmutSurvivedReporter._parse_results(RESULTS_STDOUT)
        assert statuses == {
            "user.x_adult__mutmut_1": "killed",
            "user.x_adult__mutmut_2": "survived",
            "user.x_adult__mutmut_3": "timeout",
            "user.xǁUserǁvalid__mutmut_1": "no tests",
            "user.xǁUserǁvalid__mutmut_2": "not checked",
            "user.xǁUserǁvalid__mutmut_3": "skipped",
        }

    def test_parse_results_ignores_non_result_lines(self) -> None:
        stdout = "Browsing results...\nno-indent: killed\n\n"
        assert MutmutSurvivedReporter._parse_results(stdout) == {}

    # --- ``_split_mutant_name`` recovers module and function names. ---

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("user.x_adult__mutmut_2", ("user", "adult")),
            ("user.xǁUserǁvalid__mutmut_1", ("user", "valid")),
            ("pkg.sub.x_run__mutmut_9", ("pkg.sub", "run")),
            ("user.plain", ("user", "plain")),
            ("mod.", ("mod", None)),
            ("x_alone__mutmut_1", ("", "alone")),
        ],
    )
    def test_split_mutant_name_returns_module_and_function(
        self, name: str, expected: tuple[str, str | None]
    ) -> None:
        assert MutmutSurvivedReporter._split_mutant_name(name) == expected

    # --- ``_resolve_file`` maps modules onto configured source roots. ---

    def test_resolve_file_under_root_returns_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "user.py").write_text("x = 1\n")
        assert MutmutSurvivedReporter._resolve_file("user", ["src"]) == "src/user.py"

    def test_resolve_file_outside_roots_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tools.py").write_text("x = 1\n")
        assert MutmutSurvivedReporter._resolve_file("tools", ["src"]) is None

    def test_resolve_file_missing_returns_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert MutmutSurvivedReporter._resolve_file("pkg.mod", ["src"]) == "src/pkg/mod.py"

    def test_resolve_file_no_roots_returns_relative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert MutmutSurvivedReporter._resolve_file("pkg.mod", []) == "pkg/mod.py"

    # --- ``_under_source_root`` scopes diff files to configured roots. ---

    def test_under_source_root_empty_roots_allows_everything(self) -> None:
        assert MutmutSurvivedReporter._under_source_root("anywhere/x.py", []) is True

    def test_under_source_root_inside_returns_true(self) -> None:
        assert MutmutSurvivedReporter._under_source_root("src/a/b.py", ["src"]) is True

    def test_under_source_root_outside_returns_false(self) -> None:
        assert MutmutSurvivedReporter._under_source_root("vendor/x.py", ["src"]) is False

    # --- ``_parse_show`` extracts file, line, mutation, and diff. ---

    def test_parse_show_full_output_extracts_all_fields(self) -> None:
        file, line, mutation, diff = MutmutSurvivedReporter._parse_show(SHOW_STDOUT)
        assert file == "src/user.py"
        assert line == 10
        assert mutation == "return age >= 18 → return age > 18"
        assert "--- src/user.py" in diff
        assert "+    return age > 18" in diff

    def test_parse_show_without_header_keeps_all_lines(self) -> None:
        stdout = "--- src/user.py\n@@ -1 +1 @@\n- a\n+ b\n"
        file, line, mutation, diff = MutmutSurvivedReporter._parse_show(stdout)
        assert file == "src/user.py"
        assert line == 1
        assert mutation == "a → b"
        assert diff.startswith("--- src/user.py")

    def test_parse_show_without_removed_line_reports_no_mutation(self) -> None:
        stdout = "# m.x_f__mutmut_1: survived\n--- src/user.py\n@@ -1 +1 @@\n+ new\n"
        file, _line, mutation, _diff = MutmutSurvivedReporter._parse_show(stdout)
        assert file == "src/user.py"
        assert mutation is None

    def test_parse_show_without_file_header_reports_none_file(self) -> None:
        stdout = "# m.x_f__mutmut_1: survived\n@@ -3 +3 @@\n- a\n+ b\n"
        file, line, _mutation, _diff = MutmutSurvivedReporter._parse_show(stdout)
        assert file is None
        assert line == 3

    # --- ``_survivor_entry`` merges ``results`` + ``show`` and filters scope. ---

    def test_survivor_entry_with_show_output_populates_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "user.py").write_text("def adult(age):\n    return age >= 18\n")
        _install_mutmut(monkeypatch, {("show", "user.x_adult__mutmut_2"): _proc(SHOW_STDOUT)})
        entry = MutmutSurvivedReporter._survivor_entry(
            "user.x_adult__mutmut_2", "survived", ["src"]
        )
        assert entry is not None
        assert entry["file"] == "src/user.py"
        assert entry["line"] == 10
        assert entry["function"] == "adult"
        assert entry["mutation"] == "return age >= 18 → return age > 18"
        assert entry["diff"] is not None

    def test_survivor_entry_show_failure_keeps_partial_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _install_mutmut(monkeypatch, {})
        entry = MutmutSurvivedReporter._survivor_entry(
            "pkg.x_f__mutmut_1", "survived", ["src"]
        )
        assert entry is not None
        assert entry["file"] == "src/pkg.py"
        assert entry["line"] is None
        assert entry["mutation"] is None
        assert entry["diff"] is None

    def test_survivor_entry_file_outside_roots_drops_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "x.py").write_text("x = 1\n")
        show = "# vendor.x_f__mutmut_1: survived\n--- vendor/x.py\n@@ -1 +1 @@\n- a\n+ b\n"
        _install_mutmut(monkeypatch, {("show", "vendor.x_f__mutmut_1"): _proc(show)})
        assert (
            MutmutSurvivedReporter._survivor_entry("vendor.x_f__mutmut_1", "survived", ["src"])
            is None
        )

    # --- ``_report`` assembles counts, score, and capped survivors. ---

    def test_report_mixed_statuses_scores_evaluated_mutants(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _install_mutmut(monkeypatch, {})
        report = MutmutSurvivedReporter._report(
            MutmutSurvivedReporter._parse_results(RESULTS_STDOUT), 80, 50, ["src"]
        )
        assert report["counts"]["killed"] == 1
        assert report["counts"]["survived"] == 1
        assert report["counts"]["timeout"] == 1
        assert report["counts"]["no tests"] == 1
        # evaluated = killed+survived+timeout+no tests = 4; score = 1/4
        assert report["mutation_score"] == 25.0
        assert report["status"] == "FAIL"
        assert report["survivor_count"] == 2
        assert report["survivors_shown"] == 2
        assert report["survivors_capped"] is False
        assert [s["name"] for s in report["survivors"]] == [
            "user.x_adult__mutmut_2",
            "user.xǁUserǁvalid__mutmut_1",
        ]

    def test_report_score_at_threshold_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_mutmut(monkeypatch, {})
        statuses = {f"m.x_f__mutmut_{n}": "killed" for n in range(8)}
        statuses["m.x_g__mutmut_1"] = "survived"
        statuses["m.x_h__mutmut_1"] = "survived"
        report = MutmutSurvivedReporter._report(statuses, 80, 50, [])
        assert report["mutation_score"] == 80.0
        assert report["status"] == "PASS"

    def test_report_empty_statuses_scores_100(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_mutmut(monkeypatch, {})
        report = MutmutSurvivedReporter._report({}, 80, 50, [])
        assert report["mutation_score"] == 100.0
        assert report["status"] == "PASS"
        assert report["survivor_count"] == 0

    def test_report_max_mutants_caps_survivors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_mutmut(monkeypatch, {})
        statuses = {f"m.x_f__mutmut_{n}": "survived" for n in range(5)}
        report = MutmutSurvivedReporter._report(statuses, 80, 2, [])
        assert report["survivor_count"] == 5
        assert report["survivors_shown"] == 2
        assert report["survivors_capped"] is True
        assert [s["name"] for s in report["survivors"]] == [
            "m.x_f__mutmut_0",
            "m.x_f__mutmut_1",
        ]

    def test_report_out_of_scope_survivor_filtered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "x.py").write_text("x = 1\n")
        show = "# vendor.x_f__mutmut_1: survived\n--- vendor/x.py\n@@ -1 +1 @@\n- a\n+ b\n"
        _install_mutmut(monkeypatch, {("show", "vendor.x_f__mutmut_1"): _proc(show)})
        report = MutmutSurvivedReporter._report(
            {"vendor.x_f__mutmut_1": "survived"}, 80, 50, ["src"]
        )
        assert report["survivor_count"] == 1
        assert report["survivors_shown"] == 0
        assert report["survivors"] == []

    # --- ``_print_text`` renders the deterministic text format. ---

    def test_print_text_with_survivors_renders_table_and_diffs(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report: dict[str, Any] = {
            "counts": {"killed": 2, "survived": 1},
            "mutation_score": 66.7,
            "threshold": 80,
            "status": "FAIL",
            "survivor_count": 1,
            "survivors": [
                {
                    "name": "m.x_f__mutmut_1",
                    "status": "survived",
                    "file": "src/m.py",
                    "line": 3,
                    "function": "f",
                    "mutation": "a → b",
                    "diff": "--- src/m.py\n+ b",
                }
            ],
        }
        MutmutSurvivedReporter._print_text(report)
        out = capsys.readouterr().out
        assert "MUTMUT SURVIVED MUTANTS" in out
        assert "| killed" in out
        assert "Mutation score: 66.7% (threshold: 80%) — FAIL" in out
        assert "Survived mutants (1 of 1 shown):" in out
        assert "src/m.py | 3 | m.x_f__mutmut_1" in out
        assert "```diff" in out

    def test_print_text_survivor_without_details_renders_dashes(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report: dict[str, Any] = {
            "counts": {"survived": 1},
            "mutation_score": 0.0,
            "threshold": 80,
            "status": "FAIL",
            "survivor_count": 1,
            "survivors": [
                {
                    "name": "m.x_f__mutmut_1",
                    "status": "survived",
                    "file": None,
                    "line": None,
                    "function": "f",
                    "mutation": None,
                    "diff": None,
                }
            ],
        }
        MutmutSurvivedReporter._print_text(report)
        out = capsys.readouterr().out
        assert "| - | - | m.x_f__mutmut_1 | survived | - |" in out
        assert "```diff" not in out

    def test_print_text_no_survivors_prints_empty_note(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report: dict[str, Any] = {
            "counts": {"killed": 3},
            "mutation_score": 100.0,
            "threshold": 80,
            "status": "PASS",
            "survivor_count": 0,
            "survivors": [],
        }
        MutmutSurvivedReporter._print_text(report)
        assert "No survived mutants." in capsys.readouterr().out

    def test_print_text_all_filtered_prints_in_scope_note(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report: dict[str, Any] = {
            "counts": {"survived": 1},
            "mutation_score": 0.0,
            "threshold": 80,
            "status": "FAIL",
            "survivor_count": 1,
            "survivors": [],
        }
        MutmutSurvivedReporter._print_text(report)
        assert "No in-scope survived mutants." in capsys.readouterr().out

    # --- ``main``: skip paths, mutmut failure, text and JSON runs. ---

    def test_main_tool_unavailable_prints_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, {"tools": {"mutmut": {"available": False}}})
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 0
        assert "SKIPPED" in capsys.readouterr().out

    def test_main_tool_unavailable_json_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, {"tools": {"mutmut": {"available": False}}})
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["skipped"] is True
        assert "mutmut" in data["reason"]

    def test_main_check_disabled_prints_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, {"testing": {"check_mutation_testing": False}})
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 0
        assert "SKIPPED" in capsys.readouterr().out

    def test_main_results_failure_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        _install_mutmut(monkeypatch, {})
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 1
        assert "mutmut results" in capsys.readouterr().err

    def test_main_success_text_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, {"testing": {"mutation_score_threshold": 80}})
        _install_mutmut(
            monkeypatch,
            {
                RESULTS_ALL_TRUE: _proc(RESULTS_STDOUT),
                ("show", "user.x_adult__mutmut_2"): _proc(SHOW_STDOUT),
            },
        )
        rc = _run_scan(tmp_path, monkeypatch, [])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Mutation score: 25% (threshold: 80%) — FAIL" in out
        assert "user.x_adult__mutmut_2" in out

    def test_main_success_json_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(
            tmp_path,
            {"testing": {"mutation_score_threshold": 80, "mutation_max_mutants": 1}},
        )
        _install_mutmut(
            monkeypatch,
            {
                RESULTS_ALL_TRUE: _proc(RESULTS_STDOUT),
                ("show", "user.x_adult__mutmut_2"): _proc(SHOW_STDOUT),
            },
        )
        rc = _run_scan(tmp_path, monkeypatch, ["--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["skipped"] is False
        assert data["mutation_score"] == 25.0
        assert data["threshold"] == 80
        assert data["status"] == "FAIL"
        assert data["survivor_count"] == 2
        assert data["survivors_shown"] == 1
        assert data["survivors_capped"] is True
        assert data["survivors"][0]["name"] == "user.x_adult__mutmut_2"
