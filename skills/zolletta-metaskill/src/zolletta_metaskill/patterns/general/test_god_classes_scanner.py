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
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding, ModuleInfo


class TestGodClassesScanner:
    """Scan Python test files for test class metrics and mixed-SUT detection.

    Triage tool for test-side God classes. Reports test classes sorted by
    size, with method count and optional method name listing. Use
    --show-methods to spot test classes that test multiple unrelated SUTs.
    """

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
        EngineRegistry.ensure_python()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:
            return []
        module = engine.parse_module(path)
        return TestGodClassesScanner.scan_module(module)

    @staticmethod
    def _resolve_top_n(settings: dict[str, Any], py_langs: set[str]) -> int:
        """Resolve top N limit from settings (highest configured wins)."""
        top_limits: list[int] = []
        for lang in sorted(py_langs):
            value = ProjectConfig.setting(settings, f"{lang}.patterns.test_god_classes_top", None)
            if isinstance(value, int) and not isinstance(value, bool):
                top_limits.append(value)
        return max(top_limits) if top_limits else 30

    @staticmethod
    def _collect_metrics(roots: list[Path]) -> list[dict[str, Any]]:
        """Collect test class metrics across all roots."""
        all_results: list[dict[str, Any]] = []
        for root in roots:
            for py in ProjectConfig.iter_files(root, {".py"}):
                engine = EngineRegistry.get_for_file(py)
                # pragma: no mutate start — unreachable for .py paths once PythonEngine is
                # registered
                if engine is None:  # pragma: no cover — the registry always serves .py files
                    continue
                # pragma: no mutate end
                module = engine.parse_module(py)
                all_results.extend(TestGodClassesScanner._test_class_metrics(module))
        return all_results

    @staticmethod
    def _emit_json(
        roots: list[Path], top_n: int, total_classes: int, classes: list[dict[str, Any]]
    ) -> None:
        """Emit JSON formatted test class metrics."""
        print(
            json.dumps(
                {
                    "directories": [str(root) for root in roots],
                    "top": top_n,
                    "total_classes": total_classes,
                    "classes": classes,
                },
                indent=2,
            )
        )

    @staticmethod
    def _emit_text(top: list[dict[str, Any]], show_methods: bool) -> None:
        """Emit text formatted test class metrics."""
        if show_methods:
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

    @staticmethod
    def main() -> int:  # pragma: no mutate — help text is not a tested contract
        """Entry point for the test God class scanner CLI."""
        # pragma: no mutate start — help/description text is not a tested contract
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
        # pragma: no mutate end
        args = parser.parse_args()

        EngineRegistry.ensure_python()
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

        top_n = TestGodClassesScanner._resolve_top_n(settings, py_langs)
        all_results = TestGodClassesScanner._collect_metrics(roots)

        if not all_results:
            print("No test classes found", file=sys.stderr)
            return 0

        all_results.sort(key=lambda r: r["lines"], reverse=True)
        top = all_results[:top_n]

        if args.json:
            TestGodClassesScanner._emit_json(roots, top_n, len(all_results), top)
            return 0

        TestGodClassesScanner._emit_text(top, args.show_methods)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(TestGodClassesScanner.main())
