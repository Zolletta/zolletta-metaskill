"""Tests for ``scan_test_naming`` — the deterministic test-naming convention checker.

Covers the public ``main`` entry point, the two private helpers
(``_count_segments`` and ``_find_test_functions``), and a variety of edge
cases: empty files, syntax errors, the ``--skip`` / ``--strict`` / ``--json``
flags, ignored directories, custom ``--min-segments``, and naming patterns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.common.models import Finding
from zolletta_metaskill.python_testing_patterns.scan_test_naming import (
    _count_segments,
    _find_test_functions,
    main,
    scan_file,
)

# ---------------------------------------------------------------------------
# _count_segments
# ---------------------------------------------------------------------------


class TestCountSegments:
    """``_count_segments`` strips ``test_`` and counts non-empty segments."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            # Convention-compliant names (>= 3 segments)
            ("test_init_with_valid_dependencies_stores_attributes", 6),
            ("test_to_dict_with_empty_input_returns_empty_dict", 8),
            ("test_add_with_two_integers_returns_sum", 6),
            # Exactly three segments — the minimum
            ("test_init_with_valid_stores_attributes", 5),
            ("test_unit_scenario_expected", 3),
            # Four segments — still compliant
            ("test_to_dict_returns_expected", 4),
            # One segment — only the unit
            ("test_init", 1),
            ("test_add", 1),
            # Empty remainder after prefix
            ("test_", 0),
            # Consecutive underscores produce empty segments that are filtered
            ("test__foo", 1),
            ("test___a___b", 2),
            # Names that do not start with test_ return 0
            ("not_test", 0),
            ("helper_function", 0),
            ("TestInit", 0),
            ("test", 0),
            ("", 0),
        ],
    )
    def test_segment_counts(self, name: str, expected: int) -> None:
        """Parametrized check of segment counts across naming patterns."""
        assert _count_segments(name) == expected

    def test_returns_zero_for_non_test_prefix(self) -> None:
        """A function name without the ``test_`` prefix yields zero segments."""
        assert _count_segments("setup_module") == 0

    def test_filters_empty_segments(self) -> None:
        """Consecutive underscores create empty parts that are not counted."""
        # "test__a__b" -> rest = "_a__b" -> split = ['', 'a', '', 'b'] -> 2
        assert _count_segments("test__a__b") == 2


# ---------------------------------------------------------------------------
# _find_test_functions
# ---------------------------------------------------------------------------


class TestFindTestFunctions:
    """``_find_test_functions`` parses a file and returns ``(name, line)`` tuples."""

    def test_finds_sync_test_functions(self, tmp_path: Path) -> None:
        """Synchronous ``test_`` functions are returned with their line numbers."""
        f = tmp_path / "test_sample.py"
        f.write_text(
            "def test_init_with_valid_stores_attrs():\n"
            "    assert True\n"
            "\n"
            "def test_add_returns_sum():\n"
            "    assert True\n"
        )
        result = _find_test_functions(f)
        assert result == [
            ("test_init_with_valid_stores_attrs", 1),
            ("test_add_returns_sum", 4),
        ]

    def test_finds_async_test_functions(self, tmp_path: Path) -> None:
        """Asynchronous ``test_`` functions are also discovered."""
        f = tmp_path / "test_async.py"
        f.write_text(
            "async def test_fetch_with_valid_url_returns_data():\n"
            "    assert True\n"
        )
        result = _find_test_functions(f)
        assert result == [("test_fetch_with_valid_url_returns_data", 1)]

    def test_finds_nested_test_functions(self, tmp_path: Path) -> None:
        """Only top-level test functions are found (engine does not walk into nested scopes)."""
        f = tmp_path / "test_nested.py"
        f.write_text(
            "def test_outer_with_context_does_thing():\n"
            "    def test_inner_helper():\n"
            "        assert True\n"
            "    assert True\n"
        )
        result = _find_test_functions(f)
        names = [name for name, _ in result]
        assert "test_outer_with_context_does_thing" in names
        # Inner function is nested — the engine only extracts top-level functions
        assert "test_inner_helper" not in names

    def test_ignores_non_test_functions(self, tmp_path: Path) -> None:
        """Functions not starting with ``test_`` are excluded."""
        f = tmp_path / "test_sample.py"
        f.write_text(
            "def helper():\n"
            "    pass\n"
            "\n"
            "def setup():\n"
            "    pass\n"
            "\n"
            "def test_only():\n"
            "    pass\n"
        )
        result = _find_test_functions(f)
        assert result == [("test_only", 7)]

    def test_ignores_classes_and_assignments(self, tmp_path: Path) -> None:
        """Classes and module-level assignments are not treated as functions."""
        f = tmp_path / "test_sample.py"
        f.write_text(
            "class TestSomething:\n"
            "    pass\n"
            "\n"
            "test_value = 42\n"
            "\n"
            "def test_real_function_works():\n"
            "    pass\n"
        )
        result = _find_test_functions(f)
        assert result == [("test_real_function_works", 6)]

    def test_finds_test_methods_in_class(self, tmp_path: Path) -> None:
        """Test methods inside classes are also discovered by _find_test_functions."""
        f = tmp_path / "test_class.py"
        f.write_text(
            "class TestFoo:\n"
            "    def test_init_with_valid_stores(self):\n"
            "        assert True\n"
            "    def helper(self):\n"
            "        pass\n",
        )
        result = _find_test_functions(f)
        names = [name for name, _ in result]
        assert "test_init_with_valid_stores" in names
        assert "helper" not in names

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        """A completely empty file yields no test functions."""
        f = tmp_path / "test_empty.py"
        f.write_text("")
        assert _find_test_functions(f) == []

    def test_file_with_only_comments_returns_empty(self, tmp_path: Path) -> None:
        """A file containing only comments has no functions to return."""
        f = tmp_path / "test_comments.py"
        f.write_text("# just a comment\n# another comment\n")
        assert _find_test_functions(f) == []

    def test_syntax_error_returns_empty_list(self, tmp_path: Path) -> None:
        """A ``SyntaxError`` causes the file to be skipped (empty result)."""
        f = tmp_path / "test_broken.py"
        f.write_text("def test_foo(:\n    assert True\n")
        assert _find_test_functions(f) == []

    def test_returns_line_numbers_correctly(self, tmp_path: Path) -> None:
        """Line numbers reflect the actual source position of each def."""
        f = tmp_path / "test_lines.py"
        f.write_text(
            "\n"  # line 1 blank
            "\n"  # line 2 blank
            "def test_first_works_fine():\n"  # line 3
            "    assert True\n"
            "\n"
            "def test_second_also_works():\n"  # line 6
            "    assert True\n"
        )
        result = _find_test_functions(f)
        assert result == [("test_first_works_fine", 3), ("test_second_also_works", 6)]


