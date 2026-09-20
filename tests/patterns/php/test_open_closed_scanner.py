"""Tests for ``open_closed_scanner`` — PHP OCP validator.

Covers ``scan_module``, ``scan_file``, ``main``, helper functions, and
edge cases: empty files, syntax errors, no violations, custom
thresholds, and non-PHP files.

Tests that require ``tree-sitter-php`` are skipped when the optional
dependency is not installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.structs import Finding, ModuleInfo
from zolletta_metaskill.patterns.php.open_closed_scanner import (
    OpenClosedScanner,
)

TS_PHP_AVAILABLE = PHPEngine._have_tree_sitter_php()
_skip_no_ts = pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")


def _write_php(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# scan_file / scan_module tests (require tree-sitter-php)
# ---------------------------------------------------------------------------


@_skip_no_ts
class TestScanFile:
    """``scan_file`` parses a .php file and returns ``list[Finding]``."""

    def test_instanceof_chain_detected(self, tmp_path: Path) -> None:
        """An if/elseif chain with 3 instanceof branches is flagged."""
        f = tmp_path / "Processor.php"
        _write_php(
            f,
            "<?php\n"
            "class Processor {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof Foo) {\n"
            "            return 'foo';\n"
            "        } elseif ($obj instanceof Bar) {\n"
            "            return 'bar';\n"
            "        } elseif ($obj instanceof Baz) {\n"
            "            return 'baz';\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "ocp"
        assert findings[0].severity == "medium"
        assert findings[0].fix_type == "manual"
        assert "3 instanceof" in findings[0].description
        assert "polymorphism" in findings[0].description

    def test_two_branches_not_flagged(self, tmp_path: Path) -> None:
        """An if/elseif with only 2 instanceof branches is not flagged."""
        f = tmp_path / "Processor.php"
        _write_php(
            f,
            "<?php\n"
            "class Processor {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof Foo) {\n"
            "            return 'foo';\n"
            "        } elseif ($obj instanceof Bar) {\n"
            "            return 'bar';\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert findings == []

    def test_custom_min_branches(self, tmp_path: Path) -> None:
        """``min_branches=2`` flags a chain with only 2 instanceof branches."""
        f = tmp_path / "Processor.php"
        _write_php(
            f,
            "<?php\n"
            "class Processor {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof Foo) {\n"
            "            return 'foo';\n"
            "        } elseif ($obj instanceof Bar) {\n"
            "            return 'bar';\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f, min_branches=2)
        assert len(findings) == 1
        assert "2 instanceof" in findings[0].description

    def test_no_instanceof_not_flagged(self, tmp_path: Path) -> None:
        """A regular if/elseif chain without instanceof is not flagged."""
        f = tmp_path / "Processor.php"
        _write_php(
            f,
            "<?php\n"
            "class Processor {\n"
            "    public function process($x) {\n"
            "        if ($x == 1) {\n"
            "            return 'one';\n"
            "        } elseif ($x == 2) {\n"
            "            return 'two';\n"
            "        } elseif ($x == 3) {\n"
            "            return 'three';\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert findings == []

    def test_write_php_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        """An empty .php file produces no findings."""
        f = tmp_path / "empty.php"
        _write_php(f, "<?php\n")
        findings = OpenClosedScanner.scan_file(f)
        assert findings == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A file with a syntax error produces no findings."""
        f = tmp_path / "broken.php"
        _write_php(f, "<?php\nclass {\n    \n")
        findings = OpenClosedScanner.scan_file(f)
        assert findings == []

    def test_file_path_in_finding(self, tmp_path: Path) -> None:
        """The finding's file field matches the path."""
        f = tmp_path / "Processor.php"
        _write_php(
            f,
            "<?php\n"
            "class Processor {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof C) {\n"
            "            return 3;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 1
        assert findings[0].file == str(f)

    def test_write_php_no_classes_returns_ocp(self, tmp_path: Path) -> None:
        """A file with only free functions can still have violations."""
        f = tmp_path / "functions.php"
        _write_php(
            f,
            "<?php\n"
            "function dispatch($obj) {\n"
            "    if ($obj instanceof A) {\n"
            "        return 'a';\n"
            "    } elseif ($obj instanceof B) {\n"
            "        return 'b';\n"
            "    } elseif ($obj instanceof C) {\n"
            "        return 'c';\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "ocp"

    def test_non_php_file_returns_empty(self, tmp_path: Path) -> None:
        """A non-.php file returns no findings (no matching engine)."""
        f = tmp_path / "script.py"
        _write_php(f, "class Foo:\n    pass\n")
        findings = OpenClosedScanner.scan_file(f)
        assert findings == []

    def test_write_php_multiple_chains_returns_2(self, tmp_path: Path) -> None:
        """Multiple instanceof chains produce multiple findings."""
        f = tmp_path / "Multi.php"
        _write_php(
            f,
            "<?php\n"
            "class Multi {\n"
            "    public function a($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof C) {\n"
            "            return 3;\n"
            "        }\n"
            "    }\n"
            "    public function b($obj) {\n"
            "        if ($obj instanceof X) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof Y) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof Z) {\n"
            "            return 3;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 2

    def test_write_php_four_branches_contains_4_instanceof(self, tmp_path: Path) -> None:
        """An if/elseif chain with 4 instanceof branches is flagged."""
        f = tmp_path / "Four.php"
        _write_php(
            f,
            "<?php\n"
            "class Four {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof C) {\n"
            "            return 3;\n"
            "        } elseif ($obj instanceof D) {\n"
            "            return 4;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 1
        assert "4 instanceof" in findings[0].description

    def test_else_clause_not_counted(self, tmp_path: Path) -> None:
        """An else clause (no instanceof) does not affect the branch count."""
        f = tmp_path / "WithElse.php"
        _write_php(
            f,
            "<?php\n"
            "class WithElse {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof C) {\n"
            "            return 3;\n"
            "        } else {\n"
            "            return 0;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 1
        assert "3 instanceof" in findings[0].description

    def test_write_php_mixed_branches_contains_3_instanceof(self, tmp_path: Path) -> None:
        """Only branches with instanceof are counted toward the threshold."""
        f = tmp_path / "Dispatcher.php"
        _write_php(
            f,
            "<?php\n"
            "class Dispatcher {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof C) {\n"
            "            return 3;\n"
            "        } elseif ($x == 4) {\n"
            "            return 4;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        # 3 instanceof branches (A, B, C) out of 4 total → flagged with default=3
        findings = OpenClosedScanner.scan_file(f)
        assert len(findings) == 1
        assert "3 instanceof" in findings[0].description


@_skip_no_ts
class TestScanModule:
    """``scan_module`` consumes ``ModuleInfo`` and returns ``list[Finding]``."""

    def test_returns_finding_objects(self, tmp_path: Path) -> None:
        """Violations are returned as ``Finding`` dataclass instances."""
        f = tmp_path / "Processor.php"
        _write_php(
            f,
            "<?php\n"
            "class Processor {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        } elseif ($obj instanceof C) {\n"
            "            return 3;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        OpenClosedScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        findings = OpenClosedScanner.scan_module(module)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)

    def test_syntax_error_module(self, tmp_path: Path) -> None:
        """A module with ``has_syntax_error`` returns no findings."""
        f = tmp_path / "bad.php"
        _write_php(f, "<?php\nclass {\n")
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        OpenClosedScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        assert module.has_syntax_error
        assert OpenClosedScanner.scan_module(module) == []

    def test_non_php_language(self, tmp_path: Path) -> None:
        """A module with language != 'php' returns no findings."""
        module = ModuleInfo(
            path=tmp_path / "test.py",
            language="python",
            has_syntax_error=False,
        )
        assert OpenClosedScanner.scan_module(module) == []

    def test_write_php_no_violations_returns_empty_list(self, tmp_path: Path) -> None:
        """A module with no instanceof chains returns no findings."""
        f = tmp_path / "Clean.php"
        _write_php(
            f,
            "<?php\n"
            "class Clean {\n"
            "    public function process($x) {\n"
            "        if ($x == 1) {\n"
            "            return 'one';\n"
            "        } elseif ($x == 2) {\n"
            "            return 'two';\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        OpenClosedScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        assert OpenClosedScanner.scan_module(module) == []

    def test_custom_min_branches(self, tmp_path: Path) -> None:
        """``scan_module`` respects a custom ``min_branches`` threshold."""
        f = tmp_path / "Two.php"
        _write_php(
            f,
            "<?php\n"
            "class Two {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        OpenClosedScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        # Default threshold (3) → not flagged
        assert OpenClosedScanner.scan_module(module) == []
        # min_branches=2 → flagged
        assert len(OpenClosedScanner.scan_module(module, min_branches=2)) == 1


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal PHP settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "php",
        "python": None,
        "php": {
            "autoload": {"psr-4": {"App\\": "src/"}},
            "patterns": {},
        },
    }
    php_overrides = overrides.pop("php", None)
    if isinstance(php_overrides, dict):
        base_php = settings["php"]
        assert isinstance(base_php, dict)
        for key, value in php_overrides.items():
            if isinstance(value, dict) and isinstance(base_php.get(key), dict):
                base_php[key].update(value)
            else:
                base_php[key] = value
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Chdir into tmp_path and run main() with *argv*."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    return OpenClosedScanner.main()


_INSTANCEOF_LADDER = (
    "<?php\n"
    "class Bad {\n"
    "    public function process($obj) {\n"
    "        if ($obj instanceof A) {\n"
    "            return 1;\n"
    "        } elseif ($obj instanceof B) {\n"
    "            return 2;\n"
    "        } elseif ($obj instanceof C) {\n"
    "            return 3;\n"
    "        }\n"
    "    }\n"
    "}\n"
)

_CLEAN_PHP = (
    "<?php\n"
    "class Good {\n"
    "    public function process($x) {\n"
    "        if ($x == 1) { return 'one'; }\n"
    "    }\n"
    "}\n"
)


class TestMain:
    """Tests for ``main()`` CLI entry point."""

    def test_check_disabled_reports_skipped(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, php={"patterns": {"check_ocp": False}})
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_check_disabled_json(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, php={"patterns": {"check_ocp": False}})
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        assert json.loads(out)["skipped"] is True

    def test_main_missing_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "source" in err

    @_skip_no_ts
    def test_main_all_clear(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Good.php", _CLEAN_PHP)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    @_skip_no_ts
    def test_main_violation_report_only(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Bad.php", _INSTANCEOF_LADDER)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "OCP violations" in out
        assert "instanceof" in out
        assert "report-only" in out

    @_skip_no_ts
    def test_main_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Bad.php", _INSTANCEOF_LADDER)
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        payload = json.loads(out)
        assert payload["violation_count"] == 1
        assert payload["min_branches"] == 3
        assert payload["scanned_files"] == 1

    @_skip_no_ts
    def test_main_custom_min_branches(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path, php={"patterns": {"ocp_min_branches": 2}})
        _write_php(
            tmp_path / "src" / "Two.php",
            "<?php\n"
            "class Two {\n"
            "    public function process($obj) {\n"
            "        if ($obj instanceof A) {\n"
            "            return 1;\n"
            "        } elseif ($obj instanceof B) {\n"
            "            return 2;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "OCP violations" in out

    @_skip_no_ts
    def test_main_report_shows_threshold(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        _write_php(tmp_path / "src" / "Good.php", _CLEAN_PHP)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "threshold: 3" in out
