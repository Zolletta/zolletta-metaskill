#!/usr/bin/env python3
"""Scan Python source files for class metrics (lines, methods, attributes).

Triage tool for God class detection. Reports every class sorted by line count,
with method count, public method count, and self.* attribute count.

Scan roots come from ``python.paths.source`` in ``settings.json``; the
``--top`` and ``--min-lines`` thresholds come from
``python.patterns.class_metrics_top`` (default 30) and
``python.patterns.class_metrics_min_lines`` (default 50). File
enumeration is git-ignore aware.

Usage:
    python3 class_metrics_scanner.py [--json]

Options:
    --json          Output as JSON instead of a table.

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


class ClassMetricsScanner:
    """Scan Python source files for class metrics (lines, methods, attributes).

    Triage tool for God class detection. Reports every class sorted by line
    count, with method count, public method count, and self.* attribute count.
    """

    @staticmethod
    def _ensure_python_engine() -> None:
        """Ensure the PythonEngine is registered."""
        EngineRegistry.ensure(PythonEngine())

    @staticmethod
    def _class_metrics(module: ModuleInfo) -> list[dict[str, Any]]:
        """Compute raw class metric dicts from a :class:`ModuleInfo`.

        Args:
            module: The parsed module to inspect.

        Returns:
            A list of dicts with keys ``file``, ``class``, ``lines``, ``methods``,
            ``public``, ``attrs``, ``start``, and ``end``.

        """
        results: list[dict[str, Any]] = []
        for cls in module.classes:
            start = cls.lineno
            end = cls.end_lineno
            lines = end - start + 1
            methods = len(cls.methods)
            public = sum(1 for m in cls.methods if m.is_public)
            attrs = len(cls.attributes)
            results.append(
                {
                    "file": str(module.path),
                    "class": cls.name,
                    "lines": lines,
                    "methods": methods,
                    "public": public,
                    "attrs": attrs,
                    "start": start,
                    "end": end,
                }
            )
        return results

    @staticmethod
    def scan_module(module: ModuleInfo) -> list[Finding]:
        """Scan a :class:`ModuleInfo` and return class metric findings.

        Args:
            module: The parsed module to inspect.

        Returns:
            A list of :class:`Finding` objects, one per class.

        """
        findings: list[Finding] = []
        for r in ClassMetricsScanner._class_metrics(module):
            findings.append(
                Finding(
                    file=r["file"],
                    line=r["start"],
                    category="class_metrics",
                    severity="low",
                    description=(
                        f"class={r['class']} lines={r['lines']} "
                        f"methods={r['methods']} public={r['public']} "
                        f"attrs={r['attrs']} start={r['start']} end={r['end']}"
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
        ClassMetricsScanner._ensure_python_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:
            return []
        module = engine.parse_module(path)
        return ClassMetricsScanner.scan_module(module)

    @staticmethod
    def main() -> int:
        """Entry point for the class metrics scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Scan Python source for class metrics (God class triage). "
            "Roots and thresholds come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        ClassMetricsScanner._ensure_python_engine()
        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_class_metrics")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(args.json, "check_class_metrics disabled in settings.json")
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, py_langs))
        if not roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1

        # Thresholds: smallest configured min_lines wins (reports more classes);
        # largest configured top wins (shows more rows).
        min_lines_limits: list[int] = []
        top_limits: list[int] = []
        for lang in sorted(py_langs):
            ml = ProjectConfig.setting(settings, f"{lang}.patterns.class_metrics_min_lines", None)
            if isinstance(ml, int) and not isinstance(ml, bool):
                min_lines_limits.append(ml)
            tp = ProjectConfig.setting(settings, f"{lang}.patterns.class_metrics_top", None)
            if isinstance(tp, int) and not isinstance(tp, bool):
                top_limits.append(tp)
        min_lines = min(min_lines_limits) if min_lines_limits else 50
        top_n = max(top_limits) if top_limits else 30

        all_results: list[dict[str, Any]] = []
        for root in roots:
            for py in ProjectConfig.iter_files(root, {".py"}):
                engine = EngineRegistry.get_for_file(py)
                if engine is None:  # pragma: no cover
                    continue
                module = engine.parse_module(py)
                all_results.extend(ClassMetricsScanner._class_metrics(module))

        if not all_results:
            print("No classes found", file=sys.stderr)
            return 0

        filtered = [r for r in all_results if r["lines"] >= min_lines]
        filtered.sort(key=lambda r: r["lines"], reverse=True)
        top = filtered[:top_n]

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "top": top_n,
                        "min_lines": min_lines,
                        "total_classes": len(all_results),
                        "classes": top,
                    },
                    indent=2,
                )
            )
            return 0

        print(f"{'LINES':>6} {'ALL':>4} {'PUB':>4} {'ATTRS':>5}  CLASS  (file:start-end)")
        print("-" * 110)
        for r in top:
            print(
                f"{r['lines']:>6} {r['methods']:>4} {r['public']:>4} {r['attrs']:>5}  "
                f"{r['class']}  ({r['file']}:{r['start']}-{r['end']})"
            )

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(ClassMetricsScanner.main())
