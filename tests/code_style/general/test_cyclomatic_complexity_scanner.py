"""Tests for cyclomatic_complexity_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.general.cyclomatic_complexity_scanner import (
    CyclomaticComplexityScanner,
)
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.structs import Finding

TS_PHP_AVAILABLE = PHPEngine._have_tree_sitter_php()


class TestCyclomaticComplexityScanner:
    # --- Helpers. ---

    @staticmethod
    def _write_settings(dirpath: Path, **overrides: object) -> Path:
        """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
        settings: dict[str, object] = {
            "language": "python",
            "python": {"code_style": {}},
            "php": None,
        }
        settings.update(overrides)
        meta = dirpath / ".zolletta-metaskill"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "settings.json"
        path.write_text(json.dumps(settings))
        return path

    @staticmethod
    def _git_init(root: Path) -> None:
        """Initialise a git repo at *root* so gitignore rules apply."""
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    @staticmethod
    def _write(path: Path, source: str) -> Path:
        """Write *source* to *path* and return it."""
        path.write_text(source)
        return path

    @staticmethod
    def _complex_python(ifs: int = 0, loops: int = 0, name: str = "fn") -> str:
        """Return Python source for a function with the given complexity."""
        lines = [f"def {name}(x):"]
        lines += [f"    if x == {i}:\n        pass" for i in range(ifs)]
        lines += [f"    for i in range({i}):\n        pass" for i in range(loops)]
        lines.append("    return x")
        return "\n".join(lines) + "\n"

    # --- Tests for CyclomaticComplexityScanner.resolve_extensions(). ---

    def test_python_language_returns_py(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, language="python")
        assert CyclomaticComplexityScanner.resolve_extensions(settings) == {".py"}

    def test_php_language_returns_php(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, language="php", python=None, php={"code_style": {}}
        )
        assert CyclomaticComplexityScanner.resolve_extensions(settings) == {".php"}

    def test_polyglot_settings_scans_all_configured_languages(
        self, tmp_path: Path
    ) -> None:
        settings = self._write_settings(tmp_path, language="python", php={"code_style": {}})
        assert CyclomaticComplexityScanner.resolve_extensions(settings) == {
            ".py",
            ".php",
        }

    def test_missing_settings_falls_back_to_all_engines(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert CyclomaticComplexityScanner.resolve_extensions(missing) == {
            ".py",
            ".php",
        }

    def test_unknown_language_falls_back_to_all_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = self._write_settings(tmp_path, language="go", python=None)
        result = CyclomaticComplexityScanner.resolve_extensions(settings)
        err = capsys.readouterr().err
        assert "no engine for language 'go'" in err
        assert result == {".py", ".php"}

    def test_invalid_json_falls_back(self, tmp_path: Path) -> None:
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        bad = meta / "settings.json"
        bad.write_text("{ not json")
        assert CyclomaticComplexityScanner.resolve_extensions(bad) == {".py", ".php"}

    def test_disabled_language_not_scanned(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_cyclomatic_complexity": False}},
            php={"code_style": {}},
        )
        assert CyclomaticComplexityScanner.resolve_extensions(settings) == {".php"}

    def test_all_languages_disabled_returns_empty(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"check_cyclomatic_complexity": False}},
        )
        assert CyclomaticComplexityScanner.resolve_extensions(settings) == set()

    # --- Tests for CyclomaticComplexityScanner.resolve_max_complexity(). ---

    def test_reads_max_complexity_from_settings(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, python={"code_style": {"max_cyclomatic_complexity": 3}}
        )
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 3

    def test_smallest_limit_wins_across_languages(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_cyclomatic_complexity": 12}},
            php={"code_style": {"max_cyclomatic_complexity": 8}},
        )
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 8

    def test_no_configured_limit_falls_back_to_default(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path)  # code_style is empty
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 10

    def test_missing_settings_falls_back_to_default(self, tmp_path: Path) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert CyclomaticComplexityScanner.resolve_max_complexity(missing) == 10

    def test_language_field_without_section_falls_back(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, python=None)
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 10

    def test_non_integer_limit_falls_back(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, python={"code_style": {"max_cyclomatic_complexity": "10"}}
        )
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 10

    def test_boolean_limit_falls_back(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, python={"code_style": {"max_cyclomatic_complexity": True}}
        )
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 10

    def test_disabled_language_limit_ignored(self, tmp_path: Path) -> None:
        """A disabled language's max_cyclomatic_complexity doesn't lower it."""
        settings = self._write_settings(
            tmp_path,
            language="python",
            python={"code_style": {"max_cyclomatic_complexity": 15}},
            php={
                "code_style": {
                    "check_cyclomatic_complexity": False,
                    "max_cyclomatic_complexity": 1,
                }
            },
        )
        assert CyclomaticComplexityScanner.resolve_max_complexity(settings) == 15

    # --- Tests for Python complexity counting (ruff C901 parity). ---

    def test_python_if_elif_else(self, tmp_path: Path) -> None:
        src = (
            "def f(x):\n"
            "    if x == 1:\n"
            "        pass\n"
            "    elif x == 2:\n"
            "        pass\n"
            "    else:\n"
            "        pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        assert len(findings) == 1
        assert "complexity 3 (max 2)" in findings[0].description

    def test_python_loops_counted(self, tmp_path: Path) -> None:
        src = (
            "def f(xs):\n"
            "    for x in xs:\n"
            "        pass\n"
            "    while xs:\n"
            "        break\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        assert len(findings) == 1
        assert "complexity 3 (max 2)" in findings[0].description

    def test_python_async_constructs_counted(self, tmp_path: Path) -> None:
        src = (
            "async def f(xs):\n"
            "    async for x in xs:\n"
            "        pass\n"
            "    async def inner():\n"
            "        if xs:\n"
            "            pass\n"
            "    await inner()\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        by_name = {x.description.split("'")[1]: x for x in findings}
        assert "complexity 4 (max 2)" in by_name["f"].description
        assert "complexity 2 (max 2)" not in by_name.get(
            "f.inner", Finding(file="", line=0, category="", severity="",
                               description="", fix_type="")
        ).description

    def test_python_except_handlers_counted(self, tmp_path: Path) -> None:
        src = (
            "def f():\n"
            "    try:\n"
            "        pass\n"
            "    except ValueError:\n"
            "        pass\n"
            "    except KeyError:\n"
            "        pass\n"
            "    finally:\n"
            "        pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        assert len(findings) == 1
        assert "complexity 3 (max 2)" in findings[0].description

    def test_python_try_else_counts_else(self, tmp_path: Path) -> None:
        """Ruff C901 counts a ``try`` ``else`` clause as a decision point."""
        src = (
            "def f():\n"
            "    try:\n"
            "        pass\n"
            "    except ValueError:\n"
            "        pass\n"
            "    else:\n"
            "        pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        assert len(findings) == 1
        assert "complexity 3 (max 2)" in findings[0].description

    def test_python_except_star_counted(self, tmp_path: Path) -> None:
        src = (
            "def f():\n"
            "    try:\n"
            "        pass\n"
            "    except* ValueError:\n"
            "        pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "complexity 2 (max 1)" in findings[0].description

    def test_python_match_cases_counted(self, tmp_path: Path) -> None:
        src = (
            "def f(x):\n"
            "    match x:\n"
            "        case 1:\n"
            "            pass\n"
            "        case 2:\n"
            "            pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        assert len(findings) == 1
        assert "complexity 3 (max 2)" in findings[0].description

    def test_python_match_wildcard_not_counted(self, tmp_path: Path) -> None:
        """``case _`` and bare captures are catch-alls — no decision point."""
        src = (
            "def f(x):\n"
            "    match x:\n"
            "        case 1:\n"
            "            pass\n"
            "        case _:\n"
            "            pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "complexity 2 (max 1)" in findings[0].description

    def test_python_match_bare_capture_not_counted(self, tmp_path: Path) -> None:
        src = (
            "def f(x):\n"
            "    match x:\n"
            "        case 1:\n"
            "            pass\n"
            "        case y:\n"
            "            pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "complexity 2 (max 1)" in findings[0].description

    def test_python_match_guard_counts_case(self, tmp_path: Path) -> None:
        """A guarded catch-all case is still a decision point."""
        src = (
            "def f(x):\n"
            "    match x:\n"
            "        case y if y > 0:\n"
            "            pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "complexity 2 (max 1)" in findings[0].description

    def test_python_boolop_ternary_comprehension_not_counted(
        self, tmp_path: Path
    ) -> None:
        """BoolOp, IfExp, and comprehensions add no decision points (ruff)."""
        src = (
            "def f(a, b, c, xs):\n"
            "    ok = a and b or c\n"
            "    n = 1 if ok else 2\n"
            "    return [x for x in xs if x]\n"
        )
        f = self._write(tmp_path / "m.py", src)
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []

    def test_python_assert_with_not_counted(self, tmp_path: Path) -> None:
        src = (
            "def f(x):\n"
            "    assert x\n"
            "    with open('f') as h:\n"
            "        pass\n"
        )
        f = self._write(tmp_path / "m.py", src)
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []

    def test_python_nested_def_counts_and_reports_independently(
        self, tmp_path: Path
    ) -> None:
        src = (
            "def outer(x):\n"
            "    if x:\n"
            "        pass\n"
            "    def inner(y):\n"
            "        while y:\n"
            "            pass\n"
            "    return inner\n"
        )
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        descs = [x.description for x in findings]
        assert any(
            "'outer' has cyclomatic complexity 4" in d for d in descs
        )
        assert any("'outer.inner' has cyclomatic complexity 2" not in d for d in descs)
        # inner has complexity 2 = within max 2, not flagged; but with max 1:
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        descs = [x.description for x in findings]
        assert any("'outer.inner'" in d for d in descs)

    def test_python_method_qualified_name(self, tmp_path: Path) -> None:
        src = "class Foo:\n    def bar(self, x):\n        if x:\n            pass\n"
        f = self._write(tmp_path / "m.py", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "Method 'Foo.bar'" not in findings[0].description
        assert "Function 'Foo.bar'" in findings[0].description

    def test_python_finding_fields(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "m.py", "def f(x):\n    if x:\n        pass\n")
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        finding = findings[0]
        assert isinstance(finding, Finding)
        assert finding.category == "cyclomatic_complexity"
        assert finding.severity == "medium"
        assert finding.fix_type == "manual"
        assert finding.line == 1
        assert finding.file == str(f)

    def test_python_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "broken.py", "def foo(:\n    pass\n")
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []

    def test_python_unreadable_file_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> bytes:
            raise OSError("unreadable")

        monkeypatch.setattr(Path, "read_bytes", _fail)
        f = tmp_path / "m.py"
        f.touch()
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []

    # --- Tests for PHP complexity counting. ---

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_decision_points_counted(self, tmp_path: Path) -> None:
        src = (
            "<?php\n"
            "function f($x) {\n"
            "    if ($x) {} elseif ($x) {}\n"
            "    foreach ($x as $v) {}\n"
            "    while ($x) {}\n"
            "    do {} while ($x);\n"
            "}\n"
        )
        f = self._write(tmp_path / "f.php", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=2)
        assert len(findings) == 1
        # 1 + if + elseif + foreach + while + do = 6
        assert "complexity 6 (max 2)" in findings[0].description

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_switch_match_try_ternary_boolean(self, tmp_path: Path) -> None:
        src = (
            "<?php\n"
            "function f($x) {\n"
            "    switch ($x) { case 1: break; default: break; }\n"
            "    $m = match($x) { 1 => 'a', default => 'b' };\n"
            "    try {} catch (E $e) {} finally {}\n"
            "    $t = $x ? 1 : 2;\n"
            "    if ($a && $b || $c ?? $d) {}\n"
            "}\n"
        )
        f = self._write(tmp_path / "f.php", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=5)
        assert len(findings) == 1
        # 1 + case + match-arm + catch + ternary + if + && + || + ?? = 9
        assert "complexity 9 (max 5)" in findings[0].description

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_method_qualified_name(self, tmp_path: Path) -> None:
        src = (
            "<?php\n"
            "class C {\n"
            "    public function m() { if (true) {} }\n"
            "}\n"
        )
        f = self._write(tmp_path / "f.php", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "Method 'C.m' has cyclomatic complexity 2" in findings[0].description

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_closure_reported_independently(self, tmp_path: Path) -> None:
        src = (
            "<?php\n"
            "function f($x) {\n"
            "    $cl = function () use ($x) { if ($x) {} };\n"
            "}\n"
        )
        f = self._write(tmp_path / "f.php", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        descs = [x.description for x in findings]
        assert any("'f' has cyclomatic complexity 3" in d for d in descs)
        assert any("Closure 'f.closure'" in d for d in descs)

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_arrow_function_reported(self, tmp_path: Path) -> None:
        src = "<?php\n$a = fn($x) => $x ? 1 : 2;\n"
        f = self._write(tmp_path / "f.php", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "Closure 'arrow'" in findings[0].description

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_for_and_non_decision_operators(self, tmp_path: Path) -> None:
        """``for`` counts; non-branching binary operators do not."""
        src = (
            "<?php\n"
            "function f($x) {\n"
            "    for ($i = 0; $i < 3; $i++) {}\n"
            "    $y = $x + 1 === 2;\n"
            "}\n"
        )
        f = self._write(tmp_path / "f.php", src)
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=1)
        assert len(findings) == 1
        assert "complexity 2 (max 1)" in findings[0].description

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "broken.php", "<?php\nfunction f( {\n")
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []

    def test_php_parse_failure_warns(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> None:
            raise ImportError("tree-sitter-php is required")

        monkeypatch.setattr(PHPEngine, "parse_raw", _fail)
        f = self._write(tmp_path / "f.php", "<?php\nfunction f() {}\n")
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []
        assert "Warning: could not parse" in capsys.readouterr().err

    # --- Tests for CyclomaticComplexityScanner.scan_file(). ---

    def test_scan_file_python_function(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "m.py", self._complex_python(ifs=12))
        findings = CyclomaticComplexityScanner.scan_file(f, max_complexity=10)
        assert len(findings) == 1
        assert findings[0].file == str(f)
        assert "'fn'" in findings[0].description

    def test_scan_file_at_limit_passes(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "m.py", self._complex_python(ifs=9))
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=10) == []

    def test_scan_file_unknown_extension_returns_empty(self, tmp_path: Path) -> None:
        f = self._write(tmp_path / "notes.txt", "def f(x):\n    if x: pass\n")
        assert CyclomaticComplexityScanner.scan_file(f, max_complexity=1) == []

    # --- Tests for CyclomaticComplexityScanner.scan_directory(). ---

    def test_scans_only_matching_extension(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "a.py", self._complex_python(ifs=12))
        self._write(root / "b.php", "<?php\nfunction g() { if (true) {} }\n")
        findings = CyclomaticComplexityScanner.scan_directory(
            root, max_complexity=10, extensions={".py"}
        )
        assert len(findings) == 1
        assert findings[0].file == str(root / "a.py")

    def test_nested_directories_scanned(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        sub = root / "pkg" / "sub"
        sub.mkdir(parents=True)
        self._write(sub / "deep.py", self._complex_python(ifs=12))
        findings = CyclomaticComplexityScanner.scan_directory(
            root, max_complexity=10, extensions={".py"}
        )
        assert len(findings) == 1
        assert findings[0].file == str(sub / "deep.py")

    def test_gitignored_file_skipped(self, tmp_path: Path) -> None:
        self._git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "ignored.py", self._complex_python(ifs=12))
        self._write(root / "real.py", "def ok(x):\n    return x\n")
        findings = CyclomaticComplexityScanner.scan_directory(
            root, max_complexity=10, extensions={".py"}
        )
        assert findings == []

    def test_outside_git_repo_scans_everything(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        vendor = root / "vendor"
        vendor.mkdir(parents=True)
        self._write(vendor / "dep.py", self._complex_python(ifs=12))
        findings = CyclomaticComplexityScanner.scan_directory(
            root, max_complexity=10, extensions={".py"}
        )
        assert len(findings) == 1

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir()
        assert (
            CyclomaticComplexityScanner.scan_directory(
                root, max_complexity=10, extensions={".py"}
            )
            == []
        )

    def test_max_complexity_resolved_from_settings(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, python={"code_style": {"max_cyclomatic_complexity": 2}}
        )
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=3))
        findings = CyclomaticComplexityScanner.scan_directory(
            root, extensions={".py"}, settings_path=settings
        )
        assert len(findings) == 1

    def test_extensions_resolved_from_settings(self, tmp_path: Path) -> None:
        """Omitted extensions resolve from settings.json (python → .py)."""
        settings = self._write_settings(tmp_path, language="python")
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=12))
        self._write(root / "f.php", "<?php\nfunction g() { if (true) {} }\n")
        findings = CyclomaticComplexityScanner.scan_directory(
            root, settings_path=settings
        )
        assert len(findings) == 1
        assert findings[0].file == str(root / "m.py")

    def test_git_missing_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_git(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("git not installed")

        monkeypatch.setattr(subprocess, "run", _no_git)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=12))
        findings = CyclomaticComplexityScanner.scan_directory(
            root, max_complexity=10, extensions={".py"}
        )
        assert len(findings) == 1

    # --- Tests for CyclomaticComplexityScanner.main(). ---

    def test_main_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_cyclomatic_complexity=false for all languages → SKIPPED."""
        monkeypatch.chdir(tmp_path)
        self._write_settings(
            tmp_path,
            python={"code_style": {"check_cyclomatic_complexity": False}},
        )
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=12))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = CyclomaticComplexityScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(
            tmp_path,
            python={"code_style": {"check_cyclomatic_complexity": False}},
        )
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = CyclomaticComplexityScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured source directory on disk → usage error."""
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = CyclomaticComplexityScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "ok.py", "def ok(x):\n    return x\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = CyclomaticComplexityScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_violation_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=12))
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = CyclomaticComplexityScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "m.py" in out
        assert "fn" in out

    def test_main_json_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=12))
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = CyclomaticComplexityScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["max_complexity"] == 10
        assert report["violation_count"] == 1
        assert report["violations"][0]["function"] == "fn"
        assert report["violations"][0]["complexity"] == 13
        assert report["violations"][0]["over"] == 3

    def test_main_unparsable_file_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file with no registered engine does not abort the scan."""
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        self._write(root / "m.py", self._complex_python(ifs=12))
        monkeypatch.setattr(EngineRegistry, "get_for_file", lambda _p: None)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = CyclomaticComplexityScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