# ---------------------------------------------------------------------------
# main() — skip flag
# ---------------------------------------------------------------------------


class TestMainSkip:
    """``--skip`` short-circuits the scan and exits 0."""

    def test_skip_prints_skipped_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--skip`` prints a SKIPPED banner and returns 0."""
        rc = main_with_argv(["scan", str(tmp_path), "--skip"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "SKIPPED" in out
        assert "--skip flag" in out

    def test_skip_with_json_prints_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--skip --json`` produces no output and returns 0."""
        rc = main_with_argv(["scan", str(tmp_path), "--skip", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.out == ""


# ---------------------------------------------------------------------------
# main() — directory errors
# ---------------------------------------------------------------------------


class TestMainDirectoryErrors:
    """Missing directories produce an error on stderr and exit 1."""

    def test_nonexistent_directory_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A non-existent directory prints an error to stderr and returns 1."""
        missing = tmp_path / "does_not_exist"
        rc = main_with_argv(["scan", str(missing)])
        assert rc == 1
        err = capsys.readouterr().err
        assert "does not exist" in err
        assert str(missing) in err


# ---------------------------------------------------------------------------
# main() — no test files
# ---------------------------------------------------------------------------


class TestMainNoTestFiles:
    """An empty or test-file-free directory reports zero functions."""

    def test_empty_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """An empty directory scans zero functions and reports success."""
        rc = main_with_argv(["scan", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Total test functions scanned: 0" in out
        assert "Violations: 0" in out
        assert "All test functions meet the naming convention." in out

    def test_directory_with_only_non_test_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Non-test ``.py`` files do not contribute to the scan."""
        (tmp_path / "helpers.py").write_text("def helper():\n    pass\n")
        (tmp_path / "conftest.py").write_text("def fixture():\n    pass\n")
        rc = main_with_argv(["scan", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Total test functions scanned: 0" in out


# ---------------------------------------------------------------------------
# main() — violations and markdown output
# ---------------------------------------------------------------------------


class TestMainViolationsMarkdown:
    """Markdown report lists violations and respects ``--strict``."""

    def test_violations_listed_no_strict_returns_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Violations are listed but exit code stays 0 without ``--strict``."""
        write_test_file(
            tmp_path / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Violations: 1" in out
        assert "test_init" in out
        assert "test_bad.py" in out

    def test_violations_with_strict_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--strict`` flips the exit code to 1 when violations exist."""
        write_test_file(
            tmp_path / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--strict"])
        assert rc == 1
        out = capsys.readouterr().out
        assert "Violations: 1" in out

    def test_no_violations_with_strict_returns_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--strict`` with no violations still returns 0."""
        write_test_file(
            tmp_path / "test_good.py",
            "def test_init_with_valid_stores_attrs():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--strict"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Violations: 0" in out
        assert "All test functions meet the naming convention." in out

    def test_violation_rate_displayed_when_functions_present(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The violation rate is printed only when test functions exist."""
        # One good (3 segments), one bad (1 segment) -> 50% violation rate
        write_test_file(
            tmp_path / "test_mixed.py",
            "def test_unit_scenario_expected():\n    assert True\n"
            "\n"
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Total test functions scanned: 2" in out
        assert "Violations: 1" in out
        assert "Violation rate: 50.0%" in out

    def test_no_violation_rate_when_zero_functions(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No violation rate line is shown when there are no test functions."""
        rc = main_with_argv(["scan", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Violation rate" not in out

    def test_report_header_present(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The markdown report always starts with the validation banner."""
        main_with_argv(["scan", str(tmp_path)])
        out = capsys.readouterr().out
        assert "TEST FUNCTION NAMING" in out
        assert "VALIDATION REPORT" in out


# ---------------------------------------------------------------------------
# main() — JSON output
# ---------------------------------------------------------------------------


class TestMainJsonOutput:
    """``--json`` emits a machine-readable report."""

    def test_json_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output includes total counts and full violation details."""
        write_test_file(
            tmp_path / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["total_test_functions"] == 1
        assert data["violation_count"] == 1
        assert data["min_segments"] == 3
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["function"] == "test_init"
        assert v["segments"] == 1
        assert v["min_required"] == 3
        assert v["file"] == "test_bad.py"
        assert v["line"] == 1

    def test_json_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output with compliant tests reports zero violations."""
        write_test_file(
            tmp_path / "test_good.py",
            "def test_unit_scenario_expected():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 1
        assert data["violation_count"] == 0
        assert data["violations"] == []

    def test_json_empty_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output for an empty directory reports all-zero counts."""
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 0
        assert data["violation_count"] == 0

    def test_json_with_strict_violations_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--json --strict`` returns 1 when violations are present."""
        write_test_file(
            tmp_path / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json", "--strict"])
        assert rc == 1


# ---------------------------------------------------------------------------
# main() — min-segments
# ---------------------------------------------------------------------------


class TestMainMinSegments:
    """Custom ``--min-segments`` thresholds change what counts as a violation."""

    def test_custom_min_segments_higher(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Raising ``--min-segments`` turns previously-compliant names into violations."""
        # 3 segments — fine at default 3, violation at 4
        write_test_file(
            tmp_path / "test_edge.py",
            "def test_unit_scenario_expected():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--min-segments", "4", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["violation_count"] == 1
        assert data["min_segments"] == 4

    def test_custom_min_segments_lower(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Lowering ``--min-segments`` lets short names pass."""
        # 1 segment — violation at default 3, fine at 1
        write_test_file(
            tmp_path / "test_short.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--min-segments", "1", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["violation_count"] == 0


# ---------------------------------------------------------------------------
# main() — ignore dirs and file filtering
# ---------------------------------------------------------------------------


class TestMainIgnoreDirs:
    """Ignored directories and non-test files are skipped during the scan."""

    @pytest.mark.parametrize("ignored", ["__pycache__", ".venv", "venv", ".tox", "dist", "build"])
    def test_ignored_directory_skipped(
        self, tmp_path: Path, ignored: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each configured ignore-dir is excluded from the recursive scan."""
        sub = tmp_path / ignored
        sub.mkdir()
        write_test_file(
            sub / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 0
        assert data["violation_count"] == 0

    def test_non_test_py_file_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A ``.py`` file that is neither ``test_*.py`` nor ``*_test.py`` is skipped."""
        write_test_file(
            tmp_path / "utils.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 0

    def test_suffix_test_file_scanned(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``*_test.py`` files are treated as test files and scanned."""
        write_test_file(
            tmp_path / "feature_test.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 1
        assert data["violation_count"] == 1

    def test_nested_directory_scanned(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``rglob`` recurses into nested subdirectories."""
        nested = tmp_path / "subdir" / "deep"
        nested.mkdir(parents=True)
        write_test_file(
            nested / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 1
        v = data["violations"][0]
        assert v["file"] == str(Path("subdir") / "deep" / "test_bad.py")


# ---------------------------------------------------------------------------
# main() — default directory
# ---------------------------------------------------------------------------


class TestMainDefaultDirectory:
    """Omitting the directory argument defaults to ``tests``."""

    def test_default_directory_is_tests(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With no directory argument the scanner targets ``./tests``."""
        # Create a tests/ dir in the cwd and chdir into tmp_path so the default
        # "tests" resolves to our temp directory.
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        write_test_file(
            tests_dir / "test_default.py",
            "def test_init():\n    assert True\n",
        )
        monkeypatch.chdir(tmp_path)
        rc = main_with_argv(["scan"])  # no directory -> defaults to "tests"
        assert rc == 0
        out = capsys.readouterr().out
        assert "Total test functions scanned: 1" in out


# ---------------------------------------------------------------------------
# main() — mixed scenarios
# ---------------------------------------------------------------------------


class TestMainMixedScenarios:
    """Combined real-world scenarios across multiple files."""

    def test_multiple_files_some_good_some_bad(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Good and bad files in one run are aggregated correctly."""
        write_test_file(
            tmp_path / "test_good.py",
            "def test_init_with_valid_stores_attrs():\n    assert True\n"
            "def test_add_with_two_ints_returns_sum():\n    assert True\n",
        )
        write_test_file(
            tmp_path / "test_bad.py",
            "def test_init():\n    assert True\n"
            "def test_add():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 4
        assert data["violation_count"] == 2
        bad_files = {v["file"] for v in data["violations"]}
        assert bad_files == {"test_bad.py"}

    def test_syntax_error_file_does_not_crash(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A syntax-error file is skipped while valid files are still scanned."""
        (tmp_path / "test_broken.py").write_text("def test_foo(:\n    pass\n")
        write_test_file(
            tmp_path / "test_good.py",
            "def test_unit_scenario_expected():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["total_test_functions"] == 1
        assert data["violation_count"] == 0

    def test_relative_path_in_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Violation file paths are reported relative to the scan root."""
        sub = tmp_path / "pkg"
        sub.mkdir()
        write_test_file(
            sub / "test_bad.py",
            "def test_init():\n    assert True\n",
        )
        rc = main_with_argv(["scan", str(tmp_path), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["violations"][0]["file"] == str(Path("pkg") / "test_bad.py")


# ---------------------------------------------------------------------------
# scan_module / scan_file
# ---------------------------------------------------------------------------


class TestScanModule:
    """``scan_module`` consumes ``ModuleInfo`` and returns ``list[Finding]``."""

    def test_returns_finding_objects(self, tmp_path: Path) -> None:
        """Violations are returned as ``Finding`` dataclass instances."""
        f = tmp_path / "test_bad.py"
        write_test_file(f, "def test_init():\n    assert True\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "test_naming"
        assert findings[0].severity == "medium"
        assert "test_init" in findings[0].description

    def test_no_violation_for_compliant_name(self, tmp_path: Path) -> None:
        """A compliant test function name produces no findings."""
        f = tmp_path / "test_good.py"
        write_test_file(f, "def test_unit_scenario_expected():\n    assert True\n")
        findings = scan_file(f)
        assert findings == []

    def test_custom_min_segments(self, tmp_path: Path) -> None:
        """``min_segments`` is respected by ``scan_file``."""
        f = tmp_path / "test_edge.py"
        write_test_file(f, "def test_unit_scenario_expected():\n    assert True\n")
        # 3 segments — fine at default 3, violation at 4
        assert scan_file(f, min_segments=3) == []
        assert len(scan_file(f, min_segments=4)) == 1

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A syntax-error file produces no findings."""
        f = tmp_path / "test_broken.py"
        f.write_text("def test_foo(:\n    pass\n")
        assert scan_file(f) == []

    def test_finds_test_methods_in_classes(self, tmp_path: Path) -> None:
        """Test methods inside classes are also found by scan_file."""
        f = tmp_path / "test_class.py"
        write_test_file(
            f,
            "class TestFoo:\n"
            "    def test_init(self):\n"
            "        assert True\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert "test_init" in findings[0].description

    def test_non_test_function_skipped(self, tmp_path: Path) -> None:
        """Non-test top-level functions are skipped by scan_module."""
        f = tmp_path / "test_mixed.py"
        write_test_file(
            f,
            "def helper():\n"
            "    pass\n"
            "\n"
            "def test_init():\n"
            "    assert True\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert "test_init" in findings[0].description

    def test_non_test_method_in_class_skipped(self, tmp_path: Path) -> None:
        """Non-test methods inside classes are skipped by scan_module."""
        f = tmp_path / "test_class_mixed.py"
        write_test_file(
            f,
            "class TestFoo:\n"
            "    def setUp(self):\n"
            "        pass\n"
            "    def test_init(self):\n"
            "        assert True\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert "test_init" in findings[0].description


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def main_with_argv(argv: list[str]) -> int:
    """Run ``main()`` with a mocked ``sys.argv``.

    The first element is treated as the program name by argparse, so the
    caller passes the full argv list (program name included).
    """
    saved = sys.argv
    sys.argv = argv
    try:
        return main()
    finally:
        sys.argv = saved


def write_test_file(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
