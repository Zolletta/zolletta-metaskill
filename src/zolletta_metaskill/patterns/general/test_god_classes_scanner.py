#!/usr/bin/env python3
"""Scan Python test files for test class metrics and mixed-SUT detection.

Triage tool for test-side God classes. Reports test classes sorted by size,
with method count and optional method name listing. Use --show-methods to
spot test classes that test multiple unrelated SUTs.

Test roots come from ``python.paths.tests`` in ``settings.json``; the row
limit comes from ``python.patterns.test_god_classes_top`` (default 30).
File enumeration is git-ignore aware.

Usage:
    python3 test_god_classes_scanner.py [--show-methods] [--json]

Options:
    --show-methods    List all method names per class (helps spot mixed SUTs)
    --json            Output as JSON instead of a table.

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.python_engine import PythonEngine
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding, ModuleInfo


class TestGodClassesScanner:
    """Scan Python test files for test class metrics and mixed-SUT detection.

    Triage tool for test-side God classes. Reports test classes sorted by
    size, with method count and optional method name listing. Use
    --show-methods to spot test classes that test multiple unrelated SUTs.
    """

    @staticmethod
    def _ensure_python_engine() -> None:
        """Ensure the PythonEngine is registered."""
        EngineRegistry.ensure(PythonEngine())

    @staticmethod
    def _test_class_metrics(module: ModuleInfo) -> list[dict[str, Any]]:
        """Compute raw test class metric dicts from a :class:`ModuleInfo`.

        Args:
            module: The parsed module to inspect.

        Returns:
            A list of dicts with keys ``file``, ``class``, ``lines``, ``methods``,
            ``method_names``, ``start``, and ``end``.

        """
        results: list[dict[str, Any]] = []
        for cls in module.classes:
            start = cls.lineno
            end = cls.end_lineno
            lines = end - start + 1
            method_names = [m.name for m in cls.methods]
            results.append(
                {
                    "file": str(module.path),
                    "class": cls.name,
                    "lines": lines,
                    "methods": len(cls.methods),
                    "method_names": method_names,
                    "start": start,
                    "end": end,
                }
            )
        return results

    @staticmethod
    def scan_module(module: ModuleInfo) -> list[Finding]:
        """Scan a :class:`ModuleInfo` and return test class metric findings.

        Args:
            module: The parsed module to inspect.

        Returns:
            A list of :class:`Finding` objects, one per class.

        """
        findings: list[Finding] = []
        for r in TestGodClassesScanner._test_class_metrics(module):
            findings.append(
                Finding(
                    file=r["file"],
                    line=r["start"],
                    category="test_god_class",
                    severity="low",
                    description=(
                        f"class={r['class']} lines={r['lines']} "
                        f"methods={r['methods']} "
                        f"method_names={','.join(r['method_names'])} "
                        f"start={r['start']} end={r['end']}"
                    ),
                    fix_type="skip",
                )
            )
        return findings

    @staticmethod
    def scan_file(path: Path) -> list[Finding]:
        """Backward-compatible wrapper that uses the registry to get an engine.

        Args:
            path: Path to a Python source file.

        Returns:
            A list of :class:`Finding` objects for each class in the file.

        """
        TestGodClassesScanner._ensure_python_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:
            return []
        module = engine.parse_module(path)
        return TestGodClassesScanner.scan_module(module)

    @staticmethod
    def main() -> int:
        """Entry point for the test God class scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Scan Python test classes for size and mixed-SUT detection. "
            "Roots and thresholds come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--show-methods",
            action="store_true",
            help="List all method names per class (helps spot mixed SUTs)",
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        TestGodClassesScanner._ensure_python_engine()
        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_test_god_classes")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(
                args.json, "check_test_god_classes disabled in settings.json"
            )
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.test_roots(settings, py_langs))
        if not roots:
            print(
                "Error: no configured test directories exist on disk",
                file=sys.stderr,
            )
            return 1

        top_limits: list[int] = []
        for lang in sorted(py_langs):
            value = ProjectConfig.setting(settings, f"{lang}.patterns.test_god_classes_top", None)
            if isinstance(value, int) and not isinstance(value, bool):
                top_limits.append(value)
        top_n = max(top_limits) if top_limits else 30

        all_results: list[dict[str, Any]] = []
        for root in roots:
            for py in ProjectConfig.iter_files(root, {".py"}):
                engine = EngineRegistry.get_for_file(py)
                if engine is None:  # pragma: no cover
                    continue
                module = engine.parse_module(py)
                all_results.extend(TestGodClassesScanner._test_class_metrics(module))

        if not all_results:
            print("No test classes found", file=sys.stderr)
            return 0

        all_results.sort(key=lambda r: r["lines"], reverse=True)
        top = all_results[:top_n]

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "top": top_n,
                        "total_classes": len(all_results),
                        "classes": top,
                    },
                    indent=2,
                )
            )
            return 0

        if args.show_methods:
            for r in top:
                print(f"\n=== {r['class']} ({r['lines']} lines, {r['methods']} methods) ===")
                for name in r["method_names"]:
                    print(f"  {name}")
        else:
            print(f"{'LINES':>6} {'METHODS':>7}  CLASS  (file:start-end)")
            print("-" * 100)
            for r in top:
                print(
                    f"{r['lines']:>6} {r['methods']:>7}  "
                    f"{r['class']}  ({r['file']}:{r['start']}-{r['end']})"
                )

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(TestGodClassesScanner.main())
